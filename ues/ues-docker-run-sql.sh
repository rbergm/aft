#!/bin/sh

docker exec ues_container /home/postgres/ues/psql/bin/bin/psql imdb -f $1 --csv > $2

