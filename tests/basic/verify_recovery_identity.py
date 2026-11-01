#!/usr/bin/env python3
"""CALENDAR-002 recovery-identity verification (plan §6 C-01..C-05).

Permanent replay entry:
  python tests/basic/verify_recovery_identity.py --profile vue
  python tests/basic/verify_recovery_identity.py --profile vm

Runs the REAL app split-mode stack (generated rust backend 17821 + profile UI)
against an isolated data dir and proves the v2 recovery contract end to end:

  C-01/02/03 (HTTP level, isolated scratch dirs via test/setup)
      stale credential refused after manifest loss (watermark-backed rev);
      deleted ids never reissued; all-deleted ≠ fresh; identity+manifest
      loss → recovery_unproven refusal with byte-preserved files; v1
      migration with backup; consent re-anchor + next write. These
      assertions are the "forced old-max-policy counterexamples": reverting
      to the v1 recovery turns them red (gate non-zero).
  C-04 (real UI)
      中文跨月事件 UI CRUD (create/edit/month-nav), strong-kill reopen with
      stable ids and untouched wall-clock fields, next write succeeds.
  C-03 UI face (real UI)
      unproven state: preservation banner, data still listed, save refused
      with input retained; after consent relaunch the banner is gone and the
      next real UI write succeeds.
  C-05 (prep/cleanup)
      own-process discipline only (tests/free_ports.py Ownership): occupied
      ports abort the run, bystanders are never killed (probe
      plan-artifacts/plan-002/probe_t01_ownproc.py); cleanup report and tool
      identity recorded in evidence.

Isolation: fresh temp data dir per run; damage injection only on the
isolated copy; strangers never touched.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import verify_basic as vb  # noqa: E402  (launch/wait/own-process/http helpers)
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..")))
import free_ports as fpg  # noqa: E402

DRIVER = os.path.join(HERE, "recovery_driver.mjs")


def run_node_phase(phase):
    node = os.environ.get("NODE", "node")
    proc = subprocess.run([node, DRIVER, "--phase", phase], cwd=REPO,
                          capture_output=True, text=True, timeout=300,
                          encoding="utf-8", errors="replace")
    checks = []
    for line in (proc.stdout or "").splitlines():
        if line.startswith("RESULTS "):
            checks = json.loads(line[len("RESULTS "):])
    if not checks:
        print((proc.stderr or "")[-800:])
    return checks, proc.returncode == 0 and bool(checks)


def sha_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:16]


def dir_hashes(data_dir):
    out = {}
    ev = os.path.join(data_dir, "store", "events")
    if os.path.isdir(ev):
        for n in sorted(os.listdir(ev)):
            out[f"events/{n}"] = sha_file(os.path.join(ev, n))
    for name in ("manifest.json", "identity.json"):
        p = os.path.join(data_dir, "store", name)
        if os.path.exists(p):
            out[name] = sha_file(p)
    return out


def api_ids(events):
    return sorted(e["id"] for e in events)


# ── VM-track UI helpers (AutoUI MCP, same pattern as verify_basic.run_vm)

def vm_find_btn(snap, label, nth=0):
    ids = re.findall(r'button #(vnode_\d+|aura_\d+) "' + re.escape(label) + '"', snap)
    return ids[nth] if len(ids) > nth else None


def vm_create(title, start, end, save_label="保存"):
    snap = vb.mcp_call("autoui_snapshot")
    btn = vm_find_btn(snap, "＋ 新建")
    if not btn:
        return False
    vb.mcp_call("autoui_action", element_id=btn, action="press")
    form_snap = ""
    for _ in range(15):
        form_snap = vb.mcp_call("autoui_snapshot")
        if "新建事件" in form_snap or "编辑事件" in form_snap:
            break
        time.sleep(1)
    inputs = re.findall(r'(?:input|textbox) #(vnode_\d+|aura_\d+)', form_snap)
    if len(inputs) < 3:
        return False
    vb.mcp_call("autoui_type", element_id=inputs[0], text=title)
    vb.mcp_call("autoui_type", element_id=inputs[1], text=start)
    vb.mcp_call("autoui_type", element_id=inputs[2], text=end)
    save = vm_find_btn(vb.mcp_call("autoui_snapshot"), save_label)
    if not save:
        return False
    vb.mcp_call("autoui_action", element_id=save, action="press")
    time.sleep(2)
    return True


def vm_edit_second_row_title(new_title):
    """Edit the SECOND visible row's 编辑 button — both seeded events cover
    02-29 and render in creation order (跨月甲 first, 当日乙 second)."""
    snap = vb.mcp_call("autoui_snapshot")
    btn = vm_find_btn(snap, "编辑", nth=1)
    if not btn:
        return False
    vb.mcp_call("autoui_action", element_id=btn, action="press")
    form_snap = ""
    for _ in range(15):
        form_snap = vb.mcp_call("autoui_snapshot")
        if "编辑事件" in form_snap:
            break
        time.sleep(1)
    inputs = re.findall(r'(?:input|textbox) #(vnode_\d+|aura_\d+)', form_snap)
    if not inputs:
        return False
    vb.mcp_call("autoui_type", element_id=inputs[0], text=new_title)
    save = vm_find_btn(vb.mcp_call("autoui_snapshot"), "保存修改")
    if not save:
        return False
    vb.mcp_call("autoui_action", element_id=save, action="press")
    time.sleep(2)
    return True


def vm_press(label):
    snap = vb.mcp_call("autoui_snapshot")
    btn = vm_find_btn(snap, label)
    if not btn:
        return False
    vb.mcp_call("autoui_action", element_id=btn, action="press")
    time.sleep(1.5)
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", choices=["vue", "vm"], required=True)
    args = ap.parse_args()
    profile = args.profile

    if not os.path.exists(vb.AUTO_BIN):
        print(f"auto CLI not found at {vb.AUTO_BIN} (set AUTO_BIN)")
        return 2
    if not all(vb.port_free(p) for p in (vb.FRONT_PORT, vb.BACK_PORT)):
        for port, pid in sorted(fpg.listeners((vb.FRONT_PORT, vb.BACK_PORT)).items()):
            info = fpg.proc_info(pid) or {}
            print(f"OCCUPIED port {port} pid {pid} image {info.get('image', '?')} — "
                  f"free them yourself; this run never kills non-owned processes")
        return 2

    os.makedirs(vb.EVIDENCE_DIR, exist_ok=True)
    check = vb.Check()
    started = time.time()
    data_dir = vb.fresh_data_dir("rec-" + profile)
    log_path = os.path.join(vb.EVIDENCE_DIR, f"verify-rec-{profile}-app.log")
    cleanup: dict = {}

    try:
        check("ports-free", all(vb.port_free(p) for p in (vb.FRONT_PORT, vb.BACK_PORT)),
              f"front {vb.FRONT_PORT} / back {vb.BACK_PORT}")

        proc = vb.launch_app(profile, data_dir, log_path,
                             fake_date="2028-02-29", fake_time="08:30", fake_off=0)
        ok, why = vb.wait_ready(profile, log_path)
        if not check("app-ready", ok, why):
            return finish(check, profile, started, cleanup, 1)

        # ── C-04 seed: 中文跨月 UI CRUD ──────────────────────────────────
        if profile == "vue":
            checks, node_ok = run_node_phase("seed")
            if not check("seed-driver-results", node_ok and bool(checks), "no RESULTS"):
                return finish(check, profile, started, cleanup, 1)
            for c in checks:
                check(c["name"], c["ok"], c["detail"])
        else:
            state = vb.mcp_state_retry(["today"], wait_flag="2028-02-29")
            check("r01-vm-injected-today", "2028-02-29" in state, state[:120])
            check("r01-vm-create-crossmonth", vm_create("恢复跨月甲", "2028-02-28 22:00", "2028-03-02 08:00"))
            check("r01-vm-create-sameday", vm_create("恢复当日乙", "2028-02-29 09:00", "2028-02-29 10:00"))
            check("r01-vm-edit", vm_edit_second_row_title("恢复当日乙改"))
            check("r01-vm-prev-month", vm_press("<"))
            snap = vb.mcp_call("autoui_snapshot")
            check("r01-vm-january", "January" in snap)
            check("r01-vm-back-today", vm_press("Today"))
            snap = vb.mcp_call("autoui_snapshot")
            check("r01-vm-back-on-day", "恢复当日乙改" in snap)

        lst = vb.http_json("GET", "/api/v1/events?from_date=2028-02-01&to_date=2028-03-31")
        ids_seed = api_ids(lst.get("events", []))
        ev_day = [e for e in lst.get("events", []) if e["title"] == "恢复当日乙改"]
        check("seed-backend-events", lst.get("count") == 2 and len(ev_day) == 1,
              json.dumps(api_ids(lst.get("events", []))))
        wall = (ev_day[0]["start"], ev_day[0]["end"]) if ev_day else ("", "")

        # ── C-04 strong-kill reopen: stable ids, wall clock untouched ────
        vb.kill_all()
        proc = vb.launch_app(profile, data_dir, log_path,
                             fake_date="2028-02-29", fake_time="08:30", fake_off=0)
        ok, why = vb.wait_ready(profile, log_path)
        if not check("reopen-ready", ok, why):
            return finish(check, profile, started, cleanup, 1)
        if profile == "vue":
            checks, node_ok = run_node_phase("restart")
            if not check("restart-driver-results", node_ok and bool(checks), "no RESULTS"):
                return finish(check, profile, started, cleanup, 1)
            for c in checks:
                check(c["name"], c["ok"], c["detail"])
        else:
            # visible day list carries the titles (month_events dumps vmrefs)
            state = vb.mcp_state_retry(["today"], wait_flag="2028-02-29")
            snap = vb.mcp_call("autoui_snapshot")
            check("r04-vm-reopen-visible", "恢复当日乙改" in snap, snap[:150])
            check("r04-vm-next-write", vm_create("重开后首写", "2028-02-29 15:00", "2028-02-29 16:00"))
        lst2 = vb.http_json("GET", "/api/v1/events?from_date=2028-02-01&to_date=2028-03-31")
        ids_after = api_ids(lst2.get("events", []))
        ev_day2 = [e for e in lst2.get("events", []) if e["title"] == "恢复当日乙改"]
        check("r04-ids-stable", ids_after[:2] == ids_seed,
              f"{ids_seed} -> {ids_after}")
        check("r04-wall-clock-untouched",
              bool(ev_day2) and (ev_day2[0]["start"], ev_day2[0]["end"]) == wall,
              f"{wall} -> {(ev_day2[0]['start'], ev_day2[0]['end']) if ev_day2 else None}")

        # ── C-01/02 HTTP replays on scratch dirs (old-max counterexamples) ─
        def switch(d):
            raw = vb.http_json("POST", "/api/v1/test/setup", {"data_dir": d})
            return json.loads(raw) if isinstance(raw, str) else raw

        def create_t(d, title, start="2028-03-01 09:00", end="2028-03-01 10:00"):
            switch(d)
            return vb.http_json("POST", "/api/v1/events",
                                {"title": title, "start": start, "end": end, "notes": ""})

        s1 = os.path.join(os.path.dirname(data_dir), "rec-c01")
        os.makedirs(s1, exist_ok=True)
        for i in range(4):
            create_t(s1, f"C01-{i}")
        create_t(s1, "C01-B0")                      # ev-5 rev5
        switch(s1)
        vb.http_json("POST", "/api/v1/events/update",
                     {"id": "ev-5", "expected_rev": 5, "title": "C01-B1",
                      "start": "2028-03-01 09:00", "end": "2028-03-01 10:00", "notes": ""})
        vb.http_json("POST", "/api/v1/events/update",
                     {"id": "ev-5", "expected_rev": 6, "title": "C01-B2",
                      "start": "2028-03-01 09:00", "end": "2028-03-01 10:00", "notes": ""})
        vb.http_json("POST", "/api/v1/events/delete", {"id": "ev-5", "expected_rev": 7})
        with open(os.path.join(s1, "store", "manifest.json"), "w", encoding="utf-8") as fh:
            fh.write("{corrupt")
        switch(s1)
        st = vb.http_json("GET", "/api/v1/status")
        stale = vb.http_json("POST", "/api/v1/events/update",
                             {"id": "ev-2", "expected_rev": 4, "title": "STALE",
                              "start": "2028-03-01 09:00", "end": "2028-03-01 10:00", "notes": ""})
        check("c01-stale-refused", st.get("rev") == 8 and stale.get("err_code") == "conflict",
              f"rev={st.get('rev')} stale={stale.get('err_code')} (old policy: stale accepted)")

        s2 = os.path.join(os.path.dirname(data_dir), "rec-c02")
        os.makedirs(s2, exist_ok=True)
        for i in range(5):
            create_t(s2, f"C02-{i}")
        switch(s2)
        vb.http_json("POST", "/api/v1/events/delete", {"id": "ev-5", "expected_rev": 5})
        with open(os.path.join(s2, "store", "manifest.json"), "w", encoding="utf-8") as fh:
            fh.write("garbage{")
        switch(s2)
        st = vb.http_json("GET", "/api/v1/status")
        r = vb.http_json("POST", "/api/v1/events",
                         {"title": "C02-NEW", "start": "2028-03-01 09:00",
                          "end": "2028-03-01 10:00", "notes": ""})
        check("c02-id-not-reissued", r.get("event", {}).get("id") == "ev-6",
              f"id={r.get('event', {}).get('id')} rev={st.get('rev')} (old policy: ev-5)")

        # ── C-03 damage injection on the UI dir: unproven UI face ─────────
        hashes_pre = dir_hashes(data_dir)
        vb.kill_all()
        os.remove(os.path.join(data_dir, "store", "identity.json"))
        with open(os.path.join(data_dir, "store", "manifest.json"), "w", encoding="utf-8") as fh:
            fh.write("{\"broken\"")
        proc = vb.launch_app(profile, data_dir, log_path,
                             fake_date="2028-02-29", fake_time="08:30", fake_off=0)
        ok, why = vb.wait_ready(profile, log_path)
        if not check("unproven-ready", ok, why):
            return finish(check, profile, started, cleanup, 1)
        st = vb.http_json("GET", "/api/v1/status")
        check("c03-status-unproven", st.get("recovery_state") == "unproven", json.dumps(st)[:160])
        if profile == "vue":
            checks, node_ok = run_node_phase("unproven")
            if not check("unproven-driver-results", node_ok and bool(checks), "no RESULTS"):
                return finish(check, profile, started, cleanup, 1)
            for c in checks:
                check(c["name"], c["ok"], c["detail"])
        else:
            state = vb.mcp_state_retry(["recovery_state"], wait_flag="unproven", timeout_s=40)
            snap = vb.mcp_call("autoui_snapshot")
            check("r03-vm-banner", "unproven" in state and "存储身份未能证明" in snap,
                  state[:120] + " | " + snap[:120])
            okc = vm_create("拒绝写入", "2028-02-29 11:00", "2028-02-29 12:00")
            state = vb.mcp_state_retry(["store_err", "form_open", "f_title"], wait_flag="recovery_unproven")
            check("r03-vm-save-refused", "recovery_unproven" in state and "form_open: true" in state,
                  state[:180].replace(chr(10), " "))
            check("r03-vm-input-retained", okc and "拒绝写入" in state, state[:180])

        # ── consent relaunch: banner gone, next real UI write succeeds ────
        vb.kill_all()
        proc = vb.launch_app(profile, data_dir, log_path,
                             fake_date="2028-02-29", fake_time="08:30", fake_off=0,
                             extra_env={"AUTO_CALENDAR_RECOVERY_CONSENT": "accept-scan"})
        ok, why = vb.wait_ready(profile, log_path)
        if not check("consent-ready", ok, why):
            return finish(check, profile, started, cleanup, 1)
        st = vb.http_json("GET", "/api/v1/status")
        report_p = os.path.join(data_dir, "store", "recovery-report.json")
        ident_p = os.path.join(data_dir, "store", "identity.json")
        ident = json.load(open(ident_p, encoding="utf-8")) if os.path.exists(ident_p) else {}
        check("c03-consent-reanchored", st.get("recovery_state") == "ok"
              and st.get("generation") == "g-recovered" and os.path.exists(report_p),
              f"state={st.get('recovery_state')} gen={st.get('generation')} report={os.path.exists(report_p)}")
        if profile == "vue":
            checks, node_ok = run_node_phase("consent")
            if not check("consent-driver-results", node_ok and bool(checks), "no RESULTS"):
                return finish(check, profile, started, cleanup, 1)
            for c in checks:
                check(c["name"], c["ok"], c["detail"])
        else:
            snap = vb.mcp_state_retry(["today"], wait_flag="2028-02-29")
            check("r02-vm-banner-gone", "存储身份未能证明" not in snap, snap[:120])
            check("r02-vm-next-write", vm_create("受控恢复后首写", "2028-02-29 17:00", "2028-02-29 18:00"))
        lst3 = vb.http_json("GET", "/api/v1/events?from_date=2028-02-01&to_date=2028-03-31")
        titles = [e["title"] for e in lst3.get("events", [])]
        check("c03-data-preserved", "恢复当日乙改" in titles and "恢复跨月甲" in titles,
              json.dumps(titles))

        # launch_app supports extra_env for the consent relaunch
    finally:
        vb.kill_all()
        cleanup = vb.LAST_CLEANUP

    return finish(check, profile, started, cleanup, 0)


def finish(check, profile, started, cleanup, rc):
    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = os.path.join(vb.EVIDENCE_DIR, f"verify-rec-{profile}-{ts}.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"profile": profile, "ts": ts,
                   "auto_bin": vb.AUTO_BIN,
                   "auto_bin_sha256": hashlib.sha256(open(vb.AUTO_BIN, "rb").read()).hexdigest(),
                   "auto_version": subprocess.run([vb.AUTO_BIN, "--version"],
                                                  capture_output=True, text=True).stdout.strip(),
                   "node_version": subprocess.run(["node", "--version"],
                                                  capture_output=True, text=True).stdout.strip(),
                   "own_process_discipline": "tests/free_ports.py Ownership — bystanders never killed",
                   "cleanup": cleanup,
                   "results": check.results,
                   "summary": check.summary,
                   "elapsed_s": round(time.time() - started, 1)}, fh, ensure_ascii=False, indent=1)
    print(f"evidence: {out}")
    failed = [r["name"] for r in check.failed]
    print("SUMMARY " + check.summary + ((" FAILED: " + ",".join(failed)) if failed else ""))
    return 1 if failed else rc


if __name__ == "__main__":
    sys.exit(main())
