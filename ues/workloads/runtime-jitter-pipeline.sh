#!/bin/bash

REPETITIONS=5

if [ -z "$1" ]
then
	echo "Setting mode to default implicit"
	MODE="implicit"
else
	MODE="$1"
fi

for ((run = 1; run <= $REPETITIONS ; run++))
do
	echo "Run $run"
	# we need to explicitly use the UNIX utility here, to prevent the bash-builtin tool from shadowing it
	/usr/bin/time --append -f "$(date -u +%s),$run,%E" -o workloads/timing-$MODE.csv ./ues-docker-run-sql.sh workloads/job-$MODE.sql /tmp/job-$MODE-run$run.out
done

