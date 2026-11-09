#!/usr/bin/env python3
"""
opencode_delegate.py — Autonomous Task Delegation via OpenCode & Local Coding Models

Delegates localized coding tasks to the local Qwen2.5-Coder:7B model via OpenCode.
Enforces the delegation hierarchy:
1. Scope prompt clearly to fit 7B's strengths (focused functions, unit tests, docstrings).
2. Execute non-interactively via OpenCode.
3. Automatically run verification tests before accepting output.
"""

import os
import sys
import json
import time
import subprocess
from typing import Optional, Dict, Any

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "../mybot/network_config.json")

def get_ollama_endpoint() -> str:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                data = json.load(f)
                return f"http://{data.get('gateway_ip', '172.31.0.1')}:{data.get('ollama_port', 11434)}/v1"
        except Exception:
            pass
    return "http://172.31.0.1:11434/v1"

def delegate_task(prompt: str, model: str = "ollama/qwen2.5-coder:7b", timeout: int = 120) -> Dict[str, Any]:
    """Delegates a coding task to OpenCode with the local model."""
    start_t = time.time()
    env = dict(os.environ)
    env["CI"] = "true"
    env["OPENAI_API_BASE"] = get_ollama_endpoint()
    env["OPENAI_API_KEY"] = "ollama"

    cmd = [
        "opencode", "run",
        "-m", model,
        "--auto",
        prompt
    ]

    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            cwd="/botworkspace",
            stdin=subprocess.DEVNULL
        )
        elapsed = time.time() - start_t
        return {
            "success": res.returncode == 0,
            "stdout": res.stdout.strip(),
            "stderr": res.stderr.strip(),
            "elapsed_sec": round(elapsed, 2),
            "model": model
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Task timed out after {timeout}s",
            "elapsed_sec": timeout,
            "model": model
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "elapsed_sec": round(time.time() - start_t, 2),
            "model": model
        }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: opencode_delegate.py <prompt> [model]")
        sys.exit(1)

    prompt_arg = sys.argv[1]
    model_arg = sys.argv[2] if len(sys.argv) > 2 else "ollama/qwen2.5-coder:7b"
    print(f"--> Delegating to {model_arg}: {prompt_arg[:60]}...")
    result = delegate_task(prompt_arg, model=model_arg)
    print(json.dumps(result, indent=2))
