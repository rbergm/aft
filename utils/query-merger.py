#!/usr/bin/env python3

import argparse
import pathlib
import sys
from typing import List


def read_queries(source_dir: str, *, query_pattern="[0-9]*sql") -> List[str]:
    if not query_pattern:
        query_pattern = "[0-9]*sql"

    source_path = pathlib.Path(source_dir)
    queries = source_path.glob(query_pattern)

    contents = []
    for query_file in queries:
        with query_file.open("r") as query:
            query_content = " ".join([line.strip() for line in query.readlines()])
            contents.append("explain (analyze, format json) " + query_content + "\n")

    return contents


def write_queries(queries: List[str], outfile: str, *, prefix="", suffix="", include_preamble=True) -> None:
    preamble = "-- Generated by `" + " ".join(sys.argv) + "`\n" if include_preamble else ""
    effective_output = [preamble]
    if prefix:
        effective_output.append(prefix + "\n")
    effective_output.extend(queries)
    if suffix:
        effective_output.append(suffix + "\n")
    with open(outfile, mode="w") as out_writer:
        out_writer.writelines(effective_output)


def main():
    parser = argparse.ArgumentParser(description = "Utility to create SQL batches from individual queries")
    parser.add_argument("source_dir", action="store", help="Directory containing the source queries")
    parser.add_argument("out_file", action="store", help="Name of the output file")
    parser.add_argument("--prefix", action="store", required=False, default="", help="Prefix (e.g. query) to insert before the first real query")
    parser.add_argument("--suffix", action="store", required=False, default="", help="Suffix (e.g. query) to insert after the last query")
    parser.add_argument("--pattern", action="store", required=False, default="", help="Glob-pattern matching the source file names")

    args = parser.parse_args()
    queries = read_queries(args.source_dir, query_pattern=args.pattern)
    write_queries(queries, args.out_file, prefix=args.prefix, suffix=args.suffix)


if __name__ == "__main__":
    main()
