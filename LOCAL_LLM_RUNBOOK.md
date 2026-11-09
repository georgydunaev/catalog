# OPERATIONAL RUNBOOK FOR LOCAL / SMALLER CODING LLMs
### Target Models: Qwen 2.5 Coder 7B / 14B, DeepSeek Coder V2 Lite, Llama 3.1 8B
### Hardware Context: Asus TUF Gaming A17 (16 GB RAM, 6 GB VRAM)

---

## 1. Golden Rules for Local Models (Context Defense)

Smaller models (7B–14B) suffer from severe attention degradation beyond 4,000–8,000 tokens. To maintain precision:

1. **NEVER Read Full Source Code Files (> 100 lines):**
   Dumping `newchecker.ML` (335KB) or `gateway.py` (68KB) into your context will cause immediate amnesia or context exhaustion.
2. **ALWAYS Use the Cognitive Reader:**
   Do NOT read raw HTML files. Run:
   ```bash
   python3 /botworkspace/catalog/cognition.py read <node_path>
   ```
   *(Example: `python3 /botworkspace/catalog/cognition.py read repos/set_theory_prover/index.html`)*
   This automatically strips HTML into token-efficient Markdown (~400 tokens).
3. **NEVER Run Interactive Poly/ML:**
   Raw `poly` without null input will hang your terminal forever. Always use:
   ```bash
   python3 /botworkspace/set_theory_prover/obelisk_cli.py check <theorem_name>
   # or
   python3 /botworkspace/set_theory_prover/obelisk_cli.py compile <file.nbg> --stage nbg
   ```
4. **NEVER Delete Commented-Out Code:**
   In `set_theory_prover`, large commented chunks in `.ML` files are working implementations temporarily commented out for fast tests. Never delete them.

---

## 2. Standard 4-Step Task Tramline

Whenever you awaken with a new task, follow this exact deterministic sequence:

### Step 1: Check System & Memory Telemetry
```bash
python3 /botworkspace/catalog/cognition.py status
```

### Step 2: Search the Memory Tree
```bash
python3 /botworkspace/catalog/cognition.py search "<keyword>"
```

### Step 3: Read Only the Relevant Memory Node
```bash
python3 /botworkspace/catalog/cognition.py read <matched_node.html>
```

### Step 4: Execute & Verify
Run non-interactive tests. If an error occurs, run the automated diagnostic:
```bash
python3 /botworkspace/catalog/cognition.py diagnose "<error message>"
```

---

## 3. Failure Protocol

If you encounter an irreconcilable bug, type clash, or contradictory requirement:
1. Log a ticket in Local GitLab:
   ```bash
   python3 /botworkspace/mybot/scripts/manage_tickets.py create "<Title>" "<Clear description of failure>"
   ```
2. Log the failure in the cognitive ledger:
   ```bash
   python3 /botworkspace/catalog/cognition.py falsify "<Failure details>"
   ```
3. **STOP AND ASK THE USER (Layer 0).** Do not invent axioms or fabricate fake proofs.
