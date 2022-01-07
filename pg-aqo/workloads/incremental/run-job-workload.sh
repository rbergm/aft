#!/bin/bash

echo "JOB workload for PG-aqo"
date

echo "Run 1"
psql imdb -f job-full.sql --csv > job-full-run-1.results
date

echo "Run 2"
psql imdb -f job-full.sql --csv > job-full-run-2.results
date

echo "Run 3"
psql imdb -f job-full.sql --csv > job-full-run-3.results


echo "Workload done"
date

