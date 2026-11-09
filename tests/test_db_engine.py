#!/usr/bin/env python3
"""
Unit test suite for /ramdisk/catalog/db.py engine and connection lifecycle.
"""

import os
import sys
import unittest
import sqlite3

CATALOG_ROOT = os.environ.get("CATALOG_ROOT", os.path.normpath(os.path.join(os.path.dirname(__file__), "..")))
if CATALOG_ROOT not in sys.path:
    sys.path.insert(0, CATALOG_ROOT)

import db


class TestDbEngine(unittest.TestCase):

    def test_01_open_db_context_manager(self):
        """Test open_db context manager opens and guarantees connection closure."""
        with db.open_db() as conn:
            self.assertIsInstance(conn, sqlite3.Connection)
            row = conn.execute("SELECT 1 AS val;").fetchone()
            self.assertEqual(row["val"], 1)
        # Connection should be closed after exiting context manager
        with self.assertRaises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1;")

    def test_02_html_to_clean_markdown(self):
        """Test html_to_clean_markdown entity decoding and markdown conversion."""
        raw_html = "<h1>Title</h1><p>Text with &bull; bullet and &isin; element.</p><a href='link.html'>Link Text</a>"
        clean = db.html_to_clean_markdown(raw_html)
        self.assertIn("# Title", clean)
        self.assertIn("Text with • bullet and ∈ element.", clean)
        self.assertIn("[Link Text](link.html)", clean)

    def test_03_query_get_node(self):
        """Test query_get_node returns valid dict for existing node and None for nonexistent."""
        node = db.query_get_node("index.html")
        self.assertIsNotNone(node)
        self.assertEqual(node["relpath"], "index.html")
        self.assertIn("clean_markdown", node)

        missing = db.query_get_node("nonexistent/dummy_node.html")
        self.assertIsNone(missing)

    def test_04_query_search_fts(self):
        """Test FTS5 BM25 search ranking and snippet generation."""
        hits = db.query_search_fts("Morse-Kelley", limit=5)
        self.assertIsInstance(hits, list)
        self.assertGreater(len(hits), 0)
        first = hits[0]
        self.assertIn("relpath", first)
        self.assertIn("title", first)
        self.assertIn("snippet", first)

    def test_05_query_audit_integrity(self):
        """Test query_audit returns consistent metrics and zero broken links."""
        audit = db.query_audit()
        self.assertGreater(audit["total_nodes"], 100)
        self.assertGreater(audit["total_links"], 200)
        self.assertEqual(len(audit["broken_links"]), 0)


if __name__ == "__main__":
    unittest.main()
