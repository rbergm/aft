#!/usr/bin/env python3

import argparse
from typing import List

COMMENT_PREFIX = "--"
QUERY_PLAN = "QUERY PLAN"
QUERY_PLAN_START = '"['
QUERY_PLAN_END = ']"'


def read_dirty(file: str) -> List[str]:
    lines = []
    with open(file, "r") as contents:
        lines = contents.readlines()
    return lines


def clean_results(contents: List[str]) -> List[str]:

    # drop all comments
    cleaned = [
        line for line in contents if not line.startswith(COMMENT_PREFIX)]

    # drop all statements before the first actual query plan
    while not cleaned[0].startswith(QUERY_PLAN) and not cleaned[0].startswith(QUERY_PLAN_START):
        cleaned.pop(0)

    # drop all statements after the last actual query plan
    while not cleaned[-1].startswith(QUERY_PLAN_END):
        cleaned.pop(-1)

    return cleaned


def write_cleaned(contents: List[str], out: str) -> None:
    with open(out, "w") as file:
        file.writelines(contents)


def main():
    parser = argparse.ArgumentParser(
        description="Utility to strip unnecessary information from batch query result files.")
    parser.add_argument("input", action="store",
                        help="Input file containing the (dirty) batch results")
    parser.add_argument("out", action="store",
                        help="File to write the cleaned output to.")

    args = parser.parse_args()
    contents = read_dirty(args.input)
    cleaned = clean_results(contents)
    write_cleaned(cleaned, args.out)


if __name__ == "__main__":
    main()
