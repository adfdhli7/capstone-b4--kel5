from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, Response
import redis.asyncio as redis
import json
import uuid
from prometheus_fastapi_instrumentator import Instrumentator
import time
from redis.exceptions import TimeoutError
from psycopg_pool import AsyncConnectionPool
from prometheus_client import Counter, generate_latest
# from contextlib import asynccontextmanager

db_pool = AsyncConnectionPool(
    conninfo=(
        "dbname=cimb_db "
        "user=admin "
        "password=password "
        "host=postgres "
        "port=5432"
    ),
    min_size=5,
    max_size=100,
    open=False
)

app = FastAPI(title="CIMB Peak Load API")

pool = redis.ConnectionPool(
    host="redis",
    port=6379,
    db=0,
    decode_responses=True,
    max_connections=2000,
    socket_timeout=5,
    socket_connect_timeout=5,
)

redis_client = redis.Redis(
    connection_pool=pool
)

MAX_QUEUE_SIZE = 10000
FAILURE_THRESHOLD = 5
RECOVERY_TIMEOUT = 10

failure_count = 0
circuit_open = False
last_failure_time = 0

# Integrasi Prometheus Metrics
# Instrumentator().instrument(app).expose(app)

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP Requests",
    ["method", "status"]
)

@app.get("/metrics")
async def metrics():
    return Response(
        content=generate_latest(),
        media_type="text/plain"
    )

@app.on_event("startup")
async def startup_event():
    await db_pool.open()

    async with db_pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id VARCHAR(50) PRIMARY KEY,
                    user_id INT,
                    amount DECIMAL,
                    status VARCHAR(20)
                )
            """)
        
        await conn.commit()

@app.on_event("shutdown")
async def shutdown_event():
    await db_pool.close()

# ENDPOINT WRITE (Masuk ke Message Queue)
@app.post("/transaction")
async def create_transaction(user_id: int, amount: float):
    
    if is_circuit_open():
        REQUEST_COUNT.labels(
            method="POST",
            status="503"
        ).inc()

        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "message": "Circuit breaker active"
            }
        )
    
    global failure_count, circuit_open, last_failure_time
    
    try:

        tx_id = str(uuid.uuid4())
        payload = {"id": tx_id, "user_id": user_id, "amount": amount, "status": "PENDING"}

        pipe = redis_client.pipeline()

        pipe.lpush(
            "tx_queue",
            json.dumps(payload)
        )

        pipe.setex(
            f"tx_status:{tx_id}",
            300,
            "PENDING"
        )

        await pipe.execute()

        failure_count = 0

        REQUEST_COUNT.labels(
            method="POST",
            status="200"
        ).inc()

        return {"message": "Transaction queued", "tx_id": tx_id}

    except Exception as e:

        print("REDIS ERROR:", e)

        try:
            async with db_pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        INSERT INTO transactions
                        (id, user_id, amount, status)
                        VALUES (%s,%s,%s,%s)
                        """,
                        (
                            tx_id,
                            user_id,
                            amount,
                            "SUCCESS"
                        )
                    )
                    
                await conn.commit()
                
            print("ADDED DATA WITH DATABASE")

            REQUEST_COUNT.labels(
                method="POST",
                status="200"
            ).inc()

            return {"message": "Transaction queried to Database", "tx_id": tx_id}

        except Exception as e:

            print("DATABASE ERROR:", e)

            failure_count += 1
            print("ERROR COUNT:", failure_count)

            if failure_count >= FAILURE_THRESHOLD:
                circuit_open = True
                last_failure_time = time.time()
            
            REQUEST_COUNT.labels(
                method="POST",
                status="503"
            ).inc()

            return JSONResponse(
                status_code=503,
                content={
                    "status": "error",
                    "message": "Redis and Database unavailable"
                }
            )

            

# ENDPOINT READ (Caching Strategy)
@app.get("/inquiry/{tx_id}")
async def transaction_inquiry(tx_id: str):
    
    cached_status = None

    try:
        # 1. Cek Redis Cache dulu (Sangat Cepat)
        cached_status = await redis_client.get(f"tx_status:{tx_id}")
    
    except Exception as e:

        print("REDIS ERROR:", e)
    
    
    if cached_status:    
        REQUEST_COUNT.labels(
            method="GET",
            status="200"
        ).inc()

        return {"tx_id": tx_id, "status": cached_status, "source": "cache"}

    # 2. Jika tidak ada di cache, baru cek Database (Lebih Lambat)

    try:
        async with db_pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT status FROM transactions WHERE id = %s",
                    (tx_id,)
                )

                result = await cur.fetchone()

        cur.close()

    except Exception as e:
        print("DB ERROR:", e)
    
    if result:

        try:
            # Simpan ke cache untuk request berikutnya
            await redis_client.setex(f"tx_status:{tx_id}", 300, result[0])
            print("CACHE STORE TO REDIS SUCCESSED")
        except:
            print("CACHE STORE TO REDIS FAILED")
                
        REQUEST_COUNT.labels(
            method="GET",
            status="200"
        ).inc()

        return {"tx_id": tx_id, "status": result[0], "source": "database"}
                
    REQUEST_COUNT.labels(
        method="GET",
        status="404"
    ).inc()
    
    raise HTTPException(status_code=404, detail="Transaction not found")

def redis_with_retry(operation, retries=1, delay=1):
    for attempt in range(retries):
        try:
            return operation()

        except TimeoutError:

            print(f"Retry attempt {attempt+1}")

            if attempt == retries - 1:
                raise

            time.sleep(delay)

def is_circuit_open():
    global circuit_open, last_failure_time

    if circuit_open:
        print("CIRCUIT OPEN")
        elapsed = time.time() - last_failure_time

        # HALF-OPEN setelah timeout
        if elapsed > RECOVERY_TIMEOUT:
            circuit_open = False
            return False

        return True

    return False