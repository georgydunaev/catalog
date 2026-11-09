#!/usr/bin/env python3
"""
Unit test suite for /botworkspace/catalog integrity (Tickets 7433, 7434, 27451, 7414-7418).
"""

import os
import re
import sys
import unittest

CATALOG_ROOT = os.environ.get("CATALOG_ROOT", os.path.normpath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, CATALOG_ROOT)

import db
import benchmark_search


class TestCatalogIntegrity(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        db.sync_db()

    def test_01_index_html_and_all_nodes_zero_broken_links(self):
        """Tickets 7433, 7416: Validate relative href and markdown links in catalog/index.html and all catalog nodes."""
        index_path = os.path.join(CATALOG_ROOT, "index.html")
        self.assertTrue(os.path.isfile(index_path))
        with open(index_path, "r", encoding="utf-8") as f:
            html = f.read()

        hrefs = re.findall(r'href=["\']([^"\'#]+)["\']', html)
        self.assertGreater(len(hrefs), 0)
        for href in hrefs:
            if href.startswith(("http://", "https://", "mailto:")):
                continue
            target = os.path.normpath(os.path.join(CATALOG_ROOT, href))
            self.assertTrue(os.path.exists(target), f"Orphaned link in catalog/index.html: {href}")

        audit = db.query_audit()
        self.assertGreaterEqual(audit["total_nodes"], 50)
        self.assertEqual(len(audit["broken_links"]), 0, f"Broken links detected: {audit['broken_links']}")

    def test_02_fts5_bm25_search_quality_and_obelisk_sync(self):
        """Tickets 7414, 7417: Verify high-precision BM25 search and set_theory_prover cross-referencing."""
        results = db.query_search_fts("set_theory_prover", limit=15)
        self.assertGreater(len(results), 0)
        relpaths = [r["relpath"] for r in results]
        self.assertTrue(any("set_theory_prover" in p for p in relpaths))
        node = db.query_get_node("repos/set_theory_prover/theorems.html")
        self.assertIsNotNone(node)
        self.assertIn("90 Morse-Kelley theorems", node["clean_markdown"])

    def test_03_model_profiles_attention_shield_compliance(self):
        """Ticket 7415: Verify all model profile files in catalog/models/ exist and stay within line limits."""
        models_dir = os.path.join(CATALOG_ROOT, "models")
        self.assertTrue(os.path.isdir(models_dir))
        entries = [f for f in os.listdir(models_dir) if f.endswith((".html", ".md"))]
        self.assertGreater(len(entries), 0)
        for fname in entries:
            fpath = os.path.join(models_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                lines = f.readlines()
            self.assertLessEqual(len(lines), 250, f"Model profile {fname} exceeds attention shield line budget")

    def test_04_probably_outdated_synchronized(self):
        """Ticket 27451: Verify catalog/repos/probably-outdated/index.html removes stale run-pending-tasks reference."""
        po_path = os.path.join(CATALOG_ROOT, "repos", "probably-outdated", "index.html")
        with open(po_path, "r", encoding="utf-8") as f:
            text = f.read()
        self.assertNotIn("run-pending-tasks.sh", text)
        self.assertIn("mybot/host_tasks/", text)

    def test_05_fts_benchmark_search_latency(self):
        """Tickets 7434, 7418: Verify FTS5 benchmark script runs and mean latency is under 50ms."""
        stats = benchmark_search.run_benchmark(iterations=3)
        self.assertGreater(stats["queries_executed"], 0)
        self.assertGreater(stats["total_hits"], 0)
        self.assertLess(stats["mean_latency_ms"], 50.0)


if __name__ == "__main__":
    unittest.main()
