#!/bin/sh

cd postgres-bao
LD_LIBRARY_PATH=$(pwd)/build/lib:$LD_LIBRARY_PATH
export LD_LIBRARY_PATH

PATH=$(pwd)/build/bin:$PATH
export PATH

echo ".. Creating cluster"
initdb -D $(pwd)/build/data

echo ".. Starting Postgres"
pg_ctl -D $(pwd)/build/data -l pg.log start

echo ".. Creating user database for $USER"
createdb $(whoami)

echo ".. Setting up BAO"
echo "shared_preload_libraries = 'pg_bao'" >> $(pwd)/build/data/postgresql.conf
sed -i "s/^shared_buffers.*/shared_buffers = 12GB/" $(pwd)/build/data/postgresql.conf

echo ".. Restarting to apply changes"
pg_ctl restart -D $(pwd)/build/data

echo ".. Done, Ready to connect"
