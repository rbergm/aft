#!/usr/bin/env python3

import argparse
import os
import pathlib
import textwrap


def load_online(out: str, source="http://homepages.cwi.nl/~boncz/job/imdb.tgz") -> None:
    print(".. Downloading data set")
    os.system("wget --output-document imdb_temp {source}".format(source=source, out=out))
    os.makedirs(out, exist_ok=True)
    print(".. Unpacking data")
    os.system("tar xvf imdb_temp --directory {out}".format(out=out))
    os.system("rm imdb_temp")
    print(".. Download done")


def postgres_setup(source_dir: str) -> None:
    print(".. Creating database")
    os.system("createdb imdb")
    os.system("psql imdb -f {wdir}/schematext.sql".format(wdir=source_dir))

    source_path = pathlib.Path(source_dir)
    data_files = source_path.glob("*.csv")
    for data_file in data_files:
        print(".. Now importing", data_file)
        table = data_file.stem
        os.system("""psql imdb -c "\copy {table} from {source} with csv quote '\\"' escape '\\';" """.format(table=table, source=data_file))

def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=textwrap.dedent("""\
        Utility to create IMDB database instances for PostgreSQL

        When running this script, the PostgreSQL server has to be running and accessible via the `psql` command. Furthermore, utilities
        such as `createdb` have to be on the PATH as well."""))
    arg_grp = parser.add_mutually_exclusive_group()
    arg_grp.add_argument("--online", action="store_true", help="If set, download the IMDB data set")
    arg_grp.add_argument("--source", action="store", help="Directory to load the raw IMDB data set from")
    parser.add_argument("--target", action="store", default="imdb", help="Directory to store the raw IMDB data in, if downloading from network")

    args = parser.parse_args()

    source_dir = ""
    if args.online:
        load_online(args.target)
        source_dir = args.target
    elif args.source:
        source_dir = args.source

    postgres_setup(source_dir)


if __name__ == "__main__":
    main()
