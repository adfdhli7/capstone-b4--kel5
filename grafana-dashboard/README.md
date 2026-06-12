# Dashboard Grafana

Sistem menyediakan dua dashboard Grafana utama untuk memantau performa aplikasi dan hasil pengujian load testing secara real-time.

## Dashboard 1 - Container Resource Usage

![Container Resource Usage](screenshoot/container-dashboard.png)

Dashboard ini digunakan untuk memantau penggunaan resource seluruh container yang terlibat dalam sistem, baik API Service maupun Worker Service. Data diperoleh dari cAdvisor yang di-scrape oleh Prometheus.

### API Service Monitoring

#### Service Count

Menampilkan jumlah instance API Service yang sedang aktif.

Metric:

```promql
count(
  container_last_seen{
    container_label_com_docker_compose_service="api-service"
  }
)
```

Fungsi:

* Memastikan seluruh replica API berjalan.
* Memverifikasi hasil horizontal scaling.

---

#### API Service Total Memory Usage

Menampilkan total penggunaan memori seluruh instance API Service.

Metric:

```promql
sum(
  container_memory_usage_bytes{
    container_label_com_docker_compose_service="api-service"
  }
)
```

Fungsi:

* Mengukur konsumsi memori keseluruhan aplikasi.
* Mengidentifikasi kemungkinan memory leak.

---

#### API Service Total CPU Usage

Menampilkan total penggunaan CPU seluruh instance API Service.

Metric:

```promql
sum(
  rate(
    container_cpu_usage_seconds_total{
      container_label_com_docker_compose_service="api-service"
    }[1m]
  )
)
```

Fungsi:

* Mengetahui beban pemrosesan API.
* Membandingkan penggunaan CPU sebelum dan saat peak load.

---

#### API Service CPU Usage

Menampilkan penggunaan CPU masing-masing container API Service secara real-time.

Metric:

```promql
rate(container_cpu_usage_seconds_total{
  container_label_com_docker_compose_service="api-service"
}[1m])
```

Fungsi:

* Mengidentifikasi replica yang menerima beban lebih tinggi.
* Memverifikasi distribusi beban oleh Nginx Load Balancer.

---

#### API Service Memory Usage

Menampilkan penggunaan memori setiap container API Service.

Metric:

```promql
container_memory_usage_bytes{
  container_label_com_docker_compose_service="api-service"
}
```

Fungsi:

* Memantau konsumsi RAM tiap replica.
* Mengidentifikasi ketidakseimbangan penggunaan resource.

---

### Worker Monitoring

#### Worker Count

Menampilkan jumlah worker yang aktif.

Metric:

```promql
count(
  container_last_seen{
    container_label_com_docker_compose_service="worker-service"
  }
)
```

Fungsi:

* Memastikan seluruh worker berjalan.
* Memverifikasi mekanisme scaling worker.

---

#### Total Worker Memory Usage

Menampilkan total penggunaan memori seluruh worker.

Metric:

```promql
sum(
  container_memory_usage_bytes{
    container_label_com_docker_compose_service="worker-service"
  }
)
```

Fungsi:

* Mengetahui total kebutuhan RAM sistem pemrosesan transaksi.

---

#### Total Worker CPU Usage

Menampilkan total penggunaan CPU seluruh worker.

Metric:

```promql
sum(
  rate(
    container_cpu_usage_seconds_total{
      container_label_com_docker_compose_service="worker-service"
    }[1m]
  )
)
```

Fungsi:

* Mengukur beban pemrosesan transaksi di backend.

---

#### Worker CPU Usage

Menampilkan penggunaan CPU masing-masing worker.

Metric:

```promql
rate(container_cpu_usage_seconds_total{
  container_label_com_docker_compose_service="worker-service"
}[1m])
```

Fungsi:

* Mengidentifikasi worker yang mengalami bottleneck.
* Melihat distribusi beban antar worker.

---

#### Worker Memory Usage

Menampilkan penggunaan memori setiap worker secara individual.

Metric:

```promql
container_memory_usage_bytes{
  container_label_com_docker_compose_service="worker-service"
}
```

Fungsi:

* Memantau stabilitas worker selama peak load.
* Mengidentifikasi worker yang mengalami konsumsi memori berlebih.

---

## Dashboard 2 - K6 Monitoring

![K6 MOnitoring](screenshoot/k6-dashboard.png)

Dashboard ini digunakan untuk memonitor performa sistem selama proses load testing menggunakan K6.

### Konfigurasi K6 Metrics

Agar metrik K6 dapat dikirim ke Prometheus dan ditampilkan pada Grafana, jalankan script K6 menggunakan Prometheus Remote Write:

```bash
k6 run \
--out experimental-prometheus-rw=http://localhost:9090/api/v1/write \
load-test/peak_load_test.js
```

