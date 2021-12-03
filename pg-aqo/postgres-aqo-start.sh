#!/bin/sh

cd postgres-aqo
LD_LIBRARY_PATH=$(pwd)/build/lib:$LD_LIBRARY_PATH
export LD_LIBRARY_PATH

PATH=$(pwd)/build/bin:$PATH
export PATH

pg_ctl -D $(pwd)/build/data -l pg.log start
