#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AI_DIR="$ROOT_DIR/ai-agent"
BACKEND_DIR="$ROOT_DIR/backend"

FASTAPI_PORT=8001
STARTUP_WAIT_SECONDS=2

# If set to 1, script will kill processes that occupy required ports before starting.
FORCE_KILL_PORTS="${FORCE_KILL_PORTS:-0}"
# If set to 1, script will start Laravel Reverb (if command exists).
START_REVERB="${START_REVERB:-0}"

RUNTIME_DIR="$ROOT_DIR/.runtime"
mkdir -p "$RUNTIME_DIR"

FASTAPI_PID_FILE="$RUNTIME_DIR/fastapi.pid"
QUEUE_PID_FILE="$RUNTIME_DIR/queue.pid"
REVERB_PID_FILE="$RUNTIME_DIR/reverb.pid"

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "[error] Required command not found: $cmd"
    exit 1
  fi
}

ensure_dir() {
  local dir="$1"
  if [[ ! -d "$dir" ]]; then
    echo "[error] Directory not found: $dir"
    exit 1
  fi
}

port_in_use() {
  local port="$1"
  ss -ltn 2>/dev/null | grep -q ":${port}[[:space:]]"
}

kill_port_if_needed() {
  local port="$1"

  if ! port_in_use "$port"; then
    return
  fi

  if [[ "$FORCE_KILL_PORTS" == "1" ]]; then
    echo "[warn] Port ${port} is in use, killing existing process(es)"
    fuser -k "${port}/tcp" >/dev/null 2>&1 || true
  else
    echo "[error] Port ${port} is already in use"
    echo "        Run: ss -ltnp | grep -E ':${FASTAPI_PORT}'"
    echo "        Or rerun with FORCE_KILL_PORTS=1 ./start.sh"
    exit 1
  fi
}

record_pid() {
  local pid="$1"
  local file="$2"
  echo "$pid" >"$file"
}

is_alive() {
  local pid="$1"
  kill -0 "$pid" 2>/dev/null
}

stop_by_file() {
  local label="$1"
  local file="$2"

  if [[ -f "$file" ]]; then
    local pid
    pid="$(cat "$file" 2>/dev/null || true)"
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      echo "[$label] stopped (pid $pid)"
    fi
    rm -f "$file"
  fi
}

cleanup() {
  echo
  echo "Stopping all services..."

  stop_by_file "fastapi" "$FASTAPI_PID_FILE"
  stop_by_file "queue" "$QUEUE_PID_FILE"
  stop_by_file "reverb" "$REVERB_PID_FILE"

  wait 2>/dev/null || true
  echo "All services stopped."
}

usage() {
  cat <<'EOF'
Usage:
  ./start.sh start      Start production services
  ./start.sh stop       Stop production services
  ./start.sh restart    Restart production services
  ./start.sh status     Show service status

Environment options:
  FORCE_KILL_PORTS=1    Kill process occupying FastAPI port (8001)
  START_REVERB=1        Start Laravel Reverb if command is available

Notes:
  - This script is for production runtime helper.
  - Frontend should be built once using npm run build and served by nginx.
  - Laravel should be served by nginx + php-fpm (not artisan serve).
EOF
}

status_by_file() {
  local label="$1"
  local file="$2"
  if [[ -f "$file" ]]; then
    local pid
    pid="$(cat "$file" 2>/dev/null || true)"
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      echo "[$label] running (pid $pid)"
      return
    fi
  fi
  echo "[$label] stopped"
}

start_all() {
  trap cleanup INT TERM

  require_cmd ss
  require_cmd php
  require_cmd fuser

  ensure_dir "$AI_DIR"
  ensure_dir "$BACKEND_DIR"

  kill_port_if_needed "$FASTAPI_PORT"

  echo "[1/2] Running FastAPI on port ${FASTAPI_PORT}..."
  cd "$AI_DIR"
  if [[ -x "$AI_DIR/.venv/bin/uvicorn" ]]; then
    "$AI_DIR/.venv/bin/uvicorn" app.main:app --host 127.0.0.1 --port "$FASTAPI_PORT" &
  else
    echo "[warn] .venv uvicorn not found, fallback to python3.11 -m uvicorn"
    python3.11 -m uvicorn app.main:app --host 127.0.0.1 --port "$FASTAPI_PORT" &
  fi
  FASTAPI_PID=$!
  record_pid "$FASTAPI_PID" "$FASTAPI_PID_FILE"

  echo "[2/2] Starting Laravel queue worker..."
  cd "$BACKEND_DIR"
  php artisan queue:work --queue=ai-review,default --sleep=3 --tries=1 --timeout=0 &
  QUEUE_PID=$!
  record_pid "$QUEUE_PID" "$QUEUE_PID_FILE"

  if [[ "$START_REVERB" == "1" ]]; then
    if php artisan list --raw | grep -q '^reverb:start$'; then
      echo "[opt] Starting Laravel Reverb..."
      php artisan reverb:start &
      REVERB_PID=$!
      record_pid "$REVERB_PID" "$REVERB_PID_FILE"
    else
      echo "[warn] Reverb command not found, skipping"
    fi
  fi

  sleep "$STARTUP_WAIT_SECONDS"

  if ! is_alive "$FASTAPI_PID"; then
    echo "[error] FastAPI failed to start"
    cleanup
    exit 1
  fi

  if ! is_alive "$QUEUE_PID"; then
    echo "[error] Queue worker failed to start"
    cleanup
    exit 1
  fi

  if [[ -n "${REVERB_PID:-}" ]] && ! is_alive "$REVERB_PID"; then
    echo "[error] Reverb failed to start"
    cleanup
    exit 1
  fi

  echo "=========================================="
  echo "Production services are running"
  echo "=========================================="
  echo "FastAPI   : http://127.0.0.1:${FASTAPI_PORT}/docs"
  echo "Queue     : running"
  if [[ "$START_REVERB" == "1" ]]; then
    echo "Reverb    : requested"
  fi
  echo
  echo "Press Ctrl+C to stop started services"

  if [[ -n "${REVERB_PID:-}" ]]; then
    wait "$FASTAPI_PID" "$QUEUE_PID" "$REVERB_PID"
  else
    wait "$FASTAPI_PID" "$QUEUE_PID"
  fi
}

stop_all() {
  cleanup
}

status_all() {
  status_by_file "fastapi" "$FASTAPI_PID_FILE"
  status_by_file "queue" "$QUEUE_PID_FILE"
  status_by_file "reverb" "$REVERB_PID_FILE"
}

command="${1:-start}"

case "$command" in
  start)
    start_all
    ;;
  stop)
    stop_all
    ;;
  restart)
    stop_all
    start_all
    ;;
  status)
    status_all
    ;;
  *)
    usage
    exit 1
    ;;
esac
