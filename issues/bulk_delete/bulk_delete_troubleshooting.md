# Bulk Delete Troubleshooting
Cockroach Database supports the serializable isolation level to ensure data correctness.  Since serializable is more strict, it can increase contention when running larger bulk data operations within the cluster. With serializable, the scope of each transaction needs to be minimized.  Indeed, if large operations are attempted, often they get aborted due to running out of memory or the inability to guarantee serializable isolation.  

This typically happens when an application desires to archive old data.  If the application itself does not take care of this, then it is often up to the DB operations group to assist.  The data to be archived must have a clean filter typically by timestamp. 


## Symptoms and Diagnosis
Your bulk `DELETE` statements can fail for multiple reasons.
* Run out of memory
* Timeout

These failures can be observed via the CLI prompt and the `crdb.log` files.

## Treatment
The docs are pretty good with some examples written in Python.
* [https://www.cockroachlabs.com/docs/v20.2/bulk-delete-data.html](https://www.cockroachlabs.com/docs/v20.2/bulk-delete-data.html)

For this blog entry, I have included simple examples of how to do this with via the CLI.

### Simple Delete script

This simple script runs via the shell and accesses CockroachDB with the `cockroach` binary.  Data is removed in small batches using the `LIMIT` operation.  The `--watch` option is used with the `cockroach` CLI to run the same statement over and over again at the desired frequency.  The `bash` script loop reads the returned data and exits once their are no more rows to be deleted.

```bash
cockroach sql --insecure --format csv --execute """
 delete from bigtable where ts < now() - ‘30d’ limit 1000
""" --watch 0.0001s |
while read d
do
 echo $d
 if [[ "$d" == "DELETE 0" ]]; then
    echo "DONE"
    exit
 fi
done
```

### Simple Delete with Accounting
Building on the previous example, you can use a CTE with the `RETURNING` clause to `INSERT` data into a table for tracking.  This allows you to monitor progress and inserts the count for each `DELETE`'s for that batch statement into `mytable_cnt`.

```bash
cockroach sql --insecure --format csv --execute """
  WITH dmin as (
    DELETE FROM mytable WHERE 1=1 
    LIMIT 1000
    RETURNING (id)
  )
  INSERT INTO mytable_cnt (cnt)
  SELECT count(*) 
  FROM dmin 
  WHERE id IS NOT NULL
  RETURNING (cnt)
""" --watch 0.0001s |
while read d
do
  echo $d
  if [[ "$d" == "0" ]]; then
     echo "DONE"
     exit
  fi
done
```

**Determine Delete's per second after running:**

The `mytable_cnt` table also inserts the `TIMESTAMP` values into the `ts` column to keep track of the entries.  This can be very useful to track the delete progress like so:

```sql
SELECT (sum(cnt)/EXTRACT(EPOCH from max(ts)-min(ts))::decimal(8,2))::decimal(8,2) as delete_per_second 
FROM mytable_cnt;

  delete_per_second
---------------------
            1587.30
```

I have created the [delete_batch_with_accounting.sh](delete_batch_with_accounting.sh) script in my troubleshooting repository so you can experiment with this technique.

### Multi Treaded Delete on Timestamp
To delete timeseries data in parallel, a `HASH` index is your best bet.  This example has the `created_at` column which contains the timestamp of when the data was inserted.  This example has a `HASH` index `WITH BUCKET_COUNT=9` to match the number of nodes in the cluster.

```sql
CREATE TABLE mybigtable (
    id UUID PRIMARY KEY,
    created_at TIMESTAMP DEFAULT now(),
    c1 STRING,
    c2 STRING,
    c3 STRING
);

SET experimental_enable_hash_sharded_indexes=true;

CREATE INDEX idx_mybigtable_created_at 
ON mybigtable(created_at)
USING HASH WITH BUCKET_COUNT = 9;
```

When you run a `SHOW CREATE mybigtable`, notice there is a hidden column `crdb_internal_created_at_shard_9`.  This column can be used to efficiently access each hash bucket.

```sql

SHOW CREATE mybigtable;

  table_name |                                    create_statement
-------------+-----------------------------------------------------------------------------------------
  mybigtable | CREATE TABLE public.mybigtable (
             |     id UUID NOT NULL,
             |     created_at TIMESTAMP NULL,
             |     c1 STRING NULL,
             |     c2 STRING NULL,
             |     c3 STRING NULL,
             |     CONSTRAINT "primary" PRIMARY KEY (id ASC),
             |     INDEX idx_mybigtable_created_at (created_at ASC) USING HASH WITH BUCKET_COUNT = 9,
             |     FAMILY "primary" (id, created_at, c1, c2, c3, crdb_internal_created_at_shard_9)
             | )
```

With a `BUCKET_COUNT=9`, you can create 9 parallel threads to `DELETE` from each shard:

**Thread 1:**
```sql
    -- thread 1
    --
    DELETE FROM mybigtable 
    WHERE created_at < now() - INTERVAL '30d' AND
          crdb_internal_created_at_shard_9 = 0
    LIMIT 1000
    RETURNING (id)
```

**Thread 2:**
```sql
    -- thread 2
    --
    DELETE FROM mybigtable 
    WHERE created_at < now() - INTERVAL '30d' AND
          crdb_internal_created_at_shard_9 = 1
    LIMIT 1000
    RETURNING (id)
```
...
...

**Thread 9:**
```sql
    -- thread 9
    --
    DELETE FROM mybigtable 
    WHERE created_at < now() - INTERVAL '30d' AND
          crdb_internal_created_at_shard_9 = 8
    LIMIT 1000
    RETURNING (id)
```

## Conclusion
Hopefully this was useful to give you some ideas on how to best perform BULK DELETEs with CockroachDB.  Depending on your scenario, there are multiple paths to `DELETE` data with minimual impact.