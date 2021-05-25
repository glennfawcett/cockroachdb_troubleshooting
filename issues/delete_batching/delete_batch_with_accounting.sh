cockroach sql --insecure --execute "create table if not exists mytable (id int primary key)"
cockroach sql --insecure --execute "insert into mytable select * from generate_series(1,10000)"
cockroach sql --insecure --execute "select count(*) from mytable"

cockroach sql --insecure --execute "create table if not exists mytable_cnt (cnt int, ts timestamp default now())"


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

cockroach sql --insecure --execute "select (sum(cnt)/EXTRACT(EPOCH from max(ts)-min(ts))::decimal(8,2))::decimal(8,2) as delete_per_second from mytable_cnt"
 