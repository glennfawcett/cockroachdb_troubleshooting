# Hash Index Query Peformance 
Hash indexes were added to CockroachDB to improve the performance of ingest with sequential values.  
This helps with lookup single point lookup as in a PK while not hotspotting on Ranges.  While Hash
Indexes are useful for this workflow, it is not ideal for *range* scans of data.

This entry will explore the performance characteristics of Hash Indexes in various scenarios with CRDB.

## Symptoms
Created a hash index to manage ingest performance.  This helped elimnate a hotspotting on ranges during
ingest, but performance of some queries that use the index are worse.  Overall summary of symptoms: 
* Queries with range scans `BETWEEN` are slower than before switching to HASH indexes
* More ranges are scanned


## Diagnosis (work in progress...)
* statement bundle
* show ddl

## Treatment
Live with it :)

## Test scenario Demo

```sql
create table int_pk(id int primary key);
insert into int_pk select generate_series(1,1000000);

SET experimental_enable_hash_sharded_indexes=on;
create table int_pkhash2(id int primary key USING HASH WITH BUCKET_COUNT=8);
insert into int_pkhash2 select generate_series(1,1000000);


select count(*) from int_pk where id BETWEEN 500 and 2000;

root@localhost:26257/defaultdb> select count(*) from int_pk where id BETWEEN 500 and 2000;
  count
---------
   1501
(1 row)

Time: 4ms total (execution 4ms / network 0ms)


root@localhost:26257/defaultdb> select count(*) from int_pkhash where id BETWEEN 500 and 2000;
  count
---------
   1501
(1 row)

Time: 651ms total (execution 651ms / network 0ms)



select count(*) from int_pkhash where id BETWEEN 500 and 2000;

select sum(count) from (
select count(*) from int_pkhash where id BETWEEN 500 and 2000 and crdb_internal_id_shard_8=0
union all
select count(*) from int_pkhash where id BETWEEN 500 and 2000 and crdb_internal_id_shard_8=1
union all
select count(*) from int_pkhash where id BETWEEN 500 and 2000 and crdb_internal_id_shard_8=2
union all
select count(*) from int_pkhash where id BETWEEN 500 and 2000 and crdb_internal_id_shard_8=3
union all
select count(*) from int_pkhash where id BETWEEN 500 and 2000 and crdb_internal_id_shard_8=4
union all
select count(*) from int_pkhash where id BETWEEN 500 and 2000 and crdb_internal_id_shard_8=5
union all
select count(*) from int_pkhash where id BETWEEN 500 and 2000 and crdb_internal_id_shard_8=6
union all
select count(*) from int_pkhash where id BETWEEN 500 and 2000 and crdb_internal_id_shard_8=7
);

SELECT m100, count(*), sum(v100), min(ts), max(ts)
FROM measure
WHERE ts BETWEEN '2001-01-01' and '2021-01-02'
GROUP BY m100
ORDER BY 3 desc
LIMIT 10