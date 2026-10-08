#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""공개 사이트에는 SERP 캡처를 최근 N일치만 싣는다(manifest와 파일이 함께 줄어야 깨진 이미지가 없다)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import build_pages  # noqa: E402


class TestRecentCaptures(unittest.TestCase):
    def test_trims_manifest_and_file_set_together(self):
        manifest = {"asof": "2026-10-04", "brands": {"kb": {"products": {"driver": {"captures": [
            {"file": "kb-driver-pc-2026-08-01.png", "date": "2026-08-01"},
            {"file": "kb-driver-pc-2026-09-20.png", "date": "2026-09-20"},
            {"file": "kb-driver-pc-2026-10-04.jpg", "date": "2026-10-04"},
        ]}}}}}
        trimmed, keep = build_pages._recent_captures(manifest, days=28)
        caps = trimmed["brands"]["kb"]["products"]["driver"]["captures"]
        self.assertEqual([c["date"] for c in caps], ["2026-09-20", "2026-10-04"])
        self.assertEqual(keep, {"kb-driver-pc-2026-09-20.png", "kb-driver-pc-2026-10-04.jpg"})
        self.assertEqual(len(manifest["brands"]["kb"]["products"]["driver"]["captures"]), 3, "원본 manifest는 그대로")


if __name__ == "__main__":
    unittest.main()
