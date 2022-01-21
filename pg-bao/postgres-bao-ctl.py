#!/usr/bin/env python3

import argparse
import functools
import getpass
import json
import os
import sqlite3
from typing import Any, List

import psycopg2 as pg

SELECT_QUERY_PREFIX = "select"
EXPLAIN_QUERY_PREFIX = "explain"
COMMENT_PREFIX = "--"


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


def read_raw_workload(workload: str, *, simplify=False) -> List[str]:
    contents = []
    with open(workload, "r") as workload_file:
        contents = workload_file.readlines()

    without_comments = [query for query in contents if not query.startswith(COMMENT_PREFIX)]
    if simplify:
        return [simplify_query(query) for query in without_comments] if simplify else without_comments
    else:
        return without_comments


def execute_single_query(cursor: "pg.cursor", query: str, gather_results=True) -> Any:
    cursor.execute(query)
    if gather_results:
        return json.dumps(cursor.fetchall())


def bao_retrain():
    os.system("cd bao/bao_server && python3 baoctl.py --retrain")
    os.system("sync")


def bao_reset():
    conn = sqlite3.connect("bao/bao_server/bao.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM experience")
    conn.commit()
    os.system("rm -rf bao/bao_server/bao_*_model")


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
            action_workload.append(bao_retrain)
            current_chunk_size = 0

        if is_workload_query(query):
            action_workload.append(functools.partial(execute_single_query, cursor, query))
            current_chunk_size += 1
        else:
            action_workload.append(functools.partial(execute_single_query, cursor, query, False))

    # now, execute the actual workload
    results = []
    for action in action_workload:
        results.append(action())

    return [res + "\n" for res in results if res is not None]


def run_workload_complete(workload: List[str], *, conn: "pg.connection") -> List[str]:
    cursor = conn.cursor()
    results = []
    for query in workload:
        cursor.execute(query)
        if is_workload_query(query):
            results.append(json.dumps(cursor.fetchall()))
            results.append("")
    return [res + "\n" for res in results]


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
                         help="Run a specific workload on the BAO/Postgres instance. How the BAO features should used has to be specified in the workload file, e.g. via SET enable_bao='on';")
    arg_grp.add_argument("--retrain-bao", action="store_true",
                         help="Don't run any workload, simply train the BAO model.")
    arg_grp.add_argument("--reset-bao", action="store_true", help="Delete everything BAO has learned so far.")
    parser.add_argument("--workload", "-w", action="store",
                        help="File to load the workload from. Only used if --run-workload is set.")
    parser.add_argument("--retrain", "-r", metavar="N", action="store", type=int, default=-1,
                        help="Retrain the BAO model every N queries. Only used if --run-workload is set.")
    parser.add_argument("--output", "-o", action="store",
                        help="File to write the workload results to.")
    parser.add_argument("--pg-connect", "-c", metavar="connect", action="store", help="Custom Postgres connect string")
    parser.add_argument("--simplify", action="store_true", help="If set, don't run queries as EXPLAIN but only the actual query.")

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
        workload = read_raw_workload(args.workload, simplify=args.simplify)
        results = []
        if args.retrain >= 0:
            results = run_workload_chunked(workload, conn=postgres, chunk_size=args.retrain)
        elif args.run_workload:
            results = run_workload_complete(workload, conn=postgres)
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
