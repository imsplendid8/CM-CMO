import base64
import json
import pathlib
import unittest

from scripts import generate_image_assets as provider


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "scripts" / "generate_image_assets.py").read_text(encoding="utf-8")
WORKFLOW = (ROOT / ".github" / "workflows" / "generate-image-assets.yml").read_text(encoding="utf-8")
ADMIN = (ROOT / "material-admin.html").read_text(encoding="utf-8")
DOC = (ROOT / "docs" / "ima2-oauth-image-generation.md").read_text(encoding="utf-8")


class FakeResponse:
    def __init__(self, payload, status=200):
        self.body = json.dumps(payload).encode("utf-8")
        self.status = status

    def read(self, limit=-1):
        return self.body if limit < 0 else self.body[:limit]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


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
        self.assertIn("MAX_BATCH = 20", SCRIPT)
        self.assertIn("HTTPS 주소여야 함", SCRIPT)
        self.assertIn("OPENAI_API_KEY Secret이 없습니다", SCRIPT)
        self.assertIn("DEFAULT_API_URL = \"https://api.openai.com/v1/images/generations\"", SCRIPT)
        self.assertIn("DEFAULT_MODEL = \"gpt-image-1\"", SCRIPT)
        self.assertIn("ima2-oauth", SCRIPT)
        self.assertIn("validate_ima2_url", SCRIPT)

    def test_admin_exposes_local_oauth_runbook_without_browser_token_handling(self):
        self.assertIn("이미지 생성 연결 · ima2 OAuth", ADMIN)
        self.assertIn("copyIma2Command", ADMIN)
        self.assertIn("자동 조회하지 않습니다", ADMIN)
        self.assertIn("OAuth 토큰", DOC)
        self.assertIn("GitHub Actions", DOC)

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
        self.assertIn('if not items:\n        print("[OK] 처리할 pending 항목이 없습니다.", flush=True)', SCRIPT)

    def test_workflow_commits_failure_statuses_after_warning(self):
        self.assertIn("continue-on-error: true", WORKFLOW)
        self.assertIn("steps.validate.outcome == 'success'", WORKFLOW)
        self.assertIn("Report generation warnings", WORKFLOW)

    def test_asset_target_is_scoped_to_product_generated_folder(self):
        target = provider.asset_target("assets/insurance/generated/driver-2026-08-01.png", "driver")
        self.assertTrue(str(target).endswith("driver-2026-08-01.png"))
        with self.assertRaises(ValueError):
            provider.asset_target("assets/insurance/generated/hrmf-2026-08-01.png", "driver")
        with self.assertRaises(ValueError):
            provider.asset_target("assets/insurance/../secret.png", "driver")

    def test_ima2_oauth_accepts_loopback_only(self):
        self.assertEqual(provider.validate_ima2_url("http://127.0.0.1:3333"), "http://127.0.0.1:3333")
        self.assertEqual(provider.validate_ima2_url("http://localhost:3333/"), "http://localhost:3333")
        with self.assertRaises(ValueError):
            provider.validate_ima2_url("https://127.0.0.1:3333")
        with self.assertRaises(ValueError):
            provider.validate_ima2_url("http://192.168.0.10:3333")

    def test_ima2_oauth_request_decodes_data_url_and_separates_model(self):
        image = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8 + (214).to_bytes(4, "big") + (214).to_bytes(4, "big")
        encoded = "data:image/png;base64," + base64.b64encode(image).decode("ascii")
        captured = {}

        def opener(request, timeout=0):
            captured["request"] = request
            return FakeResponse({"image": encoded})

        result = provider.ima2_generate(
            {"queue_id": "driver-thumb-1", "prompt": "운전 장면"},
            model="oauth/gpt-5.6-luna",
            opener=opener,
        )
        self.assertEqual(result, image)
        body = json.loads(captured["request"].data.decode("utf-8"))
        self.assertEqual(body["provider"], "oauth")
        self.assertEqual(body["model"], "gpt-5.6-luna")
        self.assertEqual(body["format"], "png")
        self.assertNotIn("Authorization", captured["request"].headers)

    def test_ima2_oauth_multi_image_response_uses_first_image(self):
        image = b"first-image"
        payload = {"images": [{"image": "data:image/png;base64," + base64.b64encode(image).decode("ascii")}]}
        self.assertEqual(provider.ima2_image_bytes(payload), image)


if __name__ == "__main__":
    unittest.main()
