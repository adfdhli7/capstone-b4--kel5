# CIMB Peak Load Resilient Transaction System

## Deskripsi Proyek

Proyek ini merupakan implementasi arsitektur sistem transaksi perbankan yang dirancang untuk tetap responsif saat menghadapi lonjakan trafik (peak load). Sistem menerapkan pendekatan asynchronous processing menggunakan Redis sebagai message queue, worker Golang sebagai pemroses transaksi, PostgreSQL sebagai penyimpanan utama, serta Redis cache untuk mempercepat proses inquiry.

Selain itu, sistem dilengkapi dengan:

* Load balancing menggunakan Nginx
* Monitoring menggunakan Prometheus dan Grafana
* Stress testing menggunakan K6
* Circuit Breaker untuk meningkatkan resiliency ketika Redis dan Database mengalami kegagalan

Arsitektur ini mensimulasikan pola transaksi pada sistem perbankan modern yang memisahkan proses penerimaan transaksi dan pemrosesan transaksi agar tetap stabil saat menerima beban tinggi.

---

# Arsitektur Sistem

```text
Client / K6
      │
      ▼
+-------------+
|    Nginx    |
| API Gateway |
+-------------+
      │
      ▼
+------------------+
| FastAPI Service  |
| (3 Replicas)     |
+------------------+
      │
      ▼
+-------------+
|    Redis    |
| Message Q.  |
+-------------+
      │
      ▼
+------------------+
| Golang Workers   |
| (5 Replicas)     |
+------------------+
      │
      ▼
+-------------+
| PostgreSQL  |
+-------------+

Monitoring:
Prometheus + Grafana + cAdvisor
```

---

# Teknologi yang Digunakan

| Komponen         | Teknologi        |
| ---------------- | ---------------- |
| API Service      | FastAPI (Python) |
| Worker Service   | Golang           |
| Message Queue    | Redis            |
| Database         | PostgreSQL       |
| Load Balancer    | Nginx            |
| Monitoring       | Prometheus       |
| Visualization    | Grafana          |
| Containerization | Docker Compose   |
| Load Testing     | K6               |

---

# Struktur Direktori

```text
capstone-cimb/
│
├── docker-compose.yml
│
├── infra/
│   ├── nginx.conf
│   └── prometheus.yml
│
├── services/
│   ├── api-python/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── main.py
│   │
│   └── worker-golang/
│       ├── Dockerfile
│       ├── go.mod
│       ├── go.sum
│       └── main.go
│
├── load-test/
│   ├── baseline.js
│   ├── k6-benchmark.js
│   ├── peak_load_test.js
│   └── results/
│
└── scripts/
    └── dummy_load_test.py

grafana-dashboard/
├── dashboard-container.json
└── dashboard-k6.json
```

---

# Penjelasan Setiap Direktori

## docker-compose.yml

File utama untuk menjalankan seluruh layanan:

* Nginx API Gateway
* FastAPI Service
* Golang Worker
* Redis
* PostgreSQL
* Prometheus
* Grafana
* cAdvisor

---

## infra/

### nginx.conf

Konfigurasi load balancer.

Fitur:

* Least Connection Load Balancing
* Distribusi request ke 3 instance FastAPI
* Reverse Proxy ke Application Layer

Target upstream:

```nginx
capstone-cimb-api-service-1
capstone-cimb-api-service-2
capstone-cimb-api-service-3
```

---

### prometheus.yml

Konfigurasi scraping Prometheus.

Target monitoring:

* FastAPI Service
* cAdvisor Container Metrics

Interval scraping:

```yaml
scrape_interval: 5s
```

---

## services/api-python

Application Layer yang menerima request dari client.

### Endpoint

#### POST /transaction

Membuat transaksi baru.

Parameter:

```text
user_id
amount
```

Contoh:

```http
POST /transaction?user_id=1001&amount=50000
```

Response:

```json
{
  "message":"Transaction queued",
  "tx_id":"..."
}
```

---

#### GET /inquiry/{tx_id}

Melakukan pengecekan status transaksi.

Contoh:

```http
GET /inquiry/12345
```

Response:

```json
{
  "tx_id":"12345",
  "status":"SUCCESS",
  "source":"cache"
}
```

atau

```json
{
  "tx_id":"12345",
  "status":"SUCCESS",
  "source":"database"
}
```

---

### Fitur Resiliency

#### Circuit Breaker

Aktif apabila Redis dan Database gagal secara berulang.

Konfigurasi:

```python
FAILURE_THRESHOLD = 5
RECOVERY_TIMEOUT = 10
```

Jika threshold tercapai:

```http
503 Service Unavailable
```

---

### Cache Strategy

Alur inquiry:

```text
Redis Cache
    ↓ miss
PostgreSQL
    ↓
Store kembali ke Redis
```

Tujuan:

* Mengurangi query database
* Mempercepat response inquiry

