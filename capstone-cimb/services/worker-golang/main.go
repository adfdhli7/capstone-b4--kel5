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

	// Spawn goroutine worker
	for i := 0; i < WORKER_COUNT; i++ {

		go worker(i, db, rdb, ctx)
	}

	select {}
}

func worker(
    id int,
    db *sql.DB,
    rdb *redis.Client,
    ctx context.Context,
) {
    for {

        result, err := rdb.BLPop(
            ctx,
            5*time.Second,
            "tx_queue",
        ).Result()

        if err != nil {
            log.Printf(
                "Worker %d Redis Error: %v",
                id,
                err,
            )

			time.Sleep(3*time.Second)
            continue
        }

        payload := result[1]

        var tx Transaction

        err = json.Unmarshal(
            []byte(payload),
            &tx,
        )

        if err != nil {
            continue
        }

        // proses transaksi
        tx.Status = "SUCCESS"

        _, err = db.Exec(
            "INSERT INTO transactions (id,user_id,amount,status) VALUES ($1,$2,$3,$4)",
            tx.ID,
            tx.UserID,
            tx.Amount,
            tx.Status,
        )

        if err != nil {
            continue
        }

        fmt.Printf(
            "Worker %d processed %s\n",
            id,
            tx.ID,
        )
    }
}