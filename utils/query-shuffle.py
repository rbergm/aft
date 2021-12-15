#!/usr/bin/env python3

import argparse
import random
from typing import List

def permute_queries(queries: List[str]) -> List[str]:
    return random.sample(queries, k=len(queries))

def read_queries(filename: str) -> List[str]:
    queries = []
    with open(filename, mode="r") as query_file:
        queries = query_file.readlines()
    return queries

def write_queries(queries: List[str], outfile: str, prefix="", suffix="") -> None:
    effective_output = []
    if prefix:
        effective_output.append(prefix + "\n")
    effective_output.extend(queries)
    if suffix:
        effective_output.append(suffix + "\n")
    with open(outfile, mode="w") as out_writer:
        out_writer.writelines(effective_output)

def main():
    parser = argparse.ArgumentParser(description = "Utility to create permutations of a sequence of SQL queries.")
    parser.add_argument("file", action="store", help="File containing the SQL queries (one per line)")
    parser.add_argument("out", action="store", help="Name of the output file")
    parser.add_argument("--prefix", action="store", required=False, default="", help="Prefix (e.g. query) to insert before the first real query")
    parser.add_argument("--suffix", action="store", required=False, default="", help="Suffix (e.g. query) to insert after the last query")

    args = parser.parse_args()
    queries = read_queries(args.file)
    permuted = permute_queries(queries)
    write_queries(permuted, args.out, prefix=args.prefix, suffix=args.suffix)

if __name__ == "__main__":
    main()
