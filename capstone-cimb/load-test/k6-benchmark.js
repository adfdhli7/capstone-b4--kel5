import http from 'k6/http';
import { check, sleep } from 'k6';

// konfigurasi untuk load test dengan beberapa tahap dan target SLO untuk latency Read dan Write
export const options = {
  stages: [
    { duration: '10s', target: 50 },  
    { duration: '20s', target: 10 },
    { duration: '20s', target: 50 },
    { duration: '20s', target: 100 },
    { duration: '20s', target: 200 },
    { duration: '30s', target: 300 }, 
    { duration: '10s', target: 0 },   
  ],
  thresholds: {
    // memisahkan target SLO antara Read dan Write menggunakan 'tags'
    'http_req_duration{name:POST /transaction}': ['p(95)<500'], // latency Write p95 
    'http_req_duration{name:GET /transaction}': ['p(95)<500'],  // latency Read p95 
  },
};

export default function () {
  const url = 'http://localhost:8080/transaction';
  
  // Membuat user_id acak antara 1000 - 9999
  const userId = Math.floor(Math.random() * 8999) + 1000;
  
  // bagian write untuk membuat transaksi baru
  const writeRes = http.post(
    `${url}?user_id=${userId}&amount=50000`,
    null,
    {
      tags: { name: 'POST /transaction' }
    }
  );

  // bagian read untuk membaca data transaksi yang dibuat
  const readRes = http.get(
    `${url}?user_id=${userId}`, 
    {
      tags: { name: 'GET /transaction' }
    }
  );

  // bagian pengecekan hasil write dan read
  check(writeRes, {
    '📝 Write Status 200 (Masuk Antrean)': (r) => r.status === 200,
    '🛡️ Write Status 429/503 (Ditolak Nginx)': (r) => r.status === 429 || r.status === 503,
  });

  check(readRes, {
    '🔍 Read Status 200 (Sukses Membaca)': (r) => r.status === 200,
  });

  // mencegah crash
  sleep(0.01);
}