import http from 'k6/http';
import { check, sleep } from 'k6';
import { textSummary } from 'https://jslib.k6.io/k6-summary/0.1.0/index.js';

// Konfigurasi buat load test Baseline (agar beban lebih stabil)
export const options = {
  stages: [
    { duration: '1s', target: 10 }, // Menjaga 10 VU secara stabil selama 30 detik
    { duration: '29s', target: 10 }, // Menjaga 10 VU secara stabil selama 30 detik
  ],
  thresholds: {
    'http_req_duration{name:POST /transaction}': ['p(95)<500'], // Latency Write p95
    'http_req_duration{name:GET /inquiry}': ['p(95)<500'],      // Latency Read p95
  },
};

export default function () {
  const url = 'http://localhost:8080'; 
  
  // memmbuat user_id acak antara 1000 - 9999
  const userId = Math.floor(Math.random() * 8999) + 1000;
  
  // bagian write untuk melakukan transaksi baru
  const writeRes = http.post(
    `${url}/transaction?user_id=${userId}&amount=50000`,
    null,
    { tags: { name: 'POST /transaction' } }
  );

  // cek hasil write
  check(writeRes, {
    '📝 Write Status 200 (Masuk Antrean)': (r) => r.status === 200,
  });

  // bagian read untuk melakukan inquiry jika write berhasil
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

      // cek hasil read
      check(readRes, {
        '🔍 Read Status 200 (Sukses Membaca)': (r) => r.status === 200,
      });
    }
  }

  // mencegah crash dan mengurangi beban CPU k6
  sleep(0.01);
}

export function handleSummary(data) {
  const timestamp = new Date()
    .toISOString()
    .replace(/[:.]/g, '-');

  return {
    [`load-test/results/summary-baseline-test-${timestamp}.json`]: JSON.stringify(data, null, 2),
    stdout: textSummary(data, { indent: ' ', enableColors: true }),
  };
}