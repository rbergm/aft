#!/bin/sh

WD=$(pwd)

echo ".. Cloning Postgres 12"
git clone --depth 1 --branch REL_12_8 https://github.com/postgres/postgres.git postgres-bao
cd postgres-bao

echo ".. Downloading BAO for Postgres 12"
git clone --depth 1 https://github.com/learnedsystems/BaoForPostgreSQL contrib/bao
patch contrib/bao/pg_extension/Makefile < ../pg-bao-makefile.patch
patch contrib/bao/bao_server/main.py < ../pg-bao-server.patch

echo ".. Building Postgres"
./configure --prefix=$(pwd)/build
make clean && make && make install
export PATH="$(pwd)/build/bin:$PATH"

echo ".. Installing BAO extension for Postgres"
cd contrib/bao/pg_extension
make USE_PGXS=1 install
cd ..

echo ".. Setting up BAO server"
echo "... Creating virtual environment for BAO under $(pwd)/bao-venv"
python3 -m venv bao-venv
. bao-venv/bin/activate
echo "... Installing dependencies"
pip3 install wheel scikit-learn numpy joblib torch psycopg2 pandas
echo "Configuring server"
sed -i "s/^PostgreSQLConnectString.*/PostgreSQLConnectString = dbname=imdb user=$USER host=localhost/" bao_server/bao.cfg

cd $WD
ln -s postgres-bao/contrib/bao/ bao
