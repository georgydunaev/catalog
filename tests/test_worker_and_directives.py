#!/usr/bin/env python3
"""
Unit test suite for worker_memory.py and correction_memory.py.
"""

import os
import sys
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
if CATALOG_ROOT not in sys.path:
    sys.path.insert(0, CATALOG_ROOT)

import worker_memory
import correction_memory


class TestWorkerAndDirectives(unittest.TestCase):

    def test_01_correction_memory_seed_and_query(self):
        """Test user directives seeding and retrieval in priority order."""
        correction_memory.seed_core_directives()
        directives = correction_memory.get_directives(limit=10)
        self.assertGreater(len(directives), 0)
        priorities = [d["priority"] for d in directives]
        # Must be sorted descending by priority
        self.assertEqual(priorities, sorted(priorities, reverse=True))

    def test_02_worker_scratchpad_record_and_history(self):
        """Test recording note in scratchpad and reading history."""
        test_ticket = "TKT-TEST-999"
        note_id = worker_memory.record_worker_note(
            ticket_id=test_ticket,
            model_name="test-model",
            lemma_name="Lemma 1",
            summary="Tested hypothesis in isolated scratchpad",
            status="PROVED"
        )
        self.assertIsInstance(note_id, int)
        history = worker_memory.get_ticket_history(test_ticket, limit=5)
        self.assertGreaterEqual(len(history), 1)
        self.assertEqual(history[0]["lemma_name"], "Lemma 1")
        self.assertEqual(history[0]["status"], "PROVED")

    def test_03_query_canonical_catalog(self):
        """Test canonical read-only queries."""
        hits = worker_memory.query_canonical_catalog("emojis", limit=3)
        self.assertIsInstance(hits, list)
        self.assertGreater(len(hits), 0)


if __name__ == "__main__":
    unittest.main()
