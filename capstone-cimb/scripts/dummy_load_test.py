import requests
import concurrent.futures
import time
import random

API_URL = "http://localhost:8080/transaction"
CONCURRENCY = 50  # Jumlah "pekerja" yang mengirim bersamaan

def send_transaction():
    user_id = random.randint(1, 10000)
    try:
        response = requests.post(f"{API_URL}?user_id={user_id}&amount=50000", timeout=2)
        
        # Menerjemahkan status code menjadi teks
        if response.status_code == 200:
            return "Sukses"
        elif response.status_code == 503:
            return "Gagal (Ditolak Sistem)"
        else:
            return "Gagal (Lainnya)"
            
    except:
        return "Gagal (Timeout)"

print("======================================================")
print(" Memulai Serangan Real-Time...")
print("======================================================")

try:
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        while True:
            # Membuat gelombang trafik yang dinamis (kadang 50 request, kadang 200 request)
            gelombang_trafik = random.randint(50, 200) 
            
            futures = [executor.submit(send_transaction) for _ in range(gelombang_trafik)]
            
            status_counts = {}
            for future in concurrent.futures.as_completed(futures):
                status = future.result()
                status_counts[status] = status_counts.get(status, 0) + 1
            
            waktu_sekarang = time.strftime('%H:%M:%S')
            print(f"[{waktu_sekarang}] mengirim {gelombang_trafik} request -> Hasil: {status_counts}")
            
            # Beri jeda 1 detik sebelum gelombang serangan berikutnya
            time.sleep(1) 

except KeyboardInterrupt:
    print("\n Serangan dihentikan oleh pengguna.")