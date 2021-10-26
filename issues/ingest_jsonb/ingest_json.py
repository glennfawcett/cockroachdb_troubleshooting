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
        bigfastvals = bigfastvals + '"k' + str(random.randint(1, randomRange)) + '":"' + str(random.randint(1, randomRange)) + '"'
        if (i != numberOfPairs - 1):
            bigfastvals = bigfastvals + ','

    bigfastvals = bigfastvals + "}'" 
    
    return bigfastvals

def crJSONrowVals(numOfValues, numberOfPairs, randomRange): 
    ## Create Value string for insert
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
    
    return vstring

def qj1(jTable, numOfValues, numberOfPairs, randomRange):
    qTemplate = """
    INSERT INTO {} (id, ts0, k1, k2, k3, k4, k5, v1, v2, v3, v4, v5, j) 
    VALUES {}
    """
    # print("{}".format(qTemplate.format(bigfastvals)))
    return (qTemplate.format(jTable, crJSONrowVals(numOfValues, numberOfPairs, randomRange)))


def worker_steady(num, tpsPerThread, dbstr, runtime, qFunc, jtable, valsPerJSON, distIntPerVal, vsize):
    """ingest worker:: Lookup valid session and then account"""
    print("Worker Steady State")
    valsPerJSON = 10
    distIntPerVal = 10000

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

                # Run the query from qFunc
                # cur.execute(qFunc(varray)+";\n"+qFunc(varray)+";")
                cur.execute(qFunc(jtable, valsPerJSON, distIntPerVal, vsize))
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
    j JSON
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
    j JSON
);
"""

mycon = psycopg2.connect(connStr)
onestmt(mycon, crBase)
onestmt(mycon, crInverted)
onestmt(mycon, crStoring)



# Misc Values
valsPerJSON = 10
distIntPerVal = 10000


# Runtime Per Table
runtime = 10
QPS = 0

# Define Tables to Test
tables = ['jtable_base', 'jtable_inverted', 'jtable_storing']

# Define batch size tests
batchSize = [1, 2, 4, 6, 8, 10]

# Number of Threads
threadsToRun = [1, 2]

for tab in tables:
    print ("Inserting to table: {}".format(tab))

    for numThreads in batchSize:
        print("Threads : {}".format(numThreads))
        qpsPerThread = QPS/numThreads

        for currentBatchSize in batchSize:
            print ("Insert BatchSize: {}".format(currentBatchSize))

            threads1 = []
            for i in range(numThreads):
                t1 = ThreadWithReturnValue(target=worker_steady, args=((i+1), qpsPerThread, connStr, runtime, qj1, tab, valsPerJSON, distIntPerVal, currentBatchSize))
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

            print("{} Total Inserts : {}".format(tab, tq1*currentBatchSize))
            print("{} Total Threads : {}".format(tab, numThreads))
            print("{} BatchSize : {}".format(tab, currentBatchSize))        
            print("{} InsertsPerSecond : {}".format(tab, tq1*currentBatchSize/runtime))
            print("{} respP90 : {}".format(tab, numpy.percentile(tq1resp,90)))

            time.sleep(1)

exit()

