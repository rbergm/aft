#!/bin/sh

docker run -d -i --shm-size=4g --name ues_container --mount type=bind,source=$(pwd),target=/home/postgres/host ues
docker exec -ti ues_container sed -i "s/^shared_buffers.*/shared_buffers = 12GB/" ../ues/psql/data/postgresql.conf

