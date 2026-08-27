#!/usr/bin/env python3
"""월간 SERP 관측을 SA·이미지·파워콘텐츠의 공통 소재 기획안으로 변환한다.

경쟁사 원문은 화면의 비교 근거로만 남긴다. 자동 제안에는 검색 의도, 반복 패턴,
상품 마스터의 범위, 아직 덜 쓰인 각도만 전달해 경쟁사 문구를 그대로 복제하지 않는다.
"""
from __future__ import annotations

import argparse
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
    "driver-safe-animation-v3.png": "도심 도로에서 안전운전하는 운전자",
    "driver-traffic-3d.png": "교차로 신호와 앞차를 확인하는 운전자",
    "driver-schoolzone-animation-v4.png": "스쿨존 횡단보도 앞에서 감속하는 운전자",
    "driver-accident-animation-v4.png": "가벼운 접촉사고 뒤 현장을 확인하는 운전자",
    "driver-rain-animation-v4.png": "비 오는 저녁 도로에서 방어운전하는 운전자",
    "event-safety-3d.png": "행사 현장의 시설과 동선을 확인하는 운영자",
    "event-safety-animation-v3.png": "공연 시작 전 안전을 점검하는 스태프",
    "family-baby-animation-v3.png": "아기와 가족이 함께 건강을 준비하는 장면",
    "family-pregnancy-3d.png": "예비 부모가 출산 준비물을 확인하는 장면",
    "golf-hole-animation-v3.png": "그린 위 홀인원 순간을 기뻐하는 골퍼",
    "golf-holeinone-3d.png": "깃대와 공이 보이는 홀인원 장면",
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
    "home": ["calculator-animation-v3.png", "driver-safe-animation-v3.png", "home-fire-animation-v3.png", "health-check-animation-v3.png", "travel-airport-animation-v3.png"],
    "hrmf": ["home-fire-animation-v3.png", "home-leak-animation-v3.png", "home-weather-3d.png", "event-safety-animation-v3.png", "calculator-animation-v3.png"],
    "golf": ["golf-hole-animation-v3.png", "golf-holeinone-3d.png", "calculator-animation-v3.png", "event-safety-animation-v3.png", "driver-safe-animation-v3.png"],
    "cncr": ["health-check-animation-v3.png", "health-review-3d.png", "family-baby-animation-v3.png", "family-pregnancy-3d.png", "calculator-animation-v3.png"],
    "dntl": ["dental-consult-animation-v3.png", "dental-consult-3d.png", "health-check-animation-v3.png", "health-review-3d.png", "calculator-animation-v3.png"],
    "driver": ["driver-safe-animation-v3.png", "driver-traffic-3d.png", "driver-schoolzone-animation-v4.png", "driver-accident-animation-v4.png", "driver-rain-animation-v4.png"],
    "woman": ["health-check-animation-v3.png", "health-review-3d.png", "family-baby-animation-v3.png", "family-pregnancy-3d.png", "calculator-animation-v3.png"],
    "birth": ["family-baby-animation-v3.png", "family-pregnancy-3d.png", "health-check-animation-v3.png", "health-review-3d.png", "calculator-animation-v3.png"],
    "overseas": ["travel-airport-animation-v3.png", "travel-airport-3d.png", "student-campus-animation-v3.png", "student-overseas-3d.png", "calculator-animation-v3.png"],
    "overseaslong": ["student-campus-animation-v3.png", "student-overseas-3d.png", "travel-airport-animation-v3.png", "travel-airport-3d.png", "calculator-animation-v3.png"],
    "holeinone": ["golf-hole-animation-v3.png", "golf-holeinone-3d.png", "calculator-animation-v3.png", "event-safety-3d.png", "driver-safe-animation-v3.png"],
    "event": ["event-safety-animation-v3.png", "event-safety-3d.png", "home-fire-animation-v3.png", "calculator-animation-v3.png", "home-weather-3d.png"],
    "chronic": ["health-check-animation-v3.png", "health-review-3d.png", "calculator-animation-v3.png", "family-baby-animation-v3.png", "dental-consult-animation-v3.png"],
}


