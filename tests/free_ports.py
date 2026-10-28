#!/usr/bin/env python3
"""CALENDAR-001 dev-server port hygiene (T-03/T-05 helper).

Kills stale listeners on the calendar dev ports (vite orphans survive their
parent auto.exe) plus any node.exe whose command line references this app's
generated frontend. Refuses to touch anything else.

Usage: python tests/free_ports.py [--ports 17820,17821]
Exit 0 = all listed ports free afterwards; exit 1 = still occupied.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys

DEFAULT_PORTS = (17820, 17821)


def listeners(ports: tuple[int, ...]) -> list[int]:
    out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True).stdout
    pids: set[int] = set()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[3].upper() == "LISTENING":
            m = re.search(r":(\d+)$", parts[1])
            if m and int(m.group(1)) in ports:
                pids.add(int(parts[4]))
    return sorted(pids)


def calendar_node_pids() -> list[int]:
    """node.exe processes whose command line mentions auto-calendar."""
    ps = (
        "Get-CimInstance Win32_Process -Filter \"Name='node.exe'\" | "
        "Where-Object { $_.CommandLine -like '*auto-calendar*' } | "
        "Select-Object -ExpandProperty ProcessId"
    )
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True
    ).stdout
    pids: list[int] = []
    for tok in out.split():
        if tok.strip().isdigit():
            pids.append(int(tok))
    return pids


def kill(pid: int) -> None:
    subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ports", default=",".join(str(p) for p in DEFAULT_PORTS))
    args = ap.parse_args()
    ports = tuple(int(p) for p in args.ports.split(","))

    victims = set(listeners(ports)) | set(calendar_node_pids())
    for pid in sorted(victims):
        print(f"kill stale pid {pid}")
        kill(pid)

    import time

    time.sleep(1.5)
    left = listeners(ports)
    if left:
        print(f"STILL OCCUPIED on {ports}: pids {left}", file=sys.stderr)
        return 1
    print(f"ports {ports} free")
    return 0


if __name__ == "__main__":
    sys.exit(main())
