#!/bin/sh

echo ".. Starting BAO Server"
WD=$(pwd)
cd postgres-bao/contrib/bao/
. bao-venv/bin/activate
cd bao_server
python3 main.py > $WD/bao_server.log &
echo $! > $WD/.bao_server.pid
echo ".. BAO Server started"

echo ".. Starting Postgres Server"
cd postgres-aqo
LD_LIBRARY_PATH=$(pwd)/build/lib:$LD_LIBRARY_PATH
export LD_LIBRARY_PATH

PATH=$(pwd)/build/bin:$PATH
export PATH

pg_ctl -D $(pwd)/build/data -l pg.log start
echo ".. Postgres Server started"