def read(rel, default, root=ROOT):
    try:
        return json.loads((root / rel).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


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


def sa_recommendations(product, keyword, angle, table_stakes, basis):
    name = product.get("serpKw") or product["name"]
    other = (table_stakes or product.get("special") or [angle])[0]
    rows = [
        {
            "strategy": "검색결과 운영형",
            "title": _fit([f"{keyword} 보장 확인", f"{name} 보장 확인"], 4, 15),
            "description": _fit([f"{angle} 관련 내용과 보험료를 가입 전에 한 번에 확인해 보세요.", f"{name} 보장내용과 보험료를 온라인에서 확인해 보세요."], 20, 45),
            "additional_description": _fit([f"{angle} 관련 특약과 제외 조건을 상품자료에서 확인해 보세요.", f"{name} 가입 전 보장내용과 제외 조건을 확인해 보세요."], 2, 45),
            "promo": _fit(["보험료 확인", "보장내용 확인"], 2, 14),
            "sublinks": ["보험료계산", "보장내용", "가입조건", "상품안내"],
            "why": f"{basis} · 실제 SERP의 상품명+행동어 구조를 적용",
        },
        {
            "strategy": "상황·담보 차별형",
            "title": _fit([f"{angle} 대비 {name}", f"{angle} 특약 확인", f"{name} 특약 확인"], 4, 15),
            "description": _fit([f"{angle}부터 {other}까지 필요한 항목과 가입조건을 차례로 살펴보세요.", f"{angle} 관련 보장내용과 가입조건을 가입 전에 확인해 보세요."], 20, 45),
            "additional_description": _fit([f"{angle} 상황이 걱정될 때 확인할 보장내용과 가입조건을 정리했습니다.", f"{angle} 관련 보장내용을 상품자료에서 확인해 보세요."], 2, 45),
            "promo": _fit(["가입조건 확인", "특약 확인"], 2, 14),
            "sublinks": ["보장내용", "가입조건", "보험료계산", "가입안내"],
            "why": f"경쟁 공통 소구를 그대로 반복하지 않고 ‘{angle}’ 탐색 의도를 전면 배치",
        },
        {
            "strategy": "공식채널 선택형",
            "title": _fit([f"한화손보 {name}", f"{name} 공식 안내"], 4, 15),
            "description": _fit([f"{name} 보장내용과 보험료, 가입 절차를 공식 채널에서 확인해 보세요.", f"{name} 가입 전 필요한 항목을 공식 채널에서 살펴보세요."], 20, 45),
            "additional_description": _fit(["보장내용과 보험료, 가입 절차를 한화손보 다이렉트에서 확인하세요."], 2, 45),
            "promo": _fit(["공식 채널", "상품 안내"], 2, 14),
            "sublinks": ["보험료계산", "상품안내", "보장내용", "가입안내"],
            "why": "운영 광고에서 반복되는 공식성·명확한 다음 행동을 반영",
        },
    ]
    return rows


def monthly_image_assets(product_key, planning_month):
    """기준월마다 상품 후보군에서 중복 없는 4개 원본을 순환 선정한다."""
    pool = list(dict.fromkeys(IMAGE_POOLS.get(product_key) or IMAGE_POOLS["home"]))
    if len(pool) < 4:
        raise ValueError(f"{product_key}: 월간 썸네일 후보 원본이 4개 미만")
    try:
        year, month = (int(value) for value in str(planning_month).split("-")[:2])
    except (TypeError, ValueError):
        year, month = date.today().year, date.today().month
    offset = (year * 12 + month + sum(ord(char) for char in product_key)) % len(pool)
    rotated = pool[offset:] + pool[:offset]
    return rotated[:4]


def image_directions(product, angle, patterns, basis, planning_month):
    assets = monthly_image_assets(product["key"], planning_month)
    roles = ("파워링크 대표", "보험료 탐색", "보장내용 탐색", "가입안내 탐색")
    return [{
        "proposal_id": f"{product['key']}-{planning_month}-{index + 1:02d}",
        "role": roles[index],
        "scene": ASSET_SCENES[asset],
        "asset": f"assets/insurance/{asset}",
        "composition": "핵심 인물·사물을 중앙에 크게 두고 작은 화면에서도 상황이 바로 보이는 정사각 구도",
        "style": "친근하지만 유아틱하지 않은 프리미엄 3D 애니메이션, 현실적인 생활 공간과 부드러운 조명",
        "text_overlay": False,
        "refresh_cadence": "monthly",
        "planning_month": planning_month,
        "generation_brief": f"{product['name']} 검색 맥락을 {ASSET_SCENES[asset]}으로 표현. 텍스트·숫자·로고 없이 정사각형 3D 애니메이션으로 제작.",
        "why": f"{basis} · 상품종목을 우선 고정하고 SERP의 {patterns[0][0] if patterns else '검색 행동'} 패턴은 역할 선정에만 연결",
    } for index, asset in enumerate(assets)]


def power_topics(product, keyword, angle, table_stakes, basis, planning_month):
    name = product.get("serpKw") or product["name"]
    second = (table_stakes or product.get("special") or [angle])[0]
    specs = [
        ("serp_gap", f"{keyword}, 가입 전 {angle} 확인하는 순서", "가입 전 준비", angle,
         [f"{angle}이 필요한 상황", "지급사유와 보장하지 않는 경우", "가입 전 확인 순서", "최종 체크리스트"]),
        ("coverage_question", f"{angle} 특약의 보장 범위를 읽는 방법", "보장 정보 탐색", angle,
         [f"{angle} 특약을 찾는 이유", "약관의 지급사유 읽기", "한도·기간·제외 조건", "청약 화면과 대조하기"]),
        ("decision_guide", f"{name} 보험료와 가입조건 확인 순서", "비교·의사결정", second,
         ["가입 목적 먼저 정하기", "같은 담보 조건으로 맞추기", "보험료에 영향을 주는 항목", "최종 선택 전 확인"]),
        ("exclusion_guide", f"{name} 보장하지 않는 경우 찾는 법", "약관 정보 탐색", angle,
         ["보장 내용과 제외 조건 함께 보기", "면책·감액기간 확인", "알릴 의무 확인", "궁금한 조항 기록하기"]),
        ("claim_ready", f"{name} 청구 전에 준비할 체크리스트", "청구 준비", second,
         ["사고 직후 기록할 내용", "필요 서류 확인", "청구 절차와 기한", "접수 전 최종 점검"]),
        ("audience_fit", f"{name}, 내 상황에 필요한지 판단하는 법", "필요성 판단", angle,
         ["대비하려는 상황 정의", "현재 보장과 겹치는 항목", "필요한 기간과 범위", "가입 여부 판단 질문"]),
        ("terms_navigation", f"{name} 약관에서 먼저 찾아볼 항목", "약관 정보 탐색", angle,
         ["약관 목차 활용하기", "용어 정의 먼저 읽기", "지급사유와 제외 조항 연결", "확인한 기준일 기록"]),
        ("renewal_period", f"{name} 보험기간과 갱신 조건 보는 법", "계약 조건 탐색", second,
         ["보험기간과 납입기간 구분", "갱신 여부 확인", "보험료 변경 가능성", "장기 유지 가능성 점검"]),
        ("search_to_contract", f"{keyword} 검색 뒤 청약까지 확인할 것", "가입 전 준비", angle,
         ["검색 결과에서 질문 만들기", "상품설명서와 약관 대조", "보험료 계산 조건 확인", "청약 내용 최종 검토"]),
    ]
    try:
        year, month = (int(value) for value in str(planning_month).split("-")[:2])
    except (TypeError, ValueError):
        year, month = date.today().year, date.today().month
    offset = (year * 12 + month + sum(ord(char) for char in product["key"])) % len(specs)
    specs = (specs[offset:] + specs[:offset])[:3]
    rows = []
    for index, (pattern, title, intent, focus, sections) in enumerate(specs, 1):
        rows.append({
            "id": f"{product['key']}-serp-topic-{index}",
            "pattern": pattern,
            "title": _fit([title, f"{name} 가입 전 확인할 핵심 기준"], 15, 34),
            "target_query": keyword if index != 2 else f"{name} {focus}",
            "intent": intent,
            "focus": focus,
            "angle": f"경쟁 광고의 짧은 보장 나열에서 빠진 ‘{focus} 확인 기준’을 실제 생활 질문으로 확장",
            "sections": sections,
            "faq": [f"{focus} 관련 내용은 무엇을 확인해야 하나요?", f"{name} 보험료는 무엇에 따라 달라지나요?"],
            "image_brief": f"{SCENES.get(product['key'], SCENES['home'])[index-1]}. 텍스트·숫자·로고 없이 프리미엄 3D 애니메이션으로 표현.",
            "serp_basis": basis,
            "source": "월간 SERP 운영소재 분석",
        })
    return rows


def generate(products, analysis, volume, manifest=None, dom=None, planning_month=None):
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
        sa = sa_recommendations(product, keyword, angle, table_stakes, basis)
        images = image_directions(product, angle, patterns, basis, plan_month)
        topics = power_topics(product, keyword, angle, table_stakes, basis, plan_month)
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
            "observed_count": len(ads),
            "copy_direction": f"{keyword} 상품명·행동어를 기본으로 두고 {angle} 상황을 차별 각도로 사용",
            "visual_direction": f"보험종목 장면: {images[0]['scene']}",
            "operating_gap": {
                "current_gap": "실제 SERP의 상품명·행동어·확장소재 구조보다 기존 제안이 추상적",
                "direction": f"{keyword} 검색자의 다음 행동과 {angle} 상황을 제목·설명·추가설명에 일관되게 연결",
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
                "selection": "monthly_rotating_product_pool",
            },
            "power_content_topics": topics,
            "analysis_status": "ready",
        })
    dates = [analysis.get("asof"), manifest.get("asof"), dom.get("asof"), volume.get("asof")]
    asof = _latest(*dates) or date.today().isoformat()
    return {
        "_comment": "월간 SERP 캡처·자동 DOM 패턴·검토 관측·검색량을 결합한 공통 소재 기획안. 경쟁사 원문은 자동 제안에 복사하지 않는다.",
        "schema_version": 2,
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


def main(root=ROOT, planning_month=None, archive_images=False):
    planning_month = planning_month or date.today().strftime("%Y-%m")
    result = generate(
        read("data/products.json", {}, root),
        read("serp/ad_analysis.json", {}, root),
        read("data/volume.json", {}, root),
        read("serp/manifest.json", {}, root),
        read("serp/dom_observations.json", {}, root),
        planning_month,
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
