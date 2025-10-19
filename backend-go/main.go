package main
import (
"encoding/json"
"log"
"net/http"
"os"
"time"
"github.com/go-chi/chi/v5"
)
func j(w http.ResponseWriter, code int, v any){ w.Header().Set("Content-Type","application/json"); w.WriteHeader(code); _=json.NewEncoder(w).Encode(v) }
func main(){
port:=os.Getenv("PORT"); if port==""{port="8080"}
r:=chi.NewRouter()
r.Get("/go/health", func(w http.ResponseWriter, _ *http.Request){ j(w,200,map[string]any{"status":"ok","ts":time.Now().UTC().Format(time.RFC3339)}) })
r.Get("/go/version", func(w http.ResponseWriter, _ *http.Request){ sha:=os.Getenv("COMMIT_SHA"); if sha==""{sha="dev"}; j(w,200,map[string]any{"sha":sha}) })
log.Printf("listening on :%s\n", port)
log.Fatal(http.ListenAndServe(":"+port, r))
}
