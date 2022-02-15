#!/bin/sh

WD=$(pwd)
export PATH=$WD/postgres-bao/build/bin:$PATH

cd ..
export PATH=$(pwd)/utils:$PATH
cd $WD

. $WD/bao/bao-venv/bin/activate

