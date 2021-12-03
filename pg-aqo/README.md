# Postgres Adaptive Query Optimization

The scripts in this directory contain utilities to setup the Adaptive query optimization extension for Postgres 12 (found here: https://github.com/postgrespro/aqo/)
To reproduce, execute them in this order:

. `postgres-aqo-setup.sh` - this will clone the PG 12 as well as the extension (without Git history, etc.) into the directory `postgres-aqo`
. `postgres-aqo-initial-start.sh` - this will setup an example database in the directory `postgres-aqo/build/data`, for the current user. Furthermore, the AQO extension is activated. After this script has run, you may connect to the Postgres instance via `psql`, etc.
. `postgres-aqo-start.sh` and `postgres-aqp-shutdown.sh` - these are used to terminate the Postgres process and to restart it after all initialization steps have been executed

The final script `postgres-aqo-env.sh` should be run by the `source` command to set up the `$PATH` variable correctly for further use, i.e. to have `psql`, etc. available directly on the command line.
