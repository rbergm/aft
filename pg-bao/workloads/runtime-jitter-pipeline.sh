#!/bin/bash

REPETITIONS=5

for ((run = 1; run <= $REPETITIONS ; run++))
do
	echo "Run $run"
	echo ".. Running workload"
	# we need to explicitly use the UNIX utility here, to prevent the bash-builtin tool from shadowing it
	/usr/bin/time --append -f "$(date -u +%s),$run,%E" -o workloads/timing$1.csv workloads/run-job-workload-full-train.sh --dummy
done

