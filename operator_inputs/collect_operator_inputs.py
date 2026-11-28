#!/usr/bin/env python3
"""
catalog/operator_inputs/collect_operator_inputs.py -- collect what the operator typed, from every
assistant harness on this machine, into one local file.

[WHY] Instructions were given over weeks to several harnesses (Claude Code, opencode, Antigravity
"agy"). To know what was actually asked, as opposed to what agents later wrote about it, we read
the harnesses' own logs. Prompts that one agent generated for another (sub-agent role prompts,
automated "irregularity detector" calls) are filtered out.

Output (git-ignored, local only, because the messages can contain private matters):
  catalog/operator_inputs/raw/operator_inputs.jsonl   one JSON object per message:
      {"harness", "session", "time" (ISO, UTC), "text"}
The committed summary is catalog/operator_inputs/SUMMARY.md, written by hand from this file.

Usage:  python3 catalog/operator_inputs/collect_operator_inputs.py
"""
import datetime
import glob
import json
import os
import re
import sqlite3

HOME = os.path.expanduser("~")
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw")
OUT = os.path.join(OUT_DIR, "operator_inputs.jsonl")

# Texts that agents generate for other agents or that harnesses inject; not operator input.
AUTOMATED = re.compile(
    r"^\s*\"?\s*(You are |===|\[Message\]|<command-|<local-command|<system-reminder>|<task-notification>|"
    r"Caveat: The messages below|This session is being continued|\[Request interrupted)",
    re.S)


def iso(ms):
    return datetime.datetime.fromtimestamp(ms / 1000, datetime.timezone.utc).isoformat(timespec="seconds")


def claude():
    for f in glob.glob(os.path.join(HOME, ".claude/projects/*/*.jsonl")):
        for line in open(f, encoding="utf-8", errors="replace"):
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get("type") != "user" or d.get("isMeta") or d.get("isSidechain"):
                continue
            c = (d.get("message") or {}).get("content")
            if isinstance(c, list):  # tool results are lists; typed text is a string or text parts
                c = "\n".join(p.get("text", "") for p in c if isinstance(p, dict) and p.get("type") == "text")
            if isinstance(c, str) and c.strip():
                yield {"harness": "claude-code", "session": os.path.basename(f)[:-6],
                       "time": d.get("timestamp", ""), "text": c}


def opencode():
    db = os.path.join(HOME, ".local/share/opencode/opencode.db")
    if not os.path.isfile(db):
        return
    con = sqlite3.connect("file:" + db + "?mode=ro", uri=True)
    for sid, data in con.execute("select session_id, data from session_message where type='user' order by time_created"):
        try:
            d = json.loads(data)
        except ValueError:
            continue
        t = d.get("text") or ""
        if t.strip():
            yield {"harness": "opencode", "session": sid,
                   "time": iso(d.get("time", {}).get("created", 0)), "text": t}


def antigravity():
    # step_type 14 is a user turn; 101 are prompts that an agent wrote for a sub-agent.
    for f in glob.glob(os.path.join(HOME, ".gemini/antigravity-cli/conversations/*.db")):
        try:
            con = sqlite3.connect("file:" + f + "?mode=ro", uri=True)
            rows = list(con.execute("select idx, step_payload from steps where step_type = 14 order by idx"))
        except sqlite3.Error:
            continue
        for idx, p in rows:
            b = p if isinstance(p, bytes) else b""
            parts = [t.decode("utf-8", "replace") for t in
                     re.findall(rb"(?:[\x20-\x7e\n\t]|[\xc2-\xf4][\x80-\xbf]+){12,}", b)]
            parts = [s for s in parts if not re.fullmatch(r"[\w$\-\"\s:]*[0-9a-f]{8}-[0-9a-f-]{27,}.*", s)]
            if parts:
                text = max(parts, key=len).strip().strip('"')
                text = re.sub(r"^[^\w\"'(\[]{1,3}", "", text)  # protobuf length bytes before the text
                yield {"harness": "antigravity", "session": os.path.basename(f)[:-3], "time": "", "text": text}


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    seen = set()
    rows = []
    for src in (claude, opencode, antigravity):
        for r in src():
            t = r["text"].strip()
            if AUTOMATED.match(t) or len(t) < 3:
                continue
            key = (r["harness"], t)
            if key in seen:
                continue
            seen.add(key)
            r["text"] = t
            rows.append(r)
    rows.sort(key=lambda r: (r["time"] or "~", r["harness"]))
    with open(OUT, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    by = {}
    for r in rows:
        by[r["harness"]] = by.get(r["harness"], 0) + 1
    print(OUT, len(rows), by)


if __name__ == "__main__":
    main()
