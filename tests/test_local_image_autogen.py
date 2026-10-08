#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""구독 OAuth 로컬 자동 생성 실행기 — 대기 집계·안전장치."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import local_image_autogen as lia  # noqa: E402


class TestLocalImageAutogen(unittest.TestCase):
    def test_pending_count(self):
        with tempfile.TemporaryDirectory() as d:
            q = Path(d) / "q.json"
            q.write_text(json.dumps({"items": [{"status": "pending"}, {"status": "failed"}, {"status": "generated"}]}), encoding="utf-8")
            with mock.patch.object(lia, "QUEUE", q):
                self.assertEqual(lia.pending_count(), 1)
                self.assertEqual(lia.pending_count(retry_failed=True), 2)

    def test_limit_bounds(self):
        with mock.patch.object(sys, "argv", ["x", "--limit", "0"]):
            self.assertEqual(lia.main(), 2)

    def test_commits_only_generated_assets_and_queue(self):
        self.assertEqual(lia.COMMIT_PATHS, ["assets/insurance/generated", "data/adcopy/image-generation-queue.json",
                                            "data/adcopy/serp-candidates.json"])

    def test_oauth_lane_only(self):
        src = Path(lia.__file__).read_text(encoding="utf-8")
        self.assertIn('"--provider", "ima2-oauth"', src)
        self.assertNotIn("OPENAI_API_KEY", src)


if __name__ == "__main__":
    unittest.main()
