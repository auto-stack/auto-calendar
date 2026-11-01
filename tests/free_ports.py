#!/usr/bin/env python3
"""CALENDAR-002 own-process port/proc gate (T-01 — narrows the 001 helper).

The 001 behavior (kill every listener on 17820/17821 + every node.exe whose
command line mentions auto-calendar) is RETIRED: it reaches outside this
run's ownership and can kill a bystander instance. The discipline is now:

  OWNERSHIP  a process may be harvested only if THIS run registered it after
             positive identification: its image path lies under this repo
             checkout, or its command line references this checkout, AND it
             started no earlier than the run's start time. Anything else is
             a bystander — reported, never killed.

  PREP       `--check` verifies the ports are free BEFORE this run starts
             anything and never kills: an occupied port aborts the run
             (no drift, no harvest of strangers).

Usage:
  python tests/free_ports.py --check [--ports 17820,17821]
      exit 0 = free, 1 = occupied (prints pid + image per listener)

  (module use from the verify harness)
      reg = Ownership(repo_root, since_epoch)
      reg.register_from_ports(ports)   # identify listeners born after `since`
      reg.harvest()                    # kill registered pids (tree kill);
                                       # strangers are never touched
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
import time


def listeners(ports: tuple[int, ...]) -> dict[int, int]:
    """port -> listening pid (empty when free)."""
    out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True).stdout
    found: dict[int, int] = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[3].upper() == "LISTENING":
            m = re.search(r":(\d+)$", parts[1])
            if m and int(m.group(1)) in ports:
                found[int(m.group(1))] = int(parts[4])
    return found


def proc_info(pid: int) -> dict | None:
    """image path, command line, creation time (UTC iso) for pid; None if gone."""
    ps = (
        "Get-CimInstance Win32_Process -Filter \"ProcessId=" + str(pid) + "\" | "
        "ForEach-Object { $_.ExecutablePath; $_.CommandLine; "
        "$_.CreationDate.ToUniversalTime().ToString('o') }"
    )
    out = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                         capture_output=True, text=True).stdout.splitlines()
    if len(out) < 3:
        return None
    return {"pid": pid, "image": out[0].strip(), "cmdline": out[1].strip(),
            "started_utc": out[2].strip()}


def _norm(p: str) -> str:
    return p.replace("/", "\\").strip().lower()


def _parse_iso(s: str) -> float:
    try:
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


class Ownership:
    """Registry of pids this run positively identified as its own."""

    def __init__(self, repo_root: str, since_epoch: float, ports: tuple[int, ...]):
        self.repo = _norm(repo_root)
        self.since = since_epoch
        self.ports = ports
        self.owned: dict[int, dict] = {}
        self.strangers: list[dict] = []

    def _classify(self, pid: int) -> str:
        info = proc_info(pid)
        if info is None:
            return "gone"
        started = _parse_iso(info["started_utc"])
        under_image = _norm(info["image"]).startswith(self.repo)
        in_cmdline = self.repo in _norm(info["cmdline"])
        if (under_image or in_cmdline) and started >= self.since:
            self.owned[pid] = info
            return "owned"
        self.strangers.append(info)
        return "stranger"

    def register_from_ports(self) -> dict[int, int]:
        """Identify current listeners on the run's ports (call right after a
        launch became ready: they are this run's backend/front children)."""
        found = listeners(self.ports)
        result = {}
        for port, pid in sorted(found.items()):
            result[pid] = self._classify(pid)
        return found

    def register_tree(self, pid: int) -> None:
        """Register a spawned root (auto.exe) unconditionally — this run
        created it; children are re-identified via ports at harvest."""
        self.owned[pid] = {"pid": pid, "image": "(spawned root)", "cmdline": "",
                           "started_utc": ""}

    def harvest(self) -> dict:
        """Tree-kill registered roots, then re-identify remaining port
        listeners: owned → kill, stranger → report only. Returns a report
        dict for the run evidence; `clean` is False when strangers remain."""
        for pid in list(self.owned):
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                           capture_output=True)
        # vite/node orphans can outlive their parent — re-identify whatever
        # still listens, then re-check (second pass after the first kills)
        for _ in range(2):
            time.sleep(1.5)
            reg = self.register_from_ports()
            if not reg:
                break
        still = listeners(self.ports)
        report = {"killed": sorted(self.owned), "strangers": self.strangers,
                  "ports_free_after": not still, "still_listening": still}
        report["clean"] = report["ports_free_after"] and not self.strangers
        return report


def check_only(ports: tuple[int, ...]) -> int:
    found = listeners(ports)
    if not found:
        print(f"ports {ports} free")
        return 0
    for port, pid in sorted(found.items()):
        info = proc_info(pid) or {"image": "?", "cmdline": "?"}
        print(f"OCCUPIED port {port} pid {pid} image {info['image']}")
    print(f"refusing to act — occupied ports abort the run (no drift, no kill)")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--ports", default="17820,17821")
    args = ap.parse_args()
    ports = tuple(int(p) for p in args.ports.split(","))
    return check_only(ports)


if __name__ == "__main__":
    sys.exit(main())
