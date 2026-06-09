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
mkdir -p "$LOG_DIR"

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

if systemctl list-unit-files maker-stash.service >/dev/null 2>&1; then
  echo "[update] restarting maker-stash.service..."
  sudo systemctl stop maker-stash.service || true
  pkill -TERM -f "$SCRIPT_DIR/start.py" 2>/dev/null || true
  pkill -TERM -f "uvicorn app.main:app.*--port $BACKEND_PORT" 2>/dev/null || true
  pkill -TERM -f "$SCRIPT_DIR/frontend/node_modules/.bin/vite" 2>/dev/null || true
  pkill -TERM -f "$SCRIPT_DIR/frontend/node_modules/@esbuild" 2>/dev/null || true
  sleep 2
  sudo systemctl daemon-reload
  sudo systemctl restart maker-stash.service
  PID=$(systemctl show -p MainPID --value maker-stash.service)
else
  echo "[update] stopping old Maker Stash processes..."
  pkill -TERM -f "$SCRIPT_DIR/start.py" 2>/dev/null || true
  pkill -TERM -f "uvicorn app.main:app.*--port $BACKEND_PORT" 2>/dev/null || true
  pkill -TERM -f "$SCRIPT_DIR/frontend/node_modules/.bin/vite" 2>/dev/null || true
  pkill -TERM -f "$SCRIPT_DIR/frontend/node_modules/@esbuild" 2>/dev/null || true
  sleep 2

  echo "[update] starting production backend on port $BACKEND_PORT..."
  nohup "$PYTHON" start.py --config start.toml --skip-frontend > "$LOG_FILE" 2>&1 &
  PID=$!
fi
sleep 2

if command -v curl >/dev/null 2>&1; then
  if curl -fsS "http://127.0.0.1:$BACKEND_PORT/" >/dev/null; then
    echo "[ok] frontend is available at http://127.0.0.1:$BACKEND_PORT/"
  else
    echo "[warn] service started but frontend check failed; inspect $LOG_FILE"
  fi
fi

echo "[ok] production service started, pid=$PID"
echo "[info] log: $LOG_FILE"
