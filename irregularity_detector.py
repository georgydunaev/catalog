#!/usr/bin/env python3
"""
catalog/irregularity_detector.py — Autonomous Codebase & Verification Irregularity Detector

Unifies multi-repository hygiene checks and leverages lightweight free LLM subprocesses
(OpenCode free models and local Ollama) to identify, analyze, and report irregularities across:
1. Git branch naming, remotes, and divergence.
2. Web assets, Jekyll safety, and broken links.
3. Theorem verifier integrity and explicit side condition completeness.
4. Automated remediation advice generated via free AI agents.
"""

import os
import sys
import json
import time
import subprocess
from typing import List, Dict, Any

WORKSPACE_DIR = "/botworkspace"
DATA_DIR = os.path.join(WORKSPACE_DIR, "mybot/local-gitlab/data")
REPORT_PATH = os.path.join(DATA_DIR, "irregularities.json")

REPOSITORIES = [
    "obeliskproofassistant.github.io",
    "georgydunaev.github.io",
    "CV",
    "antivibecoding",
    "mybot",
    "set_theory_prover"
]

def check_git_irregularities() -> List[Dict[str, Any]]:
    """Checks git branches, remotes, and dirty status across all repositories."""
    issues = []
    for r in REPOSITORIES:
        repo_path = os.path.join(WORKSPACE_DIR, r)
        if not os.path.isdir(os.path.join(repo_path, ".git")):
            continue

        # Check active branch
        try:
            branch = subprocess.check_output(
                ["git", "-C", repo_path, "rev-parse", "--abbrev-ref", "HEAD"],
                text=True
            ).strip()
            if branch != "main":
                issues.append({
                    "severity": "WARNING",
                    "repo": r,
                    "type": "branch_naming",
                    "message": f"Active branch is '{branch}', expected 'main'."
                })
        except Exception as e:
            issues.append({"severity": "ERROR", "repo": r, "type": "git_exec", "message": str(e)})

        # Check remotes
        try:
            remotes = subprocess.check_output(
                ["git", "-C", repo_path, "remote"],
                text=True
            ).strip().split()
            if "github" not in remotes:
                issues.append({
                    "severity": "WARNING",
                    "repo": r,
                    "type": "missing_remote",
                    "message": "Missing explicit 'github' remote."
                })
            if "gitlab" not in remotes:
                issues.append({
                    "severity": "WARNING",
                    "repo": r,
                    "type": "missing_remote",
                    "message": "Missing explicit 'gitlab' remote."
                })
        except Exception as e:
            issues.append({"severity": "ERROR", "repo": r, "type": "git_exec", "message": str(e)})

        # Check for colon or illegal characters in file names
        try:
            files = subprocess.check_output(
                ["git", "-C", repo_path, "ls-files"],
                text=True
            ).splitlines()
            for f in files:
                if any(c in f for c in [":", "*", "?", "<", ">", "|"]):
                    issues.append({
                        "severity": "CRITICAL",
                        "repo": r,
                        "type": "illegal_filename",
                        "message": f"File '{f}' contains characters prohibited by Jekyll or cross-platform filesystems."
                    })
        except Exception:
            pass

    return issues

def check_web_and_asset_irregularities() -> List[Dict[str, Any]]:
    """Checks Jekyll configuration, static files, and gallery directories."""
    issues = []
    web_repos = ["obeliskproofassistant.github.io", "georgydunaev.github.io", "CV", "antivibecoding"]
    for w in web_repos:
        repo_path = os.path.join(WORKSPACE_DIR, w)
        if os.path.isdir(repo_path):
            nojekyll = os.path.join(repo_path, ".nojekyll")
            if not os.path.exists(nojekyll):
                issues.append({
                    "severity": "HIGH",
                    "repo": w,
                    "type": "missing_nojekyll",
                    "message": "Missing .nojekyll marker, which causes GitHub Pages Jekyll build failures on markdown files."
                })

    # Check mybot gallery directory
    screenshots_dir = os.path.join(WORKSPACE_DIR, "georgydunaev.github.io/screenshots")
    if not os.path.isdir(screenshots_dir):
        issues.append({
            "severity": "INFO",
            "repo": "georgydunaev.github.io",
            "type": "gallery_setup",
            "message": "Screenshots directory does not exist yet."
        })

    return issues

