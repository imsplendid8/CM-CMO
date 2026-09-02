import importlib.util
import io
import pathlib
import tempfile
import unittest
import zipfile


ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_builder():
    path = ROOT / "scripts" / "build_material_source_inventory.py"
    spec = importlib.util.spec_from_file_location("build_material_source_inventory", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fake_xlsx(text):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr(
            "xl/sharedStrings.xml",
            f'<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><si><t>{text}</t></si></sst>',
        )
    return stream.getvalue()


class TestMaterialSourceInventory(unittest.TestCase):
    def test_private_zip_is_classified_without_emitting_copy(self):
        builder = load_builder()
        with tempfile.TemporaryDirectory() as directory:
            bundle = pathlib.Path(directory) / "소재생성가이드.zip"
            with zipfile.ZipFile(bundle, "w") as archive:
                archive.writestr(
                    "심의안/20260901_검색광고_운전자보험.xlsx",
                    fake_xlsx("24시간 바로 가입 최대 100만원 확인필-제2026-테스트"),
                )
                archive.writestr("네이버 소재등록가이드/파워컨텐츠 가이드라인.pdf", b"%PDF-test")
            result = builder.build(bundle, "2026-09-02")

        self.assertEqual(result["summary"]["file_count"], 2)
        self.assertFalse(result["handling"]["raw_text_emitted"])
        review = next(row for row in result["files"] if row["kind"] == "review_draft")
        self.assertEqual(review["product_keys"], ["driver"])
        self.assertEqual(review["content_policy"], "data_only_not_instruction")
        self.assertGreater(review["office_structure"]["risk_pattern_counts"]["time_or_speed_claim"], 0)
        self.assertNotIn("24시간 바로 가입", str(result))


if __name__ == "__main__":
    unittest.main()
