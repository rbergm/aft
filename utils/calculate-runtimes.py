#!/usr/bin/env python3

import argparse
import json
import pathlib

import pandas as pd


def read_batch(file: str) -> "pd.DataFrame":
    df = pd.read_csv(file)
    df.plan = df.plan.apply(json.loads)
    return df


def main():
    parser = argparse.ArgumentParser(description="Utility to quickly calculate SQL batch runtimes.")
    parser.add_argument("--dir", "-d", action="store", help="Directory containing the batch result CSV files")
    parser.add_argument("--file-prefix", "-p", action="store", help="File name pattern (suffix) for the result files. All matching files will be included.")
    parser.add_argument("--separator", "-s", action="store", default=": ", help="Output separator between file name and runtime")

    args = parser.parse_args()

    files_to_analyze = sorted(list(pathlib.Path(args.dir).glob(f"{args.file_prefix}*-cout.csv")))
    plans = [(file, read_batch(file)) for file in files_to_analyze]
    runtimes = [(file, plan.t_exec.sum()) for (file, plan) in plans]
    for file, rt in runtimes:
        print(f"{file}{args.separator}{rt}")


if __name__ == "__main__":
    main()
