#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass


DEFAULT_PORTS = [8000, 5173]


@dataclass
class PortProcess:
    port: int
    pid: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stop Maker Stash local services by port.")
    parser.add_argument("--ports", nargs="*", type=int, default=DEFAULT_PORTS, help="Ports to stop. Default: 8000 5173")
    parser.add_argument("--force", action="store_true", help="Force kill processes without graceful termination.")
    return parser.parse_args()


def is_windows() -> bool:
    return os.name == "nt"


def run(command: list[str]) -> str:
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return completed.stdout


def find_windows_processes(ports: list[int]) -> list[PortProcess]:
    output = run(["netstat", "-ano", "-p", "tcp"])
    found: dict[tuple[int, int], PortProcess] = {}
    wanted = set(ports)
    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 5 or parts[0].upper() != "TCP":
            continue
        local = parts[1]
        state = parts[3].upper()
        if state != "LISTENING":
            continue
        try:
            port = int(local.rsplit(":", 1)[1])
            pid = int(parts[4])
        except (IndexError, ValueError):
            continue
        if port in wanted:
            found[(port, pid)] = PortProcess(port=port, pid=pid)
    return sorted(found.values(), key=lambda item: (item.port, item.pid))


def find_unix_processes(ports: list[int]) -> list[PortProcess]:
    found: dict[tuple[int, int], PortProcess] = {}
    for port in ports:
        output = run(["sh", "-c", f"command -v lsof >/dev/null 2>&1 && lsof -ti tcp:{port} -sTCP:LISTEN || true"])
        for value in output.split():
            try:
                pid = int(value)
            except ValueError:
                continue
            found[(port, pid)] = PortProcess(port=port, pid=pid)
    return sorted(found.values(), key=lambda item: (item.port, item.pid))


def find_processes(ports: list[int]) -> list[PortProcess]:
    return find_windows_processes(ports) if is_windows() else find_unix_processes(ports)


def stop_pid(pid: int, force: bool) -> None:
    if is_windows():
        command = ["taskkill", "/PID", str(pid)]
        if force:
            command.append("/F")
        run(command)
        return

    sig = signal.SIGKILL if force else signal.SIGTERM
    try:
        os.kill(pid, sig)
    except ProcessLookupError:
        return


def main() -> int:
    args = parse_args()
    ports = sorted(set(args.ports))
    processes = find_processes(ports)
    if not processes:
        print(f"[done] no listening services found on ports: {', '.join(map(str, ports))}")
        return 0

    for process in processes:
        print(f"[stop] port {process.port}: pid {process.pid}")
        stop_pid(process.pid, args.force)

    time.sleep(0.8)
    remaining = find_processes(ports)
    if remaining and not args.force:
        for process in remaining:
            print(f"[force] port {process.port}: pid {process.pid}")
            stop_pid(process.pid, True)
        time.sleep(0.5)

    remaining = find_processes(ports)
    if remaining:
        for process in remaining:
            print(f"[warn] still running on port {process.port}: pid {process.pid}")
        return 1

    print("[done] services stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
