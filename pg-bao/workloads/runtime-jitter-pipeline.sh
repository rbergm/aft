#!/bin/bash

trap "exit" INT

# default argument values
REPETITIONS=5
CACHE_OPT=""
ITERATIONS=3
TIMING_SUFFIX="-full-train"
DEBUG_OPT=""

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
			TIMING_SUFFIX="-full-train-no-cache"
			shift
			;;
		-i|--iterations)
			ITERATIONS="$2"
			shift
			shift
			;;
		--debug)
			DEBUG_OPT="--debug"
			shift
			;;
	esac
done

for ((run = 1; run <= $REPETITIONS ; run++))
do
	echo "Run $run"
	echo ".. Running workload"
	# we need to explicitly use the UNIX utility here, to prevent the bash-builtin tool from shadowing it
	/usr/bin/time --append -f "$(date -u +%s),$run,%E" -o workloads/timing$TIMING_SUFFIX.csv workloads/run-job-workload-full-train.sh --dummy --repetitions $ITERATIONS $CACHE_OPT $DEBUG_OPT
done

