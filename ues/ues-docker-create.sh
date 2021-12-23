#!/bin/sh

docker run -d -i --shm-size=4g --name ues_container --mount type=bind,source=$(pwd),target=/home/postgres/host ues

