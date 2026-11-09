#!/usr/bin/env python3
"""
catalog_mcp_server.py — Model Context Protocol (MCP) Server for Antigravity & AI Fleet

Exposes the 134-node Epistemic Catalog, Model Dispatcher, Security Guard,
Theorem Prover Verifier, Railway Concurrency Interlocking, and GPU Acceleration Engine
via standard Model Context Protocol (MCP) over Stdio (JSON-RPC 2.0).

Compatible with:
- Antigravity CLI (AGY)
- Claude Code
- DeepCode CLI
- OpenCode CLI
- Custom BotHarness

Available Tools:
1. query_epistemic_memory: Search long-term memory nodes with BM25 FTS5 ranking.
2. read_catalog_node: Retrieve clean token-efficient Markdown for any catalog node.
3. get_model_profile: Retrieve cognitive bounds, attention shield, and tramline for a model.
4. self_configure_model: Calibrate workspace and activate optimal profile for current model.
5. verify_soundness: Run non-interactive check on a theorem in set_theory_prover.
6. scan_security_guard: Scan file for private keys or secrets before committing.
7. list_pending_tasks: List pending host automation tasks and tickets.
8. check_track_signal: Check Railway semaphore block signal (GREEN, AMBER, RED).
9. acquire_track_semaphore: Acquire track semaphore before beginning work.
10. release_track_semaphore: Release track semaphore and clear signal.
11. defer_subtask_to_sidetrack: Safely park a subtask on Sidetrack when track is RED.
12. list_railway_signals: Render visual Railway Block Signaling & Interlocking Board.
13. assess_gpu_hardware: Inspect GPU accelerator, host endpoints, VRAM, and CPU SIMD.
14. calculate_model_vram: Calculate VRAM requirements, KV cache footprint, and layer offload.
15. benchmark_local_llm: Benchmark local LLM throughput (tok/s, TTFT) or hardware projection.

Usage:
  python3 /botworkspace/catalog/catalog_mcp_server.py
"""

import os
import sys
import json
import sqlite3
import subprocess
from typing import Dict, Any, List

WORKSPACE_ROOT = "/botworkspace"
CATALOG_ROOT = os.path.join(WORKSPACE_ROOT, "catalog")
DB_PATH = os.path.join(CATALOG_ROOT, "catalog.db")

# Import SQLite & Tools modules
sys.path.insert(0, CATALOG_ROOT)
sys.path.insert(0, os.path.join(WORKSPACE_ROOT, "tools"))
try:
    import db
except ImportError:
    db = None

try:
    import model_dispatch
except ImportError:
    model_dispatch = None

try:
    import railway_interlocking as ri
except ImportError:
    ri = None

try:
    import gpu_accelerator
except ImportError:
    gpu_accelerator = None


def get_db_conn():
    if os.path.isfile(DB_PATH):
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn
    return None


def handle_query_epistemic_memory(query: str, limit: int = 3) -> str:
    """Search catalog memory nodes using SQLite FTS5."""
    if not os.path.isfile(DB_PATH):
        return f"Error: catalog.db not found at {DB_PATH}."
    try:
        if db and hasattr(db, "query_search_fts"):
            rows = db.query_search_fts(query, limit=limit, db_path=DB_PATH)
        else:
            conn = get_db_conn()
            if not conn:
                return f"Error: could not connect to {DB_PATH}."
            cur = conn.cursor()
            cur.execute(
                """
                SELECT n.relpath, n.title, snippet(nodes_fts, 3, '[MATCH]', '[/MATCH]', '...', 15) as snippet
                FROM nodes_fts f
                JOIN nodes n ON f.relpath = n.relpath
                WHERE nodes_fts MATCH ?
                ORDER BY bm25(nodes_fts)
                LIMIT ?;
                """,
                (query, limit),
            )
            rows = [dict(r) for r in cur.fetchall()]
            conn.close()

        if not rows:
            return f"No catalog memory nodes matched '{query}'."
        out = [f"=== Catalog Memory Results for '{query}' ==="]
        for r in rows:
            snip = r.get("snippet", "").replace("[MATCH]", "**").replace("[/MATCH]", "**")
            out.append(f"• [{r.get('title')}]({r.get('relpath')}): {snip}")
        return "\n".join(out)
    except Exception as e:
        return f"Search error: {e}"


