#!/usr/bin/env python3
"""
worker_memory.py — Dual-Partitioned Epistemic Scratchpad for Free & Local Subagents

Solves the Conscience Preservation & Hierarchical Memory Dilemma:
1. READ-ONLY ACCESS to Canonical Catalog (catalog.db):
   Workers can query verified mathematical definitions, axioms, and user directives
   without being overwhelmed by full documentation dumps or having write access.
2. ISOLATED WORKER SCRATCHPAD (worker_memory.db):
   Workers record intermediate lemmas, hypothesis trails, test runs, and counterexamples
   in an isolated scratch database. This prevents hallucinated assumptions from polluting
   the parent agent's canonical consciousness.
3. TOKEN-ECONOMICAL COMPACT RESULTS:
   All queries return compact snippets (under 250 tokens) optimized for free model context limits.

Usage (by autonomous workers or CLI):
  python3 /botworkspace/catalog/worker_memory.py query "Morse-Kelley"
  python3 /botworkspace/catalog/worker_memory.py query "tagged pair"
  python3 /botworkspace/catalog/worker_memory.py note --ticket TKT-101 --model "qwen2.5-coder:7b" --lemma "Axiom 3.12" --summary "Tried impredicative instantiation"
  python3 /botworkspace/catalog/worker_memory.py history --ticket TKT-101
"""

import os
import sys
import argparse
import sqlite3
import json
import time
from typing import List, Dict, Optional

WORKSPACE_ROOT = "/botworkspace"
CATALOG_DIR = os.path.join(WORKSPACE_ROOT, "catalog")
CANONICAL_DB_PATH = os.path.join(CATALOG_DIR, "catalog.db")
WORKER_DB_PATH = os.path.join(WORKSPACE_ROOT, "devsessions", "worker_memory.db")


