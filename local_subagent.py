#!/usr/bin/env python3
"""
local_subagent.py — Background Subagent Runner via Local Coding LLM

Dispatches small, mechanical background tasks to local models (e.g., Qwen 2.5 Coder 7B/14B)
or local AST heuristics so the primary agent does not waste context window or time:
- Background directory indexing and draft catalog node generation
- SML / Python signature extraction
- Git diff preservation audits
- Detached asynchronous execution with job tracking

Endpoints checked:
1. http://127.0.0.1:11434/v1 (Container local Ollama)
2. http://host.docker.internal:11434/v1 (Host Ollama daemon)
3. Configurable via LOCAL_LLM_URL
"""

import os
import sys
import json
import time
import glob
import uuid
import argparse
import urllib.request
import urllib.error
import subprocess
from typing import Dict, Any, Optional, List

JOBS_DIR = "/botworkspace/.local_subagent_jobs"
CATALOG_ROOT = os.environ.get("CATALOG_ROOT", os.path.dirname(os.path.abspath(__file__)))
MAX_CONCURRENT_BG_JOBS = 2
DEFAULT_ENDPOINTS = [
    os.environ.get("LOCAL_LLM_URL"),
    "http://127.0.0.1:11434/v1",
    "http://host.docker.internal:11434/v1",
    "http://172.31.0.1:11434/v1",
    "http://172.17.0.1:11434/v1"
]
DEFAULT_MODEL = os.environ.get("LOCAL_LLM_MODEL", "qwen2.5-coder:7b")


def ensure_jobs_dir() -> None:
    os.makedirs(JOBS_DIR, exist_ok=True)


def find_active_endpoint() -> Optional[str]:
    """Probes endpoints to find an active Ollama or OpenAI-compatible local server."""
    for ep in DEFAULT_ENDPOINTS:
        if not ep:
            continue
        try:
            url = ep.rstrip("/") + "/models"
            req = urllib.request.Request(url, headers={"User-Agent": "AntigravityLocalSubagent/1.0"})
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    return ep.rstrip("/")
        except Exception:
            continue
    return None


