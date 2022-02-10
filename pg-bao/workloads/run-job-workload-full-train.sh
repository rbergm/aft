#!/bin/bash

# default argument values
REPETITIONS=3
DUMMY=false
CLEAR_CACHE=false
RESET=true

# parse the provided arguments
while [[ $# -gt 0 ]] ; do
	case $1 in
		-r|--repetitions)
			REPETITIONS=$2
			echo "Running $REPETITIONS repetitions"
			shift
			shift
			;;
		--dummy)
			DUMMY=true
			shift
			;;
		--no-cache)
			CLEAR_CACHE=true
			shift
			;;
		--no-reset)
			RESET=false
			shift
			;;
	esac
done

if [ "$RESET" = true ] ; then
	echo "Resetting current BAO model"
	./postgres-bao-ctl.py --reset-bao
fi

if [ "$CLEAR_CACHE" = true ] ; then
	OUT_CACHE_SUFFIX="-no-cache"
else
	OUT_CACHE_SUFFIX=""
fi

for ((run=1 ; run <= $REPETITIONS ; run++))
do
	echo "Iteration $run"

	if [ "$CLEAR_CACHE" = true ] ; then
		echo ".. Clearing cache"
		./postgres-bao-shutdown.sh
		sync
		sudo sh -c "/bin/echo 3 > /proc/sys/vm/drop_caches"
		./postgres-bao-start.sh --no-env
	fi

	echo ".. Running workload"
	if [ "$DUMMY" = true ] ; then
		OUT_FILE=/dev/null
		LOG_FILE=/dev/null
		TIM_FILE=/dev/null
		QUIET="-q"
	else
		OUT_FILE=workloads/job-full-train$OUT_CACHE_SUFFIX-run$run.out
		LOG_FILE=workloads/job-full-train$OUT_CACHE_SUFFIX-run$run.log
		TIM_FILE=workloads/job-full-train$OUT_CACHE_SUFFIX-timing-run$run.csv
		QUIET=""
	fi

	./postgres-bao-ctl.py --run-workload --workload workloads/job-full.sql -o $OUT_FILE $QUIET 2>$LOG_FILE
	echo ".. Retraining model"
	./postgres-bao-ctl.py --retrain-bao --timing --timing-out $TIM_FILE
done
