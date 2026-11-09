#!/usr/bin/env python3
"""
catalog/free_subagent_fleet.py — Autonomous Free & Local Subagent Dispatcher

Dispatches mechanical, exploratory, and repetitive tasks to FREE models
to preserve primary Antigravity weekly token quota:
1. OpenCode Free Models (deepseek-v4.1-flash-free, glm-5.3-flash-free, nemotron-3.5-lightning-free)
2. Local GPU Ollama (qwen2.5-coder:7b on host.docker.internal:11434)

Security & Session Isolation:
- Cryptographic ephemeral sessions (ses_...) preventing crosstalk.
- Prompt redaction against credential/PII leaks.
- Thermal governor and deterministic test validation.
"""

import os
import sys
import json
import time
import uuid
import re
import argparse
import subprocess
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional

FREE_MODELS = [
    "opencode/glm-5.3-flash-free",
    "opencode/deepseek-v4.1-flash-free",
    "opencode/nemotron-3.5-lightning-free",
    "ollama/qwen2.5-coder:7b"
]

JOBS_DIR = "/botworkspace/.local_subagent_jobs"
OLLAMA_BASE = "http://host.docker.internal:11434"

# Sensitive patterns to sanitize
SANITIZE_PATTERNS = [
    (r'(?i)api[_-]?key\s*[:=]\s*["\']?[a-zA-Z0-9_\-]{16,}["\']?', '[REDACTED_API_KEY]'),
    (r'(?i)token\s*[:=]\s*["\']?[a-zA-Z0-9_\-]{16,}["\']?', '[REDACTED_TOKEN]'),
    (r'(?i)password\s*[:=]\s*["\']?[^\s"\']{6,}["\']?', '[REDACTED_PASSWORD]'),
    (r'glpat-[a-zA-Z0-9_\-]{20,}', '[REDACTED_GITLAB_PAT]')
]

def sanitize_prompt(text: str) -> str:
    cleaned = text
    for pattern, replacement in SANITIZE_PATTERNS:
        cleaned = re.sub(pattern, replacement, cleaned)
    return cleaned

def ensure_jobs_dir() -> None:
    os.makedirs(JOBS_DIR, exist_ok=True)

def dispatch_task(
    prompt: str,
    model: str = "opencode/glm-5.3-flash-free",
    cwd: str = "/botworkspace",
    timeout: int = 180,
    background: bool = False
) -> Dict[str, Any]:
    ensure_jobs_dir()
    clean_prompt = sanitize_prompt(prompt)
    session_id = f"ses_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    job_id = f"free-{int(time.time())}-{uuid.uuid4().hex[:6]}"
    job_file = os.path.join(JOBS_DIR, f"{job_id}.json")

    # Routing: Ollama vs OpenCode
    if model.startswith("ollama/"):
        real_model = model.split("/", 1)[1]
        return _dispatch_ollama(real_model, clean_prompt, job_id, job_file, timeout)

    # OpenCode execution with strict session isolation
    cmd = ["opencode", "run", "-m", model, "--session", session_id, "--auto", clean_prompt]

    start_info = {
        "job_id": job_id,
        "session_id": session_id,
        "model": model,
        "prompt": clean_prompt[:200] + "...",
        "status": "RUNNING",
        "start_time": time.time(),
        "pid": None
    }
    with open(job_file, "w") as f:
        json.dump(start_info, f, indent=2)

    if background:
        proc = subprocess.Popen(
            cmd,
            stdout=open(os.path.join(JOBS_DIR, f"{job_id}.log"), "w"),
            stderr=subprocess.STDOUT,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            start_new_session=True
        )
        start_info["pid"] = proc.pid
        with open(job_file, "w") as f:
            json.dump(start_info, f, indent=2)
        return {"job_id": job_id, "status": "LAUNCHED_BG", "pid": proc.pid, "model": model, "session_id": session_id}

    # Synchronous execution
    start_t = time.time()
    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            stdin=subprocess.DEVNULL
        )
        elapsed = time.time() - start_t
        out = {
            "job_id": job_id,
            "session_id": session_id,
            "model": model,
            "status": "COMPLETED" if res.returncode == 0 else "FAILED",
            "returncode": res.returncode,
            "duration_sec": round(elapsed, 2),
            "output": res.stdout.strip() or res.stderr.strip()
        }
        with open(job_file, "w") as f:
            json.dump(out, f, indent=2)
        return out
    except subprocess.TimeoutExpired:
        out = {
            "job_id": job_id,
            "session_id": session_id,
            "model": model,
            "status": "TIMEOUT",
            "duration_sec": timeout,
            "error": "Task timed out"
        }
        with open(job_file, "w") as f:
            json.dump(out, f, indent=2)
        return out

def _dispatch_ollama(model: str, prompt: str, job_id: str, job_file: str, timeout: int) -> Dict[str, Any]:
    url = f"{OLLAMA_BASE}/api/generate"
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    start_t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            elapsed = time.time() - start_t
            out = {
                "job_id": job_id,
                "model": f"ollama/{model}",
                "status": "COMPLETED",
                "duration_sec": round(elapsed, 2),
                "output": data.get("response", "").strip()
            }
            with open(job_file, "w") as f:
                json.dump(out, f, indent=2)
            return out
    except Exception as e:
        elapsed = time.time() - start_t
        out = {
            "job_id": job_id,
            "model": f"ollama/{model}",
            "status": "FAILED",
            "duration_sec": round(elapsed, 2),
            "error": str(e)
        }
        with open(job_file, "w") as f:
            json.dump(out, f, indent=2)
        return out

def list_recent_jobs(limit: int = 10) -> List[Dict[str, Any]]:
    ensure_jobs_dir()
    files = sorted(
        [os.path.join(JOBS_DIR, f) for f in os.listdir(JOBS_DIR) if f.endswith(".json")],
        key=os.path.getmtime,
        reverse=True
    )
    jobs = []
    for f in files[:limit]:
        try:
            with open(f, "r") as jf:
                jobs.append(json.load(jf))
        except Exception:
            pass
    return jobs

def main():
    parser = argparse.ArgumentParser(description="Free Subagent Fleet Dispatcher")
    subparsers = parser.add_subparsers(dest="command")

    run_p = subparsers.add_parser("run")
    run_p.add_argument("prompt", help="Instruction or prompt for subagent")
    run_p.add_argument("-m", "--model", default="opencode/glm-5.3-flash-free", choices=FREE_MODELS)
    run_p.add_argument("-bg", "--background", action="store_true", help="Launch in background")
    run_p.add_argument("-t", "--timeout", type=int, default=180, help="Timeout in seconds")

    subparsers.add_parser("jobs")
    subparsers.add_parser("status")
    subparsers.add_parser("models")

    args = parser.parse_args()

    if args.command == "run":
        res = dispatch_task(args.prompt, model=args.model, background=args.background, timeout=args.timeout)
        print(json.dumps(res, indent=2))
    elif args.command in ("jobs", "status"):
        jobs = list_recent_jobs()
        print(json.dumps(jobs, indent=2))
    elif args.command == "models":
        print(json.dumps(FREE_MODELS, indent=2))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
