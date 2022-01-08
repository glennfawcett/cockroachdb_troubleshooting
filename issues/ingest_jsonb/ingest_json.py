# Import the driver.
import psycopg2
import psycopg2.errorcodes
import threading
from threading import Thread
import time
import datetime
import random
import numpy
import uuid
import math

usleep = lambda x: time.sleep(x/1000000.0)
msleep = lambda x: time.sleep(x/1000.0)

class dbstr:
  def __init__(self, database, user, host, port):
    self.database = database
    self.user = user
    # self.sslmode = sslmode
    self.host = host
    self.port = port

class ThreadWithReturnValue(Thread):
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs={}, Verbose=None):
        Thread.__init__(self, group, target, name, args, kwargs)
        self._return = None
    def run(self):
        print(type(self._target))
        if self._target is not None:
            self._return = self._target(*self._args,
                                                **self._kwargs)
    def join(self, *args):
        Thread.join(self, *args)
        return self._return

def onestmt(conn, sql):
    with conn:
        with conn.cursor() as cur:
            cur.execute(sql)

def getcon(dc):
    myconn = psycopg2.connect(
        # database=dc.database,
        # user=dc.user,
        # sslmode='disable',
        # port=dc.port,
        # host=dc.host
        "postgresql://root:@localhost:26257/defaultdb?sslmode=disable"
    )
    return myconn

def boolDistro(dval):
    if dval >= random.random():
        return True
    else:
        return False

def getIds(mycon, idSQL):
    # Retrieve Valid Session IDs
    #
    with mycon:
        with mycon.cursor() as cur:
            cur.execute(idSQL)
            rows = cur.fetchall()
            # Create Data Frame for vaild Session IDs
            valid_ids = []
            for row in rows:
                valid_ids.append([str(cell) for cell in row])

    return valid_ids

def perform(fun, *args):
    return(fun(*args))

def q0(val):
    return ("SELECT PG_SLEEP({})".format(val))


def jsonKVrand(numberOfPairs, randomRange): 
    ## JSON Creation
    ##
    bigfastvals = ''
    bigfastvals = bigfastvals + "'{"

    for i in range(numberOfPairs):
        if(random.random() < 0.00001):
            rval = str(999999)
        else:  
            rval = str(random.randint(1, randomRange))
        bigfastvals = bigfastvals + '"k' + str(i) + '":"' + rval + '"'
        if (i != numberOfPairs - 1):
            bigfastvals = bigfastvals + ','

    bigfastvals = bigfastvals + "}'" 
    
    return bigfastvals

def qj1(jTable, numOfValues, numberOfPairs, randomRange):
    qTemplate = """
    INSERT INTO {} (id, ts0, k1, k2, k3, k4, k5, v1, v2, v3, v4, v5, j) 
    VALUES {}
    """
    vstring = ''
    for i in range(numOfValues): 
        vstring = vstring + "("
        vstring = vstring + "'" + str(uuid.uuid4()) + "'" + ","
        vstring = vstring + "now()" + ","
        vstring = vstring + "'k100000'" + ","
        vstring = vstring + "'k200000'" + ","
        vstring = vstring + "'k300000'" + ","
        vstring = vstring + "'k400000'" + ","
        vstring = vstring + "'k500000'" + ","
        vstring = vstring + str(random.randint(100000, 199999)) + ","
        vstring = vstring + str(random.randint(200000, 299999)) + ","
        vstring = vstring + str(random.randint(300000, 399999)) + ","
        vstring = vstring + str(random.randint(400000, 499999)) + ","
        vstring = vstring + str(random.randint(500000, 599999)) + ","        
        vstring = vstring + jsonKVrand(numberOfPairs, randomRange)
        vstring = vstring + ")"
        if i != (numOfValues-1):
            vstring = vstring + ','

    return (qTemplate.format(jTable, vstring))

