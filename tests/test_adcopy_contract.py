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

    def test_serp_monitoring_changes_generated_sa_without_copying_claims(self):
        self.assertIn("function serpIdeas(p)", ADCOPY)
        self.assertIn("경쟁사 광고와 SA 제안", ADCOPY)
        self.assertIn("observed_ads", ADCOPY)
        self.assertIn('strategy:"핵심 보장 확인"', ADCOPY)
        self.assertIn('strategy:"가입 전 체크"', ADCOPY)
        self.assertIn('strategy:"보험료·보장 비교"', ADCOPY)
        self.assertIn("SA 소재 제안", ADCOPY)
        self.assertNotIn("공개 광고 관측", ADCOPY)
        self.assertNotIn("공개 SERP 관측", ADCOPY)
        self.assertIn('data-copy="${esc(o.title)}"', ADCOPY)
        self.assertIn('data-copy="${esc(o.desc)}"', ADCOPY)

    def test_power_content_brief_has_specs_and_review_guards(self):
        self.assertIn('item("__power","📝 파워컨텐츠 제안"', ADCOPY)
        self.assertIn("제목 <b>7~28자</b>", ADCOPY)
        self.assertIn("설명 <b>80~110자</b>", ADCOPY)
        self.assertIn("키워드–소재–랜딩 본문의 주제 일치", ADCOPY)
        self.assertNotIn("참고 기준", ADCOPY)

    def test_copy_candidates_use_shared_korean_humanizer(self):
        self.assertIn('shared/humanize-ko.js', ADCOPY)
        self.assertIn('dw(HUMANIZE.light(x))', ADCOPY)
        self.assertIn('node --check shared/humanize-ko.js', CI)


if __name__ == "__main__":
    unittest.main()
