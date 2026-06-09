#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR"

PYTHON="$SCRIPT_DIR/.venv/bin/python"
if [ ! -x "$PYTHON" ]; then
  PYTHON="python3"
fi

BACKEND_PORT=$("$PYTHON" - <<'PY'
import pathlib
import tomllib

config_path = pathlib.Path("start.toml")
port = 8000
if config_path.exists():
    with config_path.open("rb") as file:
        port = int(tomllib.load(file).get("backend_port", port))
print(port)
PY
)

LOG_DIR=".codex-runtime"
LOG_FILE="$LOG_DIR/maker-stash-production.log"
SERVICE_NAME="maker-stash.service"
mkdir -p "$LOG_DIR"

run_privileged() {
  if [ "$(id -u)" -eq 0 ]; then
    "$@"
  else
    sudo "$@"
  fi
}

stop_development_processes() {
  pkill -TERM -f "$SCRIPT_DIR/start.py" 2>/dev/null || true
  pkill -TERM -f "uvicorn app.main:app.*--port $BACKEND_PORT" 2>/dev/null || true
  pkill -TERM -f "$SCRIPT_DIR/frontend/node_modules/.bin/vite" 2>/dev/null || true
  pkill -TERM -f "$SCRIPT_DIR/frontend/node_modules/@esbuild" 2>/dev/null || true
}

wait_for_frontend() {
  if ! command -v curl >/dev/null 2>&1; then
    return 0
  fi

  for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
    if curl -fsS "http://127.0.0.1:$BACKEND_PORT/" >/dev/null; then
      return 0
    fi
    sleep 2
  done
  return 1
}

echo "[update] pulling latest code..."
git pull --ff-only

echo "[update] applying backend migrations..."
(
  cd backend
  "$PYTHON" -m alembic upgrade head
)

echo "[update] building frontend dist..."
(
  cd frontend
  npm run build
)

if systemctl list-unit-files "$SERVICE_NAME" >/dev/null 2>&1; then
  echo "[update] restarting $SERVICE_NAME..."
  run_privileged systemctl stop "$SERVICE_NAME" || true
  stop_development_processes
  sleep 2
  run_privileged systemctl daemon-reload
  run_privileged systemctl restart "$SERVICE_NAME"
  PID=$(systemctl show -p MainPID --value "$SERVICE_NAME")
else
  echo "[update] stopping old Maker Stash processes..."
  stop_development_processes
  sleep 2

  echo "[update] starting production backend on port $BACKEND_PORT..."
  nohup "$PYTHON" start.py --config start.toml --skip-frontend > "$LOG_FILE" 2>&1 &
  PID=$!
fi

if wait_for_frontend; then
  echo "[ok] frontend is available at http://127.0.0.1:$BACKEND_PORT/"
else
  echo "[warn] service started but frontend check failed; inspect $LOG_FILE"
fi

echo "[ok] production service started, pid=$PID"
echo "[info] log: $LOG_FILE"
