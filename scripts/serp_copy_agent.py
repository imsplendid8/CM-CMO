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
GUIDE_RULES = "data/adcopy/material-generation-guide.json"
SOURCE_CONTEXT = "data/adcopy/material-source-context.json"
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
    "search_action", "decision_detail", "scope_compare", "terms_navigation",
    "official_path", "serp_whitespace", "seasonal_scene",
)
AXIS_LABELS = {
    "search_action": "검색 직후 행동", "decision_detail": "선택 기준 구체화",
    "scope_compare": "항목 간 비교", "terms_navigation": "약관 탐색",
    "official_path": "공식 화면 대조",
    "serp_whitespace": "경쟁 소재 공백", "seasonal_scene": "실제 시즌 장면",
}
MOVING_HOLIDAY_TERMS = ("추석", "설 연휴", "명절")
STYLE_FAMILY = "premium_3d_animation_v4"
MATERIAL_RULES_VERSION = 3
GUIDE_VERSION = "2026-09-02-derived-2"
REVIEW_STATUSES = {"자동 차단", "근거 필요", "필수 고지 필요", "사람 심의 필요", "자동 위험표현 없음"}


def read(rel, default, root=ROOT):
    try:
        return json.loads((root / rel).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def product_source_context(source_context, product_key):
    return ((source_context or {}).get("products") or {}).get(product_key) or {}


def source_context_basis(source_context):
    context = source_context or {}
    return {
        "schema_version": context.get("schema_version"),
        "asof": context.get("asof"),
        "source_count": len(context.get("sources") or []),
        "raw_files_committed": (context.get("handling") or {}).get("raw_files_committed", False),
        "competitor_copy_use": (context.get("handling") or {}).get("competitor_copy_use", "pattern_only"),
        "numeric_claim_default": (context.get("handling") or {}).get("numeric_claim_default", "do_not_auto_generate"),
        "review_draft_copy_use": (context.get("handling") or {}).get("review_draft_copy_use", "structure_and_terms_only"),
        "power_content_description_rule": (context.get("handling") or {}).get("power_content_description_rule"),
    }


def product_source_basis(context, source_context=None):
    source_ids = list(context.get("source_ids") or [])
    source_rows = {row.get("id"): row for row in (source_context or {}).get("sources") or []}
    dates = [source_rows.get(source_id, {}).get("captured_at") for source_id in source_ids]
    return {
        "status": "landing_grounded" if (context.get("landing") or {}).get("verified") else (
            "structured_capture_grounded" if source_ids else "repository_signals_only"
        ),
        "source_ids": source_ids,
        "source_latest": _latest(*dates),
        "landing_verified": bool((context.get("landing") or {}).get("verified")),
        "competitor_copy_use": "pattern_only",
        "numeric_claims_used": False,
        "suppressed_numeric_claim_count": sum(
            1 for row in (context.get("landing") or {}).get("terms") or []
            if row.get("auto_copy_allowed") is False
        ),
    }


def insurance_review(status="사람 심의 필요", source_ids=None, reason=None):
    normalized = status if status in REVIEW_STATUSES else "사람 심의 필요"
    return {
        "status": normalized,
        "reason": reason or "자동 생성 결과는 최신 상품자료·약관·랜딩과 사람 심의를 거쳐야 함",
        "required_checks": ["키워드·소재·랜딩 일치", "최신 상품자료·약관", "준법·광고심의"],
        "source_ids": list(source_ids or []),
    }


def guide_pattern_for(axis, guide=None):
    """첨부 가이드에서 도출한 문구 구조를 생성 결과에 남긴다.

    가이드의 실제 문구를 복사하지 않고, 운영자가 재사용할 수 있는 구조만
    전달한다. 저장된 가이드가 없거나 축이 새로 추가되어도 안전한 기본값을
    반환해 기존 호출부와 테스트를 깨뜨리지 않는다.
    """
    mapping = {
        "search_action": "question_plus_next_step",
        "decision_detail": "split_conditions",
        "scope_compare": "split_conditions",
        "terms_navigation": "split_conditions",
        "official_path": "question_plus_next_step",
        "serp_whitespace": "scene_plus_term",
        "seasonal_scene": "segment_context",
    }
    pattern_id = mapping.get(axis, "question_plus_next_step")
    for row in (guide or {}).get("sa", {}).get("pattern_library", []):
        if row.get("id") == pattern_id:
            return {
                "id": pattern_id,
                "label": row.get("label") or pattern_id,
                "description": row.get("description") or "검색 의도와 확인 행동을 연결",
                "review": row.get("review") or "최신 상품자료·약관 확인",
            }
    return {
        "id": pattern_id,
        "label": pattern_id,
        "description": "검색 의도와 확인 행동을 연결",
        "review": "최신 상품자료·약관 확인",
    }


def guide_basis(guide=None):
    sa = (guide or {}).get("sa") or {}
    power = (guide or {}).get("power_content") or {}
    return {
        "guide_version": (guide or {}).get("guide_version") or GUIDE_VERSION,
        "source": "첨부 소재생성가이드에서 도출한 구조화 규칙",
        "sa": {
            "title_max_length": sa.get("title_max_length", 15),
            "description_range": [sa.get("description_min_length", 20), sa.get("description_max_length", 45)],
            "group_limits": sa.get("extension_limits_per_ad_group") or {},
        },
        "power_content": {
            "title_range": [power.get("title_min_length", 7), power.get("title_max_length", 28)],
            "description_range": [power.get("description_min_length", 80), power.get("description_max_length", 110)],
            "body_min_length": power.get("body_min_length", 700),
            "editorial_structure": power.get("editorial_structure") or [],
        },
    }


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


def _join_josa(values, batchim, open_value, separator="·"):
    """여러 SERP 소구를 하나의 자연스러운 조사 구로 연결한다."""
    terms = [str(value).strip() for value in values if str(value).strip()]
    if not terms:
        return "미관측"
    if len(terms) == 1:
        return _josa(terms[0], batchim, open_value)
    return f"{separator.join(terms[:-1])}{separator}{_josa(terms[-1], batchim, open_value)}"


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
            "title": _fit([f"{event} 전 {angle} 확인", f"{event} {angle} 선택", f"{name} 시즌 항목"], 4, 15),
            "description": _fit([f"{event} 전 {angle} 적용 장면과 {other} 선택 조건을 함께 비교",
                                  f"{_josa(event, '을', '를')} 앞두고 {name}의 {angle} 확인 순서 정리"], 20, 45),
            "additional_description": _fit([f"{event} 일정·{angle} 적용기간·제외 조건을 비교",
                                             f"{name} 설계 화면에서 {angle} 선택 항목 확인"], 2, 45),
            "promo": _fit([f"{event} 기준 보기", f"{angle} 조건 보기", "항목 비교"], 2, 14),
            "sublinks": ["보험료계산", "선택항목", "가입조건", "상품안내"],
        }
    if axis == "search_action":
        return {"strategy": "검색 행동형", "title": _fit([f"{name}료 계산 전", f"{angle} 보험료 계산", f"{name} 선택 항목"], 4, 15),
                "description": _fit([f"{angle}·{other} 선택 항목과 보험기간을 먼저 맞춰 보기",
                                     f"{name} 계산 화면에서 {angle} 항목과 보험기간을 비교"], 20, 45),
                "additional_description": _fit([f"같은 선택 조건으로 계산한 결과인지 최종 화면에서 대조",
                                                 f"{angle} 선택 기준을 계산 전에 먼저 기록"], 2, 45),
                "promo": _fit(["보험료 계산", f"{angle} 조건 보기"], 2, 14),
                "sublinks": ["보험료계산", "선택항목", "가입조건", "상품안내"]}
    if axis == "decision_detail":
        return {"strategy": "선택 기준형", "title": _fit([f"{angle} 지급 조건", f"{angle} 조건 읽기", f"{name} 선택 기준"], 4, 15),
                "description": _fit([f"{angle} 지급사유·적용 시점·제외 조건을 나눠 읽는 기준",
                                     f"{angle} 선택 전 기간·한도 항목을 한 줄씩 정리"], 20, 45),
                "additional_description": _fit([f"{other} 항목은 같은 기준으로 나란히 비교",
                                                 f"{angle} 항목의 보장하지 않는 경우부터 읽기"], 2, 45),
                "promo": _fit(["조건 비교", "제외 조건 보기"], 2, 14),
                "sublinks": ["보장내용", "제외조건", "가입조건", "상품안내"]}
    if axis == "scope_compare":
        return {"strategy": "항목 비교형", "title": _fit([f"{angle}·{other} 차이", f"{name} 항목 비교"], 4, 15),
                "description": _fit([f"{_josa(angle, '과', '와')} {other}의 지급사유와 적용 장면을 따로 비교",
                                     f"{_josa(angle, '과', '와')} {other}의 기간·제외 조건을 한 표로 정리"], 20, 45),
                "additional_description": _fit(["두 항목의 적용 시점과 보장하지 않는 경우를 나란히 읽기",
                                                 "지급사유와 제외 조건을 같은 순서로 구분"], 2, 45),
                "promo": _fit(["항목 비교", "조건 나누기"], 2, 14),
                "sublinks": ["항목비교", "보장내용", "보험료계산", "가입안내"]}
    if axis == "terms_navigation":
        return {"strategy": "약관 탐색형", "title": _fit([f"{name} 약관 순서", f"{angle} 약관 찾기"], 4, 15),
                "description": _fit([f"{angle} 지급사유·적용 시점·제외 조건을 차례로 읽기",
                                     f"{name} 약관에서 {angle} 정의와 지급 조항을 함께 찾기"], 20, 45),
                "additional_description": _fit([f"{other} 항목도 같은 목차 순서로 대조",
                                                 "광고 표현과 약관 용어가 같은 뜻인지 기록"], 2, 45),
                "promo": _fit(["약관 항목 보기", "지급 기준 보기"], 2, 14),
                "sublinks": ["약관확인", "지급사유", "제외조건", "가입안내"]}
    if axis == "official_path":
        return {"strategy": "공식 화면형", "title": _fit(["최종 청약 조건 대조", f"{name} 설계 순서"], 4, 15),
                "description": _fit([f"상품 안내·보험료 계산·최종 청약의 {angle} 조건을 비교",
                                     f"설계 화면에 표시된 {angle} 조건과 납입기간을 기록"], 20, 45),
                "additional_description": _fit(["선택 항목·납입 조건·보험기간을 처음 설계와 대조",
                                                 f"최종 청약 전 {angle} 조건을 한 번 더 읽기"], 2, 45),
                "promo": _fit(["청약 조건 보기", "설계 순서"], 2, 14),
                "sublinks": ["보험료계산", "상품안내", "가입조건", "청약확인"]}
    return {"strategy": "SERP 공백형", "title": _fit([f"{angle} 먼저 구분", f"{name} 놓친 질문"], 4, 15),
            "description": _fit([f"검색 결과가 덜 설명한 {angle}·{other} 조건을 따로 정리",
                                 f"{name}에서 빠지기 쉬운 {angle} 지급 기준을 질문으로 분리"], 20, 45),
            "additional_description": _fit([f"{angle} 적용 시점과 보장하지 않는 경우까지 기록",
                                             "검색 결과와 상품 안내의 차이를 메모"], 2, 45),
            "promo": _fit(["핵심 질문 보기", "조건 구분"], 2, 14),
            "sublinks": ["핵심질문", "보장내용", "보험료계산", "가입안내"]}


