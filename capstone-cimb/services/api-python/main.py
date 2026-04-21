from fastapi import FastAPI, HTTPException
import redis
import psycopg2
import json
import uuid
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="CIMB Peak Load API")
redis_client = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)

# Integrasi Prometheus Metrics
Instrumentator().instrument(app).expose(app)

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
    tx_id = str(uuid.uuid4())
    payload = {"id": tx_id, "user_id": user_id, "amount": amount, "status": "PENDING"}
    
    # Push ke Redis Queue
    redis_client.lpush("tx_queue", json.dumps(payload))
    
    # Simpan status sementara di Cache agar bisa langsung di-inquiry
    redis_client.setex(f"tx_status:{tx_id}", 300, "PENDING") 
    
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