import http from 'k6/http';
import { check, sleep } from 'k6';
import { textSummary } from 'https://jslib.k6.io/k6-summary/0.1.0/index.js';

// Konfigurasi untuk simulasi Peak Load / Spike
export const options = {
  stages: [
    { duration: '1s', target: 30 },
    { duration: '9s', target: 30 },
    { duration: '1s', target: 500 },
    { duration: '19s', target: 500 },
    { duration: '1s', target: 30 },
    { duration: '10s', target: 30 },
    { duration: '5s', target: 0 },
  ],
  thresholds: {
    'http_req_duration{name:POST /transaction}': ['p(95)<500'], // Latency Write p95
    'http_req_duration{name:GET /inquiry}': ['p(95)<500'],      // Latency Read p95
  },
};

export default function () {
  const url = 'http://localhost:8080'; // Mengarah ke API Gateway (Nginx)[cite: 4, 5]
  
  // Membuat user_id acak antara 1000 - 9999
  const userId = Math.floor(Math.random() * 8999) + 1000;
  
  // Bagian write untuk melakukan transaksi baru
  const writeRes = http.post(
    `${url}/transaction?user_id=${userId}&amount=50000`,
    null,
    { tags: { name: 'POST /transaction' } }
  );

  // Cek hasil Write
  check(writeRes, {
    '📝 Write Status 200 (Masuk Antrean)': (r) => r.status === 200,
    // '🛡️ Write Status 429/503 (Ditolak Sistem)': (r) => r.status === 429 || r.status === 503, // Diaktifkan kembali untuk memantau proteksi Nginx/Circuit Breaker
  });

  // Bagian read untuk melakukan inquiry jika write berhasil
  if (writeRes.status === 200) {
    let txId = null;
    
    try {
      const body = writeRes.json();
      txId = body.tx_id;
    } catch (e) {
      console.error('Gagal parsing JSON dari response POST');
    }

    if (txId) {
      const readRes = http.get(
        `${url}/inquiry/${txId}`, 
        { tags: { name: 'GET /inquiry' } } 
      );

      check(readRes, {
        '🔍 Read Status 200 (Sukses Membaca)': (r) => r.status === 200,
      });
    }
  }

  // Mencegah crash dan mengurangi beban CPU k6
  sleep(0.01);
}

export function handleSummary(data) {
  const timestamp = new Date()
    .toISOString()
    .replace(/[:.]/g, '-');

  return {
    [`load-test/results/summary-peak-load-test-${timestamp}.json`]: JSON.stringify(data, null, 2),
    stdout: textSummary(data, { indent: ' ', enableColors: true }),
  };
}