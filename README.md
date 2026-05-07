# Capstone-b4--kel5
## Penggunaan

Build container:

```
cd capstone-cimb
docker compose up -d --build
```
---
Cara menjalankan program (default 1 worker-service dan 1 api-service):
```
docker compose up -d
```
---
Cara menjalankan program dengan jumlah worker-service dan api-service tertentu (contoh 3 api-service dan 7 worker-service):
```
docker compose up --scale api-service=3 --scale worker-service=7 -d
```
---
Setiap ada perubahan program, build ulang container:
```
docker compose down
docker compose up -d --build

# Jika mau langsung beberapa api-service atau worker-service:

docker compose up --scale api-service=3 --scale worker-service=7 -d --build
```