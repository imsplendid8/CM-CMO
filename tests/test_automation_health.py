#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_automation_health 순수 함수 테스트 (표준 라이브러리 unittest).

실행: python3 -m unittest tests.test_automation_health   (레포 루트에서)
      또는  python3 tests/test_automation_health.py
"""
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime

SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
sys.path.insert(0, SCRIPTS)
import check_automation_health as cah  # noqa: E402

NOW = datetime(2026, 7, 27, 8, 0)          # 고정 기준 시각(결정론)
FIELD = {rel: field for (_n, rel, field, _m) in cah.AUTOMATIONS}


def make_repo(tmp, overrides=None, omit=(), garbage=()):
    """가짜 레포 디렉터리 생성. 기본은 모든 산출물이 '오늘'(2026-07-27) 최신.
    overrides={rel: 'YYYY-MM-DD'} 로 특정 파일 날짜 지정,
    omit=(rel,...) 은 파일 자체 생략(missing), garbage=(rel,...) 은 시각 필드 없는 파일.
    """
    overrides = overrides or {}
    os.makedirs(os.path.join(tmp, "data"), exist_ok=True)
    for _n, rel, field, _m in cah.AUTOMATIONS:
        if rel in omit:
            continue
        path = os.path.join(tmp, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if rel in garbage:
            payload = {"note": "시각 필드 없음"}
        else:
            payload = {field: overrides.get(rel, "2026-07-27")}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
    return tmp


def snapshot(root):
    """디렉터리 내 파일 경로+크기+mtime 스냅샷(쓰기 여부 검증용)."""
    out = {}
    for dp, _dn, fns in os.walk(root):
        for fn in fns:
            p = os.path.join(dp, fn)
            st = os.stat(p)
            out[os.path.relpath(p, root)] = (st.st_size, st.st_mtime_ns)
    return out


class TestAutomationHealth(unittest.TestCase):
    def test_all_healthy(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_repo(tmp)
            h = cah.compute_health(NOW, base_dir=tmp)
            self.assertTrue(h["ok"])
            self.assertEqual(h["summary"]["healthy"], len(cah.AUTOMATIONS))
            self.assertEqual(h["summary"]["stale"], 0)
            self.assertEqual(h["summary"]["missing"], 0)
            self.assertEqual(h["summary"]["unknown"], 0)

    def test_stale_when_over_allowed_age(self):
        with tempfile.TemporaryDirectory() as tmp:
            # 뉴스 클리핑 허용 2일 → 2026-07-10 은 stale
            make_repo(tmp, overrides={"data/clips/index.json": "2026-07-10"})
            h = cah.compute_health(NOW, base_dir=tmp)
            states = {it["name"]: it["state"] for it in h["items"]}
            self.assertEqual(states["뉴스 클리핑"], "stale")
            self.assertEqual(h["summary"]["stale"], 1)
            self.assertEqual(h["summary"]["healthy"], len(cah.AUTOMATIONS) - 1)

    def test_missing_source_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_repo(tmp, omit=("data/signals.json",))
            h = cah.compute_health(NOW, base_dir=tmp)
            states = {it["name"]: it["state"] for it in h["items"]}
            self.assertEqual(states["수요 신호"], "missing")
            self.assertEqual(h["summary"]["missing"], 1)

    def test_no_false_healthy_when_timestamp_unreadable(self):
        # 시각을 확인할 수 없으면(필드 없음) 절대 healthy 로 처리하지 않는다.
        with tempfile.TemporaryDirectory() as tmp:
            make_repo(tmp, garbage=("data/volume.json",))
            h = cah.compute_health(NOW, base_dir=tmp)
            states = {it["name"]: it["state"] for it in h["items"]}
            self.assertEqual(states["실측 검색량"], "unknown")
            self.assertNotEqual(states["실측 검색량"], "healthy")

    def test_stale_health_json_does_not_force_all_ok(self):
        # 오래된 automation_health.json(모두 정상 주장)이 있어도 무시되고,
        # 실제 소스(일부 stale/missing) 기준으로 계산돼 '정상 6건'이 뜨지 않는다.
        with tempfile.TemporaryDirectory() as tmp:
            make_repo(tmp, overrides={"data/signals.json": "2026-01-01"},
                      omit=("data/trends.json",))
            with open(os.path.join(tmp, "data", "automation_health.json"), "w", encoding="utf-8") as f:
                json.dump({"summary": {"healthy": 6, "stale": 0, "missing": 0},
                           "note": "오래된 요약(모두 정상)"}, f, ensure_ascii=False)
            h = cah.compute_health(NOW, base_dir=tmp)
            text = "\n".join(cah.format_lines(h))
            self.assertNotIn("정상 6건", text)
            self.assertNotIn("6종 정상", text)
            self.assertLess(h["summary"]["healthy"], len(cah.AUTOMATIONS))
            self.assertGreaterEqual(h["summary"]["stale"] + h["summary"]["missing"], 1)

    def test_read_only_no_tracked_file_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_repo(tmp)
            before = snapshot(tmp)
            cah.compute_health(NOW, base_dir=tmp)
            cah.format_lines(cah.compute_health(NOW, base_dir=tmp))
            after = snapshot(tmp)
            self.assertEqual(before, after)                       # 어떤 파일도 변경 안 됨
            self.assertFalse(os.path.exists(os.path.join(tmp, "data", "automation_health.json")))

    def test_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_repo(tmp, overrides={"data/clips/index.json": "2026-07-10"})
            a = cah.compute_health(NOW, base_dir=tmp)
            b = cah.compute_health(NOW, base_dir=tmp)
            self.assertEqual(a, b)

    def test_unavailable_when_sources_unreadable(self):
        # data 디렉터리가 없으면 '정상'이 아니라 '상태 확인 불가'.
        with tempfile.TemporaryDirectory() as tmp:
            h = cah.compute_health(NOW, base_dir=tmp)
            self.assertFalse(h["ok"])
            text = "\n".join(cah.format_lines(h))
            self.assertIn("상태 확인 불가", text)
            self.assertNotIn("정상", text.split("상태 확인 불가")[0] if "상태 확인 불가" in text else text)

    def test_future_date_not_healthy(self):
        # 미래 날짜는 신뢰 불가 → healthy 로 오인하지 않는다(unknown).
        with tempfile.TemporaryDirectory() as tmp:
            make_repo(tmp, overrides={"data/signals.json": "2026-12-31"})
            h = cah.compute_health(NOW, base_dir=tmp)
            states = {it["name"]: it["state"] for it in h["items"]}
            self.assertEqual(states["수요 신호"], "unknown")
            self.assertNotEqual(states["수요 신호"], "healthy")

    def test_bad_date_string_is_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_repo(tmp, overrides={"data/papers.json": "어제쯤"})
            h = cah.compute_health(NOW, base_dir=tmp)
            states = {it["name"]: it["state"] for it in h["items"]}
            self.assertEqual(states["논문 아카이브"], "unknown")

    def test_timezone_and_iso_formats_no_exception(self):
        # tz 없는 날짜 / Z(UTC) / 오프셋 / 날짜+시각이 섞여도 예외 없이 날짜로 인식.
        with tempfile.TemporaryDirectory() as tmp:
            make_repo(tmp, overrides={
                "data/clips/index.json": "2026-07-27",              # tz 없음
                "data/signals.json":     "2026-07-27T00:00:00Z",    # Z(UTC)
                "data/volume.json":      "2026-07-27 15:55",        # 날짜+시각(공백)
                "data/trends.json":      "2026-07-27T09:00:00+09:00",  # KST 오프셋
            })
            h = cah.compute_health(NOW, base_dir=tmp)   # 예외 없이 완료
            self.assertTrue(h["ok"])
            states = {it["name"]: it["state"] for it in h["items"]}
            for nm in ("뉴스 클리핑", "수요 신호", "실측 검색량", "데이터랩 트렌드"):
                self.assertEqual(states[nm], "healthy")

    def test_missing_and_unknown_distinguished_in_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_repo(tmp, omit=("data/signals.json",),          # missing
                      garbage=("data/volume.json",))             # unknown
            text = "\n".join(cah.format_lines(cah.compute_health(NOW, base_dir=tmp)))
            self.assertIn("누락 1건: 수요 신호", text)
            self.assertIn("확인 불가 1건: 실측 검색량", text)

    def test_partial_failure_mix(self):
        # 일부만 실패해도 나머지는 정상 계산, ok=True, 합계 일치.
        with tempfile.TemporaryDirectory() as tmp:
            make_repo(tmp, omit=("data/trends.json",),
                      overrides={"data/clips/index.json": "2026-07-01"})  # stale
            h = cah.compute_health(NOW, base_dir=tmp)
            self.assertTrue(h["ok"])
            s = h["summary"]
            self.assertEqual(s["missing"], 1)
            self.assertEqual(s["stale"], 1)
            self.assertEqual(sum(s.values()), len(cah.AUTOMATIONS))

    def test_papers_json_refreshed_on_noop(self):
        # 신규 논문 0건(성공적 no-op)이어도 papers.json 의 updated 가 오늘로 갱신돼야
        # 자동화 상태가 계속 노화(stale)되지 않는다. (Codex 리뷰 P2 대응)
        import importlib
        from datetime import timezone as _tz, timedelta as _td
        fp = importlib.import_module("fetch_papers")
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "data"), exist_ok=True)
            data = fp.sync_papers_json(root=tmp)     # no-op 경로가 호출하는 바로 그 함수
            self.assertIsNotNone(data)
            out = os.path.join(tmp, "data", "papers.json")
            self.assertTrue(os.path.exists(out))
            with open(out, encoding="utf-8") as f:
                j = json.load(f)
            today = datetime.now(_tz(_td(hours=9))).strftime("%Y-%m-%d")
            self.assertEqual(j["updated"], today)

    def test_daily_brief_builds_even_if_health_fails(self):
        # 상태 계산이 예외를 던져도 브리프 메시지는 생성되고 '상태 확인 불가'가 표시된다.
        import importlib
        db = importlib.import_module("daily_brief")
        orig = cah.compute_health
        try:
            cah.compute_health = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
            msg = db.build_message()
            self.assertIsInstance(msg, str)
            self.assertIn("상태 확인 불가", msg)
        finally:
            cah.compute_health = orig


if __name__ == "__main__":
    unittest.main(verbosity=2)