def source_sa_recommendations(product, context, basis, variation, feedback_rules=None, guide=None):
    rows = []
    source_ids = list(context.get("source_ids") or [])
    blueprints = list(context.get("sa_blueprints") or [])
    if source_ids and not blueprints:
        focuses = list(context.get("preferred_focus") or product.get("special") or [product["name"]])
        angle = focuses[0]
        other = focuses[1] if len(focuses) > 1 else (product.get("special") or [product["name"]])[0]
        third = focuses[2] if len(focuses) > 2 else other
        name = product.get("serpKw") or product["name"]
        actions = list((context.get("landing") or {}).get("official_actions") or ["보험료 확인", "상품안내 보기"])
        preferred_action = (next((value for value in actions if "보험료" in value), None)
                            or next((value for value in actions if re.search(r"가입|플랜", value)), None)
                            or actions[0])
        action = re.sub(r"\s*(?:자세히\s*)?(?:보기|확인하기|알아보기|하기)$", "", preferred_action).strip() or "설계"
        result_label = f"{action} 결과" if "보험료" in action else "설계 화면"
        reader_question = str(context.get("reader_question") or f"{angle}과 {other}은 어떤 조건으로 나눠 봐야 할까?")
        blueprints = [
            {"message_axis": "scope_compare", "title": _fit([f"{angle}·{other} 구분", f"{name} 항목 비교"], 4, 15),
             "description": _fit([f"{_josa(angle, '과', '와')} {other}, 지급사유와 적용 시점을 항목별로 비교"], 20, 45),
             "additional_description": _fit(["보장하지 않는 경우와 필요한 확인 자료도 나란히 정리"], 2, 45),
             "promo": "항목 차이 보기", "sublinks": ["항목비교", "지급사유", "제외조건", "상품안내"], "review_status": "필수 고지 필요"},
            {"message_axis": "decision_detail", "title": _fit([f"{angle} 조건 읽기", f"{name} 선택 질문"], 4, 15),
             "description": _fit([reader_question, f"{angle} 선택 전에 대상·시점·제외 조건을 질문으로 정리"], 20, 45),
             "additional_description": _fit([f"{third}은 정의와 제외 조건을 별도 항목으로 확인"], 2, 45),
             "promo": "선택 질문 보기", "sublinks": ["핵심질문", "보장내용", "가입조건", "상품안내"], "review_status": "사람 심의 필요"},
            {"message_axis": "terms_navigation", "title": _fit([f"{third} 약관 찾기", f"{name} 약관 순서"], 4, 15),
             "description": _fit([f"{third}의 용어 정의에서 지급 조항과 제외 조항까지 연결"], 20, 45),
             "additional_description": "확인한 기준일과 최종 선택 내용을 함께 기록",
             "promo": "약관 조항 보기", "sublinks": ["약관확인", "용어정의", "지급사유", "제외조건"], "review_status": "필수 고지 필요"},
            {"message_axis": "search_action", "title": _fit([f"{name} 설계 전", f"{angle} 설계 전"], 4, 15),
             "description": _fit([f"{action} 전에 대상·기간·선택 항목을 같은 순서로 메모"], 20, 45),
             "additional_description": _fit([f"{_josa(angle, '과', '와')} {other}이 필요한 상황을 먼저 구분"], 2, 45),
             "promo": _fit([actions[0], "설계 조건 보기"], 2, 14), "sublinks": ["보험료계산", "선택항목", "가입조건", "상품안내"], "review_status": "자동 위험표현 없음"},
            {"message_axis": "official_path", "title": "최종 선택 조건 대조",
             "description": _fit([f"{result_label}과 최종 청약의 선택 항목·기간을 비교"], 20, 45),
             "additional_description": "광고의 짧은 표현은 최신 상품자료와 약관으로 다시 확인",
             "promo": "청약 조건 보기", "sublinks": ["보험료계산", "상품안내", "가입조건", "청약확인"], "review_status": "사람 심의 필요"},
        ]
    for index, item in enumerate(blueprints):
        axis = item.get("message_axis") or "serp_whitespace"
        row = {
            "strategy": {
                "search_action": "검색 행동형", "decision_detail": "선택 기준형",
                "scope_compare": "항목 비교형", "terms_navigation": "약관 탐색형",
                "official_path": "공식 화면형", "serp_whitespace": "SERP 공백형",
            }.get(axis, "자료 근거형"),
            "title": item.get("title"),
            "description": item.get("description"),
            "additional_description": item.get("additional_description"),
            "promo": item.get("promo"),
            "sublinks": list(item.get("sublinks") or []),
        }
        for key in ("title", "description", "additional_description", "promo"):
            row[key] = apply_feedback_rules(row.get(key), feedback_rules)
        if not (4 <= len(row["title"]) <= 15 and 20 <= len(row["description"]) <= 45
                and 2 <= len(row["additional_description"]) <= 45
                and 2 <= len(row["promo"]) <= 14
                and len(row["sublinks"]) == 4
                and all(2 <= len(value) <= 6 for value in row["sublinks"])):
            continue
        blocked_hits = feedback_findings(row, feedback_rules, "search_ad", product["key"])
        if blocked_hits:
            continue
        pattern = guide_pattern_for(axis, guide)
        row.update({
            "material_id": f"{product['key']}-source-sa-{variation['variation_key'][:6]}-{index + 1}",
            "message_axis": axis,
            "variation_key": variation["variation_key"],
            "serp_signature": variation["serp_signature"],
            "why": f"{basis} · 사용자 제공 캡처를 구조화한 {AXIS_LABELS.get(axis, '자료 근거')} 축",
            "guide_pattern_id": pattern["id"],
            "guide_pattern_label": pattern["label"],
            "guide_pattern": pattern["description"],
            "review_basis": pattern["review"],
            "source_grounding": {
                "status": "landing_grounded" if (context.get("landing") or {}).get("verified") else "structured_capture_grounded",
                "source_ids": source_ids,
                "competitor_copy_use": "pattern_only",
                "numeric_claims_used": False,
            },
            "insurance_review": insurance_review(item.get("review_status"), source_ids),
            "review_lab_feedback": {
                "applied_rules_version": (feedback_rules or {}).get("schema_version"),
                "blocked_phrase_hits": blocked_hits,
                "operator_decision": "pending",
                "reason_codes": ["usable_but_review_needed"] if item.get("review_status") != "자동 위험표현 없음" else [],
            },
        })
        rows.append(row)
    return rows