Contoh lain:

```bash
k6 run \
--out experimental-prometheus-rw=http://localhost:9090/api/v1/write \
load-test/baseline.js
```

```bash
k6 run \
--out experimental-prometheus-rw=http://localhost:9090/api/v1/write \
load-test/k6-benchmark.js
```

Tanpa parameter tersebut, dashboard Grafana tidak akan menerima metrik K6 secara real-time.

---

### All Request

Menampilkan throughput seluruh request yang dikirim K6.

Metric:

```promql
sum(rate(k6_http_reqs_total[1m]))
```

Dilengkapi dengan kurva:

```promql
sum(rate(k6_http_reqs_total{status="200"}[1m]))
```

untuk membandingkan total request dan request sukses.

---

### Total Request

Menampilkan jumlah seluruh request yang telah dikirim selama pengujian.

Metric:

```promql
sum(k6_http_reqs_total)
```

---

### Total 200 OK

Menampilkan total request yang berhasil diproses.

Metric:

```promql
sum(k6_http_reqs_total{status="200"})
```

---

### Total Success %

Menampilkan persentase keberhasilan seluruh request.

Metric:

```promql
sum(k6_http_reqs_total{status="200"})
/
sum(k6_http_reqs_total)
* 100
```

Fungsi:

* Menjadi indikator utama stabilitas sistem selama pengujian.

---

### POST Requests

Menampilkan throughput endpoint transaksi.

Metric:

```promql
sum(rate(k6_http_reqs_total{url="POST /transaction"}[1m]))
```

dan

```promql
sum(rate(k6_http_reqs_total{
  url="POST /transaction",
  status="200"
}[1m]))
```

Fungsi:

* Mengukur kemampuan sistem menerima transaksi baru.

---

### POST Total

Menampilkan total request transaksi.

Metric:

```promql
sum(k6_http_reqs_total{
  url="POST /transaction"
})
```

---

### POST 200 OK

Menampilkan jumlah transaksi yang berhasil diterima.

Metric:

```promql
sum(k6_http_reqs_total{
  status="200",
  url="POST /transaction"
})
```

---

### POST Success %

Menampilkan tingkat keberhasilan endpoint transaksi.

Metric:

```promql
sum(k6_http_reqs_total{
  status="200",
  url="POST /transaction"
})
/
sum(k6_http_reqs_total{
  url="POST /transaction"
})
*100
```

---

## Dashboard 3 - SLA Compliance

![SLA Compliance](screenshoot/sla-dashboard.png)

Dashboard ini digunakan untuk memantau **Service Level Agreement (SLA)** sistem secara real-time, dengan fokus pada availability, error rate, resource health, dan performa load testing.

### SLO Definitions

| SLO | Target | SLI | Sumber Data |
|-----|--------|-----|-------------|
| **Transaction Availability** | >= 99.5% | `(POST 200 / POST total) * 100` | http_requests_total (Prometheus) |
| **Inquiry Availability** | >= 99.0% | `(GET 200 / GET total) * 100` | http_requests_total (Prometheus) |
| **Circuit Breaker Uptime** | 0 failures | `sum(increase(503[5m])) = 0` | http_requests_total (Prometheus) |
| **API Replica Health** | 3/3 replicas running | `count(container_last_seen{api-service})` | cAdvisor |
| **Worker Replica Health** | 5/5 replicas running | `count(container_last_seen{worker-service})` | cAdvisor |
| **Latency (Load Test)** | p95 < 500ms | `histogram_quantile(0.95, k6_http_req_duration)` | K6 Remote Write |

---

### Row 1: SLO Compliance Summary

Menampilkan status SLO secara instan dengan warna:
- **Hijau**: SLO terpenuhi
- **Kuning**: Mendekati batas SLO (warning)
- **Merah**: SLO dilanggar

#### POST Availability

Menampilkan persentase keberhasilan endpoint transaksi dalam 5 menit terakhir.

Metric:
```promql
100 - (sum(rate(http_requests_total{method="POST",status="503"}[5m])) 
       / sum(rate(http_requests_total{method="POST"}[5m])) * 100)
```

Threshold:
- **Hijau**: >= 99.5% (SLO terpenuhi)
- **Kuning**: >= 99%
- **Merah**: < 99% (SLO dilanggar)

---

#### GET Availability

Menampilkan persentase keberhasilan endpoint inquiry dalam 5 menit terakhir.

Metric:
```promql
(sum(rate(http_requests_total{method="GET",status="200"}[5m])) 
 / sum(rate(http_requests_total{method="GET"}[5m]))) * 100
```

Threshold:
- **Hijau**: >= 99%
- **Kuning**: >= 95%
- **Merah**: < 95%

