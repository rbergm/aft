#!/usr/bin/env python3

import argparse
import functools
import getpass
import json
import math
import os
import random
import signal
import sys
import timeit
import warnings
from typing import Any, Dict, List, Tuple, Union

import numpy as np
import pandas as pd
import psycopg2 as pg

SELECT_QUERY_PREFIX = "select"
EXPLAIN_QUERY_PREFIX = "explain"
COMMENT_PREFIX = "--"

BAO_NUM_ARMS = int(os.environ.get("BAO_NUM_ARMS", 5))

QUIET = False


def message(*contents: str) -> None:
    """print for stderr."""
    global QUIET

    if QUIET:
        return
    print(*contents, file=sys.stderr)


def is_workload_query(query: str) -> bool:
    normalized = query.lower()
    return normalized.startswith(SELECT_QUERY_PREFIX) or normalized.startswith(EXPLAIN_QUERY_PREFIX)


def simplify_query(query: str) -> str:
    """Deletes all leading statements of a query up to the first SELECT statement (e.g. EXPLAIN)."""
    if not is_workload_query(query):
        return query

    select_stmt_idx = query.lower().find(SELECT_QUERY_PREFIX)
    if select_stmt_idx >= 0:
        return query[select_stmt_idx:]
    else:
        # query is already simplified
        return query


class BaoQuery:
    """Provides a number of utilities to conveniently run SQL queries on BAO instances."""
    def __init__(self, query: str):
        simplified = simplify_query(query)
        self.pure_query = simplified
        self.explain_query = "EXPLAIN (ANALYZE, FORMAT JSON) " + simplified

    def query(self) -> str:
        return self.pure_query

    def explain(self) -> str:
        return self.explain_query

    def run(self, cursor: "pg.cursor") -> None:
        cursor.execute(self.pure_query)

    def run_analyze(self, cursor: "pg.cursor") -> Dict[Any, Any]:
        cursor.execute(self.explain_query)
        return cursor.fetchone()[0]


class BaoCtl:
    """Enables control of the BAO training/planning mode."""
    def __init__(self, cursor: "pg.cursor"):
        self.cursor = cursor

    def on(self, planning=True, learning=True) -> None:
        """Enables BAO according to the parameters given."""
        selection = 'on' if planning else 'off'
        rewards = 'on' if learning else 'off'
        self.cursor.execute("SET enable_bao='on'")
        self.cursor.execute(f"SET enable_bao_rewards='{rewards}'")
        self.cursor.execute(f"SET enable_bao_selection='{selection}'")
        self.cursor.execute(f"SET bao_num_arms={BAO_NUM_ARMS}")

    def off(self) -> None:
        """Disables BAO."""
        self.cursor.execute("SET enable_bao='off'")

    def no_selection(self) -> None:
        """Disables BAO planning (i.e. only the Postgres optimizer runs), leaving everything else on."""
        self.on(planning=False)

    def no_learning(self) -> None:
        """Disables BAO learning (i.e. executed queries are not used to improve the BAO model), leaving everything else on."""
        self.on(learning=False)


def read_raw_workload(workload: str) -> List[str]:
    contents = []
    with open(workload, "r") as workload_file:
        contents = workload_file.readlines()

    return [query for query in contents if not query.startswith(COMMENT_PREFIX)]


def read_queries_for_training(workload: List[str], src: str) -> List[Tuple[str, bool]]:
    training_df = pd.read_csv(src)
    workload_df = pd.DataFrame({"query": workload})
    merged_df = workload_df.merge(training_df, how="left")
    if merged_df.training.isna().any():
        missing_count = merged_df.training.isna().sum()
        warnings.warn(f"Could not completely reconstruct training information. Excluding missing queries from training. {missing_count} queries affected.")
        merged_df.training.fillna(value=False, inplace=True)
    return list(zip(merged_df["query"], merged_df.training))


def select_queries_for_training(workload: List[str], training_fraction: float) -> List[Tuple[str, bool]]:
    """Chooses a fraction of the workload queries for training, annotating each query accordingly."""
    n_queries = len(workload)
    num_training_queries = math.ceil(training_fraction * n_queries)
    training_idx = random.sample(range(n_queries), k=num_training_queries)
    query_idx = np.full(n_queries, fill_value=False, dtype=bool)
    query_idx[training_idx] = True
    annotated_queries = zip(workload, query_idx)
    return list(annotated_queries)