def sa_recommendations(product, keyword, angle, table_stakes, basis, season, variation,
                       feedback_rules=None, guide=None, source_context=None):
    name = product.get("serpKw") or product["name"]
    own_terms = [term for term in product.get("special") or [] if term != angle]
    context_terms = [term for term in (source_context or {}).get("comparison_terms") or [] if term != angle]
    season_keywords = [str(term).replace(" ", "") for term in season.get("keywords") or []]
    season_terms = [term for term in own_terms
                    if any(term.replace(" ", "") in keyword or keyword in term.replace(" ", "")
                           for keyword in season_keywords)]
    other = (context_terms or season_terms or own_terms or [name])[0]
    rows = source_sa_recommendations(product, source_context or {}, basis, variation, feedback_rules, guide)
    grounding = product_source_basis(source_context or {})
    seen_endings = {re.sub(r"[^가-힣]+", "", row["description"])[-6:] for row in rows}
    for axis in variation["axes"]:
        if any(row.get("message_axis") == axis for row in rows):
            continue
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
        pattern = guide_pattern_for(axis, guide)
        row.update({
            "material_id": f"{product['key']}-sa-{variation['variation_key'][:6]}-{len(rows) + 1}",
            "message_axis": axis, "variation_key": variation["variation_key"],
            "serp_signature": variation["serp_signature"],
            "why": f"{basis} · {AXIS_LABELS[axis]} 축 · 경쟁 공통 소구 {_join_josa(table_stakes[:2], '과', '와')} 다른 전개",
            "guide_pattern_id": pattern["id"],
            "guide_pattern_label": pattern["label"],
            "guide_pattern": pattern["description"],
            "review_basis": pattern["review"],
            "source_grounding": grounding,
            "insurance_review": insurance_review("사람 심의 필요", grounding.get("source_ids")),
            "review_lab_feedback": {
                "applied_rules_version": (feedback_rules or {}).get("schema_version"),
                "blocked_phrase_hits": blocked_hits,
                "operator_decision": "pending",
                "reason_codes": ["usable_but_review_needed"],
            },
        })
        rows.append(row)
        if len(rows) == 5:
            break
    return rows[:5]