---

## services/worker-golang

Background worker untuk memproses transaksi secara asynchronous.

### Mekanisme

1. Mengambil data dari Redis Queue
2. Parsing payload transaksi
3. Memproses transaksi
4. Menyimpan hasil ke PostgreSQL

Jumlah worker thread:

```go
const WORKER_COUNT = 20
```

---

## Redis

Digunakan sebagai:

### Message Queue

```text
tx_queue
```

untuk antrean transaksi.

### Cache

```text
tx_status:<transaction_id>
```

untuk menyimpan status transaksi.

---

## PostgreSQL

Tabel utama:

```sql
transactions
```

Struktur:

```sql
id
user_id
amount
status
```

---

# Monitoring

## Prometheus

Mengumpulkan metrics dari:

* FastAPI
* cAdvisor

Akses:

```text
http://localhost:9090
```

---

## Grafana

Akses:

```text
http://localhost:3000
```

Default Login:

```text
username: admin
password: admin
```

---

# Dashboard Grafana

Informasi detail mengenai dashboard grafana lihat REAMDE.md di direktori grafana-dashboard

# Load Testing

Direktori:

```text
load-test/
```

## baseline.js

Pengujian baseline untuk mengetahui performa normal sistem.

Tujuan:

* Mengukur latency normal
* Menentukan baseline throughput

---

## peak_load_test.js

Simulasi lonjakan trafik.

Skenario:

```text
30 VU
 ↓
500 VU
 ↓
30 VU
 ↓
0 VU
```

Threshold:

```javascript
p(95) < 500ms
```

untuk:

* POST /transaction
* GET /inquiry

---

## Menjalankan Load Test

Baseline Test:

```bash
k6 run --out experimental-prometheus-rw=http://localhost:9090/api/v1/write baseline.js
```

Peak Load Test:

```bash
k6 run --out experimental-prometheus-rw=http://localhost:9090/api/v1/write peak_load_test.js
```

## Output Hasil Load Testing

Setiap script K6 akan menghasilkan file summary otomatis yang disimpan pada direktori:

```text
load-test/results/
```

Contoh file yang dihasilkan:

```text
summary-peak-load-test-2026-06-06T15-37-40-581Z.json
summary-baseline-test-2026-06-10T09-15-24-112Z.json
```

File summary berisi:

* Total requests
* Success rate
* Failure rate
* Average response time
* P95 latency
* Throughput
* Detail threshold K6

File ini dapat digunakan sebagai data pendukung analisis performa sistem dan dokumentasi hasil pengujian.

---

# Menjalankan Proyek

## 1. Clone Repository

```bash
git clone <repository-url>
cd capstone-cimb
```

---

## 2. Jalankan Seluruh Service

```bash
docker compose up --build
```

---

## 3. Verifikasi Container

```bash
docker ps
```

Pastikan seluruh container berjalan:

* api-gateway
* api-service
* worker-service
* postgres
* redis
* prometheus
* grafana
* cadvisor

---

## 4. Uji Endpoint

Membuat transaksi:

```bash
curl -X POST \
"http://localhost:8080/transaction?user_id=1001&amount=50000"
```

---

Cek transaksi:

```bash
curl http://localhost:8080/inquiry/<tx_id>
```

---

# Konsep Resiliency yang Diimplementasikan

<p style="font-size: 16px"><strong>Load Balancing</strong> - Menggunakan Nginx Least Connection.</p>

<p style="font-size: 16px"><strong>Asynchronous Processing</strong> - Redis Queue + Worker Pool.</p>

<p style="font-size: 16px"><strong>Cache Aside</strong> Pattern - Redis Cache + PostgreSQL.</p>

<p style="font-size: 16px"><strong>Circuit Breaker</strong> - Proteksi ketika Redis dan PostgreSQL gagal.</p>

<p style="font-size: 16px"><strong>Horizontal Scaling</strong> - FastAPI:</p>

```yaml
replicas: 3
```

Worker:

```yaml
replicas: 5
```

---

# Tujuan Pengujian

Proyek ini dibuat untuk mengevaluasi kemampuan sistem transaksi dalam:

* Menangani peak load
* Mengurangi bottleneck database
* Memanfaatkan cache untuk mempercepat inquiry
* Menguji efektivitas load balancing
* Mengukur penggunaan resource container
* Mengimplementasikan resiliency pattern pada arsitektur microservices

---

# Anggota Kelompok

| Nama                              | NIM               |
| ----------------------------------|-------------------|
David Divad Igyou Paradise Nababan  |	235150407111049
Sandya Freda                        |	235150401111042
Muhammad Fachri Abdurafi            |	235150400111025
Muhammad Radhi Rasyidi Rafli        |	235150307111041
Andi Muhammad Fadhli                |	235150301111036
Muhammad Omar Haqqi                 |	235150219111001