def handle_read_catalog_node(node_path: str) -> str:
    """Retrieve clean, token-efficient Markdown for any catalog node."""
    clean_p = node_path.strip("/").replace("catalog/", "")
    conn = get_db_conn()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT title, clean_markdown, token_count FROM nodes WHERE relpath = ?", (clean_p,))
            r = cur.fetchone()
            if r:
                return f"# {r['title']} ({r['token_count']} tokens)\n\n{r['clean_markdown']}"
        finally:
            conn.close()

    # Fallback to file on disk
    full_p = os.path.join(CATALOG_ROOT, clean_p)
    if os.path.isfile(full_p):
        with open(full_p, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    return f"Error: Node '{node_path}' not found."


def handle_get_model_profile(model_id: str, effort: str = None) -> str:
    """Get cognitive bounds, max read limits, and tramline for a model."""
    if not model_dispatch:
        return "Error: model_dispatch module not loaded."
    prof = model_dispatch.resolve_profile(model_id, effort)
    if not prof:
        return f"Unknown model '{model_id}'. Use 'list' or check model_dispatch.py."
    return model_dispatch.format_profile_markdown(prof)


def handle_self_configure_model(model_id: str, effort: str = None) -> str:
    """Activate optimal profile and configure workspace for model."""
    if not model_dispatch:
        return "Error: model_dispatch module not loaded."
    prof = model_dispatch.resolve_profile(model_id, effort)
    if not prof:
        return f"Unknown model '{model_id}'."
    model_dispatch.activate_profile(prof)
    return f"Successfully activated profile: {prof['name']} (Max read: {prof['max_read_lines']} lines)."


def handle_verify_soundness(theorem_name: str = "") -> str:
    """Run non-interactive check on a theorem in set_theory_prover."""
    cli_path = os.path.join(WORKSPACE_ROOT, "set_theory_prover", "obelisk_cli.py")
    if not os.path.isfile(cli_path):
        return f"Error: obelisk_cli.py not found at {cli_path}."
    cmd = [sys.executable, cli_path, "check"]
    if theorem_name:
        cmd.append(theorem_name)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        status = "PASS" if proc.returncode == 0 else "FAIL"
        return f"=== Obelisk Soundness Check [{status}] ===\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
    except subprocess.TimeoutExpired:
        return "Error: Soundness check timed out after 15s."
    except Exception as e:
        return f"Execution error: {e}"


def handle_scan_security_guard(file_path: str) -> str:
    """Scan file for secrets or credentials before committing."""
    guard_path = os.path.join(WORKSPACE_ROOT, "tools", "security_guard.py")
    if not os.path.isfile(guard_path):
        return "Error: security_guard.py not found."
    try:
        proc = subprocess.run([sys.executable, guard_path, "scan", file_path], capture_output=True, text=True, timeout=10)
        return proc.stdout.strip() or proc.stderr.strip() or "[OK] File clean."
    except Exception as e:
        return f"Scan error: {e}"


def handle_list_pending_tasks() -> str:
    """List pending host automation tasks."""
    runner = os.path.join(WORKSPACE_ROOT, "mybot", "host_tasks", "run-pending-tasks.sh")
    if os.path.isfile(runner):
        try:
            proc = subprocess.run(["bash", runner, "--status"], capture_output=True, text=True, timeout=10)
            return proc.stdout
        except Exception as e:
            return f"Error checking tasks: {e}"
    return "Error: host tasks runner not found."


def handle_check_track_signal(track_zone: str, mode: str = "write") -> str:
    """Check railway semaphore signal for a project track zone."""
    if not ri:
        return "Error: railway_interlocking module not loaded."
    sig, reason, occupants = ri.evaluate_track_signal(track_zone, requested_mode=mode)
    out = [f"=== Railway Signal: Track '{track_zone}' [{sig}] ===", f"Reason: {reason}"]
    if occupants:
        out.append(f"Occupying trains ({len(occupants)}):")
        for occ in occupants:
            out.append(f"  • {occ['session_id']} (Model: {occ['model_name']}, Mode: {occ['mode']})")
    return "\n".join(out)


def handle_acquire_track_semaphore(track_zone: str, mode: str = "write", task_summary: str = "", session_id: str = None) -> str:
    """Acquire track semaphore before beginning work on a project."""
    if not ri:
        return "Error: railway_interlocking module not loaded."
    res = ri.acquire_track(track_zone, mode=mode, task_summary=task_summary, session_id=session_id)
    return json.dumps(res, indent=2)


def handle_release_track_semaphore(session_id: str = None) -> str:
    """Release track semaphore and clear signal."""
    if not ri:
        return "Error: railway_interlocking module not loaded."
    res = ri.release_track(session_id)
    return json.dumps(res, indent=2)


def handle_defer_subtask_to_sidetrack(track_zone: str, title: str, payload: str = "{}", reason: str = "") -> str:
    """Defer subtask to Sidetrack siding when track signal is RED."""
    if not ri:
        return "Error: railway_interlocking module not loaded."
    res = ri.defer_subtask_to_sidetrack(track_zone, title, payload, blocked_by=reason)
    return json.dumps(res, indent=2)


def handle_list_railway_signals() -> str:
    """Render full visual Railway Block Signaling Board."""
    if not ri:
        return "Error: railway_interlocking module not loaded."
    import io, contextlib
    f = io.StringIO()
    with contextlib.redirect_stdout(f):
        ri.print_visual_signal_board()
    return f.getvalue()


def handle_assess_gpu_hardware() -> str:
    """Assess GPU accelerator, host endpoints, VRAM capacity, and CPU SIMD."""
    if not gpu_accelerator:
        return "Error: gpu_accelerator module not available."
    res = gpu_accelerator.assess_gpu_hardware()
    return json.dumps(res, indent=2)


def handle_calculate_model_vram(params: str = "7B", quant: str = "Q4_K_M", ctx_len: int = 8192, available_vram_gb: float = None) -> str:
    """Calculate VRAM requirements, KV cache footprint, and layer offload distribution."""
    if not gpu_accelerator:
        return "Error: gpu_accelerator module not available."
    res = gpu_accelerator.calculate_model_vram(params=params, quant=quant, ctx_len=ctx_len, available_vram_gb=available_vram_gb)
    return json.dumps(res, indent=2)


def handle_benchmark_local_llm(model: str = "qwen2.5-coder:1.5b", prompt: str = "Write a python function to compute factorial.", endpoint: str = None) -> str:
    """Benchmark local LLM throughput (tok/s, TTFT) or retrieve hardware projection."""
    if not gpu_accelerator:
        return "Error: gpu_accelerator module not available."
    res = gpu_accelerator.benchmark_local_llm(model=model, prompt=prompt, endpoint=endpoint)
    return json.dumps(res, indent=2)


# MCP Tool Definitions
TOOLS = [
    {
        "name": "query_epistemic_memory",
        "description": "Search the 134-node SQLite catalog long-term memory with FTS5 BM25 ranking.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query keywords or theorem name"},
                "limit": {"type": "integer", "description": "Maximum number of results to return", "default": 3}
            },
            "required": ["query"]
        }
    },
    {
        "name": "read_catalog_node",
        "description": "Read clean, token-efficient Markdown for any catalog long-term memory node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node_path": {"type": "string", "description": "Relative path of memory node (e.g. 'rules/flash_rules.html')"}
            },
            "required": ["node_path"]
        }
    },
    {
        "name": "get_model_profile",
        "description": "Retrieve cognitive bounds, attention shield (max read lines), and tramline for a model.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "model_id": {"type": "string", "description": "Model identifier (e.g. 'gemini-3.8-flash', 'claude-sonnet', 'local-llm')"},
                "effort": {"type": "string", "enum": ["Low", "Medium", "High"], "description": "Reasoning effort level (for Gemini)"}
            },
            "required": ["model_id"]
        }
    },
    {
        "name": "self_configure_model",
        "description": "Calibrate workspace and activate optimal profile and attention shield for current model.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "model_id": {"type": "string", "description": "Model identifier (e.g. 'gemini-3.8-flash', 'claude-sonnet', 'local-llm')"},
                "effort": {"type": "string", "enum": ["Low", "Medium", "High"], "description": "Reasoning effort level"}
            },
            "required": ["model_id"]
        }
    },
    {
        "name": "verify_soundness",
        "description": "Run non-interactive soundness check on Obelisk proof assistant (set_theory_prover).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "theorem_name": {"type": "string", "description": "Specific theorem name to check (optional)", "default": ""}
            }
        }
    },
    {
        "name": "scan_security_guard",
        "description": "Scan file or directory for exposed credentials, private keys, or tokens (Rule 5).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to file or directory to scan"}
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "list_pending_tasks",
        "description": "List all pending, attempted, and completed host maintenance tasks.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "check_track_signal",
        "description": "Check Railway semaphore block signal (GREEN, AMBER, RED) for a project track.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_zone": {"type": "string", "enum": ["catalog", "set_theory_prover", "mybot", "academic_web", "tools"], "description": "Target track zone"},
                "mode": {"type": "string", "enum": ["read", "write", "reorganize"], "description": "Access mode", "default": "write"}
            },
            "required": ["track_zone"]
        }
    },
    {
        "name": "acquire_track_semaphore",
        "description": "Acquire track semaphore before beginning work on a project zone.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_zone": {"type": "string", "enum": ["catalog", "set_theory_prover", "mybot", "academic_web", "tools"], "description": "Target track zone"},
                "mode": {"type": "string", "enum": ["read", "write", "reorganize"], "description": "Access mode", "default": "write"},
                "task_summary": {"type": "string", "description": "Brief summary of planned work", "default": ""}
            },
            "required": ["track_zone"]
        }
    },
    {
        "name": "release_track_semaphore",
        "description": "Release track semaphore, clear signal, and notify waiting sidetrack tasks.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session ID to release (optional, defaults to current process)", "default": ""}
            }
        }
    },
    {
        "name": "defer_subtask_to_sidetrack",
        "description": "Safely park a subtask on the Sidetrack siding when target track is RED.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_zone": {"type": "string", "enum": ["catalog", "set_theory_prover", "mybot", "academic_web", "tools"], "description": "Blocked track zone"},
                "title": {"type": "string", "description": "Subtask title"},
                "payload": {"type": "string", "description": "JSON payload or task instruction", "default": "{}"},
                "reason": {"type": "string", "description": "Blocking reason", "default": ""}
            },
            "required": ["track_zone", "title"]
        }
    },
    {
        "name": "list_railway_signals",
        "description": "Render visual Railway Block Signaling & Interlocking Board for all tracks.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "assess_gpu_hardware",
        "description": "Inspect GPU hardware accelerator, host Ollama endpoints, total and usable VRAM, and CPU SIMD capabilities.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "calculate_model_vram",
        "description": "Universal VRAM & Layer Offload Planner: calculates model weight VRAM, KV cache size, activation buffers, and exact GPU/CPU layer partitioning for any parameter size and quantization.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "params": {"type": "string", "description": "Model parameter count (e.g. '1.5B', '7B', '8B', '14B', '32B', '70B')", "default": "7B"},
                "quant": {"type": "string", "description": "Quantization type (FP16, Q8_0, Q6_K, Q5_K_M, Q4_K_M, Q4_0, Q2_K)", "default": "Q4_K_M"},
                "ctx_len": {"type": "integer", "description": "Context window length in tokens", "default": 8192},
                "available_vram_gb": {"type": "number", "description": "Optional available GPU VRAM in GB (defaults to detected usable VRAM)"}
            }
        }
    },
    {
        "name": "benchmark_local_llm",
        "description": "Measure token generation throughput (tok/s, TTFT) across local or host LLM endpoints, or retrieve hardware projection under current policy.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "model": {"type": "string", "description": "Model identifier to benchmark", "default": "qwen2.5-coder:1.5b"},
                "prompt": {"type": "string", "description": "Prompt text for benchmark", "default": "Write a python function to compute factorial."},
                "endpoint": {"type": "string", "description": "Optional custom endpoint URL"}
            }
        }
    }
]


