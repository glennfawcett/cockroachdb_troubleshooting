# Create Cluster for ingest json

Cluster to characterize the performance of ingest with `jsonb` data and indexes.

```bash
## Setup Cluster
##
roachprod create `whoami`-json -n 3 --clouds gce --gce-machine-type n1-standard-8 --lifetime 36h
roachprod stage `whoami`-json release v21.1.11 
roachprod start `whoami`-json 

## Setup haproxy and driver
##
roachprod create `whoami`-drive -n 1 --clouds gce --gce-machine-type n1-standard-8 --lifetime 36h
roachprod stage `whoami`-drive release v21.1.11
roachprod ssh `whoami`-drive
sudo mv cockroach /usr/local/bin


##**Setup HAproxy on Driver Machine**
##  Replace HOST id below with INTERNAL VNC addresses to CRDB cluster
sudo apt-get update -y
sudo apt-get install haproxy -y
cockroach gen haproxy --insecure   --host=10.142.0.84   --port=26257 
nohup haproxy -f haproxy.cfg &


## Install Python3
sudo apt-get update
sudo apt-get install libpq-dev python-dev -y
sudo apt install python3-numpy python3-scipy python3-psycopg2 python3-dev -y

## Put Stress Script
roachprod put  `whoami`-drive ingest_json.py
```

## Running the workload for INGEST

This test table has ~10 columns with values as well as a JSON which has 10 random columns as well as columns that map to the JSON values.  The [ingest_json_performance.md](ingest_json_performance.md) has details regarding the JSON test runs.