# Ticket 7434 — Catalog: Add FTS search performance benchmark script in catalog/benchmark_search.py
**Importance:** 4/10
**State:** opened
**Labels:** catalog, automated, fleet-ticket
**Assigned:** opencode/deepseek-v4.1-flash-free

## Description
Create catalog/benchmark_search.py to measure query latency and memory efficiency of SQLite FTS5 searches in catalog.db.

## Acceptance Criteria
1. Changes are tested and verified without introducing regressions.
2. Code follows repository invariants (Rule 5 zero committed secrets, Rule 6 atomic changes).
3. Ground-truth test commands pass.
