# Project Overview: Hierarchical Long-Term Memory and Directive Catalog (`catalog`)

## 1. Purpose and Scope
`catalog` (`/hostramdisk/catalog` and `/botworkspace/catalog`) is the mandatory Step 0 epistemic knowledge base, rule registry, and model cognitive profile directory for `/botworkspace`. Before modifying any proofs, compilers, or web pages in `set_theory_prover` or `obeliskproofassistant.github.io`, agents must consult `/botworkspace/catalog/`.

## 2. Core Components and Entrypoints
- **User Directives and Mathematical Rules (`rules/` and HTML/DB indices)**:
  - [user_directives.html](file:///hostramdisk/catalog/user_directives.html) — Authoritative registry of operator directives (including Directive #6 on Provenance Headers, Directive #15/#19 on strict `MKTD1`/`MKTD2` nomenclature, Directive #16 on Dual CakeML & Poly/ML compatibility, and Directive #17 on strict `.ML`-only formula generation).
  - [rules/set_theory_rules.html](file:///hostramdisk/catalog/rules/set_theory_rules.html) — Inference rules, binder conventions, and Morse-Kelley / NBG class comprehension invariants.
- **Model Cognitive Profiles (`models/` and Runbooks)**:
  - `models/` — Tailored per-model cognitive entrypoints loaded by `python3 /botworkspace/tools/self_configure.py --auto`.
  - [FLASH_RUNBOOK.md](file:///hostramdisk/catalog/FLASH_RUNBOOK.md), [FREE_MODEL_RULES.md](file:///hostramdisk/catalog/FREE_MODEL_RULES.md), and [LOCAL_LLM_RUNBOOK.md](file:///hostramdisk/catalog/LOCAL_LLM_RUNBOOK.md) — Tier-specific operational tramlines and attention shields.
- **Cognitive Ledger, Database, and MCP Server**:
  - [cognition.py](file:///hostramdisk/catalog/cognition.py) and [cognitive_ledger.py](file:///hostramdisk/catalog/cognitive_ledger.py) — Hierarchical cognition CLI (`python3 /botworkspace/catalog/cognition.py status`).
  - [db.py](file:///hostramdisk/catalog/db.py), [correction_memory.py](file:///hostramdisk/catalog/correction_memory.py), and [catalog_mcp_server.py](file:///hostramdisk/catalog/catalog_mcp_server.py) — SQLite catalog interface (`catalog.db`), mistake-prevention memory, and MCP server (with Rule 6 fallback `catalog_mcp_server.py.prev`).
  - `GlobalTickets` — Symlink to `/botworkspace/GlobalTickets` (Mandatory Priority 0 operator drop-folder inbox).

## 3. Railway Signaling and Host RAMDisk Workflow
- **Grand Central Rule**: Reorganizing `catalog` switches dependent math/proof tracks (`track:set_theory_prover`, `track:academic_web`) to `RED`. Check `bash /botworkspace/tools/railway.sh status` before structural catalog edits.
- **Polite Host RAMDisk Sync**: Pull via `bash /botworkspace/scripts/hostramdisk_workspace.sh pull catalog` and commit via `bash /botworkspace/scripts/hostramdisk_workspace.sh commit catalog "<message>"`.
