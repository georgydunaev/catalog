# FLASH RUNBOOK: GEMINI 3.8 FLASH DIRECT DISPATCH (V1.0)
> **Purpose:** Zero-decay direct execution matrix for Gemini 3.8 Flash. Replaces 4-tier HTML traversal with single-lookup paths.

---

### 1. THE 5 GOLDEN FLASH INVARIANTS (NON-NEGOTIABLE)
1. **PRESERVE HISTORICAL CODE:** NEVER delete or alter the 26 commented-out ML blocks in `newchecker.ML`, `PreChar.ML`, or `checker.ML`.
2. **MK ONTOLOGY ONLY:** Proper classes are first-class ($\neg\text{Set}(X)$). NEVER use Kuratowski pairs $\{\{A\},\{A,B\}\}$ for proper classes; use **Dunaev Tagged Ordered Pairs** with fixed tags 1 and 2, $[A,B]_D = \operatorname{mark}(A,1)\cup\operatorname{mark}(B,2)$ (the inner Kuratowski pair $\langle u,k\rangle_K$ is only used on sets $u$).
3. **STANDARD ML 97 / CAKEML:** Pure SML 97 only. Never emit OCaml (`;;`), Haskell (`class`), or Python syntax in `.ML` files.
4. **NON-INTERACTIVE EXECUTION:** Never run interactive poly. Poly/ML must run with finite timeouts and `stdin=subprocess.DEVNULL` or `--eval`.
5. **EPISTEMIC REALITY & STRICT MKTD1/MKTD2 TAXONOMY:** Always run verification tests on disk before marking done. Use exclusively explicit `MKTD1` (`MKTD1-framework`, `MKTD1-system` / `MKTD1-prover`, `MKTD1-theory`) and `MKTD2` (`MKTD2-framework`, `MKTD2-system` / `MKTD2-prover`, `MKTD2-theory`) nomenclature without informal labels.

---

### 2. DIRECT DISPATCH MATRIX (NO HTML HOPS)
| Domain / Intent | Primary Source File | Non-Interactive Verification Test |
| :--- | :--- | :--- |
| **MKTD2-prover / MKTD2-theory** | `set_theory_prover/program/nbg_compiler.ML` | `python3 -m unittest set_theory_prover/tests/test_nbg_compiler.py` |
| **MKTD1-prover / MKTD1-theory** | `set_theory_prover/program/newchecker/all.ML` | `poly -q --use set_theory_prover/program/newchecker/00_preamble.ML` |
| **Obelisk Full Suite**| `set_theory_prover/obelisk_cli.py` | `python3 set_theory_prover/obelisk_cli.py test` |
| **Dunaev Tagged Pairs**| `set_theory_prover/program/dunaev_pairs.ML` | `python3 set_theory_prover/tests/test_dunaev_pairs.py` |
| **LCF Kernel Rules** | `set_theory_prover/program/lcf.ML` | `python3 set_theory_prover/tests/test_kernel.py` |
| **GitLab Tickets** | `mybot/scripts/manage_tickets.py` | `python3 mybot/scripts/manage_tickets.py list` |
| **Cognitive Ledger** | `.cognitive_ledger.json` | `python3 catalog/cognition.py status` |
| **Memory Audit** | `catalog/catalog.db` | `python3 catalog/cognition.py audit` |

---

### 3. FLASH ATTENTION SHIELD (WORKING CONSTRAINTS)
* **Read Window:** Read at most 150 lines per `read_file` call.
* **Single Active Goal:** Finish one ticket / proof before switching context.
* **Rapid Checkpoint:** Run `python3 catalog/cognition.py flash` after large command outputs to restore core constraints.
* **Escalation Trigger:** If a contradiction reaches workspace root invariants, **STOP AND ASK THE USER (Layer 0)**.