def crRecordTables(myconn, reset):
    """Create Tables to Record test runs"""
    if reset:
        onestmt(myconn, "DROP TABLE IF EXISTS _testruns;")
        onestmt(myconn, "DROP SEQUENCE IF EXISTS runseq;")

    onestmt(myconn, "CREATE SEQUENCE IF NOT EXISTS runseq START WITH 1 INCREMENT BY 1;")
    
    testRunDDL = """
    CREATE TABLE IF NOT EXISTS _testruns (
        id INT PRIMARY KEY DEFAULT nextval('runseq'),
        tablename STRING NOT NULL,
        numthreads INT NOT NULL,
        batchsize INT NOT NULL,
        insertspersec FLOAT as (if(end_ts IS NOT NULL,(rowsinserted)::FLOAT/extract(epoch from (end_ts - start_ts)), 0.0)) STORED,
        p90ms DECIMAL,
        rowsinserted INT,
        description STRING,
        start_ts TIMESTAMPTZ DEFAULT now(),
        end_ts TIMESTAMPTZ
    );
    """
    onestmt(myconn, testRunDDL)
    return

def crTestRun(myconn, description, tablename, numthreads, batchsize): 
    insRec = """
    INSERT INTO _testruns(description, tablename, numthreads, batchsize)
    VALUES ('{}', '{}', {}, {})
    RETURNING (id)
    """
    with myconn:
        with myconn.cursor() as cur:
            cur.execute(insRec.format(description, tablename, numthreads, batchsize))
            rows = cur.fetchall()
    return rows[0][0]

def updateTestRun(myconn, rid, rowsinserted, p90ms): 
    updateSQL = """
    UPDATE _testruns
    SET rowsinserted = {}, 
        p90ms = {},
        end_ts = now()
    WHERE id = {}
    """
    onestmt(myconn, updateSQL.format(rowsinserted, p90ms, rid))
    return

def worker_steady(num, tpsPerThread, dbstr, runtime, qFunc, jtable, valsPerJSON, distIntPerVal, vsize):
    """ingest worker:: Lookup valid session and then account"""
    print("Worker Steady State")

    #mycon = getcon(dbstr)
    mycon = psycopg2.connect(connStr)

    mycon.set_session(autocommit=True)

    # Configure Rate Limiter
    if tpsPerThread == 0:
        Limit=False
        arrivaleRateSec = 0
    else:
        Limit=True
        arrivaleRateSec = 1.0/tpsPerThread
    
    threadBeginTime = time.time()
    etime=threadBeginTime

    execute_count = 0
    resp = []

    with mycon:
        with mycon.cursor() as cur:
            while etime < (threadBeginTime + runtime):
                # begin time
                btime = time.time()

                # print(qj1(jtable, valsPerJSON, vsize, distIntPerVal))
                # exit()
                # Run the query from qFunc
                cur.execute(qFunc(jtable, valsPerJSON, vsize, distIntPerVal))
                execute_count += 1

                etime = time.time()
                resp.append(etime-btime)

                sleepTime = arrivaleRateSec - (etime - btime)

                if Limit and sleepTime > 0:
                    time.sleep(sleepTime)

            print("Worker_{}:  Queries={}, QPS={}, P90={}!!!".format(num, execute_count, (execute_count/(time.time()-threadBeginTime)), numpy.percentile(resp,90)))

    return (execute_count, resp)


## Main
##

# TODO make command-line options
#f

# connStr = "postgresql://root@delivery-crdb.us-west-2.aws.ddnw.net:26257/delivery_prod?sslmode=require&sslrootcert=/disk1/home/glennfawcett/crdb/delivery/ca.crt&sslcert=/disk1/home/glennfawcett/crdb/delivery/client.root.crt&sslkey=/disk1/home/glennfawcett/crdb/delivery/client.root.key"
connStr = "postgres://root@127.0.0.1:26257/defaultdb?sslmode=disable"

crBase = """
CREATE TABLE IF NOT EXISTS jtable_base (
    id UUID PRIMARY KEY,
    ts0 TIMESTAMP DEFAULT now(),
    k1 STRING,
    k2 STRING,
    k3 STRING,
    k4 STRING,
    k5 STRING,
    v1 INT,
    v2 INT,
    v3 INT,
    v4 INT,
    v5 INT,
    j JSON
);
"""

