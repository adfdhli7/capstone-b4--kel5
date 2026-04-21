import requests
import concurrent.futures
import time

API_URL = "http://localhost:8080/transaction"
TOTAL_REQUESTS = 1000  # Ubah ke 10000 untuk simulasi ekstrim
CONCURRENCY = 50       # Berapa user yang menembak bersamaan

def send_transaction(user_id):
    try:
        response = requests.post(f"{API_URL}?user_id={user_id}&amount=50000", timeout=2)
        return response.status_code
    except:
        return "TIMEOUT"

print(f"Memulai serangan: {TOTAL_REQUESTS} request dengan {CONCURRENCY} concurrency...")
start_time = time.time()

status_counts = {}
with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
    futures = [executor.submit(send_transaction, i) for i in range(TOTAL_REQUESTS)]
    for future in concurrent.futures.as_completed(futures):
        status = future.result()
        status_counts[status] = status_counts.get(status, 0) + 1

end_time = time.time()

print("\n=== HASIL LOAD TEST ===")
print(f"Waktu Total: {end_time - start_time:.2f} detik")
print("Distribusi Status HTTP:")
for status, count in status_counts.items():
    if status == 200:
        print(f"✅ 200 OK (Masuk Antrean): {count}")
    elif status == 503:
        print(f"🛡️ 503 Rate Limited (Proteksi Nginx Bekerja): {count}")
    else:
        print(f"❌ {status} (Error/Timeout): {count}")