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
import tomllib
import webbrowser
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"
DEFAULT_START_CONFIG = {
    "host": "127.0.0.1",
    "lan": False,
    "backend_port": 8000,
    "frontend_port": 5173,
    "no_browser": False,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start Maker Stash backend and frontend.")
    parser.add_argument("--config", default=str(ROOT / "start.toml"), help="Path to launcher config file.")
    parser.add_argument("--host", default=None, help="Host for both services.")
    parser.add_argument("--lan", action=argparse.BooleanOptionalAction, default=None, help="Expose both services on all network interfaces.")
    parser.add_argument("--backend-port", type=int, default=None, help="FastAPI backend port.")
    parser.add_argument("--frontend-port", type=int, default=None, help="Vite frontend port.")
    parser.add_argument("--no-browser", action=argparse.BooleanOptionalAction, default=None, help="Do not open the browser automatically.")
    parser.add_argument("--skip-backend", action="store_true", help="Only start the frontend.")
    parser.add_argument("--skip-frontend", action="store_true", help="Only start the backend.")
    args = parser.parse_args()
    return merge_config(args)


def load_start_config(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        with path.open("rb") as file:
            data = tomllib.load(file)
    except tomllib.TOMLDecodeError as exc:
        raise SystemExit(f"[error] invalid start config {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"[error] invalid start config {path}: expected TOML table")
    return data


def int_config_value(config: dict[str, object], key: str, default: int) -> int:
    value = config.get(key, default)
    if isinstance(value, bool):
        raise SystemExit(f"[error] start config field {key} must be an integer")
    try:
        port = int(value)
    except (TypeError, ValueError) as exc:
        raise SystemExit(f"[error] start config field {key} must be an integer") from exc
    if port < 1 or port > 65535:
        raise SystemExit(f"[error] start config field {key} must be between 1 and 65535")
    return port


def bool_config_value(config: dict[str, object], key: str, default: bool) -> bool:
    value = config.get(key, default)
    if not isinstance(value, bool):
        raise SystemExit(f"[error] start config field {key} must be true or false")
    return value


def merge_config(args: argparse.Namespace) -> argparse.Namespace:
    config_path = Path(args.config).expanduser()
    if not config_path.is_absolute():
        config_path = ROOT / config_path
    config = {**DEFAULT_START_CONFIG, **load_start_config(config_path)}

    args.host = args.host if args.host is not None else str(config.get("host", DEFAULT_START_CONFIG["host"]))
    args.lan = args.lan if args.lan is not None else bool_config_value(config, "lan", bool(DEFAULT_START_CONFIG["lan"]))
    args.backend_port = args.backend_port if args.backend_port is not None else int_config_value(config, "backend_port", int(DEFAULT_START_CONFIG["backend_port"]))
    args.frontend_port = args.frontend_port if args.frontend_port is not None else int_config_value(config, "frontend_port", int(DEFAULT_START_CONFIG["frontend_port"]))
    args.no_browser = args.no_browser if args.no_browser is not None else bool_config_value(config, "no_browser", bool(DEFAULT_START_CONFIG["no_browser"]))
    return args


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


def probe_host(host: str) -> str:
    return "127.0.0.1" if host in {"0.0.0.0", "::"} else host


def local_ipv4_addresses() -> list[str]:
    addresses: set[str] = {"127.0.0.1"}

    try:
        hostname = socket.gethostname()
        for family, _, _, _, sockaddr in socket.getaddrinfo(hostname, None, socket.AF_INET):
            if family == socket.AF_INET:
                address = sockaddr[0]
                if not address.startswith("169.254."):
                    addresses.add(address)
    except OSError:
        pass

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            addresses.add(sock.getsockname()[0])
    except OSError:
        pass

    return sorted(addresses, key=lambda item: (item != "127.0.0.1", item))


def service_urls(host: str, port: int) -> list[str]:
    if host in {"0.0.0.0", "::"}:
        return [f"http://{address}:{port}" for address in local_ipv4_addresses()]
    return [f"http://{host}:{port}"]


def print_service_urls(name: str, host: str, port: int) -> None:
    print(f"[info] {name} access URLs:", flush=True)
    for url in service_urls(host, port):
        print(f"       {url}", flush=True)


def wait_for_port(host: str, port: int, name: str, timeout: float = 25.0) -> bool:
    check_host = probe_host(host)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if port_is_open(check_host, port):
            print(f"[ok] {name} ready on {host}:{port}", flush=True)
            print_service_urls(name, host, port)
            return True
        time.sleep(0.25)
    print(f"[warn] {name} did not become ready within {timeout:.0f}s", flush=True)
    return False


def stream_output(process: subprocess.Popen[str], name: str) -> None:
    assert process.stdout is not None
    for line in process.stdout:
        print(f"[{name}] {line.rstrip()}", flush=True)


def start_process(name: str, command: Iterable[str], cwd: Path, extra_env: dict[str, str] | None = None) -> subprocess.Popen[str]:
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    if extra_env:
        env.update(extra_env)
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


def run_backend_migrations(python: Path) -> None:
    print("[backend] applying database migrations...", flush=True)
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    result = subprocess.run(
        [str(python), "-m", "alembic", "upgrade", "head"],
        cwd=str(BACKEND_DIR),
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise SystemExit("[error] backend database migration failed")


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
    if args.lan:
        args.host = "0.0.0.0"

    processes: list[subprocess.Popen[str]] = []
    frontend_url = service_urls(args.host, args.frontend_port)[0]
    check_host = probe_host(args.host)

    ensure_file(BACKEND_DIR / "app" / "main.py", "Backend entry not found")
    ensure_file(FRONTEND_DIR / "package.json", "Frontend package.json not found")

    if not args.skip_backend:
        python = venv_python()
        ensure_file(python, "Virtual environment Python not found. Create .venv and install backend dependencies first")
        if port_is_open(check_host, args.backend_port):
            print(f"[reuse] backend already running on {args.host}:{args.backend_port}", flush=True)
            print_service_urls("backend", args.host, args.backend_port)
        else:
            run_backend_migrations(python)
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
        if port_is_open(check_host, args.frontend_port):
            print(f"[reuse] frontend already running on {args.host}:{args.frontend_port}", flush=True)
            print_service_urls("frontend", args.host, args.frontend_port)
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
                    {"MAKER_STASH_API_PROXY_TARGET": f"http://127.0.0.1:{args.backend_port}"},
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
