#!/bin/sh

echo ".. Stopping Postgres Server"
pg_ctl -D $(pwd)/postgres-bao/build/data stop

echo "Stopping BAO Server"
PID=$(cat .bao_server.pid)

echo "Killing server with PID $PID"
kill -INT $PID
rm .bao_server.pid
