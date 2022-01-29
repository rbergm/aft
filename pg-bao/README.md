# Postgres BAO optimizer

The scripts in this directory contain utilities to setup the BAO query optimization extension for Postgres 12 (found here: https://github.com/learnedsystems/BaoForPostgreSQL)
To reproduce, execute them in this order:

1. `postgres-bao-setup.sh` - this will clone the PG 12 as well as the extension (without Git history, etc.) into the directory `postgres-bao` and also setup the infrastructure necessary for the BAO server. This includes creating a Python virtual environment.
2. `postgres-bao-initial-start.sh` - this will setup an example database in the directory `postgres-bao/build/data`, for the current user. Furthermore, the BAO extension is activated. After this script has run, you may connect to the Postgres instance via `psql`, etc.
3. optionally, you may whish to setup the IMDB database for BAO now. To make this process easier, there is a utility in the root folder of this project (`utils/setup-imdb.py`).
4. `postgres-bao-start.sh` and `postgres-bao-shutdown.sh` - these are used to terminate the Postgres and BAO server processes and to restart them after all initialization steps have been executed

The final script `postgres-bao-env.sh` should be run by the `source` command to set up the `$PATH` variable correctly for further use, i.e. to have `psql`, etc. available directly on the command line.

Note that all scripts are path-sensitive. They assume they are run from this folder!

In order to run a workload for BAO, yet another utility exists: `postgres-bao-ctl.py`. This makes running many common tasks such as running a workload, training the model or resetting the model data more convenient. Check `./postgres-bao-ctl.py --help` for details.

For example, you can run a example workload like so:

```bash

# execute a workload, retraining every 20 queries (all queries will be used for training)
./postgres-bao-ctl.py --run-workload --workload /path/to/workload.sql --retrain 20 --output /path/to/results.out

# execute a workload, use 20% of the queries for training (but don't retrain automatically)
./postgres-bao-ctl.py --run-workload --workload /path/to/workload.sql --training-fraction 0.2 --output /path/to/results.out

# don't run any workload, only retrain the model and measure how long this took
./postgres-bao-ctl.py --retrain-bao --timing --timing-out /path/to/timing.csv

# don't run any workload, forget everything BAO has learned so far
./postgres-bao-ctl.py --reset-bao
```

## References

Ryan Marcus, et al. 2021 - _Bao: Making Learned Query Optimization Practical._ SIGMOD/PODS'21. DOI: https://doi.org/10.1145/3448016.3452838
