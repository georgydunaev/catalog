#!/usr/bin/env python3
"""
benchmark_search.py — SQLite FTS5 Search Latency & Memory Efficiency Benchmark (Tickets 7434, 7418)

Measures BM25 query latency (mean, p95, max in ms) and memory footprint across
representative epistemic queries in /botworkspace/catalog/catalog.db.
"""

import os
import sys
import time
import json
import tracemalloc
from typing import Dict, Any, List

CATALOG_ROOT = "/botworkspace/catalog"
if CATALOG_ROOT not in sys.path:
    sys.path.insert(0, CATALOG_ROOT)

import db


BENCHMARK_QUERIES: List[str] = [
    "set_theory_prover",
    "Dunaev tagged ordered pair",
    "Morse-Kelley class comprehension",
    "railway interlocking signal",
    "network_config",
    "botharness provider failover",
    "foundations positive formulas",
    "obelisk proof assistant",
]


def run_benchmark(iterations: int = 10) -> Dict[str, Any]:
    db.sync_db()
    tracemalloc.start()
    latencies_ms: List[float] = []
    total_hits = 0

    for _ in range(iterations):
        for q in BENCHMARK_QUERIES:
            t0 = time.perf_counter()
            res = db.query_search_fts(q, limit=10)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            latencies_ms.append(elapsed_ms)
            total_hits += len(res)

    current_bytes, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    latencies_ms.sort()
    count = len(latencies_ms)
    mean_ms = sum(latencies_ms) / count if count else 0.0
    p95_idx = min(count - 1, int(count * 0.95)) if count else 0
    p95_ms = latencies_ms[p95_idx] if count else 0.0
    max_ms = latencies_ms[-1] if count else 0.0

    return {
        "queries_executed": count,
        "total_hits": total_hits,
        "mean_latency_ms": round(mean_ms, 3),
        "p95_latency_ms": round(p95_ms, 3),
        "max_latency_ms": round(max_ms, 3),
        "peak_memory_kb": round(peak_bytes / 1024.0, 2),
        "current_memory_kb": round(current_bytes / 1024.0, 2),
    }


if __name__ == "__main__":
    summary = run_benchmark()
    print(json.dumps(summary, indent=2))
