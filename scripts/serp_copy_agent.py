#!/usr/bin/env python3
"""월간 SERP 관측을 SA·이미지·파워콘텐츠의 공통 소재 기획안으로 변환한다.

경쟁사 원문은 화면의 비교 근거로만 남긴다. 자동 제안에는 검색 의도, 반복 패턴,
상품 마스터의 범위, 아직 덜 쓰인 각도만 전달해 경쟁사 문구를 그대로 복제하지 않는다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

try:
    from scripts.io_utils import atomic_json_write
except ModuleNotFoundError:  # python scripts/serp_copy_agent.py
    from io_utils import atomic_json_write

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/adcopy/serp-candidates.json"
FEEDBACK_RULES = "data/adcopy/material-feedback-rules.json"
WINDOW_DAYS = 35

SCENES = {
    "home": ["책상 위 보험료 계산기와 여러 보험종목 오브젝트", "모바일로 상품을 비교하는 생활 장면", "운전·주택·건강·여행을 한 화면에 모은 미니어처"],
    "hrmf": ["아파트 주방 천장 누수를 발견한 가족", "거실에서 작은 화재 위험을 점검하는 가족", "태풍 전 창문과 집 안을 살피는 생활 장면"],
    "golf": ["그린 위 홀인원 순간을 기뻐하는 골퍼", "라운드 전 골프백과 장비를 확인하는 골퍼", "동반자들과 티오프를 준비하는 장면"],
    "cncr": ["건강검진 결과를 차분히 확인하는 성인", "병원 상담실에서 치료 계획을 듣는 장면", "가족과 일상을 이어가는 회복 중심 장면"],
    "dntl": ["치과 상담실에서 치아 모형을 보는 환자", "정기검진을 받는 편안한 치과 장면", "식사 중 치아 불편을 느끼고 확인하는 생활 장면"],
    "driver": ["야간 교차로에서 방어운전하는 운전자", "스쿨존 앞에서 속도를 줄이는 차량", "접촉사고 뒤 안전하게 현장을 확인하는 운전자"],
    "woman": ["건강검진 일정을 확인하는 여성", "일상에서 건강을 챙기는 여성과 가족", "진료 상담을 앞두고 차분히 준비하는 장면"],
    "birth": ["아기방을 준비하는 예비 부모", "산모수첩과 초음파 사진을 확인하는 부부", "신생아 용품을 정리하는 따뜻한 가족 장면"],
    "overseas": ["공항 출국장 앞에서 여권과 짐을 확인하는 여행자", "항공 지연 안내판을 확인하는 여행자", "여행지에서 휴대품을 챙기는 생활 장면"],
    "overseaslong": ["해외 캠퍼스에 도착한 유학생", "장기 체류용 짐과 서류를 준비하는 학생", "기숙사에서 새 생활을 시작하는 유학생"],
    "holeinone": ["홀인원 직후 동반자들과 기뻐하는 골퍼", "깃대와 공이 함께 보이는 그린 클로즈업", "라운드 전 스코어카드와 장비를 챙기는 장면"],
    "event": ["공연 시작 전 무대와 관객 동선을 점검하는 스태프", "체육행사 현장에서 안전 펜스를 확인하는 운영자", "야외행사 전 시설을 살피는 안전관리 장면"],
    "chronic": ["복용약과 건강기록을 정리하는 성인", "건강상담 전 체크리스트를 확인하는 장면", "일상 속 혈압·건강 상태를 편안하게 확인하는 장면"],
}

# 월간 썸네일은 한 장을 네 번 크롭하지 않는다. 저장소에 있는 무문자 3D 애니메이션
# 원본을 상품별 후보군으로 묶고, 기준월마다 서로 다른 4장을 순환 선정한다.
ASSET_SCENES = {
    "calculator-animation-v3.png": "보험료와 가입 항목을 확인하는 계산기 오브젝트",
    "dental-consult-3d.png": "치과 상담실에서 치료 계획을 확인하는 장면",
    "dental-consult-animation-v3.png": "치아 모형을 보며 상담하는 장면",
    "dental-model-animation-v1.png": "치아 모형과 빈 상담 카드를 놓고 치료 항목을 확인하는 장면",
    "driver-safe-animation-v3.png": "도심 도로에서 안전운전하는 운전자",
    "driver-traffic-3d.png": "교차로 신호와 앞차를 확인하는 운전자",
    "driver-schoolzone-animation-v4.png": "스쿨존 횡단보도 앞에서 감속하는 운전자",
    "driver-accident-animation-v4.png": "가벼운 접촉사고 뒤 현장을 확인하는 운전자",
    "driver-rain-animation-v4.png": "비 오는 저녁 도로에서 방어운전하는 운전자",
    "event-safety-3d.png": "행사 현장의 시설과 동선을 확인하는 운영자",
    "event-safety-animation-v3.png": "공연 시작 전 안전을 점검하는 스태프",
    "event-venue-flow-animation-v1.png": "행사장 동선과 안전 구역을 사전에 점검하는 장면",
    "cancer-consult-animation-v1.png": "암보험 상담 전 건강자료와 빈 기록지를 차분히 확인하는 장면",
    "chronic-health-record-animation-v1.png": "복용약과 건강기록을 함께 정리하는 장면",
    "woman-health-planner-animation-v1.png": "여성 건강관리 일정을 빈 플래너로 정리하는 장면",
    "woman-clinic-lounge-animation-v1.png": "여성 건강 상담 전 빈 폴더를 들고 대기하는 장면",
    "woman-wellness-desk-animation-v1.png": "여성 건강 상담 전 노트와 생활용품을 정돈하는 장면",
    "golf-checklist-animation-v1.png": "라운드 전 장비와 빈 체크카드를 확인하는 장면",
    "family-baby-animation-v3.png": "아기와 가족이 함께 건강을 준비하는 장면",
    "family-pregnancy-3d.png": "예비 부모가 출산 준비물을 확인하는 장면",
    "birth-nursery-prep-animation-v1.png": "아기방과 출산 준비물을 정리하는 장면",
    "birth-planner-animation-v1.png": "빈 산모 플래너와 아기용품을 함께 확인하는 장면",
    "golf-hole-animation-v3.png": "그린 위 홀인원 순간을 기뻐하는 골퍼",
    "golf-holeinone-3d.png": "깃대와 공이 보이는 홀인원 장면",
    "golf-tee-bag-animation-v1.png": "티박스에서 골프백과 클럽을 준비하는 장면",
    "health-check-animation-v3.png": "일상에서 건강 상태를 확인하는 성인",
    "health-review-3d.png": "건강검진 결과와 체크리스트를 보는 장면",
    "home-fire-animation-v3.png": "주택 외부 설비의 화재를 발견한 가족",
    "home-leak-animation-v3.png": "천장 누수 흔적을 확인하는 가족",
    "home-weather-3d.png": "비 오는 날 집 안 누수 위험을 점검하는 장면",
    "student-campus-animation-v3.png": "해외 캠퍼스에 도착한 유학생",
    "student-overseas-3d.png": "장기 체류용 짐과 서류를 준비하는 학생",
    "travel-airport-3d.png": "공항에서 출국 준비물을 확인하는 여행자",
    "travel-airport-animation-v3.png": "여권과 여행 가방을 챙기는 출국 장면",
}

IMAGE_POOLS = {
    "home": ["calculator-animation-v3.png"],
    "hrmf": ["home-fire-animation-v3.png", "home-leak-animation-v3.png", "home-weather-3d.png"],
    "golf": ["golf-hole-animation-v3.png", "golf-holeinone-3d.png", "golf-tee-bag-animation-v1.png", "golf-checklist-animation-v1.png"],
    "cncr": ["cancer-consult-animation-v1.png", "health-check-animation-v3.png", "health-review-3d.png"],
    "dntl": ["dental-consult-animation-v3.png", "dental-consult-3d.png", "dental-model-animation-v1.png"],
    "driver": ["driver-safe-animation-v3.png", "driver-traffic-3d.png", "driver-schoolzone-animation-v4.png", "driver-accident-animation-v4.png", "driver-rain-animation-v4.png"],
    "woman": ["woman-health-planner-animation-v1.png", "woman-clinic-lounge-animation-v1.png", "woman-wellness-desk-animation-v1.png"],
    "birth": ["birth-nursery-prep-animation-v1.png", "birth-planner-animation-v1.png", "family-baby-animation-v3.png", "family-pregnancy-3d.png"],
    "overseas": ["travel-airport-animation-v3.png", "travel-airport-3d.png", "student-campus-animation-v3.png"],
    "overseaslong": ["student-campus-animation-v3.png", "student-overseas-3d.png", "travel-airport-animation-v3.png"],
    "holeinone": ["golf-hole-animation-v3.png", "golf-holeinone-3d.png", "golf-tee-bag-animation-v1.png", "golf-checklist-animation-v1.png"],
    "event": ["event-safety-animation-v3.png", "event-safety-3d.png", "event-venue-flow-animation-v1.png"],
    "chronic": ["chronic-health-record-animation-v1.png", "health-check-animation-v3.png", "health-review-3d.png"],
}

COPY_AXES = (
    "search_action", "decision_detail", "scope_compare",
    "official_path", "serp_whitespace", "seasonal_scene",
)
AXIS_LABELS = {
    "search_action": "검색 직후 행동", "decision_detail": "선택 기준 구체화",
    "scope_compare": "항목 간 비교", "official_path": "공식 화면 대조",
    "serp_whitespace": "경쟁 소재 공백", "seasonal_scene": "실제 시즌 장면",
}
MOVING_HOLIDAY_TERMS = ("추석", "설 연휴", "명절")
STYLE_FAMILY = "premium_3d_animation_v4"
MATERIAL_RULES_VERSION = 2


def read(rel, default, root=ROOT):
    try:
        return json.loads((root / rel).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def apply_feedback_rules(text, feedback_rules=None):
    value = str(text or "")
    for item in (feedback_rules or {}).get("copy_replacements") or []:
        pattern = str(item.get("pattern") or "")
        if pattern:
            value = value.replace(pattern, str(item.get("replacement") or ""))
    return re.sub(r"\s+", " ", value).strip()


def blocked_phrases_for(feedback_rules=None, channel=None, product_key=None):
    rules = feedback_rules or {}
    phrases = list(rules.get("blocked_phrases") or [])
    if channel:
        phrases.extend((rules.get("blocked_phrases_by_channel") or {}).get(channel) or [])
    if channel and product_key:
        key = f"{product_key}:{channel}"
        phrases.extend((rules.get("blocked_phrases_by_product_channel") or {}).get(key) or [])
    return sorted({str(phrase).strip() for phrase in phrases if str(phrase).strip()})


def feedback_findings(fields, feedback_rules=None, channel=None, product_key=None):
    text = " ".join(str(value or "") for value in fields.values())
    hits = [phrase for phrase in blocked_phrases_for(feedback_rules, channel, product_key)
            if phrase in text]
    return sorted(set(hits))


def rejected_asset_lookup(feedback_rules=None):
    lookup = {}
    for row in (feedback_rules or {}).get("rejected_assets") or []:
        product_key = row.get("product_key") or ""
        asset = row.get("asset") or ""
        if product_key and asset:
            lookup[(product_key, Path(asset).name)] = row
    return lookup


def _d(value):
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _latest(*values):
    dates = sorted({str(v)[:10] for v in values if _d(v)}, reverse=True)
    return dates[0] if dates else None


def out_of_scope(text, product):
    normalized = str(text).replace(" ", "").lower()
    return any(str(term).replace(" ", "").lower() in normalized for term in product.get("excluded") or [])


def term_score(term, product):
    score = 0
    if term == product.get("serpKw"):
        score += 3
    if "보험" in term:
        score += 2
    if any(bad in term.lower() for bad in ("한화생명", "고객센터", "보험금청구")):
        score -= 10
    return score


def volume_keyword(volume, product):
    rows = ((volume.get("products") or {}).get(product["key"]) or {}).get("keywords") or {}
    tokens = [x for x in product.get("core", []) + product.get("special", []) if len(x.replace(" ", "")) >= 3]
    ranked = [(term, row) for term, row in rows.items()
              if any(t.replace(" ", "") in term.replace(" ", "") for t in tokens)
              and not out_of_scope(term, product)]
    ranked.sort(key=lambda x: (-(term_score(x[0], product)),
                               -(int(x[1].get("pc") or 0) + int(x[1].get("mobile") or 0)), x[0]))
    return ranked[0][0] if ranked else product.get("serpKw") or product["name"]


def date_diff(ads):
    dates = sorted({a.get("date") for a in ads if a.get("date")}, reverse=True)
    if not dates:
        return {"latest": None, "previous": None, "entered_brands": [], "exited_brands": []}
    latest, previous = dates[0], dates[1] if len(dates) > 1 else None
    brands = lambda d: {a.get("brand") for a in ads if a.get("date") == d and a.get("brand")}
    now, before = brands(latest), brands(previous) if previous else set()
    return {"latest": latest, "previous": previous,
            "entered_brands": sorted(now-before), "exited_brands": sorted(before-now)}


def _ranked(rows, limit=5):
    return [value for value, _ in sorted(rows, key=lambda x: (-int(x[1]), str(x[0])))[:limit]]


def _text_patterns(texts):
    rules = (
        ("보험료·견적 확인", r"보험료|견적|계산"),
        ("가입 편의", r"간편|바로|즉시|24\s*시간|온라인|다이렉트"),
        ("보장·특약 제시", r"보장|특약|담보|진단비|치료비|합의금|벌금"),
        ("이벤트·혜택", r"이벤트|증정|할인|페이|상품권|쿠폰"),
        ("공식·신뢰", r"공식|전문가|상담|선택|1위"),
    )
    counts = Counter()
    for text in texts:
        for label, pattern in rules:
            if re.search(pattern, str(text), re.I):
                counts[label] += 1
    return [[label, count] for label, count in counts.most_common()]


def _title_patterns(ads):
    counts = Counter()
    for ad in ads:
        title = str(ad.get("title") or "")
        brand = str(ad.get("brand") or "")
        labels = []
        if brand and brand.replace(" ", "")[:3] in title.replace(" ", ""):
            labels.append("브랜드+상품명")
        if re.search(r"보험료|견적|계산|가입|확인|비교", title):
            labels.append("행동어 포함")
        if re.search(r"\d|할인|증정|1위", title):
            labels.append("혜택·수치 전면")
        if title and not labels:
            labels.append("상품명 중심")
        counts.update(labels)
    return [[label, count] for label, count in counts.most_common()]


def monitoring_for(product_key, manifest, dom, observed_latest):
    captures = (((manifest.get("shots") or {}).get(product_key) or {}).get("captures") or [])
    capture_dates = sorted({c.get("date") for c in captures if _d(c.get("date"))})
    capture_latest = capture_dates[-1] if capture_dates else None
    anchor = _d(capture_latest or observed_latest)
    cutoff = anchor - timedelta(days=WINDOW_DAYS) if anchor else None
    recent_captures = [d for d in capture_dates if not cutoff or _d(d) >= cutoff]
    dom_rows = [row for row in (dom.get("observations") or [])
                if row.get("product") == product_key and (not cutoff or not _d(row.get("date")) or _d(row.get("date")) >= cutoff)]
    latest_dom = _latest(*(row.get("date") for row in dom_rows))
    if latest_dom and (not observed_latest or latest_dom >= observed_latest):
        status = "current_patterns_ready"
    elif capture_latest and (not observed_latest or capture_latest > observed_latest):
        status = "capture_current_baseline_applied"
    else:
        status = "reviewed_baseline_only"
    return {
        "planning_month": (capture_latest or observed_latest or date.today().isoformat())[:7],
        "capture_latest": capture_latest,
        "capture_count_35d": len(recent_captures),
        "reviewed_observation_latest": observed_latest,
        "auto_pattern_latest": latest_dom,
        "auto_candidate_count_35d": len(dom_rows),
        "status": status,
        "status_label": {
            "current_patterns_ready": "최신 자동 패턴 반영",
            "capture_current_baseline_applied": "최신 캡처 반영 · 검토 패턴 기준",
            "reviewed_baseline_only": "검토된 기준 데이터만 반영",
        }[status],
    }, dom_rows


def _fit(options, minimum, maximum):
    cleaned = [re.sub(r"\s+", " ", str(value)).strip(" ·,:") for value in options if value]
    for value in cleaned:
        if minimum <= len(value) <= maximum:
            return value
    value = cleaned[0] if cleaned else "가입 전 확인"
    return value[:maximum].rstrip(" ·,:")


def _josa(value, batchim, open_value):
    text = str(value or "")
    if not text:
        return text
    code = ord(text[-1])
    has_batchim = 0xAC00 <= code <= 0xD7A3 and (code - 0xAC00) % 28
    return text + (batchim if has_batchim else open_value)


def _fingerprint(value, size=16):
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:size]


def _month_parts(planning_month):
    try:
        year, month = (int(value) for value in str(planning_month).split("-")[:2])
        if not 1 <= month <= 12:
            raise ValueError
        return year, month
    except (TypeError, ValueError):
        today = date.today()
        return today.year, today.month


def _event_overlaps_month(event, year, month):
    start, end = _d(event.get("start")), _d(event.get("end"))
    if not start or not end:
        return False
    first = date(year, month, 1)
    last = date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)
    return start <= last and end >= first


def season_context(product, planning_month, seasonal=None, calendar=None):
    """선택 월과 실제로 겹치는 이벤트만 소재에 허용한다."""
    year, month = _month_parts(planning_month)
    events = (calendar or {}).get("events") or []
    exact = [event for event in events
             if product["key"] in (event.get("products") or [])
             and _event_overlaps_month(event, year, month)]
    exact.sort(key=lambda row: (row.get("start") or "", row.get("name") or ""))
    if exact:
        event = exact[0]
        family = re.sub(r"-\d{4}$", "", str(event.get("id") or event.get("name") or "event"))
        return {
            "status": "active_dated_event", "event_id": event.get("id"),
            "season_key": family, "name": event.get("name") or "시즌 이슈",
            "type": event.get("type") or "시즌", "start": event.get("start"),
            "end": event.get("end"), "keywords": event.get("keywords") or [],
            "year": year, "month": month, "phase": "selected_month",
        }

    issues = (((seasonal or {}).get("seasonal") or {}).get(product["key"]) or [])
    for issue in issues:
        if month not in (issue.get("m") or []):
            continue
        tag = str(issue.get("tag") or "")
        if any(term in tag for term in MOVING_HOLIDAY_TERMS):
            dated_same_year = [event for event in events
                               if product["key"] in (event.get("products") or [])
                               and _d(event.get("start")) and _d(event.get("start")).year == year
                               and (event.get("type") == "명절"
                                    or any(term in str(event.get("name") or "") for term in MOVING_HOLIDAY_TERMS))]
            if dated_same_year:
                continue
            return {"status": "calendar_required", "season_key": None, "name": None,
                    "year": year, "month": month, "phase": "blocked_without_exact_date"}
        return {
            "status": "active_monthly_window", "event_id": None,
            "season_key": f"{product['key']}:{re.sub(r'[^0-9a-z가-힣]+', '-', tag.lower()).strip('-')}",
            "name": tag, "type": "연간 시즌", "start": None, "end": None,
            "keywords": issue.get("kws") or [], "why": issue.get("why"),
            "year": year, "month": month, "phase": "selected_month",
        }
    return {"status": "evergreen", "season_key": None, "name": None,
            "year": year, "month": month, "phase": "no_matching_season"}


def serp_signature(patterns, diff, table_stakes, observed):
    return _fingerprint({
        "patterns": patterns, "entered": diff.get("entered_brands") or [],
        "exited": diff.get("exited_brands") or [], "table_stakes": table_stakes,
        "observed": [{"brand": row.get("brand"), "title": row.get("title"), "promo": row.get("promo")}
                     for row in observed],
    })


def variation_context(product, planning_month, season, signature):
    year, month = _month_parts(planning_month)
    season_key = season.get("season_key") or "evergreen"
    available = COPY_AXES if season.get("name") else tuple(axis for axis in COPY_AXES if axis != "seasonal_scene")
    market_shift = int(signature[:8], 16) % len(available)
    start = (year + month + market_shift + sum(ord(char) for char in product["key"])) % len(available)
    axes = list(available[start:] + available[:start])
    if season.get("name"):
        axes = ["seasonal_scene", *[axis for axis in axes if axis != "seasonal_scene"]]
    return {
        "variation_key": _fingerprint({"product": product["key"], "season": season_key,
                                        "year": year, "month": month, "serp": signature}),
        "season_key": season_key, "serp_signature": signature,
        "primary_axis": axes[0], "axes": axes, "year": year,
    }


def _copy_for_axis(axis, product, keyword, angle, other, season):
    name = product.get("serpKw") or product["name"]
    event = season.get("name")
    if axis == "seasonal_scene" and event:
        return {
            "strategy": "시즌 장면형",
            "title": _fit([f"{event} 전 {name} 체크", f"{event} {name} 선택 기준", f"{name} 시즌 항목"], 4, 15),
            "description": _fit([f"{event} 전 {angle}·{other}의 적용 장면과 선택 기준 정리",
                                  f"{_josa(event, '을', '를')} 앞두고 {name}의 {angle} 항목을 읽는 순서"], 20, 45),
            "additional_description": _fit([f"{event} 전 {angle} 선택 여부와 보험기간 조건 비교",
                                             f"{name} 설계 화면의 {angle} 항목 확인"], 2, 45),
            "promo": _fit([f"{event} 전 점검", "시즌 기준 보기", "항목 비교"], 2, 14),
            "sublinks": ["보험료계산", "선택항목", "가입조건", "상품안내"],
        }
    if axis == "search_action":
        return {"strategy": "검색 행동형", "title": _fit([f"{keyword} 보험료 계산", f"{name} 보험료 보기"], 4, 15),
                "description": _fit([f"{name} 보험료 계산 전 {angle}·{other} 선택 기준 정리",
                                     f"{name} 계산 화면의 {angle} 항목 비교"], 20, 45),
                "additional_description": _fit([f"{angle} 포함 여부와 보험기간을 한 화면에서 확인",
                                                 f"{angle} 선택 기준 먼저 기록"], 2, 45),
                "promo": _fit(["보험료 계산", "선택 기준 보기"], 2, 14),
                "sublinks": ["보험료계산", "선택항목", "가입조건", "상품안내"]}
    if axis == "decision_detail":
        return {"strategy": "선택 기준형", "title": _fit([f"{angle} 조건 읽기", f"{name} 선택 기준"], 4, 15),
                "description": _fit([f"{angle} 적용 대상과 제외 조건을 한 번에 읽는 기준",
                                     f"{angle} 선택 전 확인할 기간·한도 항목"], 20, 45),
                "additional_description": _fit([f"{angle} 관련 조건과 적용 시점을 함께 비교",
                                                 f"{angle} 항목의 제외 조건부터 확인"], 2, 45),
                "promo": _fit(["조건 비교", "제외 조건 보기"], 2, 14),
                "sublinks": ["보장내용", "제외조건", "가입조건", "상품안내"]}
    if axis == "scope_compare":
        return {"strategy": "항목 비교형", "title": _fit([f"{angle}·{other} 비교", f"{name} 항목 비교"], 4, 15),
                "description": _fit([f"{_josa(angle, '과', '와')} {other} 적용 장면을 나누어 비교",
                                     f"{_josa(angle, '과', '와')} {other}가 달라지는 조건 정리"], 20, 45),
                "additional_description": _fit(["두 항목의 기간·제외 조건을 나란히 비교",
                                                 "지급사유와 보장하지 않는 경우를 구분"], 2, 45),
                "promo": _fit(["항목 비교", "조건 나누기"], 2, 14),
                "sublinks": ["항목비교", "보장내용", "보험료계산", "가입안내"]}
    if axis == "official_path":
        return {"strategy": "공식 화면형", "title": _fit([f"한화손보 {name}", f"{name} 공식 설계"], 4, 15),
                "description": _fit([f"{name} 상품 안내에서 선택 항목과 보험기간을 순서대로 확인",
                                     f"설계 화면에 표시된 {angle} 조건을 기록"], 20, 45),
                "additional_description": _fit(["선택 항목·납입 조건·보험기간을 한 번에 기록",
                                                 f"최종 청약 전 {angle} 조건 다시 읽기"], 2, 45),
                "promo": _fit(["설계 순서", "공식 안내"], 2, 14),
                "sublinks": ["보험료계산", "상품안내", "가입조건", "청약확인"]}
    return {"strategy": "SERP 공백형", "title": _fit([f"{angle} 질문부터", f"{name} 놓친 질문"], 4, 15),
            "description": _fit([f"{_josa(angle, '을', '를')} 검색 후 놓치기 쉬운 {other} 조건까지 이어서 확인",
                                 f"{name}에서 자주 빠지는 {angle} 기준 정리"], 20, 45),
            "additional_description": _fit([f"{angle}의 적용 조건과 제외 항목을 먼저 확인",
                                             "검색 결과와 공식 안내의 차이 메모"], 2, 45),
            "promo": _fit(["질문 정리", "놓친 조건 보기"], 2, 14),
            "sublinks": ["핵심질문", "보장내용", "보험료계산", "가입안내"]}


def sa_recommendations(product, keyword, angle, table_stakes, basis, season, variation, feedback_rules=None):
    name = product.get("serpKw") or product["name"]
    own_terms = [term for term in product.get("special") or [] if term != angle]
    season_keywords = [str(term).replace(" ", "") for term in season.get("keywords") or []]
    season_terms = [term for term in own_terms
                    if any(term.replace(" ", "") in keyword or keyword in term.replace(" ", "")
                           for keyword in season_keywords)]
    other = (season_terms or own_terms or [name])[0]
    rows, seen_endings = [], set()
    for axis in variation["axes"]:
        row = _copy_for_axis(axis, product, keyword, angle, other, season)
        for key in ("title", "description", "additional_description", "promo"):
            row[key] = apply_feedback_rules(row.get(key), feedback_rules)
        blocked_hits = feedback_findings({
            "title": row.get("title"), "description": row.get("description"),
            "additional_description": row.get("additional_description"), "promo": row.get("promo"),
        }, feedback_rules, "search_ad", product["key"])
        if blocked_hits:
            continue
        ending = re.sub(r"[^가-힣]+", "", row["description"])[-6:]
        if ending in seen_endings:
            continue
        seen_endings.add(ending)
        row.update({
            "message_axis": axis, "variation_key": variation["variation_key"],
            "serp_signature": variation["serp_signature"],
            "why": f"{basis} · {AXIS_LABELS[axis]} 축 · 경쟁 공통 소구 {', '.join(table_stakes[:2]) or '미관측'}와 다른 전개",
            "review_lab_feedback": {
                "applied_rules_version": (feedback_rules or {}).get("schema_version"),
                "blocked_phrase_hits": blocked_hits,
            },
        })
        rows.append(row)
        if len(rows) == 3:
            break
    return rows


def _image_history_for_product(image_history, product_key, planning_month):
    rows = []
    for archive in image_history or []:
        archive_month = str(archive.get("planning_month") or "")
        if not archive_month or archive_month > str(planning_month):
            continue
        for product in archive.get("products") or []:
            if product.get("product_key") != product_key:
                continue
            rows.append((archive_month, [row.get("asset") for row in product.get("image_directions") or [] if row.get("asset")]))
    rows.sort(key=lambda row: row[0], reverse=True)
    return rows


def monthly_image_assets(product_key, planning_month, image_history=None):
    """가장 오래 사용하지 않은 상품 적합 원본을 고른다.

    상품별 원본이 4장보다 적으면 타 보험 이미지를 끼워 넣지 않는다. 같은 원본을 스타일
    레퍼런스로 한 번 더 쓰되, 이후 image_directions에서 신규 제작 슬롯으로 표시한다.
    """
    pool = list(dict.fromkeys(IMAGE_POOLS.get(product_key) or IMAGE_POOLS["home"]))
    if not pool:
        raise ValueError(f"{product_key}: 월간 썸네일 후보 원본 없음")
    history = _image_history_for_product(image_history, product_key, planning_month)
    last_used = {}
    for archive_month, assets in history:
        for asset in assets:
            last_used.setdefault(Path(asset).name, archive_month)
    year, month = _month_parts(planning_month)
    seed = year * 12 + month + sum(ord(char) for char in product_key)
    order = {asset: (index - seed) % len(pool) for index, asset in enumerate(pool)}
    ranked = sorted(pool, key=lambda asset: (last_used.get(asset, ""), order[asset], asset))
    # 상품별 원본이 4장보다 적으면 같은 이미지를 복제하지 않는다. 부족한 슬롯은
    # 새 이미지 생성 대상으로 남겨 두어 소재제작소에서 실제 이미지가 반복 노출되지 않게 한다.
    assets = ranked[:4]
    while len(assets) < 4:
        assets.append(None)
    return assets


def image_directions(product, angle, patterns, basis, planning_month, season, variation, image_history=None, feedback_rules=None):
    assets = monthly_image_assets(product["key"], planning_month, image_history)
    rejected_assets = rejected_asset_lookup(feedback_rules)
    history = _image_history_for_product(image_history, product["key"], planning_month)
    previous_assets = set(history[0][1]) if history else set()
    roles = ("파워링크 대표", "보험료 탐색", "보장내용 탐색", "가입안내 탐색")
    base_scenes = list(SCENES.get(product["key"], SCENES["home"]))
    event = season.get("name")
    scenes = []
    if event:
        scenes.append(f"{event} 일정에 맞춰 {base_scenes[0]}")
        scenes.extend(base_scenes[1:])
    else:
        scenes.extend(base_scenes)
    scenes.append(f"스마트폰에서 {product['name']} 설계 항목과 보험료를 살펴보는 성인")
    scenes = list(dict.fromkeys(scenes))
    while len(scenes) < 4:
        scenes.append(f"{product['name']}의 {angle} 관련 생활 상황을 살펴보는 장면 {len(scenes) + 1}")
    rows, used_assets = [], set()
    for index, asset in enumerate(assets):
        asset_name = Path(asset).name if asset else ""
        asset_scene = ASSET_SCENES.get(asset_name) if asset_name else None
        if not asset_scene:
            asset_scene = base_scenes[index % len(base_scenes)]
        scene = f"{event} 일정에 맞춰 {asset_scene}" if event and index == 0 else asset_scene
        reused_previous = asset_name in {Path(value).name for value in previous_assets}
        repeated_this_set = bool(asset_name) and asset_name in used_assets
        rejected_reference = rejected_assets.get((product["key"], asset_name))
        if asset_name:
            used_assets.add(asset_name)
        rows.append({
        "proposal_id": f"{product['key']}-{planning_month}-{variation['variation_key'][:6]}-{index + 1:02d}",
        "concept_id": _fingerprint({"product": product["key"], "month": planning_month,
                                    "scene": scene, "serp": variation["serp_signature"]}),
        "role": roles[index], "scene": scene,
        "reference_scene": asset_scene,
        "asset": f"assets/insurance/{asset}" if asset else "",
        "composition": "핵심 인물·사물을 중앙에 크게 두고 작은 화면에서도 상황이 바로 보이는 정사각 구도",
        "style": "친근하지만 유아틱하지 않은 프리미엄 3D 애니메이션, 현실적인 생활 공간과 부드러운 조명",
        "style_family": STYLE_FAMILY, "text_overlay": False,
        "refresh_cadence": "monthly", "planning_month": planning_month,
        "reused_from_previous_month": reused_previous,
        "repeated_reference_in_month": repeated_this_set,
        "generation_required": not asset or reused_previous or repeated_this_set or bool(rejected_reference),
        "reference_only": not asset or reused_previous or repeated_this_set or bool(rejected_reference),
        "refresh_action": "new_image_generation_required" if (not asset or reused_previous or repeated_this_set or rejected_reference) else "reuse_approved_asset",
        "generation_brief": f"{product['name']} 검색 맥락을 ‘{scene}’으로 표현. 한국 성인 캐릭터, 자연스러운 비율, 텍스트·숫자·로고 없는 정사각형 프리미엄 3D 애니메이션. 이전 월과 인물·구도·배경을 반복하지 않는다.",
        "why": f"{basis} · {AXIS_LABELS[variation['primary_axis']]} · SERP {patterns[0][0] if patterns else '검색 행동'} 변화에서 장면 역할을 도출",
        "review_lab_feedback": {
            "applied_rules_version": (feedback_rules or {}).get("schema_version"),
            "rejected_reference": bool(rejected_reference),
            "reason_code": (rejected_reference or {}).get("reason_code"),
        },
        })
    return rows


def power_topics(product, keyword, angle, table_stakes, basis, planning_month, season, variation, content_history=None, feedback_rules=None):
    name = product.get("serpKw") or product["name"]
    own_terms = [term for term in product.get("special") or [] if term != angle]
    season_keywords = [str(term).replace(" ", "") for term in season.get("keywords") or []]
    season_terms = [term for term in own_terms
                    if any(term.replace(" ", "") in item or item in term.replace(" ", "")
                           for item in season_keywords)]
    second = (season_terms or own_terms or [name])[0]
    saturated = "·".join(table_stakes[:2]) or "공통 보장 나열"
    specs = [
        ("serp_whitespace", f"{keyword} 검색 뒤 {_josa(angle, '을', '를')} 따져볼 질문", "검색 후 탐색", angle,
         ["검색 결과에서 반복된 표현", f"{_josa(angle, '을', '를')} 기준에서 빠지기 쉬운 조건", "보험료 계산에 입력할 항목", "최종 화면에서 기록할 내용"]),
        ("decision_detail", f"{name} 보험료 전에 맞춰볼 세 가지 조건", "비교·의사결정", second,
         ["가입 목적과 기간 맞추기", f"{angle}·{second} 선택 항목 맞추기", "같은 조건으로 보험료 계산하기", "청약 화면에서 차이 찾기"]),
        ("scope_compare", f"{_josa(angle, '과', '와')} {second}, 함께 볼 때 달라지는 점", "항목 비교", angle,
         [f"{_josa(angle, '을', '를')} 찾게 되는 생활 상황", f"{_josa(second, '과', '와')} 겹치지 않는 지점", "지급사유와 제외 조건 나란히 읽기", "선택 항목 기록하기"]),
        ("official_path", f"{name} 설계 화면을 끝까지 읽는 순서", "가입 흐름 탐색", second,
         ["상품 안내에서 질문 만들기", "설계 화면에서 선택 항목 찾기", "보험료 결과의 조건 읽기", "최종 청약 내용 대조하기"]),
        ("terms_navigation", f"{_josa(angle, '을', '를')} 약관 목차에서 빠르게 찾는 법", "약관 정보 탐색", angle,
         ["용어 정의에서 시작하기", "지급사유 조항 연결하기", "보장하지 않는 경우 함께 읽기", "기준일과 질문 기록하기"]),
        ("real_life", f"{_josa(angle, '이', '가')} 궁금해지는 생활 장면부터 약관까지", "상황 정보 탐색", angle,
         ["실제 생활 질문으로 바꾸기", "광고 표현과 약관 용어 구분하기", "적용 조건을 사례 없이 설명하기", "내 조건으로 다시 계산하기"]),
    ]
    if season.get("name"):
        hook = ("출발 전 체크", "검색 뒤 비교", "약관에서 볼 항목", "보험료 전 질문")[variation["year"] % 4]
        seasonal_keyword = next((term for term in season.get("keywords") or [] if "보험" in term), keyword)
        specs.insert(0, (
            "seasonal_scene", f"{season['name']} {hook}, {name}", "시즌 의사결정", angle,
            [f"{season['name']}에 달라지는 생활 동선", f"{angle}·{second} 확인 질문",
             f"{saturated} 중심 검색 결과와 다른 관점", "일정 전 최종 설계 점검"],
            seasonal_keyword,
        ))
    year, month = _month_parts(planning_month)
    offset = (year * 12 + month + int(variation["serp_signature"][:6], 16)) % len(specs)
    rotated = specs[offset:] + specs[:offset]
    if season.get("name"):
        seasonal_spec = next(row for row in specs if row[0] == "seasonal_scene")
        rotated = [seasonal_spec, *[row for row in rotated if row[0] != "seasonal_scene"]]
    used_titles = {re.sub(r"\s+", "", str(row.get("title") or "")).lower()
                   for row in ((content_history or {}).get("entries") or [])
                   if row.get("product_key") == product["key"]}
    rows = []
    for spec in rotated:
        pattern, title, intent, focus, sections, *query_override = spec
        fitted = apply_feedback_rules(_fit([title, f"{name} 선택 전에 질문을 정리하는 법"], 15, 34), feedback_rules)
        safe_sections = [apply_feedback_rules(section, feedback_rules) for section in sections]
        blocked_hits = feedback_findings({
            "title": fitted,
            "angle": f"SERP의 ‘{saturated}’ 반복에서 벗어나 {AXIS_LABELS.get(pattern, '생활 질문')}으로 전개",
            "sections": " ".join(safe_sections),
        }, feedback_rules, "power_content", product["key"])
        if blocked_hits:
            continue
        if re.sub(r"\s+", "", fitted).lower() in used_titles:
            continue
        index = len(rows) + 1
        rows.append({
            "id": f"{product['key']}-serp-topic-{variation['variation_key'][:6]}-{index}",
            "fingerprint": _fingerprint({"product": product["key"], "title": fitted,
                                         "season": variation["season_key"], "serp": variation["serp_signature"]}),
            "pattern": pattern, "message_axis": pattern, "title": fitted,
            "target_query": query_override[0] if query_override else (keyword if index != 2 else f"{name} {focus}"),
            "intent": intent, "focus": focus,
            "angle": f"SERP의 ‘{saturated}’ 반복에서 벗어나 {AXIS_LABELS.get(pattern, '생활 질문')}으로 전개",
            "sections": safe_sections,
            "faq": [f"{_josa(focus, '을', '를')} 볼 때 먼저 비교할 항목은 무엇인가요?", f"{name} 보험료 계산 조건은 어떻게 맞추나요?"],
            "image_brief": f"{SCENES.get(product['key'], SCENES['home'])[(index-1) % 3]}. 텍스트·숫자·로고 없이 프리미엄 3D 애니메이션으로 표현.",
            "serp_basis": basis, "serp_signature": variation["serp_signature"],
            "variation_key": variation["variation_key"], "season_context": season,
            "source": "월간 SERP 변화·시즌 캘린더 결합",
            "review_lab_feedback": {
                "applied_rules_version": (feedback_rules or {}).get("schema_version"),
                "blocked_phrase_hits": blocked_hits,
            },
        })
        if len(rows) == 3:
            break
    return rows


def generate(products, analysis, volume, manifest=None, dom=None, planning_month=None,
             seasonal=None, calendar=None, content_history=None, image_history=None, feedback_rules=None):
    manifest, dom = manifest or {}, dom or {}
    output = []
    for product in products.get("products") or []:
        if product.get("cat") == "사이트":
            continue
        observed = ((analysis.get("products") or {}).get(product["key"]) or {})
        ads, common = observed.get("observed_ads") or [], observed.get("common_soju") or []
        if not ads:
            continue
        keyword = volume_keyword(volume, product)
        observed_angles = list(dict.fromkeys([*common, *_ranked(observed.get("soju") or [])]))
        gaps = [x for x in product.get("special") or []
                if not out_of_scope(x, product) and not any(x in c or c in x for c in observed_angles)]
        angle = (gaps or product.get("special") or product.get("core") or [product["name"]])[0]
        diff = date_diff(ads)
        monitoring, dom_rows = monitoring_for(product["key"], manifest, dom, diff["latest"] or observed.get("latest_date"))
        raw_texts = [f"{a.get('title', '')} {a.get('desc', '')} {a.get('promo', '')}" for a in ads]
        raw_texts += [row.get("text", "") for row in dom_rows]
        patterns = _text_patterns(raw_texts)
        pattern_date = monitoring["auto_pattern_latest"] or monitoring["reviewed_observation_latest"] or "기준일 없음"
        plan_month = planning_month or monitoring["planning_month"]
        basis = f"{plan_month} 월간 SERP · 캡처 {monitoring['capture_latest'] or '없음'} · 패턴 {pattern_date} · 최근 35일 {monitoring['capture_count_35d']}회"
        table_stakes = list(dict.fromkeys([*common, *observed_angles]))[:3]
        season = season_context(product, plan_month, seasonal, calendar)
        season_keywords = [str(term).replace(" ", "") for term in season.get("keywords") or []]
        seasonal_angle = next((term for term in product.get("special") or []
                               if any(term.replace(" ", "") in keyword or keyword in term.replace(" ", "")
                                      for keyword in season_keywords)), None)
        if seasonal_angle:
            angle = seasonal_angle
        signature = serp_signature(patterns, diff, table_stakes, ads)
        variation = variation_context(product, plan_month, season, signature)
        sa = sa_recommendations(product, keyword, angle, table_stakes, basis, season, variation, feedback_rules)
        images = image_directions(product, angle, patterns, basis, plan_month, season, variation, image_history, feedback_rules)
        topics = power_topics(product, keyword, angle, table_stakes, basis, plan_month, season, variation, content_history, feedback_rules)
        output.append({
            "product_key": product["key"],
            "month": plan_month,
            "keyword": keyword,
            "monitoring": monitoring,
            "market_patterns": {
                "message_patterns": patterns,
                "title_patterns": _title_patterns(ads),
                "table_stakes": table_stakes,
                "saturated_angles": common,
                "promo_patterns": observed.get("promos") or [],
                "cta_patterns": observed.get("cta") or [],
            },
            "common_competitor_angles": common,
            "whitespace_angles": gaps[:5],
            "selected_angle": angle,
            "latest_date": monitoring["capture_latest"] or monitoring["auto_pattern_latest"] or diff["latest"],
            "serp_diff": diff,
            "serp_signature": signature,
            "season_context": season,
            "variation": variation,
            "observed_count": len(ads),
            "copy_direction": f"{keyword} 검색자의 {_josa(AXIS_LABELS[variation['primary_axis']], '을', '를')} 중심으로 {_josa(angle, '을', '를')} 구체화",
            "visual_direction": f"보험종목 장면 · {STYLE_FAMILY} · {images[0]['scene']}",
            "operating_gap": {
                "current_gap": "실제 SERP의 상품명·행동어·확장소재 구조보다 기존 제안이 추상적",
                "direction": f"{keyword} 검색자의 다음 행동, {angle}, {season.get('name') or '선택 월의 상시 수요'}를 제목·설명·이미지·파워콘텐츠에 같은 축으로 연결",
                "guardrails": ["경쟁사 원문·프로모션 수치 복사 금지", "상품자료에 없는 금액·기간·할인 단정 금지", "이미지 안 텍스트·숫자·로고 금지"],
            },
            "sa_recommendations": sa,
            "image_directions": images,
            "image_plan": {
                "set_id": f"{product['key']}-{plan_month}",
                "planning_month": plan_month,
                "refresh_cadence": "monthly",
                "slot_count": len(images),
                "unique_asset_count": len({row["asset"] for row in images}),
                "new_generation_required": sum(bool(row["generation_required"]) for row in images),
                "style_family": STYLE_FAMILY,
                "selection": "least_recently_used_product_pool_then_new_generation",
            },
            "power_content_topics": topics,
            "analysis_status": "ready",
            "review_lab_rules": {
                "applied_rules_version": (feedback_rules or {}).get("schema_version"),
                "source": (feedback_rules or {}).get("source"),
                "updated_at": (feedback_rules or {}).get("updated_at"),
            },
            "material_refresh": {
                "rules_version": MATERIAL_RULES_VERSION,
                "scope": "sa_powercontent_thumbnail",
                "status": "regenerated_from_current_rules",
            },
        })
    dates = [analysis.get("asof"), manifest.get("asof"), dom.get("asof"), volume.get("asof")]
    asof = _latest(*dates) or date.today().isoformat()
    return {
        "_comment": "월간 SERP 캡처·자동 DOM 패턴·검토 관측·검색량을 결합한 공통 소재 기획안. 경쟁사 원문은 자동 제안에 복사하지 않는다.",
        "schema_version": 3,
        "material_rules_version": MATERIAL_RULES_VERSION,
        "refresh_scope": "all_generated_materials",
        "refresh_note": "기존 후보를 현재 SA·파워콘텐츠·썸네일 규칙으로 재생성",
        "asof": asof,
        "planning_month": planning_month or asof[:7],
        "cadence": "weekly_capture_monthly_material_plan",
        "image_refresh_cadence": "monthly",
        "products": output,
    }


def image_plan_archive(result):
    return {
        "schema_version": 1,
        "planning_month": result["planning_month"],
        "asof": result["asof"],
        "refresh_cadence": "monthly",
        "products": [{
            "product_key": row["product_key"],
            "keyword": row["keyword"],
            "selected_angle": row["selected_angle"],
            "image_plan": row["image_plan"],
            "image_directions": row["image_directions"],
        } for row in result["products"]],
    }


def _read_image_history(root):
    rows = []
    for path in sorted((root / "data/adcopy/image-plans").glob("*.json")):
        try:
            rows.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
    return rows


def main(root=ROOT, planning_month=None, archive_images=False):
    planning_month = planning_month or date.today().strftime("%Y-%m")
    result = generate(
        read("data/products.json", {}, root),
        read("serp/ad_analysis.json", {}, root),
        read("data/volume.json", {}, root),
        read("serp/manifest.json", {}, root),
        read("serp/dom_observations.json", {}, root),
        planning_month,
        read("data/seasonal.json", {}, root),
        read("data/events/calendar.json", {}, root),
        read("data/adcopy/powercontent-history.json", {}, root),
        _read_image_history(root),
        read(FEEDBACK_RULES, {}, root),
    )
    output = root / "data/adcopy/serp-candidates.json"
    atomic_json_write(output, result)
    if archive_images:
        archive = root / "data/adcopy/image-plans" / f"{planning_month}.json"
        atomic_json_write(archive, image_plan_archive(result))
        print(f"[OK] {archive.relative_to(root)} · 월간 이미지 썸네일 제안 이력")
    print(f"[OK] {output.relative_to(root)} · 상품 {len(result['products'])} · 월간 SERP 통합 소재 기획")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="월간 SERP 기반 소재·이미지 제안 생성")
    parser.add_argument("--planning-month", help="기획 기준월(YYYY-MM), 기본값은 실행월")
    parser.add_argument("--archive-images", action="store_true", help="월별 이미지 제안 이력도 저장")
    args = parser.parse_args()
    main(planning_month=args.planning_month, archive_images=args.archive_images)
