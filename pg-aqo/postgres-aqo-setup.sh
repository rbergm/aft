#!/bin/sh

echo ".. Cloning Postgres 12"
git clone --depth 1 --branch REL_12_8 https://github.com/postgres/postgres.git .

echo ".. Downloading AQO patch for Postgres 12"
git clone --depth 1 --branch stable12 https://github.com/postgrespro/aqo.git contrib/aqo

patch -p1 --no-backup-if-mismatch < contrib/aqo/aqo_pg12.patch

echo ".. Building Postgres"
./configure --prefix=$(pwd)/build
make clean && make && make install

echo ".. Building AQO extension"
cd contrib/aqo
make && make install

echo ".. Checking installation"
make check

