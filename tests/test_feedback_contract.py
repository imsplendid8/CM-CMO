import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
CLIENT = (ROOT / "shared" / "feedback-client.js").read_text(encoding="utf-8")
SCHEMA = (ROOT / "docs" / "feedback-schema.sql").read_text(encoding="utf-8")
ADCOPY = (ROOT / "adcopy-tool.html").read_text(encoding="utf-8")


class TestFeedbackContract(unittest.TestCase):
    def test_feedback_is_private_endpoint_only(self):
        self.assertNotIn("localStorage", CLIENT)
        self.assertNotIn("copy_history.json", CLIENT)
        self.assertIn("feedback endpoint not configured", CLIENT)
        self.assertIn('credentials: "include"', CLIENT)

    def test_raw_copy_is_replaced_with_fingerprint(self):
        self.assertIn("payload.textFingerprint", CLIENT)
        self.assertIn("delete payload.text", CLIENT)

    def test_schema_supports_review_and_performance(self):
        self.assertIn("CREATE TABLE IF NOT EXISTS copy_feedback", SCHEMA)
        self.assertIn("CREATE TABLE IF NOT EXISTS performance_outcome", SCHEMA)
        for action in ("copied", "accepted", "edit_requested", "rejected"):
            self.assertIn(action, SCHEMA)

    def test_recommendation_ui_exposes_human_actions(self):
        for action in ("accepted", "edit_requested", "rejected"):
            self.assertIn(f'data-feedback-action="{action}"', ADCOPY)


if __name__ == "__main__":
    unittest.main()
