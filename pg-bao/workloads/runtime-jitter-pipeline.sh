#!/bin/bash

# default argument values
REPETITIONS=5
CACHE_OPT=""
ITERATIONS=3

# parse provided command line args
while [[ $# -gt 0 ]] ; do
	case $1 in
		-r|--repetitions)
			REPETITIONS="$2"
			shift
			shift
			;;
		--no-cache)
			CACHE_OPT="--no-cache"
			shift
			;;
		-i|--iterations)
			ITERATIONS="$2"
			shift
			shift
			;;
	esac
done

if [ "$1" = "--repetitions" ] ; then
	REPETITIONS="$2"
else
	REPETITIONS=5
fi

for ((run = 1; run <= $REPETITIONS ; run++))
do
	echo "Run $run"
	echo ".. Running workload"
	# we need to explicitly use the UNIX utility here, to prevent the bash-builtin tool from shadowing it
	/usr/bin/time --append -f "$(date -u +%s),$run,%E" -o workloads/timing$1.csv workloads/run-job-workload-full-train.sh --dummy --repetitions $ITERATIONS $CACHE_OPT
done

