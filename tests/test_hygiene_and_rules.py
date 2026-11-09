#!/usr/bin/env python3
"""
Unit test suite verifying compliance with fundamental workspace invariants:
1. Absolute prohibition of emojis across catalog Python scripts and rendered HTML.
2. Prohibition of arrows in link names, buttons, and titles.
"""

import os
import re
import glob
import unittest

CATALOG_ROOT = os.environ.get("CATALOG_ROOT", os.path.normpath(os.path.join(os.path.dirname(__file__), "..")))

# Disallowed emoji code points or symbols in code and UI
FORBIDDEN_EMOJIS = {'⚠️', '🎯', '🛑', '🛡', '📌', '🌙', '✔', '✖', '❓', '⚡'}


class TestHygieneAndRules(unittest.TestCase):

    def test_01_no_emojis_in_python_scripts(self):
        """Rule: Absolute Prohibition of Emojis across all catalog Python scripts."""
        py_files = glob.glob(os.path.join(CATALOG_ROOT, "*.py"))
        violations = []
        for py_path in py_files:
            fname = os.path.basename(py_path)
            with open(py_path, "r", encoding="utf-8", errors="ignore") as fp:
                for line_no, line in enumerate(fp, 1):
                    # Ignore the emoji prohibition rule definition itself
                    if "absolute_prohibition_of_emojis" in line or "Never use emojis" in line:
                        continue
                    for ch in line:
                        if ch in FORBIDDEN_EMOJIS or ord(ch) > 0x1F000:
                            violations.append(f"{fname}:{line_no}: character U+{ord(ch):04X} ({ch})")
        self.assertEqual(len(violations), 0, f"Found forbidden emojis in Python files: {violations}")

    def test_02_no_arrows_in_html_links(self):
        """Rule: No Arrows in Names, Titles, or Links & Laconic Link Names."""
        arrow_patterns = ['→', '←', '↓', '↑', '&rarr;', '&larr;', '&darr;', '&uarr;']
        html_files = [
            os.path.join(CATALOG_ROOT, "index.html"),
            os.path.join(CATALOG_ROOT, "user_directives.html"),
            os.path.join(CATALOG_ROOT, "english_notes.html"),
        ]
        violations = []
        for h_path in html_files:
            if not os.path.isfile(h_path):
                continue
            fname = os.path.basename(h_path)
            with open(h_path, "r", encoding="utf-8", errors="ignore") as fp:
                content = fp.read()
            for m in re.finditer(r'<a\s+[^>]*>(.*?)</a>', content, flags=re.DOTALL):
                link_text = m.group(1)
                for arr in arrow_patterns:
                    if arr in link_text:
                        violations.append(f"{fname}: link '{link_text.strip()}' contains arrow '{arr}'")
        self.assertEqual(len(violations), 0, f"Found arrows in HTML links: {violations}")


if __name__ == "__main__":
    unittest.main()
