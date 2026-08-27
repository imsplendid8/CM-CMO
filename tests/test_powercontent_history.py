import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def module():
    path = ROOT / "scripts" / "powercontent_history.py"
    spec = importlib.util.spec_from_file_location("powercontent_history", path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


class TestPowerContentHistory(unittest.TestCase):
    def test_repository_history_is_minimal_deduplicated_and_excludes_home_tm(self):
        payload = json.loads((ROOT / "data/adcopy/powercontent-history.json").read_text(encoding="utf-8"))
        entries = payload["entries"]
        self.assertTrue(entries)
        self.assertEqual(len({row["fingerprint"] for row in entries}), len(entries))
        self.assertNotIn("home", {row["product_key"] for row in entries})
        self.assertFalse(any("텔레마케팅" in json.dumps(row, ensure_ascii=False) for row in entries))
        for private in ("page", "clicks", "impressions", "ctr", "position"):
            self.assertFalse(any(private in row for row in entries))

    def test_archive_is_idempotent(self):
        agent = module()
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            for relative, _ in agent.SOURCE_FILES:
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text((ROOT / relative).read_text(encoding="utf-8"), encoding="utf-8")
            output = root / "data/adcopy/powercontent-history.json"
            first = agent.archive(root=root, output=output)
            second = agent.archive(root=root, output=output)
            self.assertEqual(first["entries"], second["entries"])


if __name__ == "__main__":
    unittest.main()
