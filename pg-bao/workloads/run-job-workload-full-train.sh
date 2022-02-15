#!/bin/bash

trap "exit" INT

# default argument values
REPETITIONS=3
DUMMY=false
CLEAR_CACHE=false
RESET=true
WORKLOAD="workloads/job-full.sql"
DEBUG=false

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
		--debug)
			DEBUG=true
			WORKLOAD="workloads/job-test.sql"
			shift
			;;
	esac
done

if [ "$DEBUG" = true ] ; then
	echo "Debug mode is ACTIVE"
fi

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

	if [ "$DEBUG" = true ] ; then
		echo ".. Python processes currently running BEFORE iteration $run"
		ps -ux | grep python3
	fi

	if [ "$CLEAR_CACHE" = true ] ; then
		echo ".. Clearing cache"
		./postgres-bao-shutdown.sh
		sync
		drop-caches.bin
		./postgres-bao-start.sh --no-env
	fi

	if [ "$DEBUG" = true ] && [ "$CLEAR_CACHE" = true ] ; then
		echo ".. Python processes WITHIN iteration $run - after clearing cache"
		ps -ux | grep python3
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

	./postgres-bao-ctl.py --run-workload --workload $WORKLOAD -o $OUT_FILE $QUIET 2>$LOG_FILE

	if [ "$DEBUG" = true ] && [ "$CLEAR_CACHE" = true ] ; then
		echo ".. Python processes WITHIN iteration $run - after running workload"
		ps -ux | grep python3
	fi

	echo ".. Retraining model"
	./postgres-bao-ctl.py --retrain-bao --timing --timing-out $TIM_FILE --quiet

	if [ "$DEBUG" = true ] ; then
		echo ".. Python processes currently running AFTER iteration $run"
		ps -ux | grep python3
	fi
done
