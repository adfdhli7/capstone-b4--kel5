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

const WORKER_COUNT = 20

func main() {

	time.Sleep(5 * time.Second)

	db, err := sql.Open(
		"postgres",
		"postgres://admin:password@postgres:5432/cimb_db?sslmode=disable",
	)

	if err != nil {
		log.Fatal(err)
	}

	defer db.Close()

	rdb := redis.NewClient(&redis.Options{
		Addr: "redis:6379",
	})

	ctx := context.Background()

	fmt.Println("Worker Pool Started")

	// Channel antrean internal
	jobs := make(chan Transaction, 1000)

	// Spawn goroutine worker
	for i := 0; i < WORKER_COUNT; i++ {

		go worker(i, jobs, db, rdb, ctx)
	}

	// Dispatcher queue Redis
	for {

		result, err := rdb.BLPop(ctx, 0, "tx_queue").Result()

		if err != nil {
			log.Println("Redis Error:", err)
			continue
		}

		payload := result[1]

		var tx Transaction

		err = json.Unmarshal([]byte(payload), &tx)

		if err != nil {
			log.Println("JSON Error:", err)
			continue
		}

		jobs <- tx
	}
}

func worker(
	id int,
	jobs <-chan Transaction,
	db *sql.DB,
	rdb *redis.Client,
	ctx context.Context,
) {

	for tx := range jobs {

		// simulasi processing
		time.Sleep(20 * time.Millisecond)

		tx.Status = "SUCCESS"

		_, err := db.Exec(
			"INSERT INTO transactions (id, user_id, amount, status) VALUES ($1, $2, $3, $4)",
			tx.ID,
			tx.UserID,
			tx.Amount,
			tx.Status,
		)

		if err != nil {

			log.Printf("Worker %d DB Error: %v", id, err)

			continue
		}

		rdb.Set(
			ctx,
			"tx_status:"+tx.ID,
			"SUCCESS",
			5*time.Minute,
		)

		fmt.Printf(
			"Worker %d processed TX %s\n",
			id,
			tx.ID,
		)
	}
}