def _image_history_for_product(image_history, product_key, planning_month):
    rows = []
    for archive in image_history or []:
        archive_month = str(archive.get("planning_month") or "")
        # 현재 생성 중인 월의 archive는 직전 달 이력이 아니다. 같은 달 파일을
        # 다시 읽으면 재실행할 때마다 자기 자신을 최근 사용 원본으로 판단해
        # 월간 회전 결과가 흔들리고, 이전 원본 여부 플래그도 어긋난다.
        if not archive_month or archive_month >= str(planning_month):
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
                                    "slot": index, "scene": scene,
                                    "serp": variation["serp_signature"]}),
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
        "guide_quality": {
            "guide_version": (feedback_rules or {}).get("guide_version") or GUIDE_VERSION,
            "product_fit_required": True,
            "text_overlay": False,
            "duplicate_source_in_set": False,
            "variation_required": True,
        },
        "review_lab_feedback": {
            "applied_rules_version": (feedback_rules or {}).get("schema_version"),
            "rejected_reference": bool(rejected_reference),
            "reason_code": (rejected_reference or {}).get("reason_code"),
        },
        })
    return rows


def source_power_topics(product, context, table_stakes, basis, planning_month, season, variation,
                        used_titles=None, feedback_rules=None, guide=None):
    rows = []
    used_titles = used_titles or set()
    source_ids = list(context.get("source_ids") or [])
    saturated = "·".join(table_stakes[:2]) or "공통 표현"
    for item in context.get("power_content_blueprints") or []:
        title = apply_feedback_rules(str(item.get("title") or ""), feedback_rules)
        key = re.sub(r"\s+", "", title).lower()
        sections = [apply_feedback_rules(section, feedback_rules) for section in item.get("sections") or []]
        if not (7 <= len(title) <= 28 and len(sections) >= 4) or key in used_titles:
            continue
        blocked_hits = feedback_findings({
            "title": title,
            "angle": context.get("editorial_thesis"),
            "sections": " ".join(sections),
        }, feedback_rules, "power_content", product["key"])
        if blocked_hits:
            continue
        index = len(rows) + 1
        axis = item.get("message_axis") or "serp_whitespace"
        focus = item.get("focus") or (context.get("preferred_focus") or [product["name"]])[0]
        rows.append({
            "id": f"{product['key']}-source-topic-{variation['variation_key'][:6]}-{index}",
            "fingerprint": _fingerprint({"product": product["key"], "title": title,
                                         "season": variation["season_key"], "source_ids": source_ids}),
            "pattern": axis, "message_axis": axis, "title": title,
            "target_query": item.get("target_query") or product.get("serpKw") or product["name"],
            "intent": item.get("intent") or "검색 후 탐색", "focus": focus,
            "reader_question": context.get("reader_question"),
            "editorial_thesis": context.get("editorial_thesis"),
            "angle": context.get("editorial_thesis") or f"SERP의 ‘{saturated}’ 반복에서 벗어난 독자 질문",
            "sections": sections,
            "faq": list(item.get("faq") or [])[:2],
            "image_brief": f"{SCENES.get(product['key'], SCENES['home'])[(index - 1) % 3]}. 독자의 판단 장면을 텍스트·숫자·로고 없이 프리미엄 3D 애니메이션으로 표현.",
            "serp_basis": basis, "serp_signature": variation["serp_signature"],
            "variation_key": variation["variation_key"], "season_context": season,
            "guide_pattern_id": guide_pattern_for(axis, guide)["id"],
            "guide_quality": {
                "guide_version": (guide or {}).get("guide_version") or GUIDE_VERSION,
                "requires_concrete_reader_question": True,
                "requires_comparison_or_checklist": True,
                "requires_official_cta": True,
                "body_min_char_count": ((guide or {}).get("power_content") or {}).get("body_min_length", 700),
                "insurance_price_claim_requires_conditions": True,
                "description_source": ((guide or {}).get("power_content") or {}).get("description_source", "landing_continuous_excerpt"),
            },
            "source": "사용자 제공 캡처 구조화 컨텍스트 · 월간 SERP 결합",
            "source_grounding": {
                "status": "landing_grounded" if (context.get("landing") or {}).get("verified") else "structured_capture_grounded",
                "source_ids": source_ids,
                "competitor_copy_use": "pattern_only",
                "numeric_claims_used": False,
            },
            "insurance_review": insurance_review(item.get("review_status"), source_ids),
            "review_lab_feedback": {
                "applied_rules_version": (feedback_rules or {}).get("schema_version"),
                "blocked_phrase_hits": blocked_hits,
                "operator_decision": "pending",
                "reason_codes": ["usable_but_review_needed"] if item.get("review_status") != "자동 위험표현 없음" else [],
            },
        })
    return rows[:3]


