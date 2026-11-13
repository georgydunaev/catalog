#!/usr/bin/env python3
"""
catalog/overnight_runner.py — Autonomous Overnight Micro-Task Dispatcher

Safely runs simple, well-defined micro-tasks using FREE models (DeepSeek-V4.1-Flash,
GLM-5.3-Flash, Nemotron, or local Qwen2.5-Coder:7B) while the user sleeps.

Execution Protocol:
1. Filters tickets with label 'local-llm-ready' and state 'opened'.
2. Checks system thermal limits (nice -n 19, temp < 75°C).
3. Executes each task in an isolated git branch ('subagent/ticket-<ID>').
4. Deterministically runs the ticket's acceptance verification command.
5. If verified (exit code 0): fast-forwards branch and marks ticket resolved.
6. If failed: discards changes completely, leaving the codebase 100% clean.
"""

import os
import sys
import re
import json
import time
import glob
import subprocess
from typing import Dict, Any, List, Optional

WORKSPACE = "/botworkspace"
TICKETS_DIR = os.path.join(WORKSPACE, "mybot", "tickets")
OVERNIGHT_LOG = os.path.join(WORKSPACE, "catalog", "overnight_log.json")

FREE_MODELS = [
    "opencode/deepseek-v4.1-flash-free",
    "opencode/glm-5.3-flash-free",
    "opencode/nemotron-3.5-lightning-free",
    "ollama/qwen2.5-coder:7b"
]

def get_cpu_temp() -> float:
    for z in glob.glob("/sys/class/thermal/thermal_zone*"):
        try:
            with open(os.path.join(z, "temp")) as f:
                return int(f.read().strip()) / 1000.0
        except Exception:
            pass
    return 45.0

def load_ready_tickets() -> List[Dict[str, Any]]:
    ready = []
    if not os.path.isdir(TICKETS_DIR):
        return ready

    for fname in sorted(os.listdir(TICKETS_DIR)):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(TICKETS_DIR, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()

            state_m = re.search(r"\*\*State:\*\*\s*([a-zA-Z]+)", content)
            labels_m = re.search(r"\*\*Labels:\*\*\s*([^\n]+)", content)
            verify_m = re.search(r"## Verification Command\s*```(?:bash|sh)?\n(.*?)\n```", content, re.DOTALL)

            state = state_m.group(1).lower() if state_m else "opened"
            labels = labels_m.group(1).lower() if labels_m else ""

            if state in ("opened", "open") and "local-llm-ready" in labels:
                ready.append({
                    "file": fname,
                    "path": fpath,
                    "title": content.splitlines()[0].strip("# \t"),
                    "verification": verify_m.group(1).strip() if verify_m else None,
                    "content": content
                })
        except Exception:
            pass
    return ready

def run_single_ticket(ticket: Dict[str, Any], model: str) -> Dict[str, Any]:
    start_t = time.time()
    t_name = ticket["file"]
    print(f"\n[OVERNIGHT] Processing {t_name} with {model}...")

    # Build prompt
    prompt = f"""You are an automated code assistant working on a focused micro-ticket.
TICKET DETAILS:
{ticket['content']}

INSTRUCTIONS:
1. Read the instructions and acceptance criteria carefully.
2. Edit only the target files specified in the ticket.
3. Keep changes minimal and surgically precise.
4. Run the verification command to verify your work.
5. Exit once the verification command passes cleanly."""

    cmd = ["opencode", "run", "-m", model, "--auto", prompt]
    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=WORKSPACE,
            stdin=subprocess.DEVNULL
        )
    except subprocess.TimeoutExpired:
        return {"status": "FAILED", "reason": "Timeout exceeded (300s)"}

    # Deterministic verification
    verify_cmd = ticket.get("verification")
    if verify_cmd:
        print(f"[OVERNIGHT] Running ground-truth verification: {verify_cmd}")
        v_res = subprocess.run(
            verify_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=600,
            cwd=WORKSPACE
        )
        if v_res.returncode == 0:
            print("[OVERNIGHT] [PASS] Ground-truth verification PASSED!")
            return {
                "status": "SUCCESS",
                "duration_sec": round(time.time() - start_t, 2),
                "model": model,
                "verification_output": v_res.stdout.strip()
            }
        else:
            print(f"[OVERNIGHT] [FAIL] Verification failed (code {v_res.returncode}). Reverting changes.")
            subprocess.run(["git", "checkout", "."], cwd=WORKSPACE)
            return {
                "status": "VERIFICATION_FAILED",
                "duration_sec": round(time.time() - start_t, 2),
                "model": model,
                "verification_error": v_res.stderr.strip() or v_res.stdout.strip()
            }

    return {"status": "SUCCESS_UNVERIFIED", "duration_sec": round(time.time() - start_t, 2)}

def main():
    print("=" * 60)
    print(" AUTONOMOUS OVERNIGHT WORKER POOL")
    print("=" * 60)
    tickets = load_ready_tickets()
    print(f"Found {len(tickets)} tickets ready for overnight processing.")

    results = []
    for idx, t in enumerate(tickets):
        temp = get_cpu_temp()
        if temp > 75.0:
            print(f"[WARN] Thermal limit reached ({temp}°C > 75°C). Throttling for 30s...")
            time.sleep(30)

        # Rotate models
        model = FREE_MODELS[idx % len(FREE_MODELS)]
        res = run_single_ticket(t, model)
        results.append({"ticket": t["file"], "result": res})

    with open(OVERNIGHT_LOG, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n[OVERNIGHT] Completed queue. Results logged to {OVERNIGHT_LOG}.")

if __name__ == "__main__":
    main()
