#!/bin/bash

REPETITIONS=3

echo "Resetting current BAO model"
./postgres-bao-ctl.py --reset-bao

for ((run=1 ; run <= $REPETITIONS ; run++))
do
	echo "Run $run"
	echo ".. Running workload"
	if [ "$1" = "--dummy" ]
	then
		OUT_FILE=/dev/null
		LOG_FILE=/dev/null
		TIM_FILE=/dev/null
	else
		OUT_FILE=workloads/job-full-train-run$run.out
		LOG_FILE=workloads/job-full-train-run$run.log
		TIM_FILE=workloads/job-full-train-timing-run$run.csv
	fi
	./postgres-bao-ctl.py --run-workload --workload workloads/job-full.sql -o $OUT_FILE 2>$LOG_FILE
	echo ".. Retraining model"
	./postgres-bao-ctl.py --retrain-bao --timing --timing-out $TIM_FILE
done