def power_topics(product, keyword, angle, table_stakes, basis, planning_month, season, variation,
                 content_history=None, feedback_rules=None, guide=None, source_context=None):
    name = product.get("serpKw") or product["name"]
    own_terms = [term for term in product.get("special") or [] if term != angle]
    context_terms = [term for term in (source_context or {}).get("comparison_terms") or [] if term != angle]
    season_keywords = [str(term).replace(" ", "") for term in season.get("keywords") or []]
    season_terms = [term for term in own_terms
                    if any(term.replace(" ", "") in item or item in term.replace(" ", "")
                           for item in season_keywords)]
    second = (context_terms or season_terms or own_terms or [name])[0]
    saturated = "·".join(table_stakes[:2]) or "공통 보장 나열"
    specs = [
        ("serp_whitespace", f"{keyword} 검색 뒤 {_josa(angle, '을', '를')} 따져볼 질문", "검색 후 탐색", angle,
         ["검색 결과에서 반복된 표현", f"{angle} 기준에서 빠지기 쉬운 조건", "보험료 계산에 입력할 항목", "최종 화면에서 기록할 내용"]),
        ("decision_detail", f"{name} 보험료 전에 맞춰볼 세 가지 조건", "비교·의사결정", second,
         ["가입 목적과 기간 맞추기", f"{angle}·{second} 선택 항목 맞추기", "같은 조건으로 보험료 계산하기", "청약 화면에서 차이 찾기"]),
        ("scope_compare", f"{_josa(angle, '과', '와')} {second}, 함께 볼 때 달라지는 점", "항목 비교", angle,
         [f"{_josa(angle, '이', '가')} 궁금해지는 생활 상황", f"{_josa(second, '과', '와')} 겹치지 않는 지점", "지급사유와 제외 조건 나란히 읽기", "선택 항목 기록하기"]),
        ("official_path", f"{name} 설계 화면을 끝까지 읽는 순서", "가입 흐름 탐색", second,
         ["상품 안내에서 질문 만들기", "설계 화면에서 선택 항목 찾기", "보험료 결과의 조건 읽기", "최종 청약 내용 대조하기"]),
        ("terms_navigation", f"{_josa(angle, '을', '를')} 약관 목차에서 빠르게 찾는 법", "약관 정보 탐색", angle,
         ["용어 정의에서 시작하기", "지급사유 조항 연결하기", "보장하지 않는 경우 함께 읽기", "기준일과 질문 기록하기"]),
        ("real_life", f"{_josa(angle, '이', '가')} 궁금해지는 생활 장면부터 약관까지", "상황 정보 탐색", angle,
         ["실제 생활 질문으로 바꾸기", "광고 표현과 약관 용어 구분하기", "적용 조건을 사례 없이 설명하기", "내 조건으로 다시 계산하기"]),
    ]
    source_focuses = list((source_context or {}).get("preferred_focus") or [])
    if (source_context or {}).get("source_ids"):
        third = next((term for term in source_focuses if term not in {angle, second}), own_terms[-1] if own_terms else name)
        reader_question = (source_context or {}).get("reader_question") or f"{name}에서 {angle} 조건을 어떻게 읽어야 할까?"
        specs = [
            ("scope_compare", f"{angle}·{second} 지급 기준을 나누는 법", "항목 비교", angle,
             [reader_question, f"{angle}·{second}의 약관 정의 구분", "지급사유와 적용 시점 나란히 보기", "보장하지 않는 경우와 질문 기록"]),
            ("terms_navigation", f"{name} {third} 약관 조항 찾기", "약관 정보 탐색", third,
             [f"{third} 관련 생활 표현 정리", "약관의 용어 정의에서 시작", "지급 조항과 제외 조항 연결", "기준일과 남은 질문 기록"]),
            ("official_path", f"{name} 설계 전에 적을 세 가지 질문", "가입 흐름 탐색", angle,
             ["랜딩의 공식 행동 경로 확인", f"{angle} 선택 항목과 기간 기록", "같은 입력 조건으로 보험료 확인", "최종 청약과 처음 메모 대조"]),
        ]
    if season.get("name") and not (source_context or {}).get("source_ids"):
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
    if season.get("name") and not (source_context or {}).get("source_ids"):
        seasonal_spec = next(row for row in specs if row[0] == "seasonal_scene")
        rotated = [seasonal_spec, *[row for row in rotated if row[0] != "seasonal_scene"]]
    # 같은 기준월의 기존 후보는 이번 일괄 갱신에서 교체 대상이다. 이를 이력 중복으로
    # 막으면 규칙을 바꿔도 새 주제가 0~1개만 남으므로, 이전 월 이력만 카니벌라이제이션
    # 기준으로 사용한다.
    used_titles = {re.sub(r"\s+", "", str(row.get("title") or "")).lower()
                   for row in ((content_history or {}).get("entries") or [])
                   if row.get("product_key") == product["key"]
                   and str(row.get("planning_month") or "") != str(planning_month)}
    rows = source_power_topics(product, source_context or {}, table_stakes, basis, planning_month,
                               season, variation, used_titles, feedback_rules, guide)
    grounding = product_source_basis(source_context or {})
    for spec in rotated:
        if len(rows) == 3:
            break
        pattern, title, intent, focus, sections, *query_override = spec
        fitted = apply_feedback_rules(_fit([title, f"{name} 선택 전에 질문을 정리하는 법"], 7, 28), feedback_rules)
        safe_sections = [apply_feedback_rules(section, feedback_rules) for section in sections]
        blocked_hits = feedback_findings({
            "title": fitted,
            "angle": f"SERP의 ‘{saturated}’ 반복에서 벗어나 {_josa(AXIS_LABELS.get(pattern, '생활 질문'), '으로', '로')} 전개",
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
            "reader_question": (source_context or {}).get("reader_question"),
            "editorial_thesis": (source_context or {}).get("editorial_thesis"),
            "angle": f"SERP의 ‘{saturated}’ 반복에서 벗어나 {_josa(AXIS_LABELS.get(pattern, '생활 질문'), '으로', '로')} 전개",
            "sections": safe_sections,
            "faq": [f"{_josa(focus, '을', '를')} 볼 때 먼저 비교할 항목은 무엇인가요?", f"{name} 보험료 계산 조건은 어떻게 맞추나요?"],
            "image_brief": f"{SCENES.get(product['key'], SCENES['home'])[(index-1) % 3]}. 텍스트·숫자·로고 없이 프리미엄 3D 애니메이션으로 표현.",
            "serp_basis": basis, "serp_signature": variation["serp_signature"],
            "variation_key": variation["variation_key"], "season_context": season,
            "guide_pattern_id": guide_pattern_for(pattern, guide)["id"],
            "guide_quality": {
                "guide_version": (guide or {}).get("guide_version") or GUIDE_VERSION,
                "requires_concrete_reader_question": True,
                "requires_comparison_or_checklist": True,
                "requires_official_cta": True,
                "body_min_char_count": ((guide or {}).get("power_content") or {}).get("body_min_length", 700),
                "insurance_price_claim_requires_conditions": True,
                "description_source": ((guide or {}).get("power_content") or {}).get("description_source", "landing_continuous_excerpt"),
            },
            "source": "월간 SERP 변화·시즌 캘린더 결합" + (" · 사용자 제공 자료의 용어·구조" if grounding.get("source_ids") else ""),
            "source_grounding": grounding,
            "insurance_review": insurance_review("사람 심의 필요", grounding.get("source_ids")),
            "review_lab_feedback": {
                "applied_rules_version": (feedback_rules or {}).get("schema_version"),
                "blocked_phrase_hits": blocked_hits,
                "operator_decision": "pending",
                "reason_codes": ["usable_but_review_needed"],
            },
        })
        if len(rows) == 3:
            break
    if len(rows) < 3:
        # 과거 이력에 6개 기본 제목이 모두 남아 있어도 다음 달 주제가 0개가
        # 되지 않도록, 같은 판단 기준을 유지한 채 문장 구조만 변주한다.
        fallback_third = next((term for term in own_terms if term != second), name)
        fallback_specs = [
            ("question_plus_next_step", f"{name} {angle} 확인 질문", "검색 후 탐색", angle, f"{name} {angle}"),
            ("split_conditions", f"{name} {second} 적용 조건 비교", "비교·의사결정", second, f"{name} {second}"),
            ("scene_plus_term", f"{name}에서 {_josa(fallback_third, '을', '를')} 보는 장면", "상황 정보 탐색", fallback_third, f"{name} {fallback_third}"),
        ]
        for fallback_pattern, fallback_title, fallback_intent, fallback_focus, fallback_query in fallback_specs:
            fitted = apply_feedback_rules(_fit([fallback_title], 7, 34), feedback_rules)
            key = re.sub(r"\s+", "", fitted).lower()
            if key in used_titles or any(re.sub(r"\s+", "", row["title"]).lower() == key for row in rows):
                continue
            blocked_hits = feedback_findings({"title": fitted, "focus": fallback_focus}, feedback_rules, "power_content", product["key"])
            if blocked_hits:
                continue
            index = len(rows) + 1
            fallback_sections = {
                "question_plus_next_step": [
                    f"{fallback_focus} 검색자가 실제로 묻는 질문", "가입 시점과 대상부터 적기",
                    "공식 안내에서 필요한 답 찾기", "답이 남지 않은 질문 표시하기",
                ],
                "split_conditions": [
                    f"{fallback_focus} 용어 정의부터 구분", "지급사유와 적용 기간 나누기",
                    "보장하지 않는 경우를 옆에 놓기", "같은 조건으로 선택 항목 비교하기",
                ],
                "scene_plus_term": [
                    f"{fallback_focus}이 궁금해지는 생활 장면", "사고·진단 전후에 기록할 사실",
                    "필요 서류와 확인 경로 정리", "약관 조항과 실제 장면 대조하기",
                ],
            }[fallback_pattern]
            rows.append({
                "id": f"{product['key']}-serp-topic-{variation['variation_key'][:6]}-{index}",
                "fingerprint": _fingerprint({"product": product["key"], "title": fitted, "season": variation["season_key"], "serp": variation["serp_signature"]}),
                "pattern": fallback_pattern, "message_axis": fallback_pattern, "title": fitted,
                "target_query": fallback_query, "intent": fallback_intent, "focus": fallback_focus,
                "reader_question": (source_context or {}).get("reader_question"),
                "editorial_thesis": (source_context or {}).get("editorial_thesis"),
                "angle": f"SERP의 ‘{saturated}’ 반복에서 벗어나 {fallback_focus} 확인 행동으로 전개",
                "sections": fallback_sections,
                "faq": [f"{_josa(fallback_focus, '을', '를')} 볼 때 먼저 비교할 항목은 무엇인가요?", f"{name} 보험료 계산 조건은 어떻게 맞추나요?"],
                "image_brief": f"{SCENES.get(product['key'], SCENES['home'])[(index - 1) % 3]}. 텍스트·숫자·로고 없이 프리미엄 3D 애니메이션으로 표현.",
                "serp_basis": basis, "serp_signature": variation["serp_signature"], "variation_key": variation["variation_key"],
                "season_context": season, "guide_pattern_id": guide_pattern_for(fallback_pattern, guide)["id"],
                "guide_quality": {"guide_version": (guide or {}).get("guide_version") or GUIDE_VERSION, "requires_concrete_reader_question": True, "requires_comparison_or_checklist": True, "requires_official_cta": True, "body_min_char_count": ((guide or {}).get("power_content") or {}).get("body_min_length", 700), "description_source": ((guide or {}).get("power_content") or {}).get("description_source", "landing_continuous_excerpt")},
                "source": "월간 SERP 변화·시즌 캘린더 결합 · 이력 중복 회피 변주",
                "source_grounding": grounding,
                "insurance_review": insurance_review("사람 심의 필요", grounding.get("source_ids")),
                "review_lab_feedback": {"applied_rules_version": (feedback_rules or {}).get("schema_version"), "blocked_phrase_hits": blocked_hits, "operator_decision": "pending", "reason_codes": ["usable_but_review_needed"]},
            })
            if len(rows) == 3:
                break
    return rows


