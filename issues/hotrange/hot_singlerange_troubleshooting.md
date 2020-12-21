# Hot Single Range Troubleshooting
This issue occurs when there is an over abundance of activity on a single range.  This typically occurs with a *small* table that fits into a single range.

## Symptoms
The symptoms of a single hot range include:
* High CPU utilization on a **single** node
* Spike in SQL Latency
* Lack of workload scaling due to uneven CPU utilization

From the DB Console, we see QPS and CPU capped all on one node.  This can limit scaling of the workload.  So, either the workload can be driven at a higher rate to force splitting, or the split threshold can be lowered.

![](singlerange_qps.png)

![](singlerange_cpu.png)

## Diagnosis
The symptoms can be observed via the DB console or via metrics externally.  Before we can formulate a treatment plan, we need to identify which specific range is causing the high CPU utilization.  
* Check the DB console [statements](https://www.cockroachlabs.com/docs/v20.2/ui-statements-page) page to see the most highly executed queries
* Check to see how many *ranges* are on the supect table.  This can be done via the DB Console or using the [SHOW RANGES](https://www.cockroachlabs.com/docs/stable/show-ranges.html) SQL command.  For example:
    ```sql
    SHOW RANGES FROM TABLE hotsingle;

    start_key | end_key | range_id | range_size_mb | lease_holder |           lease_holder_locality           | replicas |                                                          replica_localities
    ------------+---------+----------+---------------+--------------+-------------------------------------------+----------+----------------------------------------------------------------------------------------------------------------------------------------
    NULL      | NULL    |       78 |    153.434101 |            4 | cloud=gce,region=us-east1,zone=us-east1-b | {1,2,4}  | {"cloud=gce,region=us-east1,zone=us-east1-b","cloud=gce,region=us-east1,zone=us-east1-b","cloud=gce,region=us-east1,zone=us-east1-b"}
    (1 row)
    ```

    It is possible that these techniques might not be able to isolate the one hot range due to other statements.  If this is the case, we can look at the *hot ranges* from the *advanced* endpoint on the DB Console `http://hostname:26258/_status/hotranges`.
* With the `range_id` you can query the ranges table to determine the name of the object using the range.

    ```sql
    SELECT database_name, table_name, index_name
    FROM crdb_internal.ranges
    WHERE range_id = 78;
        
    database_name   | table_name | index_name
    ----------------+------------+-------------
    test            | hotsingle  |
    ```
Finally, if the above methods do not show the range in question, you can use the [hottest_ranges3.py]() tool to extract data from the `http://hostname:25258/_status/raft` endpoint and lookup the hottest ranges ordered by the highest number of QueryPerSecond.


## Treatment
A small single range table can become hot for many reasons.  Microservices **pooling** data, **dashboards**, **queue** tables are some of the most common observed bottle-necks.  To resolve, we would like to split data access across multiple ranges.

### Option #1 -- Adjust Auto Splitting

To disperse data access, we need to read from multiple replicas and/or split the ranges.  CockroachDB can dynamically split ranges by configuring the split threshold.

**Adjust Auto Splitting:**

```sql
-- Adjust to Split at a lower QPS and not re-merge ranges
--
SET CLUSTER SETTING kv.range_merge.queue_enabled = false;    -- default is true
SET CLUSTER SETTING kv.range_split.by_load_enabled = true;   -- default is true
SET CLUSTER SETTING kv.range_split.load_qps_threshold = 100; -- default 2500
```

**Monitor Range Splitting:**
```sql

root@:26257/test> SHOW RANGES FROM TABLE hotsingle;
  start_key | end_key | range_id | range_size_mb | lease_holder |           lease_holder_locality           | replicas |                                                          replica_localities
------------+---------+----------+---------------+--------------+-------------------------------------------+----------+----------------------------------------------------------------------------------------------------------------------------------------
  NULL      | /200001 |       78 |     61.334101 |            4 | cloud=gce,region=us-east1,zone=us-east1-b | {1,4,5}  | {"cloud=gce,region=us-east1,zone=us-east1-b","cloud=gce,region=us-east1,zone=us-east1-b","cloud=gce,region=us-east1,zone=us-east1-b"}
  /200001   | /400001 |       69 |          61.4 |            2 | cloud=gce,region=us-east1,zone=us-east1-b | {1,2,4}  | {"cloud=gce,region=us-east1,zone=us-east1-b","cloud=gce,region=us-east1,zone=us-east1-b","cloud=gce,region=us-east1,zone=us-east1-b"}
  /400001   | NULL    |       79 |          30.7 |            2 | cloud=gce,region=us-east1,zone=us-east1-b | {1,2,4}  | {"cloud=gce,region=us-east1,zone=us-east1-b","cloud=gce,region=us-east1,zone=us-east1-b","cloud=gce,region=us-east1,zone=us-east1-b"}
(3 rows)
```

**QPS and CPU:**

Looking at the DB Console, we can see that as the ranges SPLIT and moved, we are able to scale throughput and balance the CPU load across all nodes of the cluster.

![](singlerange_split_qps.png)
![](singlerange_split_cpu.png)

#### Reproduce "hotsingle range"
A full reproduction of this topic can be run using the instructions in [repo_hot_singlerange_table.md](repo_hot_singlerange_table.md)


### Option #2 -- Use Follower Reads
Sometimes all of the activity is querying to the **same** exact value from multiple clients.  This is typically in as dashboard or polling application.  If the application logic allows to read a slightly older copy of the data, you can use the `follower_read_timestamp()` function read from the *lease-holder* as well as the *replica* copies of data.  This allows CPU to be spread over multiple nodes.

The `num_replicas` defines how many replicant ranges exhist on each object:

```sql
SHOW ZONE CONFIGURATION FOR TABLE hotsingle;

     target     |              raw_config_sql
----------------+-------------------------------------------
  RANGE default | ALTER RANGE default CONFIGURE ZONE USING
                |     range_min_bytes = 134217728,
                |     range_max_bytes = 536870912,
                |     gc.ttlseconds = 90000,
                |     num_replicas = 3,
                |     constraints = '[]',
                |     lease_preferences = '[]'
```
So, just simply using `as of system time follower_read_timestamp()` you will be able to increase the CPU resoures by 3x.  If you wish to spread this futher, you can increase the `num_replicas` by altering the table:


```sql
ALTER TABLE hotsingle CONFIGURE ZONE USING num_replicas = 5;
CONFIGURE ZONE 1
```

After a few minutes:
```sql
SELECT replicas FROM [SHOW RANGES FROM TABLE hotsingle];
  replicas
------------
  {1,2,3,4,5} 
```

**DB Console with follower reads:**


![](singlevalue_follower_cpu.png)
![](singlevalue_follower_qps.png)

Notice how CPU and QPS scales up to utilize all resource on the cluster.  This example you see some back-off with the 5 replica test.  It was hitting the cluster hard and the system needed CPU to keep concensus.

#### Reproduce "single value stress"
A full reproduction of results can be run using the instructions in [repo_single_hotvalue.md](repo_single_hotvalue.md).  It uses the same configuration as the other hotrange, but runs only **one** query from all threads.