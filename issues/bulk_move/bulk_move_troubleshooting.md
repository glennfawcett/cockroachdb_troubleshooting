# Bulk Move Troubleshooting

Cockroach Database supports the serializable isolation level to ensure data correctness.  Since serializable is more strict, it can increase contention when running larger bulk DML operations within the cluster.  With serializable, the scope of each transaction needs to be minimized.  Indeed, if large operations are attempted, often they get aborted due to running out of memory or the inability to guarantee serializable isolation.  

Recently, I was debugging an issue where a user was trying to move data from a temporary table with ~100 million rows into a table with billions of rows.  The operation was timing out and needed to be resolved.  

## Symptoms and Diagnosis

The following statements were to be run to move the data.

```sql
INSERT INTO dest_table (id)
SELECT id FROM mytemp;
```

Once this was complete, the temporary table was to be dropped.

```sql
DROP TABLE mytemp;
```

Bulk Single `INSERT` statements with this many rows, is not ideal with CockroachDB.  Bulk statements of this nature have to allocate a large amount of memory and are prone to retries, timeouts, and disruption of other traffic targeting this table.  Clearly, some batching of this operation was needed to resolve the issue.

## Treatment

To get around this issue, I decided to `LIMIT` the rows and run multiple statements.  This is a great use of a CTE with the `RETURNING` clause to essentially paginate throughout the operation.

### Example Move script

This simple script runs via the shell and accesses CockroachDB with the `cockroach` binary.  Data is removed in small batches using the `LIMIT` operation.  The `--watch` option is used with the `cockroach` CLI to run the same statement over and over again at the desired frequency.  The `bash` script loop reads the returned data and exits once their are no more rows have been inserted to the destination table. During the process, rows are deleted from the temporary table and inserted to the destination table.

```bash
cockroach sql --insecure --format csv --execute """
  WITH dmin as (
      DELETE FROM mytemp WHERE 1=1 
      LIMIT 1000
      RETURNING (id)
  )
  INSERT INTO dest_table (id)
  SELECT * 
  FROM dmin
""" --watch 0.0001s |
while read i
do
 echo $i
 if [[ "$i" == "INSERT 0" ]]; then
    echo "DONE"
    exit
 fi
done
```

## Example for Batch Move

Create a simply set of tables test the move operation and insert some test data.

```sql
cockroach sql --insecure --execute "create table if not exists mytemp (id int primary key)"
cockroach sql --insecure --execute "insert into mytemp select * from generate_series(1,10000)"
cockroach sql --insecure --execute "select count(*) from mytemp"
cockroach sql --insecure --execute "create table if not exists dest_table (id int, inserted_at timestamp default now())"
```

### Move SQL using CTE

This simple script uses the `cockroach` binary with a simple shell wrapper to move data between tables.

```bash
cockroach sql --insecure --format csv --execute """
  WITH dmin as (
    DELETE FROM mytemp WHERE 1=1 
    LIMIT 1000
    RETURNING (id)
  )
  INSERT INTO dest_table (id)
  SELECT * 
  FROM dmin 
""" --watch 0.0001s |
while read i
do
  echo $i
  if [[ "$i" == "INSERT 0" ]]; then
     echo "DONE"
     exit
  fi
done
```

### Runtime Example

```bash

    15:10 $ cockroach sql --insecure --format csv --execute """
    >   WITH dmin as (
    >     DELETE FROM mytemp WHERE 1=1
    >     LIMIT 1000
    >     RETURNING (id)
    >   )
    >   INSERT INTO dest_table (id)
    >   SELECT *
    >   FROM dmin
    > """ --watch 0.0001s |
    > while read i
    > do
    >   echo $i
    >   if [[ "$i" == "INSERT 0" ]]; then
    >      echo "DONE"
    >      exit
    >   fi
    > done
    INSERT 1000
    INSERT 1000
    INSERT 1000
    INSERT 1000
    INSERT 1000
    INSERT 1000
    INSERT 1000
    INSERT 1000
    INSERT 1000
    INSERT 1000
    INSERT 0
    DONE
```

## Conclusion

Hopefully this was useful to give you some ideas on how to best perform BULK operations with CockroachDB.  If you divide up the PK into ranges you can also pretty easily parallelize this operation as well to increase the move speed.
