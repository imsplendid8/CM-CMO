#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""실제 이미지 API 없이도 생성 큐와 완료 승격 규칙을 검증한다."""
import json
import pathlib
import sys
import tempfile
import unittest

SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import image_generation_queue as queue  # noqa: E402


class TestImageGenerationQueue(unittest.TestCase):
    def make_root(self, tmp):
        root = pathlib.Path(tmp)
        (root / "assets/insurance/generated").mkdir(parents=True)
        (root / "data/adcopy").mkdir(parents=True)
        plan = {
            "planning_month": "2026-08",
            "products": [{
                "product_key": "driver",
                "keyword": "운전자보험",
                "month": "2026-08",
                "image_directions": [{
                    "proposal_id": "driver-2026-08-01",
                    "concept_id": "abc",
                    "role": "파워링크 대표",
                    "scene": "비 오는 저녁 도로에서 안전운전하는 운전자",
                    "generation_brief": "텍스트·숫자·로고 없는 3D 애니메이션",
                    "generation_required": True,
                    "reference_only": True,
                    "asset": "assets/insurance/driver-safe-animation-v3.png",
                }],
            }],
        }
        plan_path = root / "data/adcopy/serp-candidates.json"
        plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
        (root / "data/products.json").write_text(
            json.dumps({"products": [{"key": "driver", "name": "운전자보험"}]}),
            encoding="utf-8",
        )
        return root, plan_path, root / "data/adcopy/image-generation-queue.json"

    def test_pending_is_explicit_and_does_not_use_reference_as_generated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, _, queue_path = self.make_root(tmp)
            payload = queue.build_queue(root, root / "data/adcopy/serp-candidates.json", queue_path)
            self.assertEqual(payload["summary"]["pending"], 1)
            self.assertEqual(payload["items"][0]["status"], "pending")
            self.assertTrue(payload["items"][0]["reference_only"])
            self.assertNotEqual(payload["items"][0]["asset_path"], payload["items"][0]["reference_asset"])

    def test_existing_generated_png_is_promoted_only_by_sync(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, plan_path, queue_path = self.make_root(tmp)
            queue.build_queue(root, plan_path, queue_path)
            generated = root / "assets/insurance/generated/driver-2026-08-01.png"
            generated.write_bytes(b"png placeholder")
            payload = queue.build_queue(root, plan_path, queue_path)
            self.assertEqual(payload["items"][0]["status"], "generated")
            self.assertEqual(json.loads(plan_path.read_text(encoding="utf-8"))["products"][0]["image_directions"][0]["asset"], "assets/insurance/driver-safe-animation-v3.png")
            self.assertEqual(queue.sync_generated_assets(root, plan_path, queue_path), 1)
            row = json.loads(plan_path.read_text(encoding="utf-8"))["products"][0]["image_directions"][0]
            self.assertEqual(row["asset"], "assets/insurance/generated/driver-2026-08-01.png")
            self.assertFalse(row["generation_required"])
            self.assertFalse(row["reference_only"])

    def test_committed_generated_asset_remains_generated_in_queue(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, plan_path, queue_path = self.make_root(tmp)
            generated = root / "assets/insurance/generated/driver-2026-08-01.png"
            generated.write_bytes(b"png placeholder")
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            row = plan["products"][0]["image_directions"][0]
            row["asset"] = "assets/insurance/generated/driver-2026-08-01.png"
            row["generation_required"] = False
            row["reference_only"] = False
            plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            payload = queue.build_queue(root, plan_path, queue_path)
            self.assertEqual(payload["items"][0]["status"], "generated")


if __name__ == "__main__":
    unittest.main(verbosity=2)
