#!/bin/bash

REPETITIONS=3

./postgres-bao-ctl.py --reset-bao

for ((run=1 ; run <= $REPETITIONS ; run++))
do
	echo "Run $run"
	echo ".. Running workload"
	./postgres-bao-ctl.py --run-workload --workload workloads/job-full.sql -o workloads/job-full-run$run.out 2>job-full-run$run.log
	echo ".. Retraining model"
	./postgres-bao-ctl.py --retrain-bao
done
