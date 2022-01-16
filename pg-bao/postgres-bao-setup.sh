#!/bin/sh

echo ".. Cloning Postgres 12"
git clone --depth 1 --branch REL_12_8 https://github.com/postgres/postgres.git postgres-bao
cd postgres-bao

echo ".. Downloading BAO for Postgres 12"
git clone --depth 1 https://github.com/learnedsystems/BaoForPostgreSQL contrib/bao
patch contrib/bao/pg_extension/Makefile < ../pg-bao-makefile.patch

echo ".. Building Postgres"
./configure --prefix=$(pwd)/build
make clean && make && make install

echo ".. Installing BAO extension for Postgres"
cd contrib/bao/pg_extension
make USE_PGXS=1 install

