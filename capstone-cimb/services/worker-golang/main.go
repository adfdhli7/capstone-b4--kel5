package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"time"

	_ "github.com/lib/pq"
	"github.com/redis/go-redis/v9"
)

type Transaction struct {
	ID     string  `json:"id"`
	UserID int     `json:"user_id"`
	Amount float64 `json:"amount"`
	Status string  `json:"status"`
}

func main() {
	time.Sleep(5 * time.Second) // Tunggu DB & Redis siap

	// Koneksi DB
	db, err := sql.Open("postgres", "postgres://admin:password@postgres:5432/cimb_db?sslmode=disable")
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	// Koneksi Redis
	rdb := redis.NewClient(&redis.Options{Addr: "redis:6379"})
	ctx := context.Background()

	fmt.Println("Golang Worker Started. Listening to 'tx_queue'...")

	for {
		// BLPOP: Block sampai ada data di antrean "tx_queue"
		result, err := rdb.BLPop(ctx, 0, "tx_queue").Result()
		if err != nil {
			log.Println("Error reading queue:", err)
			continue
		}

		payload := result[1]
		var tx Transaction
		json.Unmarshal([]byte(payload), &tx)

		// Simulasi proses bank yang agak memakan waktu (200ms)
		time.Sleep(200 * time.Millisecond)
		tx.Status = "SUCCESS"

		// Simpan ke Database
		_, err = db.Exec("INSERT INTO transactions (id, user_id, amount, status) VALUES ($1, $2, $3, $4)",
			tx.ID, tx.UserID, tx.Amount, tx.Status)

		if err == nil {
			// Update Cache menjadi SUCCESS
			rdb.Set(ctx, "tx_status:"+tx.ID, "SUCCESS", 5*time.Minute)
			fmt.Printf("Processed TX: %s | User: %d | Amount: %.2f\n", tx.ID, tx.UserID, tx.Amount)
		} else {
			log.Println("DB Insert Error:", err)
		}
	}
}	