def get_canonical_conn() -> Optional[sqlite3.Connection]:
    if not os.path.exists(CANONICAL_DB_PATH):
        return None
    try:
        conn = sqlite3.connect(f"file:{CANONICAL_DB_PATH}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception:
        return None


def get_worker_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(WORKER_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(WORKER_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    with conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS worker_scratchpad (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id TEXT NOT NULL,
            model_name TEXT NOT NULL,
            lemma_name TEXT,
            summary TEXT NOT NULL,
            status TEXT DEFAULT 'IN_PROGRESS',
            test_output TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_scratch_ticket ON worker_scratchpad(ticket_id);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_scratch_model ON worker_scratchpad(model_name);")
    return conn


def query_canonical_catalog(term: str, limit: int = 3) -> List[Dict]:
    """Queries canonical FTS5 nodes and user directives for relevant ground truth."""
    results = []
    conn = get_canonical_conn()
    if not conn:
        return results

    try:
        # 1. Search user directives first (highest priority rules)
        cur = conn.cursor()
        cur.execute("""
            SELECT category, directive, lesson_learned 
            FROM user_directives 
            WHERE trigger_pattern LIKE ? OR directive LIKE ? OR category LIKE ?
            ORDER BY priority DESC LIMIT ?
        """, (f"%{term}%", f"%{term}%", f"%{term}%", limit))
        for row in cur.fetchall():
            results.append({
                "type": "USER_DIRECTIVE",
                "category": row["category"],
                "content": f"Directive: {row['directive']} (Rule: {row['lesson_learned']})"
            })

        # 2. Search canonical nodes FTS5
        clean_query = "".join(c for c in term if c.isalnum() or c.isspace()).strip()
        if clean_query:
            cur.execute("""
                SELECT n.title, n.relpath, snippet(nodes_fts, 3, '[', ']', '...', 16) as snip
                FROM nodes_fts f
                JOIN nodes n ON f.relpath = n.relpath
                WHERE nodes_fts MATCH ?
                LIMIT ?
            """, (clean_query, limit))
            for row in cur.fetchall():
                results.append({
                    "type": "CANONICAL_NODE",
                    "title": row["title"],
                    "path": row["relpath"],
                    "content": row["snip"].replace("\n", " ").strip()
                })
    except Exception as e:
        results.append({"type": "ERROR", "content": f"Catalog query failed: {e}"})
    finally:
        conn.close()

    return results


def record_worker_note(ticket_id: str, model_name: str, lemma_name: str, summary: str, status: str = "IN_PROGRESS", test_output: str = "") -> int:
    conn = get_worker_conn()
    with conn:
        cur = conn.execute("""
            INSERT INTO worker_scratchpad (ticket_id, model_name, lemma_name, summary, status, test_output)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (ticket_id, model_name, lemma_name, summary, status, test_output))
        note_id = cur.lastrowid
    conn.close()
    return note_id


def get_ticket_history(ticket_id: str, limit: int = 5) -> List[Dict]:
    conn = get_worker_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, model_name, lemma_name, summary, status, created_at
        FROM worker_scratchpad
        WHERE ticket_id = ?
        ORDER BY id DESC LIMIT ?
    """, (ticket_id, limit))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def main():
    parser = argparse.ArgumentParser(description="Worker Epistemic Memory & Knowledge Query Interface")
    subparsers = parser.add_subparsers(dest="action")

    # query
    p_query = subparsers.add_parser("query", help="Query canonical catalog (read-only) for definitions and axioms")
    p_query.add_argument("term", type=str, help="Search term (e.g. 'Morse-Kelley', 'tagged pair', 'comprehension')")
    p_query.add_argument("--limit", type=int, default=3, help="Max results")

    # note
    p_note = subparsers.add_parser("note", help="Record intermediate lemma / hypothesis in isolated worker scratchpad")
    p_note.add_argument("--ticket", required=True, help="Ticket ID (e.g. TKT-101 or 016)")
    p_note.add_argument("--model", default="worker-model", help="Executing model name")
    p_note.add_argument("--lemma", default="", help="Lemma or step name")
    p_note.add_argument("--summary", required=True, help="Short summary of reasoning, proof attempt, or test failure")
    p_note.add_argument("--status", choices=["IN_PROGRESS", "PROVED", "DISPROVED", "STUCK"], default="IN_PROGRESS")
    p_note.add_argument("--test-out", default="", help="Relevant compiler stdout/stderr if any")

    # history
    p_hist = subparsers.add_parser("history", help="Retrieve recent worker notes for a ticket")
    p_hist.add_argument("--ticket", required=True, help="Ticket ID")

    args = parser.parse_args()

    if args.action == "query":
        hits = query_canonical_catalog(args.term, args.limit)
        print(f"=== CANONICAL CATALOG KNOWLEDGE (Read-Only Ground Truth) for '{args.term}' ===")
        if not hits:
            # Fallback to checking FREE_MODEL_RULES.md if DB has no match
            rules_path = os.path.join(CATALOG_DIR, "FREE_MODEL_RULES.md")
            if os.path.exists(rules_path):
                print(f"[INFO] Consult foundational rules in {rules_path}")
            else:
                print("No matching verified definitions found.")
            return

        for idx, h in enumerate(hits, 1):
            if h["type"] == "USER_DIRECTIVE":
                print(f"[{idx}] [DIRECTIVE ({h.get('category','GENERAL')})] {h['content']}")
            elif h["type"] == "CANONICAL_NODE":
                print(f"[{idx}] [NODE: {h.get('title','Node')}] ({h.get('path','')})\n    {h['content']}")
            else:
                print(f"[{idx}] {h['content']}")

    elif args.action == "note":
        nid = record_worker_note(args.ticket, args.model, args.lemma, args.summary, args.status, args.test_out)
        print(f"[OK] Worker scratchpad note recorded (ID: {nid}, Ticket: {args.ticket}, Status: {args.status})")

    elif args.action == "history":
        rows = get_ticket_history(args.ticket)
        print(f"=== WORKER SCRATCHPAD TRAIL for Ticket: {args.ticket} ===")
        if not rows:
            print("No previous worker scratchpad entries for this ticket.")
            return
        for r in rows:
            print(f"- [{r['created_at']}] Model: {r['model_name']} | Status: {r['status']}")
            if r['lemma_name']:
                print(f"  Lemma: {r['lemma_name']}")
            print(f"  Summary: {r['summary']}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
