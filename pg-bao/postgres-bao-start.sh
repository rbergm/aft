#!/bin/sh

if [ -f .bao_server.pid ]
then
	echo "ERROR: BAO Server appears to be running already (file .bao_server.pid exists)"
	exit 1
fi

echo ".. Starting BAO Server"
WD=$(pwd)
cd postgres-bao/contrib/bao/
. bao-venv/bin/activate
cd bao_server
CUDA_VISIBLE_DEVICES="" python3 main.py > $WD/bao_server.log 2>&1 &
BAO_PID=$!
echo $BAO_PID > $WD/.bao_server.pid
echo ".. BAO Server started, running on PID $BAO_PID"
sleep 2
cd $WD

echo ".. Starting Postgres Server"
cd postgres-bao

if [ "$1" != "--no-env" ] ; then
	LD_LIBRARY_PATH=$(pwd)/build/lib:$LD_LIBRARY_PATH
	export LD_LIBRARY_PATH

	PATH=$(pwd)/build/bin:$PATH
	export PATH
fi

pg_ctl -D $(pwd)/build/data -l pg.log start
echo ".. Postgres Server started"
