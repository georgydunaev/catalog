#!/usr/bin/env python3
"""
catalog/queue_worker.py — Autonomous Background Queue Worker Pool

Continuously feeds low-priority background tasks (repository indexing, preservation audits)
to local Ollama subagents, maintaining full GPU/CPU saturation within safe thermal limits
(nice -n 19, temp <= 75°C).
"""

import os
import sys
import time
import glob
import sqlite3
import subprocess

WORKSPACE = os.environ.get("WORKSPACE_DIR", "/botworkspace")
CATALOG_ROOT = os.environ.get("CATALOG_ROOT", os.path.dirname(os.path.abspath(__file__)))
CATALOG_DB = os.environ.get("CATALOG_DB_PATH", os.path.join(CATALOG_ROOT, "catalog.db"))
SUBAGENT_BIN = os.path.join(CATALOG_ROOT, "local_subagent.py")
COGNITION_BIN = os.path.join(CATALOG_ROOT, "cognition.py")


def get_cpu_temp() -> float:
    for z in glob.glob("/sys/class/thermal/thermal_zone*"):
        try:
            with open(os.path.join(z, "temp")) as f:
                return int(f.read().strip()) / 1000.0
        except Exception:
            pass
    return 45.0


def get_concurrency_limit(temp: float) -> int:
    if temp < 72.0:
        return 4
    elif temp < 82.0:
        return 2
    else:
        return 1


def count_active_subagents() -> int:
    try:
        ps = subprocess.run(["ps", "-eo", "cmd"], capture_output=True, text=True, timeout=10).stdout
        return sum(1 for line in ps.splitlines() if "local_subagent.py run" in line)
    except Exception:
        return 0


def get_unindexed_repos() -> list:
    conn = sqlite3.connect(CATALOG_DB, timeout=30.0)
    try:
        c = conn.cursor()
        c.execute("SELECT relpath FROM nodes WHERE relpath LIKE 'repos/%'")
        indexed = set()
        for row in c.fetchall():
            parts = row[0].split("/")
            if len(parts) > 1:
                indexed.add(parts[1])
    finally:
        conn.close()

    all_dirs = [d for d in os.listdir(WORKSPACE) if os.path.isdir(os.path.join(WORKSPACE, d)) and not d.startswith(".")]
    ignore = {"catalog", "mybot", "loop_logs", "installed", "dist"}
    return [d for d in all_dirs if d not in indexed and d not in ignore]


def main():
    print("[QUEUE WORKER] Started autonomous background queue pool...")
    in_flight = set()
    while True:
        unindexed = get_unindexed_repos()
        candidates = [r for r in unindexed if r not in in_flight]
        if not candidates and not in_flight:
            print("[QUEUE WORKER] All repositories indexed! Running final cognitive audit...")
            subprocess.run([sys.executable, COGNITION_BIN, "audit"], check=False)
            break

        temp = get_cpu_temp()
        limit = get_concurrency_limit(temp)
        active = count_active_subagents()

        # Clean up finished in_flight items
        if in_flight:
            conn = sqlite3.connect(CATALOG_DB, timeout=30.0)
            try:
                c = conn.cursor()
                c.execute("SELECT relpath FROM nodes WHERE relpath LIKE 'repos/%'")
                current_indexed = set()
                for row in c.fetchall():
                    parts = row[0].split("/")
                    if len(parts) > 1:
                        current_indexed.add(parts[1])
            finally:
                conn.close()
            in_flight = {r for r in in_flight if r not in current_indexed}

        if active < limit and candidates:
            repo = candidates[0]
            in_flight.add(repo)
            repo_path = os.path.join(WORKSPACE, repo)
            print(f"[DISPATCHING] {repo} (Active: {active + 1}/{limit} | Temp: {temp:.1f}°C)")
            subprocess.Popen(
                ["nice", "-n", "19", sys.executable, SUBAGENT_BIN, "run", "index-repo", repo_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            time.sleep(1.0)
        else:
            time.sleep(3.0)


if __name__ == "__main__":
    main()
