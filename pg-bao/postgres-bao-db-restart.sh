#!/bin/sh

cd postgres-bao
echo ".. Stopping Postgres server"
pg_ctl -D build/data stop
echo ".. Starting Postgres server"
pg_ctl -D build/data -l pg.log start 