def link_materials(sa_rows, topic_rows, image_rows):
    """SA·파워콘텐츠·썸네일이 같은 메시지 축을 가리키도록 연결한다."""
    for index, row in enumerate(sa_rows):
        topic = next((item for item in topic_rows if item.get("message_axis") == row.get("message_axis")), None)
        topic = topic or (topic_rows[index % len(topic_rows)] if topic_rows else None)
        image = image_rows[index % len(image_rows)] if image_rows else None
        row["linked_power_content"] = ({"topic_id": topic.get("id"), "title": topic.get("title")}
                                        if topic else None)
        row["linked_thumbnail"] = ({"concept_id": image.get("concept_id"), "scene": image.get("scene")}
                                   if image else None)
    for index, topic in enumerate(topic_rows):
        sa = next((item for item in sa_rows if item.get("message_axis") == topic.get("message_axis")), None)
        sa = sa or (sa_rows[index % len(sa_rows)] if sa_rows else None)
        topic["linked_sa_material_id"] = sa.get("material_id") if sa else None
    return sa_rows, topic_rows


def generate(products, analysis, volume, manifest=None, dom=None, planning_month=None,
             seasonal=None, calendar=None, content_history=None, image_history=None,
             feedback_rules=None, guide=None, source_context=None):
    manifest, dom, source_context = manifest or {}, dom or {}, source_context or {}
    output = []
    for product in products.get("products") or []:
        if product.get("cat") == "사이트":
            continue
        observed = ((analysis.get("products") or {}).get(product["key"]) or {})
        source_product = product_source_context(source_context, product["key"])
        source_serp = source_product.get("serp") or {}
        ads, common = observed.get("observed_ads") or [], observed.get("common_soju") or []
        if not ads:
            continue
        keyword = volume_keyword(volume, product)
        observed_angles = list(dict.fromkeys([*common, *_ranked(observed.get("soju") or [])]))
        product_gaps = [x for x in product.get("special") or []
                        if not out_of_scope(x, product) and not any(x in c or c in x for c in observed_angles)]
        gaps = list(dict.fromkeys([*(source_product.get("preferred_focus") or []),
                                   *(source_serp.get("whitespace_angles") or []), *product_gaps]))
        angle = (gaps or product.get("special") or product.get("core") or [product["name"]])[0]
        diff = date_diff(ads)
        monitoring, dom_rows = monitoring_for(product["key"], manifest, dom, diff["latest"] or observed.get("latest_date"))
        raw_texts = [f"{a.get('title', '')} {a.get('desc', '')} {a.get('promo', '')}" for a in ads]
        raw_texts += [row.get("text", "") for row in dom_rows]
        raw_texts += [row.get("title", "") for row in source_serp.get("competitor_observations") or []]
        patterns = _text_patterns(raw_texts)
        pattern_date = monitoring["auto_pattern_latest"] or monitoring["reviewed_observation_latest"] or "기준일 없음"
        plan_month = planning_month or monitoring["planning_month"]
        source_latest = product_source_basis(source_product, source_context).get("source_latest")
        basis = f"{plan_month} 월간 SERP · 캡처 {monitoring['capture_latest'] or source_latest or '없음'} · 패턴 {pattern_date} · 최근 35일 {monitoring['capture_count_35d']}회"
        table_stakes = list(dict.fromkeys([*(source_serp.get("table_stakes") or []), *common, *observed_angles]))[:5]
        season = season_context(product, plan_month, seasonal, calendar)
        season_keywords = [str(term).replace(" ", "") for term in season.get("keywords") or []]
        seasonal_angle = next((term for term in product.get("special") or []
                               if any(term.replace(" ", "") in keyword or keyword in term.replace(" ", "")
                                      for keyword in season_keywords)), None)
        if seasonal_angle and not source_product.get("source_ids"):
            angle = seasonal_angle
        signature = serp_signature(patterns, diff, table_stakes, ads)
        variation = variation_context(product, plan_month, season, signature)
        sa = sa_recommendations(product, keyword, angle, table_stakes, basis, season, variation,
                                feedback_rules, guide, source_product)
        images = image_directions(product, angle, patterns, basis, plan_month, season, variation, image_history, feedback_rules)
        topics = power_topics(product, keyword, angle, table_stakes, basis, plan_month, season, variation,
                              content_history, feedback_rules, guide, source_product)
        sa, topics = link_materials(sa, topics, images)
        basis_info = guide_basis(guide)
        qa = {
            "guide_version": basis_info["guide_version"],
            "sa_candidate_count": len(sa),
            "power_content_topic_count": len(topics),
            "thumbnail_slot_count": len(images),
            "required_checks": (guide or {}).get("quality_gate", {}).get("required_for_every_material") or [],
            "hard_fail_rules": (guide or {}).get("quality_gate", {}).get("hard_fail") or [],
            "source_context_status": product_source_basis(source_product, source_context)["status"],
            "status": "ready_for_human_review" if len(sa) == 5 and len(topics) == 3 and len(images) == 4 else "needs_generation_review",
        }
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
            "guide_basis": basis_info,
            "quality_assurance": qa,
            "material_source_context": product_source_basis(source_product, source_context),
            "material_refresh": {
                "rules_version": MATERIAL_RULES_VERSION,
                "scope": "sa_powercontent_thumbnail",
                "status": "regenerated_from_current_rules",
            },
        })
    dates = [analysis.get("asof"), manifest.get("asof"), dom.get("asof"), volume.get("asof"), source_context.get("asof")]
    asof = _latest(*dates) or date.today().isoformat()
    return {
        "_comment": "월간 SERP·랜딩 캡처 구조화 컨텍스트·자동 DOM 패턴·검색량을 결합한 공통 소재 기획안. 경쟁사 원문과 검증 전 수치는 자동 제안에 복사하지 않는다.",
        "schema_version": 4,
        "material_rules_version": MATERIAL_RULES_VERSION,
        "refresh_scope": "all_generated_materials",
        "refresh_note": "기존 후보를 현재 SA·파워콘텐츠·썸네일 규칙으로 재생성",
        "asof": asof,
        "planning_month": planning_month or asof[:7],
        "cadence": "weekly_capture_monthly_material_plan",
        "image_refresh_cadence": "monthly",
        "guide_basis": guide_basis(guide),
        "material_source_context_basis": source_context_basis(source_context),
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
        read(GUIDE_RULES, {}, root),
        read(SOURCE_CONTEXT, {}, root),
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
