import http from 'k6/http';
import { check, sleep } from 'k6';
import { textSummary } from 'https://jslib.k6.io/k6-summary/0.1.0/index.js';

// konfigurasi untuk load test dengan beberapa tahap dan target SLO untuk latency Read dan Write
export const options = {
  stages: [
    // { duration: '10s', target: 30 },   // normal load
    // { duration: '1s', target: 500 },   // instant spike
    // { duration: '19s', target: 500 },  // hold spike
    // { duration: '1s', target: 30 },    // instant recovery
    // { duration: '9s', target: 30 },    // hold normal
    // { duration: '5s', target: 0 },
    
    { duration: '10s', target: 10 },   // normal load
    { duration: '1s', target: 10 },   // instant spike
    { duration: '19s', target: 10 },  // hold spike
    { duration: '1s', target: 10 },    // instant recovery
    { duration: '9s', target: 10 },    // hold normal
    { duration: '5s', target: 0 },
  ],
  thresholds: {
    // memisahkan target SLO antara Read dan Write menggunakan 'tags'
    'http_req_duration{name:POST /transaction}': ['p(95)<500'], // latency Write p95 
    'http_req_duration{name:GET /inquiry}': ['p(95)<500'],      // latency Read p95 (Diperbarui)
  },
};

export default function () {
  const url = 'http://localhost:8080';
  
  // membuat user_id acak antara 1000 - 9999
  const userId = Math.floor(Math.random() * 8999) + 1000;
  
  // bagian write untuk melakukan transaksi baru
  const writeRes = http.post(
    `${url}/transaction?user_id=${userId}&amount=50000`,
    null,
    {
      tags: { name: 'POST /transaction' }
    }
  );

  // Cek hasil Write
  check(writeRes, {
    '📝 Write Status 200 (Masuk Antrean)': (r) => r.status === 200,
    // '🛡️ Write Status 429/503 (Ditolak Sistem)': (r) => r.status === 429 || r.status === 503,
  });

  // bagian read untuk melakukan inquiry jika write berhasil
  if (writeRes.status === 200) {
    let txId = null;
    
    // Parse response body untuk mendapatkan tx_id
    try {
      const body = writeRes.json();
      txId = body.tx_id;
    } catch (e) {
      console.error('Gagal parsing JSON dari response POST');
    }

    // Jika tx_id didapatkan, lakukan inquiry
    if (txId) {
      const readRes = http.get(
        `${url}/inquiry/${txId}`, 
        {
          tags: { name: 'GET /inquiry' } // Tag diperbarui agar sesuai threshold
        }
      );

      // Cek hasil Read
      check(readRes, {
        '🔍 Read Status 200 (Sukses Membaca)': (r) => r.status === 200,
      });
    }
  }

  // mencegah crash dan mengurangi beban CPU k6
  sleep(0.01);
}


// export function handleSummary(data) {
//   const timestamp = new Date()
//     .toISOString()
//     .replace(/[:.]/g, '-');

//   return {
//     [`load-test/results/summary-${timestamp}.json`]: JSON.stringify(data, null, 2),
//     stdout: textSummary(data, { indent: ' ', enableColors: true }),
//   };
// }