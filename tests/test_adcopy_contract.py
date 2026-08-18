import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
ADCOPY = (ROOT / "adcopy-tool.html").read_text(encoding="utf-8")
KEYWORD = (ROOT / "keyword-tool.html").read_text(encoding="utf-8")
CI = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")


class TestAdcopyContract(unittest.TestCase):
    def test_upload_claims_are_not_shipped_before_template_validation(self):
        for claim in ("연결URL만 채우면 등록", "연결URL만 채우면 바로 업로드", "네이버 바로등록"):
            self.assertNotIn(claim, ADCOPY + KEYWORD)
        self.assertIn("공식 템플릿 확인 전 업로드 금지", ADCOPY)
        self.assertIn("공식 템플릿 확인 전 업로드 금지", KEYWORD)

    def test_official_export_requires_loaded_template(self):
        self.assertIn('id="xOfficial" ${NAVER_TEMPLATE?"":"disabled"}', ADCOPY)
        self.assertIn("if(!NAVER_TEMPLATE)", ADCOPY)
        self.assertIn("필수 열 매핑 실패", ADCOPY)

    def test_ci_runs_650_row_validation(self):
        self.assertIn("node scripts/check_adcopy_export.mjs", CI)


if __name__ == "__main__":
    unittest.main()