def call_local_llm(prompt: str, model: str = DEFAULT_MODEL, max_tokens: int = 1000) -> Optional[str]:
    """Queries the local LLM if available."""
    ep = find_active_endpoint()
    if not ep:
        return None

    try:
        url = f"{ep}/chat/completions"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a concise, factual coding assistant. Output lean markdown adhering strictly to token limits. No conversational filler."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.2
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=90.0) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
            return res_json["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return None


# ==============================================================================
# Specialized Background Tasks
# ==============================================================================

def task_index_repo(repo_dir: str, output_html: Optional[str] = None) -> Dict[str, Any]:
    """Background task: Indexes an unmapped repository into a lean <=60 line catalog node."""
    repo_name = os.path.basename(os.path.normpath(repo_dir))
    files = []
    total_lines = 0
    total_bytes = 0

    for root, dirs, fnames in os.walk(repo_dir):
        if ".git" in root or "__pycache__" in root or "node_modules" in root or "dist" in root:
            continue
        for f in fnames:
            p = os.path.join(root, f)
            try:
                sz = os.path.getsize(p)
                total_bytes += sz
                rel = os.path.relpath(p, repo_dir)
                with open(p, "r", encoding="utf-8", errors="ignore") as fp:
                    lines = sum(1 for _ in fp)
                total_lines += lines
                files.append((lines, sz, rel))
            except Exception:
                pass

    files.sort(key=lambda x: x[0], reverse=True)
    top_files = files[:8]

    # Generate lean HTML content
    up_branch = "academic_web.html"
    if "cv" in repo_name.lower():
        up_branch = "academic_web.html"
    elif "anti" in repo_name.lower():
        up_branch = "archives.html"
    else:
        up_branch = "fleet_infra.html"

    # Build prompt for local LLM or fallback
    prompt = f"""
Summarize this codebase repository '{repo_name}' for an AI long-term memory node:
Total Files: {len(files)}
Total Lines: {total_lines}
Top Files: {', '.join(f[2] for f in top_files[:5])}

Write 2 concise paragraphs:
1. Core purpose and architecture of '{repo_name}'.
2. Critical file responsibilities and technical invariants.
Keep it strictly under 200 words.
"""
    summary_text = call_local_llm(prompt)
    if not summary_text:
        summary_text = f"Repository `{repo_name}` contains {len(files)} source files ({total_lines} lines). Primary components include `{', '.join(f[2] for f in top_files[:4])}`."

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Repo: {repo_name}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.5; padding: 1.5rem; max-width: 52rem; margin: 0 auto; color: #1a1a1a; background: #fdfdfd; }}
h1, h2, h3 {{ color: #0f172a; border-bottom: 1px solid #e2e8f0; padding-bottom: 0.3rem; }}
a {{ color: #2563eb; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
code {{ background: #f1f5f9; padding: 0.15rem 0.35rem; border-radius: 3px; font-family: monospace; font-size: 0.9em; }}
ul {{ padding-left: 1.25rem; }}
.meta-box {{ background: #f8fafc; border: 1px solid #e2e8f0; padding: 0.75rem 1rem; border-radius: 4px; margin: 1rem 0; }}
</style>
</head>
<body>

<p><a href="../../branches/{up_branch}">[[UP: Branch Index]]</a> &bull; <a href="../../index.html">[[UP: Root Memory Index]]</a></p>

<h1>Repository: {repo_name}</h1>

<div class="meta-box">
  <p><strong>Filesystem Path:</strong> <code>{repo_dir}</code><br>
  <strong>Metrics:</strong> {len(files)} files &bull; {total_lines} lines &bull; {total_bytes // 1024} KB</p>
</div>

<h2>Architectural Overview</h2>
<p>{summary_text}</p>

<h2>Primary Files</h2>
<ul>
"""
    for l_cnt, sz_b, rel_f in top_files:
        html_content += f'  <li><code>{rel_f}</code> ({l_cnt} lines, {sz_b} bytes)</li>\n'
    html_content += """</ul>

</body>
</html>
"""
    if not output_html:
        output_html = os.path.join(CATALOG_ROOT, "repos", repo_name, "index.html")

    os.makedirs(os.path.dirname(output_html), exist_ok=True)
    with open(output_html, "w", encoding="utf-8") as fp:
        fp.write(html_content)

    return {
        "repo": repo_name,
        "files_count": len(files),
        "total_lines": total_lines,
        "output_node": output_html,
        "llm_used": bool(find_active_endpoint())
    }


def task_audit_preservation() -> Dict[str, Any]:
    """Background task: Validates that no commented code was removed in recent commits."""
    cmd = ["git", "diff", "HEAD~1", "HEAD", "--unified=0"]
    proc = subprocess.run(cmd, cwd="/botworkspace", capture_output=True, text=True)
    deleted_comments = 0
    for line in proc.stdout.splitlines():
        if line.startswith("-") and not line.startswith("---"):
            if "(*" in line or "*)" in line or line.strip().startswith("#") or line.strip().startswith("//"):
                deleted_comments += 1

    return {
        "git_diff_audited": True,
        "deleted_comment_lines": deleted_comments,
        "preservation_clean": (deleted_comments == 0)
    }


# ==============================================================================
# Job Dispatcher & Daemon Manager
# ==============================================================================

def get_cpu_temperature() -> float:
    """Reads real-time hardware temperature from /sys/class/thermal."""
    for z in glob.glob("/sys/class/thermal/thermal_zone*"):
        try:
            with open(os.path.join(z, "temp")) as f:
                return int(f.read().strip()) / 1000.0
        except Exception:
            pass
    return 50.0


def get_dynamic_concurrency_limit() -> int:
    """Adjusts concurrency dynamically based on hardware temperature."""
    temp = get_cpu_temperature()
    if temp < 72.0:
        return 4   # Cool (<72°C): run up to 4 parallel subagents
    elif temp < 82.0:
        return 2   # Warm (72°C - 82°C): throttle to 2
    else:
        return 1   # Hot (>82°C): throttle to 1 to protect CPU/GPU


def set_thermal_and_process_limits() -> None:
    """Sets CPU nice to lowest priority (19) to prevent laptop overheating and CPU starvation."""
    try:
        os.nice(19)
    except Exception:
        pass


def count_running_jobs() -> int:
    ensure_jobs_dir()
    count = 0
    for jf in glob.glob(os.path.join(JOBS_DIR, "*.json")):
        try:
            with open(jf) as fp:
                d = json.load(fp)
                if d.get("status") == "RUNNING":
                    pid = d.get("pid")
                    if pid and os.path.exists(f"/proc/{pid}"):
                        count += 1
        except Exception:
            pass
    return count


def execute_job(job_id: str, task_name: str, args: List[str]) -> None:
    set_thermal_and_process_limits()
    ensure_jobs_dir()
    job_file = os.path.join(JOBS_DIR, f"{job_id}.json")
    job_data = {
        "id": job_id,
        "pid": os.getpid(),
        "task": task_name,
        "status": "RUNNING",
        "started_at": time.time(),
        "completed_at": None,
        "result": None,
        "error": None
    }
    with open(job_file, "w", encoding="utf-8") as fp:
        json.dump(job_data, fp, indent=2)

    try:
        if task_name == "index-repo":
            repo_path = args[0] if args else "/botworkspace/CV"
            out_path = args[1] if len(args) > 1 else None
            res = task_index_repo(repo_path, out_path)
        elif task_name == "audit-preservation":
            res = task_audit_preservation()
        elif task_name == "english-audit":
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import english_tutor
            res = english_tutor.generate_reports()
        elif task_name == "ask-local":
            prompt = " ".join(args)
            ans = call_local_llm(prompt) or "[Local LLM offline; fallback heuristic response]"
            res = {"response": ans}
        else:
            raise ValueError(f"Unknown task: {task_name}")

        job_data["status"] = "DONE"
        job_data["result"] = res
    except Exception as e:
        job_data["status"] = "ERROR"
        job_data["error"] = str(e)
    finally:
        job_data["completed_at"] = time.time()
        with open(job_file, "w", encoding="utf-8") as fp:
            json.dump(job_data, fp, indent=2)


def list_jobs() -> None:
    ensure_jobs_dir()
    job_files = glob.glob(os.path.join(JOBS_DIR, "*.json"))
    print(f"=== LOCAL SUBAGENT BACKGROUND JOBS ({len(job_files)} total) ===")
    if not job_files:
        print("No background jobs found.")
        return

    for jf in sorted(job_files, reverse=True)[:10]:
        try:
            with open(jf, "r", encoding="utf-8") as fp:
                d = json.load(fp)
            dur = ""
            if d.get("completed_at") and d.get("started_at"):
                dur = f"({d['completed_at'] - d['started_at']:.1f}s)"
            print(f"- [{d.get('status', 'UNKNOWN')}] {d.get('id', '?')} | Task: {d.get('task', '?')} {dur}")
        except Exception:
            pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Local Subagent Runner via Local Coding LLM")
    subparsers = parser.add_subparsers(dest="action")

    # run command
    run_p = subparsers.add_parser("run")
    run_p.add_argument("task", choices=["index-repo", "audit-preservation", "ask-local", "english-audit"])
    run_p.add_argument("args", nargs="*")

    # bg command
    bg_p = subparsers.add_parser("bg")
    bg_p.add_argument("task", choices=["index-repo", "audit-preservation", "ask-local", "english-audit"])
    bg_p.add_argument("args", nargs="*")

    # status command
    subparsers.add_parser("status")

    args = parser.parse_args()

    if args.action == "status":
        list_jobs()
    elif args.action == "run":
        jid = str(uuid.uuid4())[:8]
        execute_job(jid, args.task, args.args)
        with open(os.path.join(JOBS_DIR, f"{jid}.json")) as fp:
            print(json.dumps(json.load(fp), indent=2))
    elif args.action == "bg":
        max_limit = get_dynamic_concurrency_limit()
        running = count_running_jobs()
        if running >= max_limit:
            temp = get_cpu_temperature()
            print(f"[THROTTLED: DYNAMIC THERMAL MONITOR] {running} background jobs already active (max {max_limit} at {temp:.1f}°C). Deferring to prevent overheating.")
            sys.exit(0)
        jid = str(uuid.uuid4())[:8]
        cmd = ["nice", "-n", "19", sys.executable, os.path.abspath(__file__), "run", args.task] + args.args
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        print(f"[LOCAL SUBAGENT LAUNCHED IN BACKGROUND] Job ID: {jid} | Task: {args.task} (nice: 19 | limit: {max_limit} @ {get_cpu_temperature():.1f}°C)")
    else:
        parser.print_help()
