#!/bin/bash

REPETITIONS=5

for ((run = 1; run <= $REPETITIONS ; run++))
do
	if [ "$1" = "-clean" ]
	then
		echo "Setting up new Docker image"
		./ues-docker-reset.sh
		./ues-docker-create.sh
		./ues-docker-start.sh
		./ues-docker-connect.sh << EOF
exit
EOF
	fi
	echo "Run $run"
	# we need to explicitly use the UNIX utility here, to prevent the bash-builtin tool from shadowing it
	/usr/bin/time --append -f "$(date -u +%s),$run,%E" -o timing$1.csv ./ues-docker-run-sql.sh workloads/job-implicit.sql /tmp/job-implicit$1-run$run.out
done