def execute_single_query(cursor: "pg.cursor", query: str, *, workload=True, for_training=True) -> Any:
    """Runs a query, leveraging BAO functionality."""
    if not workload:
        cursor.execute(query)
        return

    # At this point, we need to run a workload query. Since BAO appears to be
    # unable to learn from EXPLAIN ANALYZE queries, but we are mainly interested
    # in the query plans, we need to execute the query twice:
    # The first execution runs the query "as is" with BAO enabled, to enable it
    # to learn from the query. The second execution is the actual EXPLAIN
    # ANALYZE RUN with learning disabled (just to be sure).
    bao_ctl = BaoCtl(cursor)
    bao_query = BaoQuery(query)

    bao_ctl.on(learning=for_training)
    bao_query.run(cursor)

    bao_ctl.no_learning()
    return json.dumps(bao_query.run_analyze(cursor))


def bao_retrain():
    global QUIET
    quiet = "> /dev/null 2>&1" if QUIET else ""
    os.system(f"""cd bao/bao_server && CUDA_VISIBLE_DEVICES="" python3 baoctl.py --retrain {quiet}""")
    os.system("sync")


def bao_reset():
    global QUIET
    quiet = "> /dev/null" if QUIET else ""
    os.system(f"./postgres-bao-shutdown.sh {quiet}")
    os.system("rm bao/bao_server/bao.db")
    os.system("rm -rf bao/bao_server/bao_*_model")
    os.system(f"./postgres-bao-start.sh --no-env {quiet}")


def run_workload_chunked(workload: Union[List[str], List[Tuple[str, bool]]], *, conn: "pg.connection", training_chunk_size: int) -> List[str]:
    """Executes a given workload on the BAO instance."""

    # when executing a workload in chunks (i.e. with retraining bao every N queries), we need to make
    # sure that the chunks do not consist of "meta-queries" (i.e. queries that modify the postgres behaviour rather
    # than EXPLAINing or SELECTing). Therefore we split the workload into segments of query chunks and segments of
    # meta statements, all while retaining the original query execution order.
    if not workload:
        return []

    # each query should be annotated by whether it should be used for BAO training. If this not the case already,
    # we assume the missing queries to  be suited for training
    workload = list(map(lambda query: query if type(query) == tuple else (query, True), workload))

    cursor = conn.cursor()

    # first up, insert retraining actions into the workload
    action_workload = []
    current_chunk_size = 0
    for query, use_for_training in workload:

        # if our current chunk of training queries is full, we insert a training action
        if current_chunk_size == training_chunk_size:
            action_workload.append((False, bao_retrain))  # False indicates no specific description
            current_chunk_size = 0

        if is_workload_query(query):
            # workload queries can potentially influence the training set and require updating of the current
            # training chunk
            action = functools.partial(execute_single_query, cursor, query, for_training=use_for_training)
            action_workload.append((query, action))

            # if the query should be used for training, we update the size of the training chunk
            if use_for_training:
                current_chunk_size += 1
                message(f"Using query {query} for training")
        else:
            # non-workload queris (e.g. SET statements) are not considered as part of the training chunk
            action_workload.append((query, functools.partial(execute_single_query, cursor, query, workload=False)))

    # now, execute the actual workload
    results = []
    for description, action in action_workload:
        if description:
            message("Now running query", description)
        else:
            message("Retraining the model")
        results.append(action())

    return [res + "\n" for res in results if res is not None]


def write_results_file(results: List[str], out: str) -> None:
    with open(out, "w") as out_file:
        out_file.writelines(results)


def write_results_stdout(results: List[str]) -> None:
    for result in results:
        print(result, end="")


def write_runtime(args: argparse.Namespace, runtime: int) -> None:
    if args.run_workload:
        action = "workload"
    elif args.retrain_bao:
        action = "retrain"
    elif args.reset_bao:
        action = "reset"

    out_file = args.timing_out if args.timing_out else "bao-ctl-timing.csv"
    timing_df = pd.DataFrame({"action": [action], "runtime": [runtime]})
    timing_df.to_csv(out_file, index=False)


