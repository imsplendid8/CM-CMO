#!/usr/bin/env python3
"""월간 SERP 관측을 SA·이미지·파워콘텐츠의 공통 소재 기획안으로 변환한다.

경쟁사 원문은 화면의 비교 근거로만 남긴다. 자동 제안에는 검색 의도, 반복 패턴,
상품 마스터의 범위, 아직 덜 쓰인 각도만 전달해 경쟁사 문구를 그대로 복제하지 않는다.
"""
from __future__ import annotations

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


def image_directions(product, angle, patterns, basis):
    scenes = SCENES.get(product["key"], SCENES["home"])
    roles = ("주 상황", "검색 의도 보조", "전환 보조")
    return [{
        "role": roles[index],
        "scene": scene,
        "composition": "핵심 인물·사물을 중앙에 크게 두고 작은 화면에서도 상황이 바로 보이는 정사각 구도",
        "style": "친근하지만 유아틱하지 않은 프리미엄 3D 애니메이션, 현실적인 생활 공간과 부드러운 조명",
        "text_overlay": False,
        "why": f"{basis} · {angle} 탐색 의도와 {patterns[0][0] if patterns else '상품 상황'} 패턴 연결",
    } for index, scene in enumerate(scenes[:3])]


def power_topics(product, keyword, angle, table_stakes, basis):
    name = product.get("serpKw") or product["name"]
    second = (table_stakes or product.get("special") or [angle])[0]
    specs = [
        ("serp_gap", f"{keyword}, 가입 전 {angle} 확인하는 순서", "가입 전 준비", angle),
        ("coverage_question", f"{angle} 관련 특약은 무엇을 확인해야 할까", "보장 정보 탐색", angle),
        ("decision_guide", f"{name} 보험료와 가입조건 확인 순서", "비교·의사결정", second),
    ]
    rows = []
    for index, (pattern, title, intent, focus) in enumerate(specs, 1):
        rows.append({
            "id": f"{product['key']}-serp-topic-{index}",
            "pattern": pattern,
            "title": _fit([title, f"{name} 가입 전 확인할 핵심 기준"], 15, 34),
            "target_query": keyword if index != 2 else f"{name} {focus}",
            "intent": intent,
            "focus": focus,
            "angle": f"경쟁 광고의 짧은 보장 나열에서 빠진 ‘{focus} 확인 기준’을 실제 생활 질문으로 확장",
            "sections": [f"{keyword} 검색자가 먼저 묻는 것", f"{focus} 지급사유와 제외 조건", "보험료·가입조건을 같은 기준으로 보는 법", "가입 전 최종 체크리스트"],
            "faq": [f"{focus} 관련 내용은 무엇을 확인해야 하나요?", f"{name} 보험료는 무엇에 따라 달라지나요?"],
            "image_brief": f"{SCENES.get(product['key'], SCENES['home'])[index-1]}. 텍스트·숫자·로고 없이 프리미엄 3D 애니메이션으로 표현.",
            "serp_basis": basis,
            "source": "월간 SERP 운영소재 분석",
        })
    return rows


def generate(products, analysis, volume, manifest=None, dom=None):
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
        basis = f"{monitoring['planning_month']} 월간 SERP · 캡처 {monitoring['capture_latest'] or '없음'} · 패턴 {pattern_date} · 최근 35일 {monitoring['capture_count_35d']}회"
        table_stakes = list(dict.fromkeys([*common, *observed_angles]))[:3]
        sa = sa_recommendations(product, keyword, angle, table_stakes, basis)
        images = image_directions(product, angle, patterns, basis)
        topics = power_topics(product, keyword, angle, table_stakes, basis)
        output.append({
            "product_key": product["key"],
            "month": monitoring["planning_month"],
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
            "power_content_topics": topics,
            "analysis_status": "ready",
        })
    dates = [analysis.get("asof"), manifest.get("asof"), dom.get("asof"), volume.get("asof")]
    asof = _latest(*dates) or date.today().isoformat()
    return {
        "_comment": "월간 SERP 캡처·자동 DOM 패턴·검토 관측·검색량을 결합한 공통 소재 기획안. 경쟁사 원문은 자동 제안에 복사하지 않는다.",
        "schema_version": 2,
        "asof": asof,
        "planning_month": asof[:7],
        "cadence": "weekly_capture_monthly_material_plan",
        "products": output,
    }


def main(root=ROOT):
    result = generate(
        read("data/products.json", {}, root),
        read("serp/ad_analysis.json", {}, root),
        read("data/volume.json", {}, root),
        read("serp/manifest.json", {}, root),
        read("serp/dom_observations.json", {}, root),
    )
    output = root / "data/adcopy/serp-candidates.json"
    atomic_json_write(output, result)
    print(f"[OK] {output.relative_to(root)} · 상품 {len(result['products'])} · 월간 SERP 통합 소재 기획")
    return result


if __name__ == "__main__":
    main()
