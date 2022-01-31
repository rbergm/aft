#!/bin/bash

REPETITIONS=3

echo "Resetting current BAO model"
./postgres-bao-ctl.py --reset-bao

for ((run=1 ; run <= $REPETITIONS ; run++))
do
	echo "Run $run"
	echo ".. Running workload"
	./postgres-bao-ctl.py --run-workload --workload workloads/job-full.sql -o workloads/job-small-train-run$run.out --training-fraction 0.3 --training-out workloads/job-small-train-samples-run$run.csv 2>job-small-train-run$run.log
	echo ".. Retraining model"
	./postgres-bao-ctl.py --retrain-bao --timing --timing-out workloads/job-small-train-timing-run$run.csv
done
