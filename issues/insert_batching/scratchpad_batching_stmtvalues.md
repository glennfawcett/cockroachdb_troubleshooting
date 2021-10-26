# Scratchpad Ingest multi-values

```sql

drop table ingest1;
drop table ingest2;
drop table ingest3;


create table ingest1(id UUID NOT NULL DEFAULT gen_random_uuid() primary key);
create table ingest2(id UUID NOT NULL DEFAULT gen_random_uuid() primary key);
create table ingest3(id UUID NOT NULL DEFAULT gen_random_uuid() primary key);


alter table ingest1 split at select gen_random_uuid from (select gen_random_uuid(),generate_series(1, 32));
alter table ingest2 split at select gen_random_uuid from (select gen_random_uuid(),generate_series(1, 32));
alter table ingest3 split at select gen_random_uuid from (select gen_random_uuid(),generate_series(1, 32));



drop table t1;
drop table t2;
drop table t3;

-- t1 single insert
-- t2 batch 10 values
-- t3 batch 10 statements
--
create table t1(a string, b string);
create table t2(a string, b string);
create table t3(a string, b string);







root@192.168.0.100:26257/ingest> select count(*) from t2;
  count
----------
  119880
(1 row)

Time: 29ms total (execution 29ms / network 0ms)

root@192.168.0.100:26257/ingest> select count(*) from t3;
  count
----------
  112360
(1 row)

Time: 29ms total (execution 29ms / network 0ms)

--
-- pct improvement 100*(119880-112360)/112360
-- 100*(119880-112360)/112360
-- 6.69277322890708437166

```