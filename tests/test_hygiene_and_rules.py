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

def _resolve_catalog_root() -> str:
    if "CATALOG_ROOT" in os.environ and os.path.isdir(os.environ["CATALOG_ROOT"]):
        return os.environ["CATALOG_ROOT"]
    for candidate in [
        "/hostramdisk/catalog",
        "/botworkspace/catalog",
        os.path.normpath(os.path.join(os.path.dirname(__file__), "..")),
    ]:
        if os.path.isdir(candidate):
            return candidate
    return os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))

CATALOG_ROOT = _resolve_catalog_root()

# Disallowed emoji code points or symbols in code and UI
FORBIDDEN_EMOJIS = {
    '\u26a0\ufe0f', '\U0001f3af', '\U0001f6d1', '\U0001f6e1', '\U0001f4cc',
    '\U0001f319', '\u2714', '\u2716', '\u2753', '\u26a1',
    '\U0001f916', '\U0001f680', '\U0001f4a1', '\U0001f525'
}


class TestHygieneAndRules(unittest.TestCase):

    def test_01_no_emojis_in_python_scripts(self):
        """Rule: Absolute Prohibition of Emojis across all catalog Python scripts."""
        py_files = glob.glob(os.path.join(CATALOG_ROOT, "**", "*.py"), recursive=True)
        violations = []
        for py_path in py_files:
            fname = os.path.relpath(py_path, CATALOG_ROOT)
            with open(py_path, "r", encoding="utf-8", errors="ignore") as fp:
                for line_no, line in enumerate(fp, 1):
                    # Ignore the emoji prohibition rule definition itself
                    if "absolute_prohibition_of_emojis" in line or "Never use emojis" in line or "FORBIDDEN_EMOJIS" in line:
                        continue
                    for ch in line:
                        if ch in FORBIDDEN_EMOJIS or ord(ch) > 0x1F000:
                            violations.append(f"{fname}:{line_no}: character U+{ord(ch):04X} ({ch})")
        self.assertEqual(len(violations), 0, f"Found forbidden emojis in Python files: {violations}")

    def test_02_no_arrows_in_html_links(self):
        """Rule: No Arrows in Names, Titles, or Links & Laconic Link Names across all catalog HTML documents."""
        arrow_patterns = ['→', '←', '↓', '↑', '&rarr;', '&larr;', '&darr;', '&uarr;']
        html_files = glob.glob(os.path.join(CATALOG_ROOT, "**", "*.html"), recursive=True)
        violations = []
        for h_path in html_files:
            if not os.path.isfile(h_path):
                continue
            fname = os.path.relpath(h_path, CATALOG_ROOT)
            with open(h_path, "r", encoding="utf-8", errors="ignore") as fp:
                content = fp.read()
            for m in re.finditer(r'<a\s+[^>]*>(.*?)</a>', content, flags=re.DOTALL):
                link_text = m.group(1)
                for arr in arrow_patterns:
                    if arr in link_text:
                        violations.append(f"{fname}: link '{link_text.strip()}' contains arrow '{arr}'")
            for m in re.finditer(r'<(title|h[1-6])[^>]*>(.*?)</\1>', content, flags=re.DOTALL):
                title_text = m.group(2)
                for arr in arrow_patterns:
                    if arr in title_text:
                        violations.append(f"{fname}: heading/title '{title_text.strip()}' contains arrow '{arr}'")
        self.assertEqual(len(violations), 0, f"Found arrows in HTML links or titles: {violations}")

    def test_03_no_emojis_in_html_files(self):
        """Rule: Absolute Prohibition of Emojis across all catalog HTML documents."""
        html_files = glob.glob(os.path.join(CATALOG_ROOT, "**", "*.html"), recursive=True)
        violations = []
        for h_path in html_files:
            fname = os.path.relpath(h_path, CATALOG_ROOT)
            with open(h_path, "r", encoding="utf-8", errors="ignore") as fp:
                for line_no, line in enumerate(fp, 1):
                    if "Never use emojis" in line or "ABSOLUTE PROHIBITION OF EMOJIS" in line:
                        continue
                    for ch in line:
                        if ch in FORBIDDEN_EMOJIS or ord(ch) > 0x1F000:
                            violations.append(f"{fname}:{line_no}: character U+{ord(ch):04X} ({ch})")
        self.assertEqual(len(violations), 0, f"Found forbidden emojis in HTML files: {violations}")

    def test_04_schemas_and_notions_ontology_integrity(self):
        """Verify schemas and machine-readable notions ontology compliance."""
        import json
        schemas_dir = os.path.join(CATALOG_ROOT, "schemas")
        self.assertTrue(os.path.isdir(schemas_dir))

        model_schema_path = os.path.join(schemas_dir, "model_profile.schema.json")
        self.assertTrue(os.path.isfile(model_schema_path))
        with open(model_schema_path, "r", encoding="utf-8") as fp:
            model_schema = json.load(fp)
        self.assertIn("properties", model_schema)

        notions_path = os.path.join(schemas_dir, "notions_ontology.json")
        self.assertTrue(os.path.isfile(notions_path))
        with open(notions_path, "r", encoding="utf-8") as fp:
            notions_data = json.load(fp)

        self.assertIn("notions", notions_data)
        self.assertGreaterEqual(len(notions_data["notions"]), 20)
        expected_domains = {"set_theory", "proof_systems", "metatheory", "platform"}
        actual_domains = set(notions_data.get("domains", []))
        self.assertTrue(expected_domains.issubset(actual_domains))

        arrow_chars = ['\u2192', '\u2190', '\u2193', '\u2191', '&rarr;', '&larr;', '&darr;', '&uarr;']
        for item in notions_data["notions"]:
            self.assertTrue(item["id"].startswith("NOTION:"))
            self.assertTrue(bool(item.get("canonical_term")))
            self.assertTrue(bool(item.get("definition")))
            self.assertIn(item.get("domain"), actual_domains)
            for arr in arrow_chars:
                self.assertNotIn(arr, item["canonical_term"])
                for alias in item.get("prohibited_aliases", []):
                    self.assertNotIn(arr, alias)

        index_html_path = os.path.join(schemas_dir, "index.html")
        self.assertTrue(os.path.isfile(index_html_path))


if __name__ == "__main__":
    unittest.main()
