#!/usr/bin/env python3
"""CALENDAR-001 basic-capabilities verification (plan §6 V-01..V-03).

Permanent replay entry for the app's basic contract:
  python tests/basic/verify_basic.py --profile vue
  python tests/basic/verify_basic.py --profile vm

Both profiles launch the REAL app split-mode stack (generated rust backend on
17821 + the profile's UI) against isolated data dirs, drive the real UI
(Playwright for vue, AutoUI MCP for vm), and check the plan's acceptance
behaviors:

  V-01  controllable clock: injected fake date renders everywhere; leap day
        and cross-midnight/cross-month transitions follow the clock; the
        hardcoded demo date is gone.
  V-02  same-day multi-event + cross-month events with stable ids; survives
        reopen.
  V-03  invalid date / inverted range explicitly rejected, form input
        retained, no fake success.

Isolation: each run uses its own data dir under a temp root and explicit
ports (front 17820, back 17821); occupied ports abort the run (never
silently drift). Evidence (commands, results, failures) is written to
docs/plans/attachments/001/verify-<profile>-<ts>.json (local-only).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
AUTO_BIN = os.environ.get("AUTO_BIN", r"D:\autostack\auto-man\target\debug\auto.exe")
FRONT_PORT = 17820
BACK_PORT = 17821
API = f"http://127.0.0.1:{BACK_PORT}"
FRONT = f"http://localhost:{FRONT_PORT}"
EVIDENCE_DIR = os.path.join(REPO, "docs", "plans", "attachments", "001")
MCPPORT = 9547


class Check:
    def __init__(self):
        self.results: list[dict] = []

    def __call__(self, name, ok, detail=""):
        self.results.append({"name": name, "ok": bool(ok), "detail": str(detail)[:300]})
        print(("PASS " if ok else "FAIL ") + name + ((" :: " + str(detail)[:200]) if detail else ""))
        return ok

    @property
    def failed(self):
        return [r for r in self.results if not r["ok"]]

    @property
    def summary(self):
        return f"{len(self.results) - len(self.failed)}/{len(self.results)}"


def port_free(port):
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def free_ports(ports=(FRONT_PORT, BACK_PORT)):
    import ctypes

    out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True).stdout
    pids = set()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[3].upper() == "LISTENING":
            m = re.search(r":(\d+)$", parts[1])
            if m and int(m.group(1)) in ports:
                pids.add(int(parts[4]))
    for pid in sorted(pids):
        subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
    time.sleep(1.5)
    return all(port_free(p) for p in ports)


def http_json(method, path, payload=None, timeout=10):
    req = urllib.request.Request(
        API + path,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Content-Type": "application/json"} if payload is not None else {},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def wait_http(url, timeout_s):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=3)
            return True
        except Exception:
            time.sleep(1)
    return False


def wait_file_contains(path, needle, timeout_s):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                if needle in fh.read():
                    return True
        except OSError:
            pass
        time.sleep(1)
    return False


def app_env(data_dir, fake_date=None, fake_time=None, fake_off=None):
    env = {**os.environ, "AUTO_CALENDAR_DATA": data_dir, "AUTO_CALENDAR_TEST_MODE": "1"}
    if fake_date:
        env["AUTO_CALENDAR_FAKE_DATE"] = fake_date
    if fake_time:
        env["AUTO_CALENDAR_FAKE_TIME"] = fake_time
    if fake_off:
        env["AUTO_CALENDAR_FAKE_OFFSET_MIN"] = str(fake_off)
    return env


def launch_app(profile, data_dir, log_path, fake_date=None, fake_time=None, fake_off=None):
    if profile == "vm":
        cmd = [AUTO_BIN, "run", "-r", "vm"]
    else:
        cmd = [AUTO_BIN, "run"]
    env = app_env(data_dir, fake_date, fake_time, fake_off)
    env["AUTOUI_MCP_PORT"] = str(MCPPORT)
    log = open(log_path, "w", encoding="utf-8")
    return subprocess.Popen(cmd, cwd=REPO, env=env, stdout=log, stderr=subprocess.STDOUT)


def wait_ready(profile, log_path):
    marker = "AutoUI MCP: listening" if profile == "vm" else "VITE"
    if not wait_file_contains(log_path, marker, 240):
        return False, f"{marker} not ready in 240s"
    if profile == "vue" and not wait_http(FRONT, 60):
        return False, "front not serving"
    if not wait_http(API + "/api/v1/status", 60):
        return False, "backend not serving"
    if profile == "vm":
        deadline = time.time() + 120
        while time.time() < deadline:
            try:
                mcp_tools()
                return True, ""
            except Exception:
                time.sleep(1)
        return False, "autoui MCP not reachable"
    return True, ""


def mcp_call(tool, **args):
    req = urllib.request.Request(
        f"http://127.0.0.1:{MCPPORT}/mcp",
        data=json.dumps({"jsonrpc": "2.0", "method": "tools/call",
                         "params": {"name": tool, "arguments": args}, "id": 1}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read().decode())
    if "error" in data:
        raise RuntimeError(f"MCP error: {data['error']}")
    content = data.get("result", {}).get("content", [])
    return content[0]["text"] if content else ""


def mcp_tools():
    req = urllib.request.Request(
        f"http://127.0.0.1:{MCPPORT}/mcp",
        data=json.dumps({"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": 1}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        json.loads(r.read().decode())


def mcp_state_retry(fields, wait_flag=None, timeout_s=40):
    """Read autoui_state, retrying until wait_flag appears (or timeout)."""
    deadline = time.time() + timeout_s
    last = ""
    while time.time() < deadline:
        try:
            last = mcp_call("autoui_state", fields=fields)
            if wait_flag is None or wait_flag in last:
                return last
        except Exception:
            pass
        time.sleep(1)
    return last


def kill_all():
    subprocess.run(["taskkill", "/F", "/IM", "auto.exe"], capture_output=True)
    subprocess.run(["taskkill", "/F", "/IM", "auto-calendar-back.exe"], capture_output=True)
    # orphan vite (node) survives its parent and holds the front port — the
    # dedicated cleaner also kills calendar node processes and verifies free
    subprocess.run([sys.executable, os.path.join(HERE, "..", "free_ports.py")],
                   capture_output=True)
    time.sleep(1.5)


def restart_with_clock(profile, data_dir, log_path, date, clock_time, off):
    kill_all()
    proc = launch_app(profile, data_dir, log_path, fake_date=date, fake_time=clock_time, fake_off=off)
    ok, why = wait_ready(profile, log_path)
    return proc, ok, why


DRIVER = os.path.join(HERE, "vue_driver.mjs")


def run_node_phase(phase):
    """Run one vue_driver phase; return (checks, ok)."""
    node = os.environ.get("NODE", "node")
    proc = subprocess.run([node, DRIVER, "--phase", phase], cwd=REPO,
                          capture_output=True, text=True, timeout=300, encoding="utf-8", errors="replace")
    checks = []
    for line in (proc.stdout or "").splitlines():
        if line.startswith("RESULTS "):
            checks = json.loads(line[len("RESULTS "):])
    if not checks:
        print((proc.stderr or "")[-800:])
    return checks, proc.returncode == 0 and bool(checks)


def fresh_data_dir(profile):
    """F-1: every run gets its own empty data dir (permanent replay must be
    re-runnable; a reused store makes the fresh-store assertions false-red)."""
    base = tempfile.mkdtemp(prefix=f"cal001-{profile}-")
    data_dir = os.path.join(base, "data")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def run_vue(check):
    data_dir = fresh_data_dir("vue")
    log_path = os.path.join(log_dir_for_run(), "verify-vue-app.log")
    check("ports-free", free_ports(), f"front {FRONT_PORT} / back {BACK_PORT}")

    # V-01/V-02/V-03 main phase on the injected leap-day clock
    proc = launch_app("vue", data_dir, log_path, fake_date="2028-02-29", fake_time="08:30", fake_off=0)
    try:
        ok, why = wait_ready("vue", log_path)
        if not check("app-ready", ok, why):
            return
        checks, node_ok = run_node_phase("main")
        if not check("driver-main-results", node_ok and bool(checks), "no RESULTS payload from vue_driver"):
            return
        for c in checks:
            check(c["name"], c["ok"], c["detail"])
        lst = http_json("GET", "/api/v1/events?from_date=2028-02-01&to_date=2028-04-30")
        ids_before = sorted(ev["id"] for ev in lst.get("events", []))
        check("v02-three-events", lst.get("count") == 3, json.dumps(ids_before))
        check("v02-backend-empty-invalid", all(ev["start"] <= ev["end"] for ev in lst.get("events", [])))

        # V-01 cross-midnight: move the clock, reload, press Today
        kill_all()
        proc = launch_app("vue", data_dir, log_path, fake_date="2026-12-31", fake_time="23:59", fake_off=0)
        ok, why = wait_ready("vue", log_path)
        if not check("restart-ready", ok, why):
            return
        checks, node_ok = run_node_phase("midnight")
        if not check("driver-midnight-results", node_ok and bool(checks), "no RESULTS payload from vue_driver"):
            return
        for c in checks:
            check(c["name"], c["ok"], c["detail"])

        # stable ids across reopen
        lst2 = http_json("GET", "/api/v1/events?from_date=2028-02-01&to_date=2028-04-30")
        ids_after = sorted(ev["id"] for ev in lst2.get("events", []))
        check("v02-ids-stable", ids_before == ids_after, f"{ids_before} -> {ids_after}")
    finally:
        kill_all()


def run_vm(check):
    data_dir = fresh_data_dir("vm")
    log_dir = log_dir_for_run()
    log_path = os.path.join(log_dir, "verify-vm-app.log")
    check("ports-free", free_ports(), f"front {FRONT_PORT} / back {BACK_PORT}")

    proc = launch_app("vm", data_dir, log_path, fake_date="2028-02-29", fake_time="08:30", fake_off=0)
    try:
        ok, why = wait_ready("vm", log_path)
        if not check("app-ready", ok, why):
            return

        def find_btn(snap, label):
            m = re.search(r'button #(vnode_\d+|aura_\d+) "' + re.escape(label) + '"', snap)
            return m.group(1) if m else None

        # wait for the VALUE (field names match pre-Init state and would race)
        state = mcp_state_retry(["today", "selected_date", "year", "month", "clock_ok"], wait_flag="2028-02-29")
        check("v01-vm-injected-today", "2028-02-29" in state, state[:160].replace(chr(10), " "))
        snap = mcp_call("autoui_snapshot")
        check("v01-vm-leap-month", ("February" in snap and "2028" in snap))

        # V-02 via the VM form: two same-day events on 2028-02-29
        def vm_create(title, start, end):
            snap = mcp_call("autoui_snapshot")
            btn = find_btn(snap, "＋ 新建")
            if not btn:
                return False
            mcp_call("autoui_action", element_id=btn, action="press")
            form_snap = ""
            for _ in range(15):
                form_snap = mcp_call("autoui_snapshot")
                if "新建事件" in form_snap:
                    break
                time.sleep(1)
            snap = form_snap
            inputs = re.findall(r'(?:input|textbox) #(vnode_\d+|aura_\d+)', snap)
            if len(inputs) < 3:
                return False
            mcp_call("autoui_type", element_id=inputs[0], text=title)
            mcp_call("autoui_type", element_id=inputs[1], text=start)
            mcp_call("autoui_type", element_id=inputs[2], text=end)
            save = find_btn(mcp_call("autoui_snapshot"), "保存")
            if not save:
                return False
            mcp_call("autoui_action", element_id=save, action="press")
            time.sleep(2)
            return True

        ok1 = vm_create("VM-V02一", "2028-02-29 09:00", "2028-02-29 10:00")
        ok2 = vm_create("VM-V02二", "2028-02-29 13:00", "2028-02-29 14:00")
        check("v02-vm-form-creates", ok1 and ok2)
        lst = http_json("GET", "/api/v1/events?from_date=2028-02-29&to_date=2028-02-29")
        check("v02-vm-same-day-two", lst.get("count") == 2, json.dumps([e["id"] for e in lst.get("events", [])]))

        # V-03 via backend + UI retention: invalid date rejected through form
        vm_create("VM-V03无效", "2029-02-29 10:00", "2029-02-29 11:00")
        state = mcp_state_retry(["store_err", "form_open"], wait_flag="invalid_start")
        check("v03-vm-invalid-rejected", ("invalid_start" in state) and ("form_open: true" in state),
              state[:160].replace(chr(10), " "))
        lst = http_json("GET", "/api/v1/events?from_date=2029-01-01&to_date=2029-12-31")
        check("v03-vm-no-fake-event", lst.get("count") == 0)

        # reopen persistence: kill + relaunch with the same data dir, real clock off
        kill_all()
        proc = launch_app("vm", data_dir, log_path)
        ok, why = wait_ready("vm", log_path)
        if not check("reopen-ready", ok, why):
            return
        lst = http_json("GET", "/api/v1/events?from_date=2028-02-29&to_date=2028-02-29")
        check("v02-vm-reopen-persist", lst.get("count") == 2, str(lst.get("count")))
        expected_today = dt.date.today().isoformat()
        state = mcp_state_retry(["today"], wait_flag=expected_today)
        expected_today = dt.date.today().isoformat()
        check("v01-vm-real-clock-after-reopen", expected_today in state,
              state[:120].replace(chr(10), " ") + f" (expect {expected_today})")
    finally:
        kill_all()


def log_dir_for_run():
    os.makedirs(EVIDENCE_DIR, exist_ok=True)
    return EVIDENCE_DIR


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", choices=["vue", "vm"], required=True)
    args = ap.parse_args()

    if not os.path.exists(AUTO_BIN):
        print(f"auto CLI not found at {AUTO_BIN} (set AUTO_BIN)")
        return 2
    if not all(port_free(p) for p in (FRONT_PORT, BACK_PORT)):
        print(f"ports {FRONT_PORT}/{BACK_PORT} occupied — run tests/free_ports.py or free them; refusing to drift")
        return 2

    os.makedirs(EVIDENCE_DIR, exist_ok=True)
    check = Check()
    started = time.time()
    try:
        if args.profile == "vue":
            run_vue(check)
        else:
            run_vm(check)
    finally:
        ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        out = os.path.join(EVIDENCE_DIR, f"verify-{args.profile}-{ts}.json")
        with open(out, "w", encoding="utf-8") as fh:
            json.dump({"profile": args.profile, "ts": ts,
                       "auto_bin": AUTO_BIN,
                       "auto_bin_sha256": hashlib.sha256(open(AUTO_BIN, "rb").read()).hexdigest(),
                       "results": check.results,
                       "summary": check.summary,
                       "elapsed_s": round(time.time() - started, 1)}, fh, ensure_ascii=False, indent=1)
        print(f"evidence: {out}")

    failed = [r["name"] for r in check.failed]
    print("SUMMARY " + check.summary + ((" FAILED: " + ",".join(failed)) if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
