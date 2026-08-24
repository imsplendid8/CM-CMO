import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
ADCOPY = (ROOT / "adcopy-tool.html").read_text(encoding="utf-8")
POWER = (ROOT / "powercontent-tool.html").read_text(encoding="utf-8")
KEYWORD = (ROOT / "keyword-tool.html").read_text(encoding="utf-8")
CI = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
MATERIAL_SPECS = (ROOT / "shared" / "naver-material-specs.js").read_text(encoding="utf-8")
MATERIAL_GUIDE = (ROOT / "docs" / "naver-ad-material-guide.md").read_text(encoding="utf-8")


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
        self.assertIn('const OUT_OF_SCOPE_VOLUME=["자동차보험","자동차 보험","한화생명"]', ADCOPY)
        self.assertNotIn("공개 광고 관측", ADCOPY)
        self.assertNotIn("공개 SERP 관측", ADCOPY)
        self.assertIn('data-copy="${esc(o.title)}"', ADCOPY)
        self.assertIn('data-copy="${esc(o.desc)}"', ADCOPY)

    def test_power_content_is_a_separate_guarded_workspace(self):
        self.assertNotIn('__power', ADCOPY)
        self.assertNotIn("powercontent-title-opportunities.json", ADCOPY)
        self.assertIn("파워콘텐츠 소재", POWER)
        self.assertIn("const EDITORIAL=MATERIAL_SPEC.powerContentEditorial", POWER)
        self.assertIn("내부 편집 기준", POWER)
        self.assertIn("data/adcopy/powercontent-title-opportunities.json", POWER)
        self.assertIn("SEO 검색 근거", POWER)
        self.assertIn("GSC가 확인되지 않으면 추천을 확정하지 않고", POWER)
        self.assertIn("최신 상품자료·약관·준법·광고심의 확인", POWER)
        self.assertIn("키워드–소재–랜딩 본문의 주제", POWER)

    def test_sa_and_power_content_share_material_review_rules(self):
        self.assertIn('shared/naver-material-specs.js', ADCOPY)
        self.assertIn('shared/naver-material-specs.js', POWER)
        self.assertIn('additionalDescription', ADCOPY)
        self.assertIn('function extensionBrief(p,c)', POWER)
        self.assertIn('function validateExtensions(value)', POWER)
        self.assertIn('maxLength: 14, maxPerGroup: 2', MATERIAL_SPECS)
        self.assertIn('minPerAd: 3, maxPerAd: 4, maxPerSite: 4', MATERIAL_SPECS)
        self.assertIn('서브링크 URL 1~4', MATERIAL_GUIDE)
        self.assertIn('node --check shared/naver-material-specs.js', CI)

    def test_urls_and_asset_ids_are_manual_only(self):
        for field in (
            "calculationUrl",
            "powerLinkImageId",
            "sublinkUrl1",
            "sublinkImageId1",
        ):
            self.assertIn(field, ADCOPY)
            self.assertIn(field, POWER)
            self.assertIn(field, MATERIAL_SPECS)
        self.assertIn('MATERIAL_SPEC.manualOnlyFields.forEach', ADCOPY)
        self.assertIn('MATERIAL_SPEC.manualOnlyFields.forEach', POWER)

    def test_power_content_rejects_out_of_scope_topics_and_exports_brief(self):
        for term in ("자동차보험", "공개관측", "공개 관측", "한화생명", "고객센터"):
            self.assertIn(term, POWER)
        self.assertIn("function inScope(p,text)", POWER)
        self.assertIn("function exportCsv()", POWER)
        self.assertIn('id="copyBrief"', POWER)
        self.assertIn('id="exportCsv"', POWER)

    def test_copy_candidates_use_shared_korean_humanizer(self):
        self.assertIn('shared/humanize-ko.js', ADCOPY)
        self.assertIn('dw(HUMANIZE.light(x))', ADCOPY)
        self.assertIn('node --check shared/humanize-ko.js', CI)


if __name__ == "__main__":
    unittest.main()