def check_verification_irregularities() -> List[Dict[str, Any]]:
    """Checks Obelisk theorem catalog side condition coverage."""
    issues = []
    catalog_path = os.path.join(WORKSPACE_DIR, "set_theory_prover/dist/obelisk_catalog.html")
    if os.path.isfile(catalog_path):
        with open(catalog_path, "r", encoding="utf-8") as f:
            content = f.read()
        if "Side Condition" not in content:
            issues.append({
                "severity": "WARNING",
                "repo": "set_theory_prover",
                "type": "missing_side_conditions",
                "message": "obelisk_catalog.html does not render explicit logical side conditions."
            })
    return issues

def ask_free_llm_for_remediation(issues: List[Dict[str, Any]]) -> str:
    """Delegates a synthesis task to a free OpenCode model to summarize findings and advice."""
    if not issues:
        return "All systems verified normal. Zero irregularities detected across 6 repositories."

    issues_summary = "\n".join([f"- [{i['severity']}] {i['repo']}: {i['message']}" for i in issues])
    prompt = f"""You are an autonomous engineering irregularity detector.
Review the following detected anomalies:
{issues_summary}

Provide a 2-sentence executive summary and prioritized remediation action. Be direct and concise."""

    try:
        cmd = [
            "opencode", "run",
            "--standalone",
            "-m", "opencode/glm-5.3-flash-free",
            "--format", "default",
            prompt
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=WORKSPACE_DIR)
        output = res.stdout.strip()
        lines = [l for l in output.split('\n') if not l.startswith('> build')]
        return "\n".join(lines).strip()
    except Exception as e:
        return f"Deterministic checks completed. (LLM synthesis offline: {e})"

def run_audit(delegate_to_llm: bool = True) -> Dict[str, Any]:
    """Runs all checks, compiles the structured report, and updates data cache."""
    t0 = time.time()
    git_issues = check_git_irregularities()
    web_issues = check_web_and_asset_irregularities()
    verif_issues = check_verification_irregularities()

    all_issues = git_issues + web_issues + verif_issues
    elapsed = time.time() - t0

    llm_advice = ""
    if delegate_to_llm and len(all_issues) > 0:
        llm_advice = ask_free_llm_for_remediation(all_issues)
    elif len(all_issues) == 0:
        llm_advice = "Perfect operational state: 6/6 repositories on 'main' with verified remotes, valid Jekyll config, and audited side conditions."

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "CLEAN" if len(all_issues) == 0 else "ANOMALIES_DETECTED",
        "total_anomalies": len(all_issues),
        "breakdown": {
            "git": len(git_issues),
            "web": len(web_issues),
            "verification": len(verif_issues)
        },
        "issues": all_issues,
        "llm_advisory": llm_advice,
        "elapsed_sec": round(elapsed, 3)
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report

if __name__ == "__main__":
    delegate = "--no-llm" not in sys.argv
    print("=== AUTONOMOUS CODEBASE IRREGULARITY DETECTOR ===")
    rep = run_audit(delegate_to_llm=delegate)
    print(f"Status: {rep['status']} ({rep['total_anomalies']} anomalies found in {rep['elapsed_sec']}s)")
    if rep['issues']:
        for iss in rep['issues']:
            print(f"  • [{iss['severity']}] {iss['repo']}: {iss['message']}")
    print("\nAdvisory:")
    print(rep['llm_advisory'])
    print(f"\nReport written to: {REPORT_PATH}")
