#!/bin/bash

# prevent the bash-builtin time command from shadowing the actual UNIX utility
alias time="/usr/bin/time"

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
	time -a -f "$run,%E" -o timing$1.csv ./ues-docker-run-sql.sh workloads/job-implicit.sql /tmp/job-implicit$1-run$run.out
done

