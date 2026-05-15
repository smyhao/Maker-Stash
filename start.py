#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start Maker Stash backend and frontend.")
    parser.add_argument("--host", default="127.0.0.1", help="Host for both services.")
    parser.add_argument("--backend-port", type=int, default=8000, help="FastAPI backend port.")
    parser.add_argument("--frontend-port", type=int, default=5173, help="Vite frontend port.")
    parser.add_argument("--no-browser", action="store_true", help="Do not open the browser automatically.")
    parser.add_argument("--skip-backend", action="store_true", help="Only start the frontend.")
    parser.add_argument("--skip-frontend", action="store_true", help="Only start the backend.")
    return parser.parse_args()


def is_windows() -> bool:
    return os.name == "nt"


def venv_python() -> Path:
    return ROOT / ".venv" / ("Scripts/python.exe" if is_windows() else "bin/python")


def npm_command() -> str:
    return "npm.cmd" if is_windows() else "npm"


def ensure_file(path: Path, message: str) -> None:
    if not path.exists():
        raise SystemExit(f"[error] {message}: {path}")


def port_is_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.35)
        return sock.connect_ex((host, port)) == 0


def wait_for_port(host: str, port: int, name: str, timeout: float = 25.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if port_is_open(host, port):
            print(f"[ok] {name} ready at http://{host}:{port}", flush=True)
            return True
        time.sleep(0.25)
    print(f"[warn] {name} did not become ready within {timeout:.0f}s", flush=True)
    return False


def stream_output(process: subprocess.Popen[str], name: str) -> None:
    assert process.stdout is not None
    for line in process.stdout:
        print(f"[{name}] {line.rstrip()}", flush=True)


def start_process(name: str, command: Iterable[str], cwd: Path) -> subprocess.Popen[str]:
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    process = subprocess.Popen(
        list(command),
        cwd=str(cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    threading.Thread(target=stream_output, args=(process, name), daemon=True).start()
    return process


def terminate(processes: list[subprocess.Popen[str]]) -> None:
    for process in processes:
        if process.poll() is not None:
            continue
        try:
            if is_windows():
                process.terminate()
            else:
                process.send_signal(signal.SIGTERM)
        except ProcessLookupError:
            pass

    deadline = time.monotonic() + 5
    for process in processes:
        remaining = max(0.1, deadline - time.monotonic())
        try:
            process.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            process.kill()


def main() -> int:
    args = parse_args()
    processes: list[subprocess.Popen[str]] = []
    frontend_url = f"http://{args.host}:{args.frontend_port}"

    ensure_file(BACKEND_DIR / "app" / "main.py", "Backend entry not found")
    ensure_file(FRONTEND_DIR / "package.json", "Frontend package.json not found")

    if not args.skip_backend:
        python = venv_python()
        ensure_file(python, "Virtual environment Python not found. Create .venv and install backend dependencies first")
        if port_is_open(args.host, args.backend_port):
            print(f"[reuse] backend already running at http://{args.host}:{args.backend_port}", flush=True)
        else:
            processes.append(
                start_process(
                    "backend",
                    [
                        str(python),
                        "-m",
                        "uvicorn",
                        "app.main:app",
                        "--host",
                        args.host,
                        "--port",
                        str(args.backend_port),
                    ],
                    BACKEND_DIR,
                )
            )

    if not args.skip_frontend:
        if not (FRONTEND_DIR / "node_modules").exists():
            raise SystemExit("[error] frontend/node_modules not found. Run npm install in frontend first.")
        if port_is_open(args.host, args.frontend_port):
            print(f"[reuse] frontend already running at {frontend_url}", flush=True)
        else:
            processes.append(
                start_process(
                    "frontend",
                    [
                        npm_command(),
                        "run",
                        "dev",
                        "--",
                        "--host",
                        args.host,
                        "--port",
                        str(args.frontend_port),
                    ],
                    FRONTEND_DIR,
                )
            )

    if not args.skip_backend:
        wait_for_port(args.host, args.backend_port, "backend")
    if not args.skip_frontend:
        wait_for_port(args.host, args.frontend_port, "frontend")
        if not args.no_browser:
            webbrowser.open(frontend_url)
            print(f"[open] {frontend_url}", flush=True)

    if not processes:
        print("[done] services are already running.", flush=True)
        return 0

    print("[info] Press Ctrl+C to stop services started by this launcher.", flush=True)
    try:
        while any(process.poll() is None for process in processes):
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[stop] stopping services...", flush=True)
        terminate(processes)
        return 0

    failed = [process.returncode for process in processes if process.returncode not in (0, None)]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
