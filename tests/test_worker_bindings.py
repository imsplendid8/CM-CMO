#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""워커 자동 배포: 대시보드 KV를 이름으로 찾아 wrangler.toml에 붙이는지(없으면 배포 중단)."""
import os
import sys
import tomllib
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import worker_bindings as wb  # noqa: E402

TOML = open(os.path.join(ROOT, "proxy", "wrangler.toml"), encoding="utf-8").read()


class TestWorkerBindings(unittest.TestCase):
    def test_attaches_usage_and_keeps_crons(self):
        text, missing = wb.attach(TOML, [{"id": "abc123", "title": "modooflow-usage"}, {"id": "x", "title": "other"}])
        self.assertEqual(missing, [])
        cfg = tomllib.loads(text)
        self.assertTrue(cfg["keep_vars"])
        self.assertEqual(cfg["kv_namespaces"], [{"binding": "USAGE", "id": "abc123"}])
        self.assertEqual(cfg["triggers"]["crons"], ["*/5 * * * *"])
        self.assertEqual(cfg["name"], "modooflow-naver-proxy")

    def test_missing_usage_blocks_deploy(self):
        _, missing = wb.attach(TOML, [{"id": "g", "title": "modooflow-gsc-tokens"}])
        self.assertEqual(missing, ["USAGE"])

    def test_optional_gsc_binding(self):
        text, _ = wb.attach(TOML, [{"id": "u", "title": "USAGE"}, {"id": "g", "title": "modooflow-gsc-tokens"}])
        self.assertIn({"binding": "GSC_TOKENS", "id": "g"}, tomllib.loads(text)["kv_namespaces"])


if __name__ == "__main__":
    unittest.main()
