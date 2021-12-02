#!/bin/sh

LD_LIBRARY_PATH=$(pwd)/build/lib:$LD_LIBRARY_PATH
export LD_LIBRARY_PATH

PATH=$(pwd)/build/bin:$PATH
export PATH

postgres -D $(pwd)/build/data >pg.log 2>&1 &
