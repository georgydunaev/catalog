#!/usr/bin/env python3
"""
db.py — High-Performance SQLite & FTS5 Database Engine for Antigravity Catalog

Solves the HTML parsing bottleneck by:
1. Indexing all HTML memory nodes into an indexed SQLite database (catalog.db).
2. Pre-computing and caching clean Markdown representations (zero runtime HTML parsing).
3. Providing full-text search with BM25 ranking via SQLite FTS5.
4. Managing the knowledge graph (nodes, hyperlinks, broken link detection via SQL joins).
5. Incremental sync based on file mtime (only re-parses modified files).
"""

import os
import re
import glob
import sqlite3
import contextlib
from typing import List, Dict, Tuple, Optional, Any, Iterator

CATALOG_ROOT = os.environ.get("CATALOG_ROOT", os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get("CATALOG_DB_PATH", os.path.join(CATALOG_ROOT, "catalog.db"))


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    return conn


@contextlib.contextmanager
def open_db(db_path: str = DB_PATH) -> Iterator[sqlite3.Connection]:
    """Context manager ensuring safe connection acquisition and guaranteed closure."""
    conn = get_connection(db_path)
    try:
        yield conn
    finally:
        conn.close()


def init_db(conn: sqlite3.Connection) -> None:
    with conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS nodes (
            relpath TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            branch TEXT,
            layer INTEGER DEFAULT 1,
            raw_html TEXT NOT NULL,
            clean_markdown TEXT NOT NULL,
            token_count INTEGER NOT NULL,
            line_count INTEGER NOT NULL,
            mtime REAL NOT NULL,
            summary TEXT,
            up_link TEXT
        );

        CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_path TEXT NOT NULL,
            target_path TEXT NOT NULL,
            raw_target TEXT NOT NULL,
            link_text TEXT NOT NULL,
            is_broken INTEGER DEFAULT 0,
            FOREIGN KEY (source_path) REFERENCES nodes(relpath) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_links_source ON links(source_path);
        CREATE INDEX IF NOT EXISTS idx_links_target ON links(target_path);
        CREATE INDEX IF NOT EXISTS idx_links_broken ON links(is_broken);

        CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
            relpath UNINDEXED,
            title,
            branch,
            content,
            tokenize = 'porter unicode61'
        );

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
        CREATE INDEX IF NOT EXISTS idx_directives_prio ON user_directives(priority DESC);
        """)


def html_to_clean_markdown(raw_html: str) -> str:
    """Pre-renders HTML to lean Markdown."""
    clean = re.sub(r'<style>.*?</style>', '', raw_html, flags=re.DOTALL)
    clean = re.sub(r'<script>.*?</script>', '', clean, flags=re.DOTALL)
    clean = re.sub(r'<h1>(.*?)</h1>', r'# \1\n', clean)
    clean = re.sub(r'<h2>(.*?)</h2>', r'## \1\n', clean)
    clean = re.sub(r'<h3>(.*?)</h3>', r'### \1\n', clean)
    clean = re.sub(r'<a\s+(?:[^>]*?\s+)?href=[\"\']([^\"\']+)[\"\'][^>]*>(.*?)</a>', r'[\2](\1)', clean, flags=re.DOTALL)
    clean = re.sub(r'<li>\s*<p>(.*?)</p>\s*</li>', r'* \1\n', clean, flags=re.DOTALL)
    clean = re.sub(r'<li>(.*?)</li>', r'* \1\n', clean)
    clean = re.sub(r'<p>(.*?)</p>', r'\1\n\n', clean, flags=re.DOTALL)
    clean = re.sub(r'<pre><code>(.*?)</code></pre>', r'```\n\1\n```', clean, flags=re.DOTALL)
    clean = re.sub(r'<pre>(.*?)</pre>', r'```\n\1\n```', clean, flags=re.DOTALL)
    clean = re.sub(r'<code>(.*?)</code>', r'`\1`', clean)
    clean = re.sub(r'<strong>(.*?)</strong>', r'**\1**', clean)
    clean = re.sub(r'<em>(.*?)</em>', r'*\1*', clean)
    clean = re.sub(r'<[^>]+>', ' ', clean)
    clean = re.sub(r'&bull;', '•', clean)
    clean = re.sub(r'&rarr;', '→', clean)
    clean = re.sub(r'&uarr;', '↑', clean)
    clean = re.sub(r'&le;', '≤', clean)
    clean = re.sub(r'&ge;', '≥', clean)
    clean = re.sub(r'&isin;', '∈', clean)
    clean = re.sub(r'&notin;', '∉', clean)
    clean = re.sub(r'&cap;', '∩', clean)
    clean = re.sub(r'&cup;', '∪', clean)
    clean = re.sub(r'&amp;', '&', clean)
    clean = re.sub(r'&lt;', '<', clean)
    clean = re.sub(r'&gt;', '>', clean)
    clean = re.sub(r'&quot;', '"', clean)
    clean = re.sub(r'\n{3,}', '\n\n', clean).strip()
    return clean


def parse_node_metadata(relpath: str, full_path: str) -> Dict[str, Any]:
    with open(full_path, "r", encoding="utf-8", errors="ignore") as fp:
        raw_html = fp.read()

    mtime = os.path.getmtime(full_path)
    sz = os.path.getsize(full_path)
    token_count = sz // 4
    line_count = raw_html.count("\n") + 1

    # Extract title
    title_m = re.search(r'<title>([^<]+)</title>', raw_html)
    title = title_m.group(1).strip() if title_m else os.path.basename(relpath)

    # Extract UP link
    up_m = re.search(r'\[\[UP:[^\]]+\]\]\(([^)]+)\)', raw_html)
    up_link = up_m.group(1) if up_m else None

    # Determine branch
    branch = "root"
    if "/" in relpath:
        parts = relpath.split("/")
        branch = parts[1] if parts[0] == "branches" else parts[0]

    # Pre-render clean markdown
    clean_md = html_to_clean_markdown(raw_html)

    # First paragraph or title as summary
    p_m = re.search(r'<p>(.*?)</p>', raw_html, flags=re.DOTALL)
    summary = re.sub(r'<[^>]+>', '', p_m.group(1)).strip() if p_m else title

    return {
        "relpath": relpath,
        "title": title,
        "branch": branch,
        "layer": relpath.count("/"),
        "raw_html": raw_html,
        "clean_markdown": clean_md,
        "token_count": token_count,
        "line_count": line_count,
        "mtime": mtime,
        "summary": summary[:200],
        "up_link": up_link
    }


def extract_links(relpath: str, raw_html: str) -> List[Tuple[str, str, str]]:
    """Returns list of (source_path, target_relpath, link_text)"""
    extracted = []
    # Pattern for <a href="...">text</a>
    for m in re.finditer(r'<a\s+(?:[^>]*?\s+)?href=[\"\']([^\"\']+)[\"\'][^>]*>(.*?)</a>', raw_html, flags=re.DOTALL):
        href = m.group(1)
        text = re.sub(r'<[^>]+>', '', m.group(2)).strip()
        if href.startswith("http://") or href.startswith("https://") or href.startswith("#") or href.startswith("mailto:"):
            continue
        # Resolve target path relative to source directory
        src_dir = os.path.dirname(relpath)
        norm_target = os.path.normpath(os.path.join(src_dir, href))
        extracted.append((relpath, norm_target, href, text))
    return extracted


def sync_db(catalog_root: str = CATALOG_ROOT, db_path: str = DB_PATH) -> Dict[str, int]:
    """Incrementally synchronizes the SQLite database with the filesystem."""
    with open_db(db_path) as conn:
        init_db(conn)

        html_files = glob.glob(f"{catalog_root}/**/*.html", recursive=True)
        stats = {"inserted": 0, "updated": 0, "deleted": 0, "skipped": 0, "total": len(html_files)}

        # Map current files
        fs_nodes = {}
        for f in html_files:
            rel = os.path.relpath(f, catalog_root)
            fs_nodes[rel] = f

        with conn:
            # 1. Detect deleted files
            db_rows = conn.execute("SELECT relpath, mtime FROM nodes").fetchall()
            db_nodes = {row["relpath"]: row["mtime"] for row in db_rows}

            for db_rel in db_nodes:
                if db_rel not in fs_nodes:
                    conn.execute("DELETE FROM nodes WHERE relpath = ?", (db_rel,))
                    conn.execute("DELETE FROM nodes_fts WHERE relpath = ?", (db_rel,))
                    stats["deleted"] += 1

            # 2. Insert or update modified files
            for rel, full_path in fs_nodes.items():
                current_mtime = os.path.getmtime(full_path)
                if rel in db_nodes and abs(db_nodes[rel] - current_mtime) < 0.001:
                    stats["skipped"] += 1
                    continue

                meta = parse_node_metadata(rel, full_path)
                is_update = rel in db_nodes

                conn.execute("""
                INSERT INTO nodes (relpath, title, branch, layer, raw_html, clean_markdown, token_count, line_count, mtime, summary, up_link)
                VALUES (:relpath, :title, :branch, :layer, :raw_html, :clean_markdown, :token_count, :line_count, :mtime, :summary, :up_link)
                ON CONFLICT(relpath) DO UPDATE SET
                    title = excluded.title,
                    branch = excluded.branch,
                    layer = excluded.layer,
                    raw_html = excluded.raw_html,
                    clean_markdown = excluded.clean_markdown,
                    token_count = excluded.token_count,
                    line_count = excluded.line_count,
                    mtime = excluded.mtime,
                    summary = excluded.summary,
                    up_link = excluded.up_link
                """, meta)

                # Update FTS
                conn.execute("DELETE FROM nodes_fts WHERE relpath = ?", (rel,))
                conn.execute("""
                INSERT INTO nodes_fts (relpath, title, branch, content)
                VALUES (?, ?, ?, ?)
                """, (rel, meta["title"], meta["branch"], meta["clean_markdown"]))

                # Update links
                conn.execute("DELETE FROM links WHERE source_path = ?", (rel,))
                raw_links = extract_links(rel, meta["raw_html"])
                for src, norm_tgt, raw_tgt, txt in raw_links:
                    conn.execute("""
                    INSERT INTO links (source_path, target_path, raw_target, link_text)
                    VALUES (?, ?, ?, ?)
                    """, (src, norm_tgt, raw_tgt, txt))

                if is_update:
                    stats["updated"] += 1
                else:
                    stats["inserted"] += 1

            # 3. Fast SQL link integrity verification
            conn.execute("""
            UPDATE links SET is_broken = CASE
                WHEN target_path IN (SELECT relpath FROM nodes) THEN 0
                ELSE 1
            END;
            """)

    return stats


def query_get_node(relpath: str, db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    """Instant O(1) fetch of pre-rendered Markdown and metadata without parsing HTML."""
    with open_db(db_path) as conn:
        row = conn.execute("SELECT * FROM nodes WHERE relpath = ?", (relpath,)).fetchone()
        if row:
            return dict(row)
        return None


def query_search_fts(query: str, limit: int = 10, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """Full-text search using SQLite FTS5 BM25 ranking."""
    clean_terms = re.findall(r'\w+', query)
    if not clean_terms:
        return []

    fts_expr = " AND ".join(f'"{t}"*' for t in clean_terms)
    with open_db(db_path) as conn:
        try:
            sql = """
            SELECT n.relpath, n.title, n.branch, n.token_count,
                   snippet(nodes_fts, 3, '[MATCH]', '[/MATCH]', '...', 15) as snippet,
                   bm25(nodes_fts) as rank
            FROM nodes_fts f
            JOIN nodes n ON n.relpath = f.relpath
            WHERE nodes_fts MATCH ?
            ORDER BY rank
            LIMIT ?;
            """
            rows = conn.execute(sql, (fts_expr, limit)).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            # Fallback to simple LIKE if query syntax fails
            sql_fallback = """
            SELECT relpath, title, branch, token_count, summary as snippet, 0 as rank
            FROM nodes
            WHERE title LIKE ? OR clean_markdown LIKE ?
            LIMIT ?;
            """
            pat = f"%{query}%"
            rows = conn.execute(sql_fallback, (pat, pat, limit)).fetchall()
            return [dict(r) for r in rows]


def query_audit(db_path: str = DB_PATH) -> Dict[str, Any]:
    """Instant SQL-based database audit."""
    with open_db(db_path) as conn:
        total_nodes = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        total_links = conn.execute("SELECT COUNT(*) FROM links").fetchone()[0]
        broken_links = conn.execute("SELECT source_path, target_path, link_text FROM links WHERE is_broken = 1").fetchall()
        bloated_nodes = conn.execute("SELECT relpath, token_count FROM nodes WHERE token_count > 1400").fetchall()
        avg_tokens = conn.execute("SELECT AVG(token_count) FROM nodes").fetchone()[0] or 0
        total_tokens = conn.execute("SELECT SUM(token_count) FROM nodes").fetchone()[0] or 0

        return {
            "total_nodes": total_nodes,
            "total_links": total_links,
            "broken_links": [dict(r) for r in broken_links],
            "bloated_nodes": [dict(r) for r in bloated_nodes],
            "avg_tokens": round(avg_tokens, 1),
            "total_tokens": total_tokens
        }


if __name__ == "__main__":
    import sys
    action = sys.argv[1] if len(sys.argv) > 1 else "sync"

    if action == "sync":
        res = sync_db()
        print(f"[CATALOG DB SYNC]: {res['total']} nodes scanned ({res['inserted']} inserted, {res['updated']} updated, {res['skipped']} unchanged, {res['deleted']} deleted)")
    elif action == "audit":
        audit = query_audit()
        print("=== DATABASE COGNITIVE AUDIT ===")
        print(f"Total Nodes:     {audit['total_nodes']}")
        print(f"Total Links:     {audit['total_links']}")
        print(f"Broken Links:    {len(audit['broken_links'])}")
        print(f"Bloated Nodes:   {len(audit['bloated_nodes'])}")
        print(f"Avg Tokens/Node: {audit['avg_tokens']}")
        print(f"Total Tokens:    {audit['total_tokens']}")
        if audit['broken_links']:
            for bl in audit['broken_links']:
                print(f"  [BROKEN]: {bl['source_path']} -> {bl['target_path']}")
    elif action == "search":
        q = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        results = query_search_fts(q)
        print(f"=== FTS5 SEARCH RESULTS FOR '{q}' ({len(results)} matches) ===")
        for r in results:
            print(f"- {r['relpath']} ({r['title']}) [{r['token_count']} tok]: {r['snippet']}")
    elif action == "read":
        p = sys.argv[2] if len(sys.argv) > 2 else ""
        node = query_get_node(p)
        if node:
            print(node["clean_markdown"])
        else:
            print(f"Node '{p}' not found.")
    else:
        print("Usage: python3 db.py [sync|audit|search <query>|read <relpath>]")
