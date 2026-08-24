import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
ADCOPY = (ROOT / "adcopy-tool.html").read_text(encoding="utf-8")
POWER = (ROOT / "powercontent-tool.html").read_text(encoding="utf-8")
KEYWORD = (ROOT / "keyword-tool.html").read_text(encoding="utf-8")
CI = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
MATERIAL_SPECS = (ROOT / "shared" / "naver-material-specs.js").read_text(encoding="utf-8")
AD_REVIEW = (ROOT / "shared" / "insurance-ad-review.js").read_text(encoding="utf-8")
MATERIAL_GUIDE = (ROOT / "docs" / "naver-ad-material-guide.md").read_text(encoding="utf-8")
REVIEW_SKILL = (ROOT / ".claude" / "skills" / "insurance-ad-review" / "SKILL.md").read_text(encoding="utf-8")
REGULATORY_BASIS = (ROOT / ".claude" / "skills" / "insurance-ad-review" / "references" / "regulatory-basis.md").read_text(encoding="utf-8")


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
        self.assertIn('strategy:"상황·담보"', ADCOPY)
        self.assertIn('strategy:"간편 전환"', ADCOPY)
        self.assertIn('strategy:"담보 묶음"', ADCOPY)
        self.assertIn("SA 소재 제안", ADCOPY)
        self.assertIn('const OUT_OF_SCOPE_VOLUME=["자동차보험","자동차 보험","한화생명"]', ADCOPY)
        self.assertNotIn("공개 광고 관측", ADCOPY)
        self.assertNotIn("공개 SERP 관측", ADCOPY)
        self.assertIn("경쟁사 구조 활용", ADCOPY)
        self.assertNotIn("data-copy", ADCOPY)
        self.assertNotIn("navigator.clipboard", ADCOPY)

    def test_sa_uses_attached_review_draft_structure_without_manual_editor(self):
        self.assertIn("const REVIEW_REFERENCE", ADCOPY)
        self.assertIn("20260730 한화CM 검색광고 운전자보험 심의안", ADCOPY)
        self.assertIn("실제 포맷 심의안 초안", ADCOPY)
        for label in ("1. 썸네일 이미지", "2. 광고 제목", "3. 추가제목 (롤링)",
                      "4. 설명 (롤링)", "5. 홍보문구 (택 1)", "6. 서브링크 (택 4)",
                      "7. 이미지형 서브링크"):
            self.assertIn(label, ADCOPY)
        self.assertNotIn('id="edT"', ADCOPY)
        self.assertNotIn('id="edD"', ADCOPY)

    def test_power_content_is_a_separate_guarded_workspace(self):
        self.assertNotIn('__power', ADCOPY)
        self.assertNotIn("powercontent-title-opportunities.json", ADCOPY)
        self.assertIn("파워콘텐츠 소재", POWER)
        self.assertIn("const POWER_SPEC=MATERIAL_SPEC.powerContent", POWER)
        self.assertIn("data/adcopy/powercontent-title-opportunities.json", POWER)
        self.assertNotIn("GSC", POWER)
        self.assertNotIn("gscLabel", POWER)
        self.assertNotIn("candidate-weak", POWER)
        self.assertIn("1. 블로그 포스팅 소재", POWER)
        self.assertIn("2. 광고 소재 등록 초안", POWER)
        self.assertIn("설명은 랜딩 원문 연속 문장만 사용", POWER)
        for removed in ("추가제목", "홍보문구", "서브링크", "FAQ 후보", "선택 포스팅 소재", "검색 의도", "상품 소구"):
            self.assertNotIn(removed, POWER)
        self.assertNotIn("data-copy", POWER)

    def test_sa_and_power_content_share_material_review_rules(self):
        self.assertIn('shared/naver-material-specs.js', ADCOPY)
        self.assertIn('shared/naver-material-specs.js', POWER)
        self.assertIn('shared/insurance-ad-review.js', ADCOPY)
        self.assertIn('shared/insurance-ad-review.js', POWER)
        self.assertIn('additionalDescription', ADCOPY)
        self.assertIn('description: freeze({ minLength: 80, maxLength: 110, source: "landing_continuous_excerpt" })', MATERIAL_SPECS)
        self.assertIn('maxPerAdGroup: 5', MATERIAL_SPECS)
        self.assertIn('maxLength: 14, maxPerGroup: 2', MATERIAL_SPECS)
        self.assertIn('minPerAd: 3, maxPerAd: 4, maxPerSite: 4', MATERIAL_SPECS)
        self.assertIn('서브링크 URL 1~4', MATERIAL_GUIDE)
        self.assertIn('node --check shared/naver-material-specs.js', CI)
        self.assertIn('node --check shared/insurance-ad-review.js', CI)

    def test_insurance_ad_review_uses_current_public_basis_and_human_gate(self):
        self.assertIn("금융소비자보호법 제22조", AD_REVIEW)
        self.assertIn("금융소비자보호법 시행령 제18조~제19조", AD_REVIEW)
        self.assertIn("금융소비자보호법 시행령 제20조", AD_REVIEW)
        self.assertIn("금융소비자 보호에 관한 감독규정 제17조~제19조", AD_REVIEW)
        self.assertIn("손해보험협회 광고심의 관리시스템", AD_REVIEW)
        self.assertIn("자동 사전검수 결과이며", AD_REVIEW)
        self.assertIn("reviewPowerMaterial", POWER)
        self.assertIn("AD_REVIEW.reviewFields", ADCOPY)
        self.assertIn("references/regulatory-basis.md", REVIEW_SKILL)
        self.assertIn("자동 위험표현 없음", REVIEW_SKILL)
        self.assertNotIn("심의 통과 리스크", REVIEW_SKILL)
        self.assertIn("확인일: 2026-08-25", REGULATORY_BASIS)
        self.assertIn("법령에 수록된 공식 금칙어 목록이 아니다", REGULATORY_BASIS)
        self.assertIn("node scripts/check_insurance_ad_review.mjs", CI)

    def test_urls_and_asset_ids_are_manual_only(self):
        for field in (
            "calculationUrl",
            "powerLinkImageId",
            "sublinkUrl1",
            "sublinkImageId1",
        ):
            self.assertIn(field, ADCOPY)
            self.assertIn(field, MATERIAL_SPECS)
        self.assertIn('MATERIAL_SPEC.manualOnlyFields.forEach', ADCOPY)
        self.assertNotIn('MATERIAL_SPEC.manualOnlyFields.forEach', POWER)

    def test_power_content_rejects_out_of_scope_topics_and_exports_brief(self):
        for term in ("자동차보험", "공개관측", "공개 관측", "한화생명", "고객센터"):
            self.assertIn(term, POWER)
        self.assertIn("function inScope(p,text)", POWER)
        self.assertIn("function exportCsv()", POWER)
        self.assertIn('id="exportCsv"', POWER)
        self.assertIn("등록 초안 CSV", POWER)

    def test_copy_candidates_use_shared_korean_humanizer(self):
        self.assertIn('shared/humanize-ko.js', ADCOPY)
        self.assertIn('dw(HUMANIZE.light(x))', ADCOPY)
        self.assertIn('node --check shared/humanize-ko.js', CI)


if __name__ == "__main__":
    unittest.main()
