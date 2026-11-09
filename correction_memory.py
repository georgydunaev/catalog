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
        "priority": 115,
        "category": "absolute_prohibition_of_emojis",
        "trigger": "emoji|emojis|smiley|icon|unicode_symbol",
        "lesson": "User explicitly instructed: 'Get rid of emojis. Never use emojis anywhere unless asked specifically. Don\\'t touch symbol in the syntax, in terms, etc.'",
        "directive": "Never use emojis anywhere unless asked specifically by the user. Do not use emojis in UI buttons, navigation bars, headers, links, badges, documentation, or assistant responses. Mathematical and syntax symbols in terms and formulas (∀, ∃, ∈, ⊆, ∪, ∩, λ, Π, Σ, ⊢, etc.) are NOT emojis and must never be altered."
    },
    {
        "priority": 105,
        "category": "no_arrows_in_links_and_titles",
        "trigger": "arrow|arrows|title|link|name|confusing|rarr|larr|darr|uarr",
        "lesson": "User explicitly instructed: 'Add as a rule, to never add arrows to the names and titles, and links, it is confusing. Never define entities in links names.'",
        "directive": "Never add arrows (→, ←, ↓, ↑, &rarr;, &larr;, &darr;, &uarr;) to names, titles, buttons, or links; it causes visual confusion and clutter. Keep link names and labels clean, direct, and laconic without embedding long definitions inside link names."
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
            for d in CORE_DIRECTIVES:
                cur = conn.execute("SELECT id FROM user_directives WHERE category = ? AND directive = ?", (d["category"], d["directive"]))
                if not cur.fetchone():
                    conn.execute("""
                    INSERT INTO user_directives (priority, category, trigger_pattern, lesson_learned, directive, last_enforced)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """, (d["priority"], d["category"], d["trigger"], d["lesson"], d["directive"], datetime.now(timezone.utc).isoformat()))
    finally:
        conn.close()

def get_directives(limit: int = 20):
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
