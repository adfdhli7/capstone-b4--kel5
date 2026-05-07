from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import redis
import psycopg2
import json
import uuid
from prometheus_fastapi_instrumentator import Instrumentator
import time
from redis.exceptions import TimeoutError

app = FastAPI(title="CIMB Peak Load API")
redis_client = redis.Redis(
    host='redis',
    port=6379,
    db=0,
    decode_responses=True,
    socket_timeout=2,
    socket_connect_timeout=2
)

MAX_QUEUE_SIZE = 1000
FAILURE_THRESHOLD = 5
RECOVERY_TIMEOUT = 10

failure_count = 0
circuit_open = False
last_failure_time = 0

# Integrasi Prometheus Metrics
Instrumentator(
    should_group_status_codes=False,
).instrument(app).expose(app)

def get_db_connection():
    return psycopg2.connect("dbname=cimb_db user=admin password=password host=postgres")

# Saat API menyala, buat tabel jika belum ada
@app.on_event("startup")
def startup_event():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id VARCHAR(50) PRIMARY KEY,
            user_id INT,
            amount DECIMAL,
            status VARCHAR(20)
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

# ENDPOINT WRITE (Masuk ke Message Queue)
@app.post("/transaction")
async def create_transaction(user_id: int, amount: float):
    if is_circuit_open():
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "message": "Circuit breaker active"
            }
        )
    
    global failure_count, circuit_open, last_failure_time

    # Backpressure Check
    queue_size = redis_client.llen("tx_queue")

    if queue_size >= MAX_QUEUE_SIZE:
        return JSONResponse(
            status_code=503,
            content={
                "queue_size": queue_size,
                "status": "error",
                "message": "Queue overload, try again later"
            }
        )

    tx_id = str(uuid.uuid4())
    payload = {"id": tx_id, "user_id": user_id, "amount": amount, "status": "PENDING"}
    
    # Push ke Redis Queue
    try:
        redis_with_retry(
            lambda: redis_client.lpush(
                "tx_queue",
                json.dumps(payload)
            )
        )

        failure_count = 0  # Reset failure count on success

    except Exception:
        failure_count += 1

        if failure_count >= FAILURE_THRESHOLD:
            circuit_open = True
            last_failure_time = time.time()

        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "message": "Redis unavailable"
            }
        )
    
    # Simpan status sementara di Cache agar bisa langsung di-inquiry
    redis_with_retry(
        lambda: redis_client.setex(
            f"tx_status:{tx_id}",
            300,
            "PENDING"
        )
    )
    
    return {"message": "Transaction queued", "tx_id": tx_id}

# ENDPOINT READ (Caching Strategy)
@app.get("/inquiry/{tx_id}")
async def transaction_inquiry(tx_id: str):
    # 1. Cek Redis Cache dulu (Sangat Cepat)
    cached_status = redis_client.get(f"tx_status:{tx_id}")
    if cached_status:
        return {"tx_id": tx_id, "status": cached_status, "source": "cache"}
    
    # 2. Jika tidak ada di cache, baru cek Database (Lebih Lambat)
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT status FROM transactions WHERE id = %s", (tx_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    
    if result:
        # Simpan ke cache untuk request berikutnya
        redis_client.setex(f"tx_status:{tx_id}", 300, result[0])
        return {"tx_id": tx_id, "status": result[0], "source": "database"}
    
    raise HTTPException(status_code=404, detail="Transaction not found")

def redis_with_retry(operation, retries=3, delay=1):
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
        elapsed = time.time() - last_failure_time

        # HALF-OPEN setelah timeout
        if elapsed > RECOVERY_TIMEOUT:
            circuit_open = False
            return False

        return True

    return False