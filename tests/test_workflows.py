#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GitHub Actions 워크플로 정적 회귀 테스트 (P0-2).

검사:
  - 모든 워크플로 YAML 파싱
  - cron 5필드 형식
  - 커밋(push)하는 워크플로끼리 같은 UTC 분에 겹치는 cron이 없음(동시 write 방지)
  - 커밋 워크플로는 모두 동일 concurrency 그룹(cm-cmo-data-writers)을 가짐
  - 읽기 전용 알림/상태 점검은 커밋 레인과 분리해 지연을 전파하지 않음
  - 모든 워크플로에 workflow_dispatch 유지(수동 복구)
  - workflow_run 대상 워크플로 name 이 실제로 존재
표준 라이브러리 + PyYAML.
"""
import glob
import os
import unittest

try:
    import yaml
except ImportError:          # PyYAML 없으면 정적 테스트 skip(로컬), CI는 pyyaml 설치 후 실행
    yaml = None

WF_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      ".github", "workflows")
SHARED_GROUP = "cm-cmo-data-writers"
READ_ONLY_GROUPS = {
    "daily-brief.yml": "cm-cmo-brief-telegram",
    "daily-email.yml": "cm-cmo-brief-email",
    "automation-status.yml": "cm-cmo-automation-status",
}


def _load_all():
    out = {}
    for p in sorted(glob.glob(os.path.join(WF_DIR, "*.yml"))):
        with open(p, encoding="utf-8") as f:
            out[os.path.basename(p)] = yaml.safe_load(f)
    return out


def _on(wf):
    # YAML 1.1에서 'on' 은 boolean True 로 파싱될 수 있어 두 키 모두 확인
    v = wf.get("on", wf.get(True, {}))
    return v or {}


def _crons(wf):
    sched = _on(wf).get("schedule") or []
    return [e["cron"] for e in sched if isinstance(e, dict) and "cron" in e]


def _has_dispatch(wf):
    on = _on(wf)
    return isinstance(on, dict) and "workflow_dispatch" in on


def _pushes(wf):
    for job in (wf.get("jobs") or {}).values():
        for step in (job.get("steps") or []):
            if "git push" in str(step.get("run", "")):
                return True
    return False


def _cron_fields(expr):
    parts = expr.split()
    return parts if len(parts) == 5 else None


def _day_overlap(a, b):
    # a,b: cron 필드 리스트. 같은 분·시일 때 요일/일이 겹칠 수 있는지(보수적).
    def match(fa, fb):
        return fa == "*" or fb == "*" or set(fa.split(",")) & set(fb.split(","))
    return bool(match(a[2], b[2]) and match(a[4], b[4]))   # dom, dow


def _same_instant(a, b):
    return a[0] == b[0] and a[1] == b[1] and _day_overlap(a, b)


@unittest.skipUnless(yaml is not None, "PyYAML 미설치 — 워크플로 정적 테스트 skip")
class TestWorkflows(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wfs = _load_all()

    def test_all_yaml_parses(self):
        self.assertTrue(self.wfs, "워크플로 파일을 찾지 못함")
        for name, wf in self.wfs.items():
            self.assertIsInstance(wf, dict, f"{name} 파싱 실패")

    def test_cron_has_five_fields(self):
        for name, wf in self.wfs.items():
            for c in _crons(wf):
                self.assertIsNotNone(_cron_fields(c), f"{name}: cron 5필드 아님 → {c!r}")

    def test_committing_workflows_have_shared_concurrency(self):
        for name, wf in self.wfs.items():
            if not _pushes(wf):
                continue
            conc = wf.get("concurrency")
            self.assertIsInstance(conc, dict, f"{name}: 커밋 워크플로에 concurrency 없음")
            self.assertEqual(conc.get("group"), SHARED_GROUP,
                             f"{name}: concurrency.group 이 공유 레인({SHARED_GROUP}) 아님 → {conc.get('group')!r}")

    def test_read_only_notifications_do_not_share_writer_lane(self):
        for name, expected in READ_ONLY_GROUPS.items():
            wf = self.wfs.get(name)
            self.assertIsNotNone(wf, f"{name}: 읽기 전용 워크플로가 없음")
            self.assertEqual((wf.get("concurrency") or {}).get("group"), expected,
                             f"{name}: 알림/상태 점검이 writer 레인을 공유함")
            self.assertNotEqual(expected, SHARED_GROUP)

    def test_notification_schedule_contract(self):
        telegram = self.wfs.get("daily-brief.yml")
        email = self.wfs.get("daily-email.yml")
        self.assertEqual(_crons(telegram), ["0 23 * * *", "0 5 * * *"])
        self.assertEqual(_crons(email), ["30 23 * * *"])

    def test_no_two_writers_share_same_instant_cron(self):
        writers = []
        for name, wf in self.wfs.items():
            if _pushes(wf):
                for c in _crons(wf):
                    fields = _cron_fields(c)
                    if fields:
                        writers.append((name, c, fields))
        for i in range(len(writers)):
            for j in range(i + 1, len(writers)):
                (na, ca, fa), (nb, cb, fb) = writers[i], writers[j]
                if na == nb:
                    continue
                self.assertFalse(
                    _same_instant(fa, fb),
                    f"동시 write 위험: {na}({ca}) 와 {nb}({cb}) 가 같은 UTC 분에 겹침")

    def test_scheduled_workflows_keep_dispatch(self):
        for name, wf in self.wfs.items():
            if _crons(wf):   # 스케줄이 있는 워크플로
                self.assertTrue(_has_dispatch(wf),
                                f"{name}: workflow_dispatch(수동 복구) 누락")

    def test_event_reco_workflow_regenerates_and_commits(self):
        wf = self.wfs.get("event-reco.yml")
        self.assertIsNotNone(wf, "event-reco.yml 워크플로가 없음")
        runs = " ".join(str(s.get("run", ""))
                        for job in (wf.get("jobs") or {}).values()
                        for s in (job.get("steps") or []))
        self.assertIn("scripts/event_engine.py", runs, "엔진 재생성 스텝 누락")
        self.assertIn("data/events/recommendations.json", runs, "추천 커밋 누락")
        self.assertIn("data/events/state_history.json", runs, "상태 저널 커밋 누락")
        self.assertEqual((wf.get("concurrency") or {}).get("group"), SHARED_GROUP)

    def test_pages_redeploys_after_committing_workflows(self):
        # 봇 커밋은 GITHUB_TOKEN push라 on:push를 못 트리거 → pages는 workflow_run으로 재배포해야 함
        pages = self.wfs.get("pages.yml")
        self.assertIsNotNone(pages, "pages.yml 없음")
        wr = _on(pages).get("workflow_run") or {}
        targets = set(wr.get("workflows") or [])
        self.assertIn("Event Recommendations", targets, "pages가 추천 재생성 후 재배포하지 않음")
        # 커밋(push)하는 워크플로는 모두 pages workflow_run 대상에 포함(사이트 신선도)
        for name, wf in self.wfs.items():
            if _pushes(wf):
                self.assertIn(wf.get("name"), targets,
                              f"{name}: 커밋 워크플로가 pages workflow_run 대상에 없음 → 배포 stale")
        guard = str(pages.get("jobs", {}).get("deploy", {}).get("if", ""))
        self.assertIn("workflow_run", guard, "실패한 커밋 실행으로 재배포 방지 가드 누락")

    def test_workflow_run_targets_exist(self):
        names = {wf.get("name") for wf in self.wfs.values()}
        for fname, wf in self.wfs.items():
            wr = _on(wf).get("workflow_run")
            if not wr:
                continue
            for target in (wr.get("workflows") or []):
                self.assertIn(target, names,
                              f"{fname}: workflow_run 대상 '{target}' 이 실제 name 에 없음")


if __name__ == "__main__":
    unittest.main(verbosity=2)
