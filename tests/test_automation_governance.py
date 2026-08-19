import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class TestAutomationGovernance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.guide = (ROOT / "docs" / "guarded-automation-loops.md").read_text(
            encoding="utf-8"
        )

    def test_wiki_links_the_guarded_automation_guide(self):
        index = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
        self.assertIn("guarded-automation-loops.md", index)

    def test_guide_is_proposal_not_implementation_claim(self):
        self.assertIn("문서 상태: **제안**", self.guide)
        self.assertIn("구현 완료 목록이 아니라", self.guide)

    def test_recovery_retry_is_bounded_and_truthful(self):
        self.assertIn("자동 재시도는 1회까지만", self.guide)
        self.assertIn("실패를 정상으로 바꾸", self.guide)
        self.assertIn("동일 알림을 중복 생성하지 않는다", self.guide)

    def test_human_approval_boundaries_remain_explicit(self):
        for phrase in (
            "최종 채택은 사람 승인",
            "보험 광고심의 최종 승인",
            "자동 입찰",
            "실제 광고계정 업로드",
            "기준 이미지는 사람이 승인한 경우에만 변경",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.guide)


if __name__ == "__main__":
    unittest.main()