---

#### Circuit Breaker

Menampilkan status circuit breaker. Hijau = CLOSED (normal), Merah = OPEN (sedang menolak request).

Metric:
```promql
sum(increase(http_requests_total{method="POST",status="503"}[5m]))
```

Nilai:
- **0** = Circuit breaker CLOSED (hijau)
- **> 0** = Circuit breaker OPEN atau error terjadi (merah)

---

#### API Replicas

Menampilkan jumlah instance API Service yang aktif.

Metric:
```promql
count(container_last_seen{
  container_label_com_docker_compose_service="api-service"
})
```

Threshold: 3 = hijau, < 3 = merah

---

#### Worker Replicas

Menampilkan jumlah Worker Service yang aktif.

Metric:
```promql
count(container_last_seen{
  container_label_com_docker_compose_service="worker-service"
})
```

Threshold: 5 = hijau, < 5 = merah

---

### Row 2: Availability & Error Trends

#### POST Availability Trend

Grafik availability endpoint transaksi dari waktu ke waktu, dengan garis SLO target di 99.5%.

Metric:
```promql
100 - (rate(http_requests_total{method="POST",status="503"}[1m]) 
       / rate(http_requests_total{method="POST"}[1m]) * 100)
```

---

#### GET Availability Trend

Grafik availability endpoint inquiry dari waktu ke waktu, dengan garis SLO target di 99%.

Metric:
```promql
rate(http_requests_total{method="GET",status="200"}[1m]) 
/ rate(http_requests_total{method="GET"}[1m]) * 100
```

---

### Row 3: Error & Circuit Breaker

#### Error Rate

Menampilkan rate error 503 (circuit breaker / database failure) dan 404 (transaksi tidak ditemukan).

Metrics:
```promql
# 503 - POST (circuit breaker / DB error)
rate(http_requests_total{method="POST",status="503"}[1m])

# 404 - GET (not found)
rate(http_requests_total{method="GET",status="404"}[1m])
```

---

### Row 4: Service Resource Health

Menampilkan penggunaan CPU dan memory per container untuk API Service dan Worker Service.

#### API Service CPU Usage (per container)

```promql
rate(container_cpu_usage_seconds_total{
  container_label_com_docker_compose_service="api-service"
}[1m])
```

#### API Service Memory (per container)

```promql
container_memory_usage_bytes{
  container_label_com_docker_compose_service="api-service"
}
```

#### Worker Service CPU Usage (per container)

```promql
rate(container_cpu_usage_seconds_total{
  container_label_com_docker_compose_service="worker-service"
}[1m])
```

#### Worker Service Memory (per container)

```promql
container_memory_usage_bytes{
  container_label_com_docker_compose_service="worker-service"
}
```

---

### Row 5: Load Test Performance (K6)

Panel ini hanya aktif saat load testing K6 berjalan dengan Prometheus Remote Write.

#### Throughput (K6)

Menampilkan request rate selama load testing.

Metrics:
```promql
# Total requests per second
sum(rate(k6_http_reqs_total[1m]))

# Successful requests per second
sum(rate(k6_http_reqs_total{status="200"}[1m]))
```

---

#### Latency Percentiles (K6)

Menampilkan response time percentiles (p50, p95, p99) dengan SLO target p95 < 500ms.

Metrics:
```promql
# p50 latency
histogram_quantile(0.50, sum(rate(k6_http_req_duration_bucket[1m])) by (le))

# p95 latency (SLO target: < 500ms)
histogram_quantile(0.95, sum(rate(k6_http_req_duration_bucket[1m])) by (le))

# p99 latency
histogram_quantile(0.99, sum(rate(k6_http_req_duration_bucket[1m])) by (le))
```

---

### GET Requests

Menampilkan throughput endpoint inquiry.

Metric:

```promql
sum(rate(k6_http_reqs_total{
  url="GET /inquiry"
}[1m]))
```

dan

```promql
sum(rate(k6_http_reqs_total{
  url="GET /inquiry",
  status="200"
}[1m]))
```

Fungsi:

* Mengukur kemampuan sistem melayani pengecekan status transaksi.

---

### GET Total

Menampilkan total request inquiry.

Metric:

```promql
sum(k6_http_reqs_total{
  url="GET /inquiry"
})
```

---

### GET 200 OK

Menampilkan total inquiry yang berhasil.

Metric:

```promql
sum(k6_http_reqs_total{
  status="200",
  url="GET /inquiry"
})
```

---

### GET Success %

Menampilkan tingkat keberhasilan endpoint inquiry.

Metric:

```promql
sum(k6_http_reqs_total{
  status="200",
  url="GET /inquiry"
})
/
sum(k6_http_reqs_total{
  url="GET /inquiry"
})
*100
```

---