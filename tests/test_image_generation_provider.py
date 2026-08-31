import base64
import json
import pathlib
import unittest

from scripts import generate_image_assets as provider


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "scripts" / "generate_image_assets.py").read_text(encoding="utf-8")
WORKFLOW = (ROOT / ".github" / "workflows" / "generate-image-assets.yml").read_text(encoding="utf-8")


class TestImageGenerationProvider(unittest.TestCase):
    def test_workflow_is_manual_and_explicitly_opt_in(self):
        self.assertIn("workflow_dispatch", WORKFLOW)
        self.assertIn("execute", WORKFLOW)
        self.assertIn("OPENAI_API_KEY", WORKFLOW)
        self.assertIn("if: ${{ inputs.execute == true }}", WORKFLOW)
        self.assertNotIn("schedule:", WORKFLOW)

    def test_provider_does_not_call_api_without_execute(self):
        self.assertIn("if not args.execute", SCRIPT)
        self.assertIn("--retry-failed", SCRIPT)
        self.assertIn("OPENAI_API_KEY Secret이 없습니다", SCRIPT)
        self.assertIn("DEFAULT_API_URL = \"https://api.openai.com/v1/images/generations\"", SCRIPT)
        self.assertIn("DEFAULT_MODEL = \"gpt-image-1\"", SCRIPT)

    def test_b64_image_response_is_decoded_and_png_is_validated(self):
        data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8 + (214).to_bytes(4, "big") + (214).to_bytes(4, "big")
        payload = {"data": [{"b64_json": base64.b64encode(data).decode("ascii")}]}
        result = provider.response_image_bytes(payload)
        self.assertEqual(result, data)
        self.assertEqual(provider.validate_png(result), (214, 214))

    def test_failed_items_are_opt_in_for_retry(self):
        queue = {"items": [
            {"status": "pending", "product_key": "driver"},
            {"status": "failed", "product_key": "driver"},
            {"status": "generated", "product_key": "driver"},
        ]}
        self.assertEqual(len(provider.pending_items(queue)), 1)
        self.assertEqual(len(provider.pending_items(queue, retry_failed=True)), 2)

    def test_existing_failures_do_not_block_a_new_batch(self):
        self.assertIn("run_failures = 0", SCRIPT)
        self.assertIn("return 1 if run_failures else 0", SCRIPT)

    def test_asset_target_is_scoped_to_product_generated_folder(self):
        target = provider.asset_target("assets/insurance/generated/driver-2026-08-01.png", "driver")
        self.assertTrue(str(target).endswith("driver-2026-08-01.png"))
        with self.assertRaises(ValueError):
            provider.asset_target("assets/insurance/generated/hrmf-2026-08-01.png", "driver")
        with self.assertRaises(ValueError):
            provider.asset_target("assets/insurance/../secret.png", "driver")


if __name__ == "__main__":
    unittest.main()
