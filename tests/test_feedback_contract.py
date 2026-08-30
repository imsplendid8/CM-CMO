import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
CLIENT = (ROOT / "shared" / "feedback-client.js").read_text(encoding="utf-8")
SCHEMA = (ROOT / "docs" / "feedback-schema.sql").read_text(encoding="utf-8")
ADCOPY = (ROOT / "adcopy-tool.html").read_text(encoding="utf-8")
MATERIAL_ADMIN = (ROOT / "material-admin.html").read_text(encoding="utf-8")
MATERIAL_CLIENT = (ROOT / "shared" / "material-feedback.js").read_text(encoding="utf-8")
MATERIAL_RULES = (ROOT / "data" / "adcopy" / "material-feedback-rules.json").read_text(encoding="utf-8")
SERP_COPY_AGENT = (ROOT / "scripts" / "serp_copy_agent.py").read_text(encoding="utf-8")


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

    def test_material_admin_is_local_review_lab(self):
        self.assertIn("ModooMaterialFeedback", MATERIAL_ADMIN)
        self.assertIn("data/adcopy/material-feedback-rules.json", MATERIAL_ADMIN)
        self.assertIn("반려 사유 요약", MATERIAL_ADMIN)
        self.assertIn("상품별 반복 실패", MATERIAL_ADMIN)
        for label in ("SA 소재", "파워콘텐츠", "썸네일"):
            self.assertIn(label, MATERIAL_ADMIN)
        for action in ("accepted", "edit_requested", "rejected", "compliance_review"):
            self.assertIn(action, MATERIAL_CLIENT)

    def test_material_feedback_uses_fingerprint_and_rule_export(self):
        self.assertIn("modoo_material_review_lab_v1", MATERIAL_CLIENT)
        self.assertIn("text_fingerprint", MATERIAL_CLIENT)
        self.assertIn("text_preview: text.slice(0, 120)", MATERIAL_CLIENT)
        self.assertIn("exportRules", MATERIAL_CLIENT)
        self.assertIn("blocked_phrases", MATERIAL_RULES)

    def test_generation_reads_material_feedback_rules(self):
        self.assertIn("material-feedback-rules.json", SERP_COPY_AGENT)
        self.assertIn("def apply_feedback_rules", SERP_COPY_AGENT)
        self.assertIn("review_lab_feedback", SERP_COPY_AGENT)


if __name__ == "__main__":
    unittest.main()
