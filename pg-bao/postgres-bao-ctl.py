#!/usr/bin/env python3

import argparse
import functools
import getpass
import json
import os
import signal
import sys
from typing import Any, Dict, List

import numpy as np
import psycopg2 as pg

SELECT_QUERY_PREFIX = "select"
EXPLAIN_QUERY_PREFIX = "explain"
COMMENT_PREFIX = "--"

BAO_NUM_ARMS = int(os.environ.get("BAO_NUM_ARMS", 5))


def message(*contents: str) -> None:
    print(*contents, file=sys.stderr)


def is_workload_query(query: str) -> bool:
    normalized = query.lower()
    return normalized.startswith(SELECT_QUERY_PREFIX) or normalized.startswith(EXPLAIN_QUERY_PREFIX)


def simplify_query(query: str) -> str:
    if not is_workload_query(query):
        return query

    select_stmt_idx = query.lower().find(SELECT_QUERY_PREFIX)
    if select_stmt_idx >= 0:
        return query[select_stmt_idx:]
    else:
        # query is already simplified
        return query


class BaoQuery:
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
    def __init__(self, cursor: "pg.cursor"):
        self.cursor = cursor

    def on(self, planning=True, learning=True) -> None:
        self.cursor.execute("SET enable_bao='on'")
        self.cursor.execute("SET enable_bao_rewards='on'")
        self.cursor.execute("SET enable_bao_selection='on'")
        self.cursor.execute(f"SET bao_num_arms={BAO_NUM_ARMS}")

    def off(self) -> None:
        self.cursor.execute("SET enable_bao='off'")

    def no_selection(self) -> None:
        self.on(planning=False)

    def no_learning(self) -> None:
        self.on(learning=False)


def read_raw_workload(workload: str) -> List[str]:
    contents = []
    with open(workload, "r") as workload_file:
        contents = workload_file.readlines()

    return [query for query in contents if not query.startswith(COMMENT_PREFIX)]


def execute_single_query(cursor: "pg.cursor", query: str, workload=True) -> Any:
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

    bao_ctl.on()
    bao_query.run(cursor)

    bao_ctl.no_learning()
    return json.dumps(bao_query.run_analyze(cursor))


def bao_retrain():
    os.system("""cd bao/bao_server && CUDA_VISIBLE_DEVICES="" python3 baoctl.py --retrain""")
    os.system("sync")


def bao_reset():
    os.system("./postgres-bao-shutdown.sh")
    os.system("rm bao/bao_server/bao.db")
    os.system("rm -rf bao/bao_server/bao_*_model")
    os.system("./postgres-bao-start.sh")


def run_workload_chunked(workload: List[str], *, conn: "pg.connection", chunk_size: int) -> List[str]:
    # when executing a workload in chunks (i.e. with retraining bao every N queries), we need to make
    # sure that the chunks do not consist of "meta-queries" (i.e. queries that modify the postgres behaviour rather
    # than EXPLAINing or SELECTing). Therefore we split the workload into segments of query chunks and segments of
    # meta statements, all while retaining the original query execution order.
    cursor = conn.cursor()

    # first up, insert retraining actions into the workload
    action_workload = []
    current_chunk_size = 0
    for query in workload:
        if current_chunk_size == chunk_size:
            action_workload.append((False, bao_retrain))
            current_chunk_size = 0

        if is_workload_query(query):
            action_workload.append((query, functools.partial(execute_single_query, cursor, query)))
            current_chunk_size += 1
        else:
            action_workload.append((query, functools.partial(execute_single_query, cursor, query, False)))

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


def main():
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
    parser.add_argument("--output", "-o", action="store",
                        help="File to write the workload results to.")
    parser.add_argument("--pg-connect", "-c", metavar="connect", action="store", help="Custom Postgres connect string")

    signal.signal(signal.SIGINT, lambda: sys.exit(1))

    args = parser.parse_args()
    if not (args.run_workload or args.retrain_bao or args.reset_bao):
        parser.error(
            "No action given, use either --run-workload, --reset-bao, or --retrain-bao")
    if args.run_workload and not args.workload:
        parser.error(
            "No workload given. Use --workload to specify the source file.")

    pg_connect = args.pg_connect if args.pg_connect else "dbname=imdb user={u} host=localhost".format(u=getpass.getuser())
    postgres = pg.connect(pg_connect)
    result_writer = functools.partial(write_results_file, out=args.output) if args.output else write_results_stdout

    if args.run_workload:
        workload = read_raw_workload(args.workload)
        results = []
        if args.retrain >= 0:
            results = run_workload_chunked(workload, conn=postgres, chunk_size=args.retrain)
        elif args.run_workload:
            results = run_workload_chunked(workload, conn=postgres, chunk_size=np.inf)
        result_writer(results)
    elif args.retrain_bao:
        bao_retrain()
    elif args.reset_bao:
        bao_reset()
    else:
        raise ValueError("Unknown action given. This is a bug!")

    postgres.close()


if __name__ == "__main__":
    main()
