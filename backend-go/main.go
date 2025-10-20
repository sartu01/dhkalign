package main

import (
	"context"
	"encoding/json"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
)

// j writes JSON with status code.
func j(w http.ResponseWriter, code int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(v)
}

var startedAt = time.Now().UTC()

func main() {
	// Port from env (Fly/Heroku style)
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	// Router + essential middlewares (no CORS needed for server-to-server)
	r := chi.NewRouter()
	r.Use(
		middleware.RequestID,
		middleware.RealIP,
		middleware.Recoverer,
		middleware.Timeout(15*time.Second),
	)

	// Health and version endpoints (under /go/*)
	r.Get("/go/health", func(w http.ResponseWriter, _ *http.Request) {
		j(w, http.StatusOK, map[string]any{
			"status": "ok",
			"ts":     time.Now().UTC().Format(time.RFC3339),
			"uptime": time.Since(startedAt).String(),
		})
	})

	r.Get("/go/version", func(w http.ResponseWriter, _ *http.Request) {
		sha := os.Getenv("COMMIT_SHA")
		if sha == "" {
			sha = "dev"
		}
		build := os.Getenv("BUILD_TIME")
		j(w, http.StatusOK, map[string]any{
			"sha":        sha,
			"build_time": build,
		})
	})

	// Simple stub translate endpoint (echoes input; replace with real logic/proxy later)
	r.Get("/go/translate", func(w http.ResponseWriter, r *http.Request) {
		q := r.URL.Query().Get("q")
		if strings.TrimSpace(q) == "" {
			j(w, http.StatusBadRequest, map[string]any{"error": "missing query param 'q'"})
			return
		}
		j(w, http.StatusOK, map[string]any{
			"translation": q, // stub: echo
			"src":         "stub",
			"ts":          time.Now().UTC().Format(time.RFC3339),
		})
	})

	// HTTP server with sane timeouts
	srv := &http.Server{
		Addr:              ":" + port,
		Handler:           r,
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       10 * time.Second,
		WriteTimeout:      10 * time.Second,
		IdleTimeout:       60 * time.Second,
	}

	// Start server
	go func() {
		log.Printf("backend-go listening on :%s", port)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("server error: %v", err)
		}
	}()

	// Graceful shutdown on SIGINT/SIGTERM
	stop := make(chan os.Signal, 1)
	signal.Notify(stop, os.Interrupt)
	<-stop
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := srv.Shutdown(ctx); err != nil {
		log.Printf("graceful shutdown failed: %v", err)
	} else {
		log.Printf("shutdown complete")
	}
}
