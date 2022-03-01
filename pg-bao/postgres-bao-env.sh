#!/bin/bash

WD=$(pwd)
. $WD/bao/bao-venv/bin/activate

export PATH=$WD/postgres-bao/build/bin:$PATH

cd ..
export PATH=$(pwd)/utils:$PATH
cd $WD

