#!/usr/bin/env python3
"""
catalog/english_tutor.py — Friendly Background English Language Companion

Analyzes user prompt transcripts and messages for recurring typos, false friends,
preposition patterns, and grammar nuances, compiling concise, encouraging explanations
into /botworkspace/ENGLISH_NOTES.md and /botworkspace/catalog/english_notes.html.
"""

import os
import re
import json
import glob
from typing import List, Dict, Tuple

TRANSCRIPT_PATH = "/home/bot/.gemini/antigravity-cli/brain/3e1b88f5-bb08-487b-95c6-dd91d60aecc2/.system_generated/logs/transcript.jsonl"
OUT_MD = "/botworkspace/docs/ENGLISH_NOTES.md"
OUT_HTML = "/botworkspace/catalog/english_notes.html"

# Pattern rules: (regex_pattern, correction, category, explanation)
RULES: List[Tuple[str, str, str, str]] = [
    (r"\bbrunches\b", "branches", "Spelling",
     "'brunch' is a late breakfast/early lunch. Git/code tree paths are 'branches' (with an 'a')."),
    (r"\bbrunch\b", "branch", "Spelling",
     "'brunch' is breakfast + lunch. A code/tree split is a 'branch'."),
    (r"\bfree tim\b", "free time", "Typo",
     "Missing final 'e' in 'time'."),
    (r"\beverythin\b", "everything", "Typo",
     "Missing final 'g' in 'everything'."),
    (r"\beveryhthing\b", "everything", "Typo",
     "Accidental extra 'h' in 'everything'."),
    (r"\bIf te\b", "If the", "Typo",
     "'te' -> 'the'."),
    (r"\bIt fells\b", "It feels", "Spelling / Verb",
     "'fell' is past tense of fall ('he fell down'). For perception, use 'It feels' (double 'e')."),
    (r"\bexplains to my\b", "explains to me", "Grammar: Pronoun",
     "Use object pronoun 'me' after a preposition ('explains to me'). 'my' is possessive ('my book')."),
    (r"\bmost perspective\b", "most promising / most prospective", "False Friend (Ложные друзья переводчика)",
     "In Russian, 'перспективный' means full of promise. In English, 'perspective' is usually a noun (viewpoint, viewpoint angle). Use 'most promising' or 'most prospective' for a project approach."),
    (r"\bleaded to\b", "led to", "Irregular Verb",
     "Past tense of 'lead' is 'led' (not 'leaded'). Example: 'the path that led to the demo'."),
    (r"\boldfashioned\b", "old-fashioned", "Hyphenation",
     "Compound adjectives are usually hyphenated: 'old-fashioned'."),
    (r"\bseparete\b", "separate", "Spelling",
     "Common spelling trap: 'separate' contains two 'a's (sep-a-rate), not 'e'."),
    (r"\bthemsels\b", "themselves", "Spelling",
     "Reflexive plural pronoun is 'themselves' (them + selves, ending in -ves)."),
    (r"\bdisplyed\b", "displayed", "Typo",
     "Missing 'a': 'displayed' (display + ed)."),
    (r"\badresses\b", "addresses", "Spelling",
     "Common double-letter trap: 'address' has double 'd' and double 's' (ad-dress)."),
    (r"\bdhs\b", "DNS", "Technical Term",
     "Domain Name System is abbreviated 'DNS' (names instead of IP numbers)."),
]


def extract_user_inputs() -> List[str]:
    texts = []
    if os.path.exists(TRANSCRIPT_PATH):
        try:
            with open(TRANSCRIPT_PATH) as f:
                for line in f:
                    try:
                        d = json.loads(line)
                        if d.get("type") == "USER_INPUT":
                            raw = d.get("content", "")
                            # Clean XML tags if present
                            clean = re.sub(r"<[^>]+>", "", raw).strip()
                            if clean and not clean.startswith("user@"):
                                texts.append(clean)
                    except Exception:
                        pass
        except Exception:
            pass
    return texts


def analyze_texts(texts: List[str]) -> List[Dict[str, str]]:
    findings = []
    seen = set()
    for text in texts:
        for pat, corr, cat, expl in RULES:
            match = re.search(pat, text, re.IGNORECASE)
            if match and (pat, corr) not in seen:
                seen.add((pat, corr))
                findings.append({
                    "original": match.group(0),
                    "correction": corr,
                    "category": cat,
                    "explanation": expl,
                    "context": text[:140] + ("..." if len(text) > 140 else "")
                })
    return findings


def generate_reports() -> Dict[str, int]:
    texts = extract_user_inputs()
    findings = analyze_texts(texts)

    # 1. Write Markdown report
    md_content = """# Friendly English Companion & Common Observations

*Generated automatically in background by your cognitive assistant.*
*These notes are completely optional and designed solely to assist your English communication.*

---

## Recent Key Observations & Tips

"""
    for f in findings:
        md_content += f"""### 📌 {f['category']}: `{f['original']}` &rarr; **`{f['correction']}`**
- **Explanation:** {f['explanation']}
- **Found in context:** *"{f['context']}"*

"""

    md_content += """---

## Helpful Summary Table

| What Was Typed | Recommended Form | Note / Rule |
| :--- | :--- | :--- |
| `brunches` | **`branches`** | Tree / Git branches have an 'a'. Brunch = late breakfast. |
| `most perspective` | **`most promising`** | 'perspective' = viewpoint. 'promising' = перспективный. |
| `It fells` | **`It feels`** | 'fell' = past of fall. 'feels' = perception. |
| `explains to my` | **`explains to me`** | Preposition + object pronoun ('to me', 'to him'). |
| `free tim` / `te` | **`free time` / `the`** | Common fast-typing key skips. |
| `leaded to` | **`led to`** | Irregular verb: lead &rarr; led &rarr; led. |

*You write very clearly and your technical intent is always completely understood!*
"""

    with open(OUT_MD, "w") as fp:
        fp.write(md_content)

    # 2. Write HTML Catalog node (<= 50-60 lines)
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>English Notes &amp; Observations</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.5; padding: 1.5rem; max-width: 50rem; margin: 0 auto; color: #1a1a1a; background: #fdfdfd; }}
a {{ color: #2563eb; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; font-size: 0.9rem; }}
th, td {{ border: 1px solid #e2e8f0; padding: 0.5rem 0.75rem; text-align: left; }}
th {{ background: #f8fafc; }}
.card {{ border: 1px solid #e2e8f0; padding: 0.75rem 1rem; border-radius: 6px; margin: 0.75rem 0; background: #fff; }}
</style>
</head>
<body>
<p><a href="index.html">[[UP: Root Index]]</a></p>
<h1>Friendly English Companion Notes</h1>
<p>Extracted {len(findings)} common observations across recent sessions. Synced with <code>/botworkspace/ENGLISH_NOTES.md</code>.</p>
<table>
<tr><th>Typed</th><th>Recommended</th><th>Rule / Tip</th></tr>
"""
    for f in findings:
        html_content += f"<tr><td><code>{f['original']}</code></td><td><strong>{f['correction']}</strong></td><td>{f['explanation']}</td></tr>\n"

    html_content += """</table>
<hr>
<p><a href="index.html">[[UP: Root Index]]</a></p>
</body>
</html>
"""
    with open(OUT_HTML, "w") as fp:
        fp.write(html_content)

    return {"observations_count": len(findings)}


if __name__ == "__main__":
    res = generate_reports()
    print(f"[ENGLISH TUTOR COMPLETED] {res['observations_count']} patterns analyzed and saved.")
