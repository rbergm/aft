#!/usr/bin/env python3

import argparse
import json
import logging
import pathlib
import re
import string
from typing import Any, Dict, List

import pandas as pd


def read_query_plans_psql(file: str) -> List[Any]:
    raw_plans = []
    with open(file, "r") as query_file:
        raw_plans = query_file.read()
    raw_plans = raw_plans.split("QUERY PLAN")[1:]

    # remove all trailing/leading whitespace from the queries and remove all
    # occurences of double-double quotes ("") due to json/csv escaping
    raw_plans = [qp.strip(string.whitespace + '"').replace('""', '"') for qp in raw_plans]

    plans = [json.loads(qp) for qp in raw_plans]
    return plans


def read_query_plans_bao(file: str) -> List[Any]:
    raw_plans = []
    with open(file, "r") as query_file:
        raw_plans = query_file.readlines()

    plans = []
    for qp in raw_plans:
        parsed_plan = json.loads(qp)

        # the first entry in the EXPLAIN ANALYZE output is the BAO output,
        # the second entry the actual planner data.
        # We need to merge this into a single dict
        refactored_plan = list(parsed_plan)
        refactored_plan[1]["Bao"] = parsed_plan[0]["Bao"]
        del refactored_plan[0]
        plans.append(refactored_plan)
    return plans


class OperatorNode:
    def __init__(self, node_type, node_description, rows_processed, child_nodes=None):
        self.node_type = node_type
        self.node_description = node_description
        self.rows_processed = rows_processed
        self.child_nodes = child_nodes if child_nodes else []

    def cout(self) -> int:
        return self.rows_processed + sum(child.cout() for child in self.child_nodes)

    def __repr__(self):
        return str(self)

    def __str__(self):
        node_description = "{node} ({rows})".format(node=self.node_type, rows=self.rows_processed)
        if self.child_nodes:
            node_description += " <- (" + " + ".join(str(child) for child in self.child_nodes) + ")"
        return node_description


def is_join_node(node_type: str) -> bool:
    return any(join_node == node_type for join_node in ["Nested Loop", "Hash Join"])


def parse_query_plan(plan_node: List[Any]) -> OperatorNode:
    node_description = ""
    if is_join_node(plan_node["Node Type"]):
        node_description = plan_node.get("Join Filter", "")
    elif plan_node["Node Type"].endswith("Scan"):
        node_description = plan_node.get("Relation Name", "")
    else:
        logging.info("Unkown node type:", plan_node["Node Type"])

    rows_processed = 0
    if is_join_node(plan_node["Node Type"]):
        rows_processed = plan_node["Actual Rows"]

    node = OperatorNode(plan_node["Node Type"], node_description, rows_processed)

    node.child_nodes = [parse_query_plan(child) for child in plan_node.get("Plans", [])]

    return node


def drop_prefix(text: str, prefix: str) -> str:
    if text.startswith(prefix):
        return text[len(prefix):]
    else:
        return text


def read_queries(file: str) -> List[str]:
    queries = []
    with open(file, "r") as query_file:
        queries = query_file.readlines()
        queries = [drop_prefix(q, "explain (analyze, format json) ") for q in queries]
    return queries


def generate_dataframe(queries: List[str], operator_trees: List[OperatorNode], query_plans: List[Any], source_labels: Dict[str, str]) -> pd.DataFrame:
    cout_values = [opt.cout() for opt in operator_trees]
    serialized_plans = [json.dumps(qp) for qp in query_plans]
    exec_times = [qp[0]["Execution Time"] for qp in query_plans]
    plan_times = [qp[0]["Planning Time"] for qp in query_plans]
    
    columns = {"query": queries, "cout": cout_values, "plan": serialized_plans, "t_exec": exec_times, "t_plan": plan_times}
    if source_labels:
        columns["label"] = source_labels

    df = pd.DataFrame(columns)
    return df


def normalize_query(query: str) -> str:
    return re.sub(r"\s", "", query).lower()


def read_query_sources(source_dir: str, query_pattern="") -> Dict[str, str]:
    if not query_pattern:
        query_pattern = "[0-9]*sql"

    source_path = pathlib.Path(source_dir)
    queries = source_path.glob(query_pattern)

    contents = {}
    for query_file in queries:
        with query_file.open("r") as query:
            query_content = " ".join([line.strip() for line in query.readlines()])
            query_content = normalize_query(query_content)
            contents[query_content] = query_file.stem
    
    return contents


def main():
    parser = argparse.ArgumentParser(description="Utility to calculate C_out values from batches of EXPLAIN ANALYZE queries")
    parser.add_argument("--plans", "-p", action="store", help="File containing the EXPLAIN ANALYZE output", required=True)
    parser.add_argument("--queries", "-q", action="store", help="File containing the actual queries", required=True)
    parser.add_argument("--out", "-o", action="store", help="Name of the output csv file", required=True)
    parser.add_argument("--sources", "-s", action="store", help="Directory containing the raw query files (before merging), file names will be used as labels", required=False, default="")
    parser.add_argument("--mode", "-m", action="store", choices=["psql", "bao"], default="psql", help="Description of the EXPLAIN ANALYZE format. 'psql' indicates that the results were obtained directly from psql, using CSV output, which makes a lot of cleanup necessary. If set to 'bao', the output was obtained from a BAO instance directly via the psycopg2 interface, resulting in a different cleanup. Defaults to 'psql'.")

    args = parser.parse_args()
    plans = read_query_plans_psql(args.plans) if args.mode == "psql" else read_query_plans_bao(args.plans)
    operator_trees = [parse_query_plan(p[0]["Plan"]) for p in plans]
    queries = read_queries(args.queries)

    sources = []
    if (args.sources):
        labels_map = read_query_sources(args.sources)
        sources = [labels_map.get(normalize_query(q), "") for q in queries]

    df = generate_dataframe(queries, operator_trees, plans, sources)
    df.to_csv(args.out, index=False)


if __name__ == "__main__":
    main()
