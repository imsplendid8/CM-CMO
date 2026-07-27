#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""자동화(수집) 상태 점검 — 각 산출물 파일의 '실제 최신성'을 매번 다시 계산.

왜:
  데일리 브리프가 저장된 요약(예: automation_health.json)만 믿으면, 그 요약 파일이
  오래됐을 때 실제로 stale인 수집도 '정상'으로 오표시될 수 있다. 그래서 이 모듈은
  **저장된 요약을 신뢰하지 않고**, 각 자동화가 커밋하는 산출물 파일 안의 시각 필드로
  healthy / stale / missing / unknown 을 직접 판정한다.

설계:
  - `compute_health()`는 순수 함수. 파일을 **읽기만** 하며 어떤 추적 파일도 쓰지 않는다.
  - 판정은 git 이력이 아니라 산출물 내부의 날짜 필드(asof/updated)로 한다(결정론적·재현 가능).
  - 시각을 읽을 수 없으면(파일 없음/필드 없음/파싱 실패) 절대 healthy 로 처리하지 않는다.
  - 상위 수준에서 소스를 전혀 읽을 수 없으면 ok=False → 브리프는 '상태 확인 불가'로 표시.

표준 라이브러리만 사용.
"""
import json
import os
import sys
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KST = timezone(timedelta(hours=9))

# (표시명, 산출물 경로(레포 루트 기준), 시각 필드, 허용 기간[일])
#   허용 기간 = 각 자동화 cron 주기 + 여유(예: 일간=2, 주간=9, 월간=35)
AUTOMATIONS = [
    ("뉴스 클리핑",     "data/clips/index.json", "updated", 2),   # news-clip: 하루 2회
    ("수요 신호",       "data/signals.json",     "asof",    2),   # signals: 매일
    ("실측 검색량",     "data/volume.json",      "asof",    9),   # searchad: 주간
    ("데이터랩 트렌드", "data/trends.json",      "asof",    35),  # trends: 월간
    ("논문 아카이브",   "data/papers.json",      "updated", 35),  # papers: 월간
    ("SERP 캡쳐",       "serp/manifest.json",    "asof",    9),   # serp-capture: 주간
]

STATES = ("healthy", "stale", "missing", "unknown")


def kst_now():
    return datetime.now(timezone.utc).astimezone(KST)


def _parse_date(value):
    """'2026-07-27' 또는 '2026-07-27 15:55' 앞 10자를 날짜로 파싱. 실패 시 None."""
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value.strip()[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _check_one(base_dir, name, rel, field, max_age, today):
    path = os.path.join(base_dir, rel)
    item = {"name": name, "file": rel, "state": "unknown",
            "date": None, "age_days": None, "max_age": max_age}
    if not os.path.exists(path):
        item["state"] = "missing"
        return item
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        item["state"] = "unknown"          # 읽기/파싱 실패 → 정상으로 단정하지 않음
        return item
    d = _parse_date(data.get(field))
    if d is None:
        item["state"] = "unknown"          # 시각 필드 없음/불명 → 정상 아님
        return item
    age = (today - d).days
    if age < 0:
        age = 0
    item["date"] = d.isoformat()
    item["age_days"] = age
    item["state"] = "healthy" if age <= max_age else "stale"
    return item


def _summarize(items):
    counts = {s: 0 for s in STATES}
    for it in items:
        counts[it["state"]] = counts.get(it["state"], 0) + 1
    return counts


def compute_health(now=None, base_dir=ROOT, automations=AUTOMATIONS):
    """자동화 상태를 지금 시점 기준으로 새로 계산. 읽기 전용.

    반환: {"ok": bool, "asof": "YYYY-MM-DD HH:MM", "items": [...], "summary": {...}}
      ok=False 는 소스를 전혀 읽을 수 없어 상태를 단정할 수 없는 경우.
    """
    now = now or kst_now()
    asof = now.strftime("%Y-%m-%d %H:%M")
    try:
        # 소스가 놓이는 data 디렉터리를 아예 읽을 수 없으면 상태 확인 불가로 본다.
        if not os.path.isdir(os.path.join(base_dir, "data")):
            return {"ok": False, "asof": asof, "reason": "data 디렉터리를 읽을 수 없음"}
        today = now.date()
        items = [_check_one(base_dir, n, rel, field, max_age, today)
                 for (n, rel, field, max_age) in automations]
        return {"ok": True, "asof": asof, "items": items, "summary": _summarize(items)}
    except Exception as e:  # noqa: BLE001 - 어떤 이유로든 계산 실패 시 정상 오표시 금지
        return {"ok": False, "asof": asof, "reason": str(e)[:120]}


def format_lines(health):
    """브리프에 넣을 '[데이터 상태]' 텍스트 라인들."""
    if not health.get("ok"):
        return ["[데이터 상태]", "· 상태 확인 불가",
                "· 자동수집이 정상이라고 단정할 수 없음"]
    s = health["summary"]
    items = health["items"]
    stale = [it["name"] for it in items if it["state"] == "stale"]
    na = [it["name"] for it in items if it["state"] in ("missing", "unknown")]
    lines = ["[데이터 상태]", f"· 정상 {s['healthy']}건"]
    lines.append(f"· 갱신 필요 {s['stale']}건" + (f": {', '.join(stale)}" if stale else ""))
    lines.append(f"· 누락/확인 불가 {s['missing'] + s['unknown']}건"
                 + (f": {', '.join(na)}" if na else ""))
    lines.append(f"· 기준 시각: {health['asof']} KST")
    return lines


if __name__ == "__main__":
    h = compute_health()
    if "--json" in sys.argv:
        print(json.dumps(h, ensure_ascii=False, indent=1))
    else:
        print("\n".join(format_lines(h)))
