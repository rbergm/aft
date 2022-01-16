#!/bin/sh

cd postgres-bao/contrib/bao/
. bao-venv/bin/activate
cd bao_server
python3 main.py | tee ../bao_server.log

