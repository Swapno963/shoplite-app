#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

API_URL="${API_URL:-http://localhost:8000}"
READY_TIMEOUT="${READY_TIMEOUT:-60}"
ORDER_TIMEOUT="${ORDER_TIMEOUT:-30}"

log() {
  printf '%s\n' "$*"
}

fail() {
  log "ERROR: $*"
  exit 1
}

json_field() {
  local json="$1"
  local field="$2"
  python3 -c 'import json,sys; print(json.load(sys.stdin)[sys.argv[1]])' "$field" <<<"$json"
}

log "Starting application stack..."
docker compose up -d --build

log "Waiting for ${API_URL}/readyz ..."
ready=0
for ((i = 0; i < READY_TIMEOUT; i++)); do
  if curl -fsS "${API_URL}/readyz" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done
if [[ "$ready" -ne 1 ]]; then
  fail "/readyz did not become available within ${READY_TIMEOUT}s"
fi
log "API is ready."

log "Placing order..."
order_file="$(mktemp)"
http_code="$(curl -sS -o "$order_file" -w '%{http_code}' \
  -X POST "${API_URL}/orders" \
  -H 'Content-Type: application/json' \
  -d '{"product_id":1,"quantity":1}')"
order_json="$(cat "$order_file")"
rm -f "$order_file"

if [[ "$http_code" != "201" ]]; then
  fail "POST /orders expected 201, got ${http_code}: ${order_json}"
fi

order_id="$(json_field "$order_json" id)"
[[ -n "$order_id" ]] || fail "POST /orders response missing id: ${order_json}"
log "Created order ${order_id}."

log "Polling order ${order_id} until COMPLETED..."
status=""
for ((i = 0; i < ORDER_TIMEOUT; i++)); do
  order_json="$(curl -fsS "${API_URL}/orders/${order_id}")" || fail "GET /orders/${order_id} failed"
  status="$(json_field "$order_json" status)"
  log "  status=${status}"
  if [[ "$status" == "COMPLETED" ]]; then
    log "Smoke test passed: order ${order_id} is COMPLETED."
    exit 0
  fi
  if [[ "$status" == "FAILED" ]]; then
    fail "order ${order_id} ended in FAILED"
  fi
  sleep 1
done

fail "order ${order_id} did not reach COMPLETED within ${ORDER_TIMEOUT}s (last status=${status})"
