#!/usr/bin/env python3
"""
correction_memory.py — Prioritized Cognitive Memory for User Directives & Grounding Rules

Implements the user requirement:
"Each time you forgot about something and user had to correct you, it is a sign,
that in your long term memory this piece of instruction, should be prioritised somehow."

Stores high-priority user directives, tracks enforcement, and renders both
rich CLI output and clean HTML documentation in the catalog.
"""

import os
import sys
import sqlite3
import html
from datetime import datetime, timezone

CATALOG_ROOT = os.environ.get("CATALOG_ROOT", os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get("CATALOG_DB_PATH", os.path.join(CATALOG_ROOT, "catalog.db"))
OUTPUT_HTML = os.environ.get("USER_DIRECTIVES_HTML", os.path.join(CATALOG_ROOT, "user_directives.html"))

# System Initial Directives (Derived directly from user corrections and critical feedback)
CORE_DIRECTIVES = [
    {
        "priority": 120,
        "category": "authoritative_fact_book_maintenance",
        "trigger": "fact|factbook|contradict|weaken|escalate|rule",
        "lesson": "User explicitly instructed: '1. FACTBOOK is no longer immutable. 2. Do whatever is reasonable to do.' and confirmed unifying the Fact Book directives.",
        "directive": "FACTBOOK.md serves as the authoritative registry of core facts (Facts 1 to 14): agents may update FACTBOOK.md when reasonable to reflect explicit user directives, taxonomy alignments, and system evolution, and MUST stop and ask the user whenever any task, ticket, or test contradicts a recorded fact."
    },
    {
        "priority": 115,
        "category": "absolute_prohibition_of_emojis",
        "trigger": "emoji|emojis|smiley|icon|unicode_symbol",
        "lesson": "User explicitly instructed: 'Get rid of emojis. Never use emojis anywhere unless asked specifically. Don\\'t touch symbol in the syntax, in terms, etc.'",
        "directive": "Never use emojis anywhere unless asked specifically by the user. Do not use emojis in UI buttons, navigation bars, headers, links, badges, documentation, or assistant responses. Mathematical and syntax symbols in terms and formulas (∀, ∃, ∈, ⊆, ∪, ∩, λ, Π, Σ, ⊢, etc.) are NOT emojis and must never be altered."
    },
    {
        "priority": 112,
        "category": "ban_development_expanded_list",
        "trigger": "cubical|tictactoe|hott|alpha|modallogic|insertsort|indigocs|hol|firstordertheory|isabelle_theorems|jech|lambek|mathlogic|mypure|prooftheory|recursiontheorem|proofs|verifiedmathfoundations|yoneda|zfc|goedel",
        "lesson": "User explicitly instructed to ban new development on cubical proofs, tictactoe, HoTT, Alpha, ModalLogic, InsertSort, IndigoCS-webgl-tutorials, HOL, FirstOrderTheory, Isabelle_Theorems, Jech, JechExercises, Lambek, MathLogic, MyPure, ProofTheory, RecursionTheorem, and legacy math archives. Maintenance (git commands) is allowed, but no new features. Active projects (set_theory_prover, foundations, obeliskproofassistant.github.io, georgydunaev.github.io, dune3000, speech, catalog, mybot, scripts/tools) are not banned.",
        "directive": "New development is banned on: some_cubical_proofs, tictactoe, HoTT, Alpha, ModalLogic, InsertSort, IndigoCS-webgl-tutorials, HOL, FirstOrderTheory, Isabelle_Theorems, Jech, JechExercises, Lambek, MathLogic, MyPure, ProofTheory, RecursionTheorem, and legacy archives (Proofs, VerifiedMathFoundations, YONEDA, article_isabelle_in_zfc, draftarticle, goedel, onlyonequantifier, zfc, problem_with_exceptions, LATEX, THESIS, TRANSLATION, TRASH). Maintenance (git commands, syncs, audits) is allowed. If prompted to develop a banned project, AI must ask first: 'Are you really sure you want to develop this one?' unless explicitly unbanned by user."
    },
    {
        "priority": 114,
        "category": "mktd1_mktd2_strict_taxonomy",
        "trigger": "first_order|higher_order|mktd|mktd1|mktd2|framework|theory|system|prover|naming",
        "lesson": "User explicitly instructed: 'It is bad something is called \"first_order\", when I specifically asked to use names MKTD1 and MKTD2: For all three things: logical frameworks, for proof assistant versions, for their theories: like \"MKTD1-theory\", \"MKTD2-prover\", \"MKTD1-system\", and no other wording is allowed. Don\\'t use vaguely these names, we must be precise.'",
        "directive": "Strictly use explicit MKTD1 and MKTD2 taxonomy across all three levels: (1) logical frameworks: MKTD1-framework, MKTD2-framework; (2) proof assistant versions/systems/provers: MKTD1-prover / MKTD1-system, MKTD2-prover / MKTD2-system; (3) theories: MKTD1-theory, MKTD2-theory. No vague or informal terms like 'first_order' are permitted; absolute precision is required."
    },
    {
        "priority": 111,
        "category": "subagent_predispatch_confirmation",
        "trigger": "subagent|dispatch|cv|webpage|confirm|subagents",
        "lesson": "User instructed: 'Develop such important things like CV and web pages, only if they are mentioned explicitly. Actually it is regarding all repositiories: before starting subagents, ask to confirm the work on a list of repositories.'",
        "directive": "Develop sensitive projects like CV and web pages only if explicitly requested. Before starting subagents across all repositories, AI agents MUST ask the user to confirm the work on an explicit list of repositories."
    },
    {
        "priority": 110,
        "category": "two_proof_assistant_variants",
        "trigger": "nbg|mktd|first-order|higher-order|formulas-as-types|newchecker|variant",
        "lesson": "Two distinct proof assistant variants and theories co-exist: MKTD1 (Sequent Calculus in newchecker.ML) and MKTD2 (Curry-Howard Formulas-as-Types in nbg_compiler.ML).",
        "directive": "Both proof assistant variants and theories (MKTD1 and MKTD2) must be actively maintained and developed. Never delete, discard, or replace one approach in favor of the other. Interconnect via program/variant_bridge.ML (User Directive #15 / Fact 14)."
    },
    {
        "priority": 108,
        "category": "frozen_files_progressive_integration",
        "trigger": "frozen|generated|integrate|html_generator|isolate|unlinked",
        "lesson": "User instructed: 'They should be kept frozen, unavailible from the rest of the site, and slowly integrated into the rest.(make tickets about it)'",
        "directive": "Files in obeliskproofassistant.github.io/frozen/ must remain strictly frozen, unlinked and unavailable from the rest of the site navigation, and slowly and progressively integrated into generated/ via SML generators in set_theory_prover, tracked via dedicated GitLab tickets."
    },
    {
        "priority": 106,
        "category": "single_branch_main_legacy_caution",
        "trigger": "branch|main|master|worktree|merge|delete|rush|legacy",
        "lesson": "User instructed: 'First of all, it is almost a rule, that we have one branch: main (don't change legacy things, don't rush to merge or delete).'",
        "directive": "Maintain a single primary branch 'main' across repositories. Never rush to merge or delete legacy branches, worktrees, or repositories prematurely; maintain stability above all."
    },
    {
        "priority": 110,
        "category": "dual_cakeml_polyml_compatibility",
        "trigger": "sml|cakeml|polyml|kernel|compatibility|sml97|pragma",
        "lesson": "Kernel, compiler, and foundations code in set_theory_prover must run on both CakeML v2000+ and Poly/ML v5.7.1+.",
        "directive": "All Standard ML code must adhere strictly to portable SML'97 core compatibility, isolate compiler pragmas, maintain zero non-ASCII string literals, and respect the Off-by-One invariant (SML stores Class_Expre, not Class) (User Directive #16)."
    },
    {
        "priority": 110,
        "category": "strict_ml_only_formula_generation",
        "trigger": "html_generator|generated|frozen|formula|token|clickable|latex",
        "lesson": "LaTeX and Unicode formula representations must never be changed directly by AI processes. Obeliskproofassistant.github.io/generated/ is strictly auto-generated.",
        "directive": "AI processes are strictly forbidden to edit any file in obeliskproofassistant.github.io/generated/. Edit only .ML files in set_theory_prover (html_generator.ML, nbg_html_generator.ML, export_theory_db.ML). Enforce 100% clickable formula tokens and default sort Class (User Directive #17)."
    },
    {
        "priority": 110,
        "category": "immutable_binaries_and_pdfs",
        "trigger": "pdf|binary|binaries|compiled|tar|gz|exe|edit",
        "lesson": "User explicitly instructed: 'Never ever edit already compiled and stored PDFs and binaries, even if I accidentally ask it. It is a rule. Remember it in catalog too.'",
        "directive": "Never ever edit, patch, overwrite, or mutate already compiled and stored PDFs and binaries across any repositories, even if explicitly requested. Keep them strictly read-only and immutable."
    },
    {
        "priority": 110,
        "category": "host_gitlab_accessibility",
        "trigger": "gitlab|dashboard|host|asi\\.host|asi\\.local|asi\\.home|down|unavailable|freeze",
        "lesson": "Operator monitors platform and tickets exclusively from the host browser via https://asi.host and https://asi.local.",
        "directive": "GitLab MUST ALWAYS remain accessible from the host via https://asi.host and https://asi.local. Zero-downtime Blue/Green architecture (router:8929 -> Blue:8931/Green:8932) and host bridge must never be stopped or broken. All changes must be deployed via deploy_blue_green.py."
    },
    {
        "priority": 105,
        "category": "no_arrows_in_links_and_titles",
        "trigger": "arrow|arrows|title|link|name|confusing|rarr|larr|darr|uarr",
        "lesson": "User explicitly instructed: 'Add as a rule, to never add arrows to the names and titles, and links, it is confusing. Never define entities in links names.'",
        "directive": "Never add arrows (→, ←, ↓, ↑, &rarr;, &larr;, &darr;, &uarr;) to names, titles, buttons, or links; it causes visual confusion and clutter. Keep link names and labels clean, direct, and laconic without embedding long definitions inside link names."
    },
    {
        "priority": 105,
        "category": "hostramdisk_workflow",
        "trigger": "hostramdisk|ramdisk|pull|commit|fast|sync",
        "lesson": "Persistent host RAMdisk (/hostramdisk) provides maximum speed and reliable isolation across multi-repo workspace.",
        "directive": "Always work directly in /hostramdisk/<repo>. Run 'hostramdisk_workspace.sh pull <repo>' before editing, and commit via 'hostramdisk_workspace.sh commit <repo> \"<msg>\"' to automatically push to GitLab and sync /botworkspace/<repo>."
    },
    {
        "priority": 100,
        "category": "pushingwatchdog_synchronization",
        "trigger": "beacon|pushingwatchdog|sync|remote|github",
        "lesson": "Manual beacon.sh scripts caused race conditions and git lock contention.",
        "directive": "Never create or run beacon.sh scripts. Repository synchronization from Local GitLab to GitHub is handled autonomously by /botworkspace/scripts/pushingwatchdog.sh."
    },
    {
        "priority": 100,
        "category": "railway_block_signaling",
        "trigger": "railway|block|signal|concurrency|track|train|session",
        "lesson": "Multiple concurrent sessions across projects risk colliding on shared tracks.",
        "directive": "Check signal board via 'bash /botworkspace/tools/railway.sh status'. When encountering a RED signal, shunt subtasks to the siding ('railway.sh defer') or switch to an unblocked track."
    },
    {
        "priority": 100,
        "category": "ban_local_gpu_llm",
        "trigger": "ollama|local_llm|qwen|gpu|ban|serve",
        "lesson": "Host GPU VRAM and thermal constraints require temporary prohibition of local LLM daemons.",
        "directive": "Local GPU Ollama is strictly banned (ban_local_llm: true in network_config.json). Do not launch ollama serve or dispatch ollama/* jobs until lifted."
    },
    {
        "priority": 100,
        "category": "container_network",
        "trigger": "ip|address|host|port|network|dhs|dns|domain",
        "lesson": "Host/container share network; user accesses from host. Raw IPs shift across Docker reboots.",
        "directive": "Never hardcode IPs in HTML. Store in mybot/network_config.json. Use friendly hostnames (mybot.local)."
    },
    {
        "priority": 100,
        "category": "deployment_availability",
        "trigger": "dashboard|server|down|offline|crash|deploy|restart",
        "lesson": "In-place restarts caused frequent dashboard downtime for the user.",
        "directive": "Zero-Downtime Blue/Green: Run Blue (:8931) and Green (:8932) behind router (:8929). Test before hot-swapping."
    },
    {
        "priority": 100,
        "category": "code_preservation",
        "trigger": "refactor|clean|remove|delete|code|prover|sml",
        "lesson": "Historical code blocks in SML contain crucial algorithmic foundations.",
        "directive": "Zero git branches. Never delete the 26 historical commented blocks. Preserve Morse-Kelley / NBG."
    },
    {
        "priority": 100,
        "category": "ui_ip_concealment",
        "trigger": "ip|bare|hide|conceal|mouseclick|click",
        "lesson": "User instructed: 'Don\\'t show IP on a dashboard. Hide or conceal until mouseclick.'",
        "directive": "Never display bare IPs on UI. Default to friendly names (mybot.local). Conceal raw IPs until clicked."
    },
    {
        "priority": 100,
        "category": "portable_paths",
        "trigger": "symlink|link|absolute|path|errno|security_guard",
        "lesson": "Absolute container symlinks (/botworkspace/...) break on host where path is /home/user/...",
        "directive": "Never use absolute container symlinks in repos. Use relative paths or bash wrapper scripts."
    },
    {
        "priority": 95,
        "category": "ui_ux",
        "trigger": "question|choice|option|cli|button|click",
        "lesson": "User prefers clicking buttons or links rather than copying CLI strings.",
        "directive": "Always provide 1-click selectable buttons/links. Never make the user copy/paste text answers."
    },
    {
        "priority": 95,
        "category": "hardware_thermals",
        "trigger": "heat|thermal|temperature|cpu|gpu|ollama|worker|fan",
        "lesson": "ASUS TUF laptop has thermal limits; unconstrained LLM loops overheat hardware.",
        "directive": "Throttle tasks: poll /sys/class/thermal, cap workers <=4, run at nice -n 19, pause if >75°C."
    },
    {
        "priority": 95,
        "category": "model_delegation",
        "trigger": "opencode|delegate|local|qwen|model|abilities",
        "lesson": "User instructed: 'Delegate more. Delegate appropriately to abilities of chosen model.'",
        "directive": "Delegate scoped tasks (tests, helpers, docstrings) to OpenCode (qwen2.5-coder:7b). Verify before accepting."
    },
    {
        "priority": 90,
        "category": "productivity_tools",
        "trigger": "time|timestamp|terminal|english|grammar|tutor",
        "lesson": "User requested terminal timestamps and background English error analysis.",
        "directive": "Maintain cyan [HH:MM:SS] timestamps in prompt/history, and keep ENGLISH_NOTES.md updated."
    },
    {
        "priority": 100,
        "category": "github_pages_nojekyll",
        "trigger": "github-pages|jekyll|relative-links|invalid scheme|URI|nojekyll",
        "lesson": "GitHub Pages runs Jekyll by default, throwing URI errors on non-standard filenames or markdown.",
        "directive": "Always create a .nojekyll file and _config.yml excluding non-site docs in static GitHub Pages repos."
    },
    {
        "priority": 100,
        "category": "safe_filename_characters",
        "trigger": "colon|asterisk|angle|pipe|filename|ntfs|windows|checkout",
        "lesson": "Colons (:), asterisks (*), and angle brackets (<>) in filenames break Jekyll and Windows checkouts.",
        "directive": "Never use ':', '*', '<', '>', or '|' in filenames. Use hyphens or underscores for cross-platform safety."
    },
    {
        "priority": 95,
        "category": "git_http_chunked_streaming",
        "trigger": "git-receive-pack|chunked|broken pipe|curl 55|packfile|push",
        "lesson": "Git pushes exceeding 1MB switch to Transfer-Encoding: chunked, breaking proxies expecting Content-Length.",
        "directive": "Always stream-decode chunked HTTP bodies in Git reverse proxies and backends before forwarding."
    }
]

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    return conn

def init_directives_table(conn: sqlite3.Connection) -> None:
    with conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS user_directives (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            priority INTEGER NOT NULL DEFAULT 100,
            category TEXT NOT NULL,
            trigger_pattern TEXT NOT NULL,
            lesson_learned TEXT NOT NULL,
            directive TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            times_enforced INTEGER DEFAULT 0,
            last_enforced TIMESTAMP
        );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_directives_prio ON user_directives(priority DESC);")

def seed_core_directives() -> None:
    conn = get_conn()
    try:
        init_directives_table(conn)
        with conn:
            # Clean up known obsolete duplicate entries
            conn.execute("DELETE FROM user_directives WHERE category = 'hostramdisk_workflow' AND directive LIKE '%ramdisk_workspace.sh%'")
            conn.execute("DELETE FROM user_directives WHERE category = 'immutable_fact_book_escalation'")
            for d in CORE_DIRECTIVES:
                cur = conn.execute("SELECT id FROM user_directives WHERE category = ?", (d["category"],))
                row = cur.fetchone()
                if row:
                    conn.execute("""
                    UPDATE user_directives
                    SET priority = ?, trigger_pattern = ?, lesson_learned = ?, directive = ?, last_enforced = ?
                    WHERE id = ?
                    """, (d["priority"], d["trigger"], d["lesson"], d["directive"], datetime.now(timezone.utc).isoformat(), row["id"]))
                else:
                    conn.execute("""
                    INSERT INTO user_directives (priority, category, trigger_pattern, lesson_learned, directive, last_enforced)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """, (d["priority"], d["category"], d["trigger"], d["lesson"], d["directive"], datetime.now(timezone.utc).isoformat()))
    finally:
        conn.close()

def get_directives(limit: int = 50):
    conn = get_conn()
    try:
        init_directives_table(conn)
        cur = conn.execute("SELECT * FROM user_directives ORDER BY priority DESC, id ASC LIMIT ?", (limit,))
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

def render_directives_html() -> None:
    directives = get_directives()
    rows = []
    for d in directives:
        p_col = "#dc2626" if d["priority"] >= 100 else "#d97706"
        c_name = html.escape(d['category'].replace('_', ' ').upper())
        les = html.escape(d['lesson_learned'])
        dir_t = html.escape(d['directive'])
        rows.append(f"<tr><td><b>{c_name}</b> <span style='color:{p_col}'>({d['priority']})</span><br/><small style='color:#fbbf24'>[LESSON] {les}</small><br/><span style='color:#34d399'>[DIRECTIVE] {dir_t}</span></td></tr>")

    doc_html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"/><title>Prioritized Directives</title>
<style>body{{font:13px sans-serif;background:#1f1e24;color:#ececef;padding:10px;max-width:800px;margin:auto}}a{{color:#60a5fa}}table{{width:100%;border-collapse:collapse}}td{{padding:6px;border-bottom:1px solid #2b2a33}}</style></head>
<body><a href="index.html">Catalog</a> | <a href="questions_for_user.html">Decisions</a>
<h3>Prioritized Cognitive Directives</h3><table>{''.join(rows)}</table></body></html>"""

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(doc_html)
    print(f"[DIRECTIVES] Rendered {len(directives)} prioritized directives to {OUTPUT_HTML}")

def print_cli_summary() -> None:
    directives = get_directives()
    print("================================================================================")
    print(" TOP-PRIORITY COGNITIVE DIRECTIVES & USER CORRECTIONS")
    print("================================================================================")
    for d in directives:
        print(f"[{d['priority']}/100] [{d['category'].upper()}]")
        print(f"  Lesson : {d['lesson_learned']}")
        print(f"  Rule   : {d['directive']}")
        print("--------------------------------------------------------------------------------")

def main():
    seed_core_directives()
    render_directives_html()
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        print_cli_summary()

if __name__ == "__main__":
    main()