def write_training_status(workload: List[Tuple[str, bool]], out: str) -> None:
    training_df = pd.DataFrame(workload, columns=["query", "training"])
    training_df.to_csv(out, index=False)


def main():
    global QUIET

    parser = argparse.ArgumentParser(
        description="Utility to run an SQL workload and control the BAO server.")
    arg_grp = parser.add_mutually_exclusive_group()
    arg_grp.add_argument("--run-workload", action="store_true",
                         help="Run a specific workload on the BAO/Postgres instance. This enables both the learning, as well as the planning feature of BAO.")
    arg_grp.add_argument("--retrain-bao", action="store_true",
                         help="Don't run any workload, simply train the BAO model.")
    arg_grp.add_argument("--reset-bao", action="store_true", help="Delete everything BAO has learned so far. This will restart both Postgres, as well as the BAO server.")
    parser.add_argument("--workload", "-w", action="store",
                        help="File to load the workload from. Only used if --run-workload is set.")
    parser.add_argument("--retrain", "-r", metavar="N", action="store", type=int, default=-1,
                        help="Retrain the BAO model every N queries. Only used if --run-workload is set.")
    parser.add_argument("--training-fraction", action="store", type=float, help="Fraction of the workload queries to be used as training data. By default, all queries will be used for training.")
    parser.add_argument("--training-in", action="store", help="File to read which workload queries should be used for training. Has to have the same format as produced by --training-out.")
    parser.add_argument("--training-out", action="store", help="File to document which queries were used for training.")
    parser.add_argument("--output", "-o", action="store",
                        help="File to write the workload results to.")
    parser.add_argument("--pg-connect", "-c", metavar="connect", action="store", help="Custom Postgres connect string")
    parser.add_argument("--timing", "-t", action="store_true", help="Measure the execution time of this script")
    parser.add_argument("--timing-out", action="store", help="Write timing information to the given file")
    parser.add_argument("--quiet", "-q", action="store_true", help="Don't write messages to stderr.", default=False)

    args = parser.parse_args()
    if not (args.run_workload or args.retrain_bao or args.reset_bao):
        parser.error(
            "No action given, use either --run-workload, --reset-bao, or --retrain-bao")
    if args.run_workload and not args.workload:
        parser.error(
            "No workload given. Use --workload to specify the source file.")

    QUIET = args.quiet
    signal.signal(signal.SIGINT, lambda: sys.exit(1))

    if args.timing:
        start_time = timeit.default_timer()

    if args.run_workload:
        # workload execution may be influenced by a number of additional arguments, the actions will be applied accordingly

        # connect to the Postgres instance
        pg_connect = args.pg_connect if args.pg_connect else "dbname=imdb user={u} host=localhost".format(u=getpass.getuser())
        postgres = pg.connect(pg_connect)

        # prepare the workload
        workload = read_raw_workload(args.workload)
        if args.training_fraction and not args.training_in:
            workload = select_queries_for_training(workload, args.training_fraction)
        elif args.training_in:
            warnings.warn("Ignoring --training-fraction argument since source file was specified explicitly.")
            workload = read_queries_for_training(workload, args.training_in)

        # prepare the computation
        chunk_size = args.retrain if args.retrain >= 0 else np.inf
        results = []

        # the actual execution
        results = run_workload_chunked(workload, conn=postgres, training_chunk_size=chunk_size)

        # store results
        result_writer = functools.partial(write_results_file, out=args.output) if args.output else write_results_stdout
        result_writer(results)

        # store additional data
        if args.training_out:
            write_training_status(workload, args.training_out)

        # teardown
        postgres.close()
    elif args.retrain_bao:
        bao_retrain()
    elif args.reset_bao:
        bao_reset()
    else:
        raise ValueError("Unknown action given. This is a bug!")

    if args.timing:
        end_time = timeit.default_timer()
        runtime = math.floor((end_time - start_time) * 1000)
        if args.timing_out:
            write_runtime(args, runtime)
        else:
            print(runtime)


if __name__ == "__main__":
    main()
