# Project Development Context (`catalog`)

> **Tier 0 Global Ruleset**: Read `/botworkspace/AGENTS.md` and `/botworkspace/FACTBOOK.md` first. Do not duplicate global rules here.

## Repository Scope & Module Boundaries
1. **Hierarchical Cognition & Tree Navigation (`cognition.py`, `cognitive_ledger.py`, `navigate.py`)**:
   - Symlinked entrypoints to `/botworkspace/.agents/skills/hierarchical-cognition/scripts/` managing multi-tier abstraction layers, epistemic verification (`Hypotheses`, `Verified Facts`, `Falsifications`), and HTML memory node traversal.
2. **Model Dispatch & Cognitive Profiles (`model_dispatch.py`, `models/`, `schemas/model_profile.schema.json`, `llm_zoo.json`)**:
   - Implements model profile resolution (`python3 /botworkspace/tools/self_configure.py --auto`), attention shield calibration (`max_read_lines`), reasoning effort configuration, and per-model HTML entrypoints in `models/`. Maintains `model_dispatch.py.prev` as a last-known-good fallback.
3. **Correction Memory & Epistemic Database (`correction_memory.py`, `db.py`, `catalog_mcp_server.py`, `catalog.db`)**:
   - `db.py`: SQLite + FTS5 storage engine backing `catalog.db`.
   - `correction_memory.py`: Mistake-prevention registry and file-scoped hazard lookup (`list`, `search`, `check-file`, `add`, `verify`, `export-html`).
   - `catalog_mcp_server.py`: Model Context Protocol server exposing catalog search and directive retrieval (with fallback `catalog_mcp_server.py.prev`).
4. **Directive & Rule Registries (`user_directives.html`, `rules/`, `schemas/notions_ontology.json`, `repos/`, `branches/`)**:
   - Structured HTML and JSON registries for operator directives (`user_directives.html`), formal set theory and binder rules (`rules/set_theory_rules.html`), and per-repository catalog pages.

## Verification & Test Commands
```bash
python3 /hostramdisk/catalog/cognition.py status
python3 /hostramdisk/catalog/correction_memory.py list
python3 -m unittest discover -s /hostramdisk/catalog/tests
```
