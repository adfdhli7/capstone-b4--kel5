import http from 'k6/http';
import { check, sleep } from 'k6';

// Konfigurasi Beban (Simulasi Lonjakan / Peak Load)
export const options = {
  stages: [
    { duration: '10s', target: 50 },  // Pemanasan: naik perlahan ke 50 user aktif
    { duration: '30s', target: 300 }, // Peak Load: ledakan ke 300 user aktif secara bersamaan!
    { duration: '10s', target: 0 },   // Pendinginan: turun kembali ke 0
  ],
  thresholds: {
    // Menetapkan Target SLO (Service Level Objective) untuk Laporan
    http_req_duration: ['p(95)<500'], // Latency p95 harus di bawah 500ms
  },
};

export default function () {
  const url = 'http://localhost:8080/transaction';
  
  // Membuat user_id acak antara 1000 - 9999
  const userId = Math.floor(Math.random() * 8999) + 1000;
  
  // Karena API kita menggunakan Query Parameter, kita masukkan di URL
  const res = http.post(`${url}?user_id=${userId}&amount=50000`);

  // Pengecekan hasil (Sama seperti Nginx/Python, kita cek lolos atau ditolak)
  check(res, {
    '✅ Status 200 (Masuk Antrean)': (r) => r.status === 200,
    '🛡️ Status 429/503 (Ditolak Nginx/Rate Limit)': (r) => r.status === 429 || r.status === 503,
  });

  // mencegah crash
  sleep(0.01);
}