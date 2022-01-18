#!/bin/sh

WD=$(pwd)
cd postgres-bao/contrib/bao/
. bao-venv/bin/activate
cd bao_server
python3 main.py > $WD/bao_server.log &
echo $! > $WD/.bao_server.pid