crInverted = """
CREATE TABLE IF NOT EXISTS jtable_inverted (
    id UUID PRIMARY KEY,
    ts0 TIMESTAMP DEFAULT now(),
    k1 STRING,
    k2 STRING,
    k3 STRING,
    k4 STRING,
    k5 STRING,
    v1 INT,
    v2 INT,
    v3 INT,
    v4 INT,
    v5 INT,
    j JSON,
    INVERTED INDEX inv_j (j)
)
"""

crStoring = """
CREATE TABLE IF NOT EXISTS jtable_storing (
    id UUID PRIMARY KEY,
    ts0 TIMESTAMP DEFAULT now(),
    k1 STRING,
    k2 STRING,
    k3 STRING,
    k4 STRING,
    k5 STRING,
    v1 INT,
    v2 INT,
    v3 INT,
    v4 INT,
    v5 INT,
    j JSON,
    jk0 INT8 NULL AS (CAST(j->>'k0':::STRING AS INT8)) STORED,
    jk1 INT8 NULL AS (CAST(j->>'k1':::STRING AS INT8)) STORED,
    jk2 INT8 NULL AS (CAST(j->>'k2':::STRING AS INT8)) STORED,
    jk3 INT8 NULL AS (CAST(j->>'k3':::STRING AS INT8)) STORED,
    jk4 INT8 NULL AS (CAST(j->>'k4':::STRING AS INT8)) STORED,
    INDEX idx_jk0 (jk0 ASC), 
    INDEX idx_jk1 (jk1 ASC), 
    INDEX idx_jk2 (jk2 ASC), 
    INDEX idx_jk3 (jk3 ASC), 
    INDEX idx_jk4 (jk4 ASC) 
);
"""

# print(jsonKVrand(10,100000))
# exit()

# Rebuild Settings
rebuildTables = False
resetTests = False

# Define Tables to Test
tables = ['jtable_base', 'jtable_inverted', 'jtable_storing']

mycon = psycopg2.connect(connStr)

# Drop Existing Tables
if rebuildTables:
    for t in tables:
        onestmt(mycon, "DROP TABLE IF EXISTS {};".format(t))

# Create Tables 
onestmt(mycon, crBase)
onestmt(mycon, crInverted)
onestmt(mycon, crStoring)

# Presplit Tables
if rebuildTables:
    for t in tables:
        onestmt(mycon, "ALTER TABLE {} SPLIT AT select gen_random_uuid() from generate_series(1,18);".format(t))

# Create Tables To Record Runs... if resetTests is TRUE it drops and recreates the table
crRecordTables(mycon, resetTests)
mycon.close()

# JSON size and Distribution of values
valsPerJSON = 10
distIntPerVal = 10000

# Runtime Per Table
runtime = 300
QPS = 61

# Define batch size tests
batchSize = [50]

# Number of Threads
threadsToRun = [9]

for tab in tables:
    print ("Inserting to table: {}".format(tab))

    for numThreads in threadsToRun:
        print("Threads : {}".format(numThreads))
        qpsPerThread = QPS/numThreads

        for currentBatchSize in batchSize:
            print ("Insert BatchSize: {}".format(currentBatchSize))
            mycon = psycopg2.connect(connStr)
            runid = crTestRun(mycon, "JSON_9threads_60qps_50batch", tab, numThreads, currentBatchSize)
            mycon.close()

            threads1 = []
            for i in range(numThreads):
                t1 = ThreadWithReturnValue(target=worker_steady, args=((i+1), qpsPerThread, connStr, runtime, qj1, tab, currentBatchSize, distIntPerVal, valsPerJSON))
                threads1.append(t1)
                t1.start()

            # Query Counters
            tq1 = 0
            tq1resp = []

            # Wait for all of them to finish
            for x in threads1:
                qc, ra = x.join()
                tq1 = tq1 + qc
                tq1resp.extend(ra)

            print("{} : Threads {} : BatchSize {} : InsertsPerSecond {} respP90 : {}".format(tab, numThreads, currentBatchSize, tq1*currentBatchSize/runtime, numpy.percentile(tq1resp,90)))
            mycon = psycopg2.connect(connStr)
            updateTestRun(mycon, runid, tq1*currentBatchSize, numpy.percentile(tq1resp,90))
            mycon.close()

            time.sleep(90)

exit()