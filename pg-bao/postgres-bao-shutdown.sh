#!/bin/sh

echo ".. Stopping Postgres Server"
pg_ctl -D $(pwd)/postgres-bao/build/data stop

if [ ! -f .bao_server.pid ]
then
    echo "ERROR: .bao_server.pid not found. Need to stop BAO server manually"
    exit 1
fi

echo ".. Stopping BAO Server"
PID=$(cat .bao_server.pid)

echo "Killing server with PID $PID"
/bin/kill -INT $PID
rm .bao_server.pid