def send_response(response: Dict[str, Any]) -> None:
    line = json.dumps(response)
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def run_server() -> None:
    for raw_line in sys.stdin:
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            req = json.loads(raw_line)
        except Exception:
            continue

        msg_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        if method == "initialize":
            send_response({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {
                        "name": "catalog-epistemic-mcp",
                        "version": "1.1.0"
                    },
                    "capabilities": {
                        "tools": {
                            "listChanged": False
                        }
                    }
                }
            })
        elif method == "notifications/initialized":
            # No response needed for notification
            pass
        elif method == "ping":
            send_response({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {}
            })
        elif method == "tools/list":
            send_response({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "tools": TOOLS
                }
            })
        elif method == "tools/call":
            tool_name = params.get("name")
            args = params.get("arguments", {})
            result_text = ""

            if tool_name == "query_epistemic_memory":
                result_text = handle_query_epistemic_memory(args.get("query", ""), args.get("limit", 3))
            elif tool_name == "read_catalog_node":
                result_text = handle_read_catalog_node(args.get("node_path", ""))
            elif tool_name == "get_model_profile":
                result_text = handle_get_model_profile(args.get("model_id", ""), args.get("effort"))
            elif tool_name == "self_configure_model":
                result_text = handle_self_configure_model(args.get("model_id", ""), args.get("effort"))
            elif tool_name == "verify_soundness":
                result_text = handle_verify_soundness(args.get("theorem_name", ""))
            elif tool_name == "scan_security_guard":
                result_text = handle_scan_security_guard(args.get("file_path", ""))
            elif tool_name == "list_pending_tasks":
                result_text = handle_list_pending_tasks()
            elif tool_name == "check_track_signal":
                result_text = handle_check_track_signal(args.get("track_zone", ""), args.get("mode", "write"))
            elif tool_name == "acquire_track_semaphore":
                result_text = handle_acquire_track_semaphore(args.get("track_zone", ""), args.get("mode", "write"), args.get("task_summary", ""), args.get("session_id"))
            elif tool_name == "release_track_semaphore":
                result_text = handle_release_track_semaphore(args.get("session_id"))
            elif tool_name == "defer_subtask_to_sidetrack":
                result_text = handle_defer_subtask_to_sidetrack(args.get("track_zone", ""), args.get("title", ""), args.get("payload", "{}"), args.get("reason", ""))
            elif tool_name == "list_railway_signals":
                result_text = handle_list_railway_signals()
            elif tool_name == "assess_gpu_hardware":
                result_text = handle_assess_gpu_hardware()
            elif tool_name == "calculate_model_vram":
                result_text = handle_calculate_model_vram(
                    params=args.get("params", "7B"),
                    quant=args.get("quant", "Q4_K_M"),
                    ctx_len=args.get("ctx_len", 8192),
                    available_vram_gb=args.get("available_vram_gb")
                )
            elif tool_name == "benchmark_local_llm":
                result_text = handle_benchmark_local_llm(
                    model=args.get("model", "qwen2.5-coder:1.5b"),
                    prompt=args.get("prompt", "Write a python function to compute factorial."),
                    endpoint=args.get("endpoint")
                )
            else:
                result_text = f"Error: Unknown tool '{tool_name}'."

            send_response({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": result_text
                        }
                    ],
                    "isError": False
                }
            })
        else:
            if msg_id is not None:
                send_response({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method '{method}' not found."
                    }
                })


if __name__ == "__main__":
    run_server()
