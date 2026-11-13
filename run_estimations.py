#!/usr/bin/env python3
"""
run_estimations.py — Multi-Model AI Estimation Engine & Comparison Benchmark
Rotates through OpenCode agent models (GLM-5.3-Flash, Nemotron-3.5-Lightning, DeepSeek-V4.1-Flash)
and local Ollama Qwen2.5-Coder:7B to generate project completion time estimates.
"""

import json
import os
import subprocess
import time
import urllib.request
import urllib.error

PROJECTS_DATA = [
    {
        "id": "set_theory_prover",
        "name": "Obelisk Set Theory Prover",
        "open_tickets": 474,
        "closed_tickets": 189,
        "total_tickets": 663,
        "stack": "Poly/ML, Standard ML, Formal Logic, Automated Theorem Prover, ZFC Set Theory",
        "complexity": "Very High (Mathematical rigor, formal proofs, tactic search)",
        "human_role": "Mathematician steering proof strategy and verifying soundness"
    },
    {
        "id": "mybot",
        "name": "MyBot Platform & GitLab Hub",
        "open_tickets": 8,
        "closed_tickets": 267,
        "total_tickets": 275,
        "stack": "Python, HTTP/TCP sockets, Bash, Multi-bot coordination, Linux daemons",
        "complexity": "Medium (Infrastructure, Blue/Green deploy, test suites)",
        "human_role": "Systems architect & devops direction"
    },
    {
        "id": "obeliskproofassistant.github.io",
        "name": "Obelisk Web Portal & REPL",
        "open_tickets": 0,
        "closed_tickets": 185,
        "total_tickets": 185,
        "stack": "HTML5, CSS3, JavaScript, WebAssembly REPL, GitHub Pages",
        "complexity": "Low-Medium (Feature-complete, maintenance & WASM linking)",
        "human_role": "Content curator & UX review"
    },
    {
        "id": "georgydunaev.github.io",
        "name": "Georgy Dunaev Academic Portfolio",
        "open_tickets": 0,
        "closed_tickets": 185,
        "total_tickets": 185,
        "stack": "HTML5, Modern CSS, WebGL, Dual AI/Classic architecture",
        "complexity": "Low (Feature-complete, publications sync)",
        "human_role": "Author & researcher updates"
    },
    {
        "id": "CV",
        "name": "Curriculum Vitae & Career Dossier",
        "open_tickets": 0,
        "closed_tickets": 185,
        "total_tickets": 185,
        "stack": "LaTeX, HTML/CSS, ATS-friendly markdown, 3D vCard",
        "complexity": "Low (Complete, custom tailored variations)",
        "human_role": "Reviewer"
    },
    {
        "id": "antivibecoding",
        "name": "Anti-Vibe Coding Manifesto",
        "open_tickets": 0,
        "closed_tickets": 185,
        "total_tickets": 185,
        "stack": "Static web, JavaScript calculators, Verified engineering laws",
        "complexity": "Low (Complete, community engagement & articles)",
        "human_role": "Author"
    }
]

def query_opencode_model(model_name: str, prompt: str, timeout: int = 45) -> str:
    """Executes a non-interactive opencode query with a specific model."""
    cmd = [
        "opencode", "run",
        "--standalone",
        "-m", model_name,
        "--format", "default",
        prompt
    ]
    try:
        t0 = time.time()
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd="/botworkspace")
        elapsed = time.time() - t0
        output = res.stdout.strip()
        # Clean opencode header line like '> build · model_name'
        lines = [l for l in output.split('\n') if not l.startswith('> build')]
        clean_text = "\n".join(lines).strip()
        print(f"[{model_name}] Query completed in {elapsed:.2f}s (code={res.returncode})")
        return clean_text
    except Exception as e:
        print(f"[{model_name}] Error: {e}")
        return ""

def query_ollama_local(prompt: str, timeout: int = 15) -> str:
    """Attempts a query to the local Ollama instance on the host machine."""
    url = "http://172.31.0.1:11434/api/generate"
    payload = json.dumps({
        "model": "qwen2.5-coder:7b",
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": 150, "temperature": 0.2}
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            elapsed = time.time() - t0
            print(f"[Ollama qwen2.5-coder:7b] Completed in {elapsed:.2f}s")
            return data.get("response", "").strip()
    except Exception as e:
        print(f"[Ollama qwen2.5-coder:7b] Fallback/Timeout: {e}")
        return ""

def build_prompt_for_model() -> str:
    proj_summary = "\n".join([
        f"- {p['id']} ({p['name']}): {p['open_tickets']} open tickets, {p['closed_tickets']} closed. Stack: {p['stack']}. Complexity: {p['complexity']}."
        for p in PROJECTS_DATA
    ])
    return f"""You are an expert AI software estimation engineer.
The developer uses AI assistants (like Claude, GPT-4, OpenCode, Antigravity) extensively for coding, testing, and drafting.
Here is the status of 6 software projects:
{proj_summary}

For each of the 6 projects, provide an estimation of how long the developer should work until completion (or maintenance stability):
1. Give 'AI-Assisted Hours' (pure focused human+AI pair programming hours).
2. Give 'Calendar Days' (assuming 2 to 4 focused hours/day).
3. A 1-sentence strategic rationale.

Format your response as a concise JSON object with keys:
{{
  "projects": {{
    "set_theory_prover": {{"hours": 30, "days": 10, "rationale": "..."}},
    "mybot": {{"hours": 5, "days": 2, "rationale": "..."}},
    "obeliskproofassistant.github.io": {{"hours": 2, "days": 1, "rationale": "..."}},
    "georgydunaev.github.io": {{"hours": 2, "days": 1, "rationale": "..."}},
    "CV": {{"hours": 1, "days": 1, "rationale": "..."}},
    "antivibecoding": {{"hours": 2, "days": 1, "rationale": "..."}}
  }},
  "overall_comment": "..."
}}
Output ONLY the valid JSON block without markdown ticks if possible."""

def main():
    print("=== AI PROJECT ESTIMATION BENCHMARK RUNNER ===")
    prompt = build_prompt_for_model()

    results = {}

    # Model 1: GLM 5.3 Flash Free
    print("\n[1/3] Querying OpenCode model: opencode/glm-5.3-flash-free ...")
    raw_glm = query_opencode_model("opencode/glm-5.3-flash-free", prompt, timeout=45)
    results["glm_5_3_flash"] = raw_glm

    # Model 2: Nemotron 3.5 Lightning Free
    print("\n[2/3] Querying OpenCode model: opencode/nemotron-3.5-lightning-free ...")
    raw_nemo = query_opencode_model("opencode/nemotron-3.5-lightning-free", prompt, timeout=45)
    results["nemotron_3_5_lightning"] = raw_nemo

    # Model 3: DeepSeek V4.1 Flash Free
    print("\n[3/3] Querying OpenCode model: opencode/deepseek-v4.1-flash-free ...")
    raw_ds = query_opencode_model("opencode/deepseek-v4.1-flash-free", prompt, timeout=45)
    results["deepseek_v4_1_flash"] = raw_ds

    # Save raw outputs
    out_dir = "/botworkspace/mybot/local-gitlab/data"
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "raw_ai_estimations.json"), "w") as f:
        json.dump(results, f, indent=2)

    print("\nBenchmark completed. Raw outputs saved to raw_ai_estimations.json.")

if __name__ == "__main__":
    main()
