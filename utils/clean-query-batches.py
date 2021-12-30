#!/usr/bin/env python3

import argparse
from typing import List

COMMENT_PREFIX = "--"
SELECT_PREFIX = "select"
EXPLAIN_PREFIX = "explain"


def clean_from_file(input: str) -> List[str]:
    lines = []
    with open(input, "r") as file:
        lines = file.readlines()
    return [l for l in lines if l.startswith(SELECT_PREFIX) or l.startswith(EXPLAIN_PREFIX)]


def main():
    parser = argparse.ArgumentParser(description="Utility to drop all non-workload queries (i.e. not SELECT nor EXPLAIN) from a query batch file.")
    parser.add_argument("input", action="store", help="File containing the raw query batch.")
    parser.add_argument("out", action="store", help="File to write the cleaned output to.")

    args = parser.parse_args()
    cleaned = clean_from_file(args.input)
    with open(args.out, "w") as out_file:
        out_file.writelines(cleaned)


if __name__ == "__main__":
    main()
