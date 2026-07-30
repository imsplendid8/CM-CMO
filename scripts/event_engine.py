#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""이벤트 기반 뉴스·시즌 캘린더 추천 엔진 (P0-EVENT · 규칙 기반).

전체 뉴스·시즌 캘린더를 결합해 상품별 문구 추천을 산출한다. 특정 이벤트(장마·폭염 등)에
하드코딩하지 않고, 아래 소스를 통합해 이벤트를 만들고 상태·근거·추천을 계산한다:
  - 예정 이벤트: data/events/calendar.json (공휴일·개학·명절·휴가·대회·지역행사·캠페인)
  - 계절/기상: data/seasonal.json, data/signals.json(기상특보·트리거)
  - 뉴스: data/clips/<latest>.json (대형화재·결항·감염병·제도 변화 등 긴급 포함)
  - 검색량: data/volume.json / data/trends.json
  - 사용 이력: data/events/copy_history.json (fingerprint + 날짜 → cooldown)

이벤트 상태: upcoming / emerging / active / cooling / ended / follow_up.
각 추천은 확인된 사실·관련 상품·이벤트 상태·제목/설명/소제목·추천 이유+사용 데이터·유효 기간·
피해야 할 표현·추천 채널·상품 근거·심의 상태·confidence·fingerprint 를 포함한다.

가드레일: 공포 조장·사건 이용 가입 압박·담보/보험금 단정 문구는 생성하지 않는다(필터).
모든 추천은 '상품 근거 미확인 · 심의 검토 전 · 운영 후보'로 시작한다.
분류 불확실 뉴스는 문구를 만들지 않고 unclassified 검토 큐로 보낸다.

순수 함수(run/build_events/make_reco …)는 주입된 dict로 동작해 테스트가 fixture를 넣을 수 있다.
표준 라이브러리만 사용.
"""
import glob
import hashlib
import json
import os
import re
from datetime import date, datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KST = timezone(timedelta(hours=9))

LEAD_DAYS = 21          # upcoming→emerging 경계(예정일 앞)
TAIL_DAYS = 7           # active→cooling 경계(종료일 뒤)
COOLDOWN_DAYS = 14      # 같은 fingerprint 재추천 금지 기간
STATES = ("upcoming", "emerging", "active", "cooling", "ended", "follow_up")

# 가드레일: 생성 금지 표현(공포 조장 / 사건 이용 압박 / 담보·보험금 단정)
AVOID_FEAR = ["끔찍", "참사", "비극", "당신도", "큰일", "불행", "공포", "눈앞의 위험", "지금 안 하면"]
AVOID_PRESSURE = ["이 사고 보고도", "더 늦기 전에 가입", "안 하면 후회", "지금 가입 안 하면", "서둘러 가입"]
AVOID_GUARANTEE = ["무조건 보상", "전액 보장", "100% 지급", "보험금 확정", "보상 확정", "무조건 지급", "보장 확정"]
AVOID_ALL = AVOID_FEAR + AVOID_PRESSURE + AVOID_GUARANTEE

# 긴급 뉴스 키워드 → 관련 상품(예방·점검 안내 톤)
EMERGENCY_MAP = {
    "대형화재": "hrmf", "화재사고": "hrmf", "아파트 화재": "hrmf",
    "결항": "overseas", "항공 지연": "overseas", "여객기": "overseas",
    "감염병": "chronic", "독감": "chronic", "코로나": "chronic",
    "빙판": "driver", "폭설 사고": "driver", "다중추돌": "driver",
}

# 이벤트 유형 → 추천 채널
CHANNEL_BY_TYPE = {
    "휴가": ["검색광고", "블로그"], "명절": ["검색광고", "블로그"], "개학": ["검색광고"],
    "대회": ["브랜드검색", "검색광고"], "지역행사": ["검색광고"], "캠페인일": ["검색광고", "카드뉴스"],
    "계절": ["검색광고"], "기상": ["검색광고"], "긴급뉴스": ["콘텐츠", "블로그"],
}

# 상태 → 추천 목적/유효기간 정책
PURPOSE_BY_STATE = {
    "upcoming": "선제 예고", "emerging": "대비 안내", "active": "시즌 대응",
    "cooling": "마무리 안내", "follow_up": "후속 점검 안내", "ended": "보관",
}


# ── 로딩 ─────────────────────────────────────────────
def _load(root, rel, default=None):
    try:
        with open(os.path.join(root, rel), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def latest_clip(root):
    idx = _load(root, "data/clips/index.json", {}) or {}
    for d in idx.get("dates", []):
        c = _load(root, f"data/clips/{d['date']}.json")
        if c:
            return c
    return None


def load_bundle(root=ROOT):
    pj = _load(root, "data/products.json", {"products": [], "main": []}) or {}
    return {
        "products": {p["key"]: p for p in pj.get("products", [])},
        "main": pj.get("main", []),
        "calendar": (_load(root, "data/events/calendar.json", {}) or {}).get("events", []),
        "seasonal": (_load(root, "data/seasonal.json", {}) or {}).get("seasonal", {}),
        "signals": _load(root, "data/signals.json", {}) or {},
        "clip": latest_clip(root),
        "volume": (_load(root, "data/volume.json", {}) or {}).get("products", {}),
        "history": (_load(root, "data/events/copy_history.json", {}) or {}).get("used", []),
    }


# ── 상태 계산 ─────────────────────────────────────────
def _d(s):
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def state_from_dates(today, start, end, follow_up_days=0, ongoing=False):
    if not (start and end):
        return "unknown"
    if today < start - timedelta(days=LEAD_DAYS):
        return "upcoming"
    if start - timedelta(days=LEAD_DAYS) <= today < start:
        return "emerging"
    if start <= today <= end:
        return "active"
    if end < today <= end + timedelta(days=TAIL_DAYS):
        return "cooling"
    if follow_up_days and today <= end + timedelta(days=TAIL_DAYS + follow_up_days) and ongoing:
        return "follow_up"
    return "ended"


def state_from_months(today, months):
    """계절(월 배열) 이벤트 상태: 현재 월 기준."""
    m, nxt, prv = today.month, today.month % 12 + 1, (today.month - 2) % 12 + 1
    if m in months:
        return "active"
    if nxt in months:
        return "emerging"
    if prv in months:
        return "cooling"
    # 2개월 앞까지 예정
    if (nxt % 12 + 1) in months:
        return "upcoming"
    return "ended"


# ── 이벤트 통합 ───────────────────────────────────────
def build_events(bundle, today):
    """calendar + seasonal + 기상(signals) + 긴급뉴스(clips) → 이벤트 목록(상태 포함)."""
    events = []

    # 1) 예정 이벤트(calendar)
    for ev in bundle.get("calendar", []):
        s, e = _d(ev.get("start")), _d(ev.get("end"))
        st = state_from_dates(today, s, e, ev.get("follow_up_days", 0),
                              ongoing=_has_recent_news(bundle, ev.get("keywords", [])))
        events.append({**ev, "source": "calendar", "state": st})

    # 2) 계절(seasonal) — 상품별 월 이슈
    for pkey, wins in (bundle.get("seasonal") or {}).items():
        for w in wins:
            st = state_from_months(today, w.get("m", []))
            events.append({"id": f"season-{pkey}-{'-'.join(map(str, w.get('m', [])))}",
                           "type": "계절", "name": w.get("tag", ""), "months": w.get("m", []),
                           "products": [pkey], "keywords": w.get("kws", []),
                           "source": "seasonal", "state": st})

    # 3) 기상특보(signals active) — active 이벤트
    for kind in (bundle.get("signals", {}).get("weather", {}) or {}).get("active", []):
        pk = "hrmf" if kind in ("건조", "호우", "태풍", "폭염", "한파", "대설") else "driver"
        events.append({"id": f"weather-{kind}", "type": "기상", "name": f"{kind} 특보",
                       "products": [pk] + (["driver"] if kind in ("대설", "강풍", "한파") else []),
                       "keywords": [kind], "source": "signal", "state": "active"})

    # 4) 긴급 뉴스(clips) — 매핑되는 것만 active(예방·점검 안내)
    for it, pk, topic in _emergency_news(bundle):
        events.append({"id": f"news-{_slug(it['t'])}", "type": "긴급뉴스", "name": topic,
                       "products": [pk], "keywords": [topic], "source": "news",
                       "state": "active", "news": it})
    return events


def _clip_items(bundle):
    out = []
    for cat in (bundle.get("clip") or {}).get("categories", {}).values():
        out += cat.get("items", [])
    return out


def _has_recent_news(bundle, keywords):
    if not keywords:
        return False
    for it in _clip_items(bundle):
        t = it.get("t", "")
        if any(k in t for k in keywords):
            return True
    return False


def _emergency_news(bundle):
    seen, out = set(), []
    for it in _clip_items(bundle):
        t = it.get("t", "")
        for kw, pk in EMERGENCY_MAP.items():
            if kw in t and it.get("url") not in seen:
                seen.add(it.get("url"))
                out.append((it, pk, kw))
                break
    return out


def _slug(s):
    return re.sub(r"[^0-9a-zA-Z가-힣]+", "-", str(s))[:32].strip("-")


# ── 근거(확인된 사실) ─────────────────────────────────
def gather_facts(ev, product_key, bundle):
    facts, used = [], []
    # 예정/계절
    if ev["source"] == "calendar":
        facts.append(f"예정: {ev['name']} {ev.get('start','')}~{ev.get('end','')}")
        used.append("calendar")
    elif ev["source"] == "seasonal":
        facts.append(f"시즌: {ev['name']} ({', '.join(str(m)+'월' for m in ev.get('months', []))})")
        used.append("seasonal")
    elif ev["source"] == "signal":
        asof = bundle.get("signals", {}).get("asof", "")
        facts.append(f"기상특보: {ev['name']} 발효(기준 {asof})")
        used.append("signals")
    elif ev["source"] == "news":
        n = ev.get("news", {})
        facts.append(f"뉴스: '{n.get('t','')[:40]}' ({n.get('src','')} {n.get('date','')})")
        used.append("clips")
    # 관련 뉴스(키워드 매칭)
    for it in _clip_items(bundle):
        if any(k in it.get("t", "") for k in ev.get("keywords", [])):
            facts.append(f"뉴스: '{it.get('t','')[:40]}' ({it.get('src','')} {it.get('date','')})")
            used.append("clips")
            break
    # 검색량
    vol = bundle.get("volume", {}).get(product_key, {}).get("keywords", {})
    if vol:
        top = max(vol.items(), key=lambda kv: (kv[1].get("pc", 0) + kv[1].get("mobile", 0)))
        facts.append(f"검색량: '{top[0]}' {top[1].get('pc',0)+top[1].get('mobile',0):,}회/월")
        used.append("volume")
    return facts, sorted(set(used))


# ── 문구 생성(가드레일 안전) ───────────────────────────
def _pname(bundle, key):
    return bundle.get("products", {}).get(key, {}).get("name", key)


def _copy(ev, product_name, state):
    """상태·유형별 예방/대비 톤 문구(제목·설명·소제목). 공포·압박·담보 단정 없음."""
    ename = ev["name"]
    if ev["type"] == "긴급뉴스":
        verb = "예방 점검 안내"
        title = f"{ename} {product_name} 점검 안내"
        desc = f"관련 소식이 있는 시기, {product_name} 보장 내용을 미리 확인해 두면 좋습니다."
        sub = f"{product_name} 예방·점검 체크리스트"
    else:
        pv = {"upcoming": "선제 준비", "emerging": "미리 대비", "active": "지금 점검",
              "cooling": "마무리 점검", "follow_up": "후속 점검", "ended": "보관"}.get(state, "점검")
        title = f"{ename} {product_name} {pv}"
        desc = f"{ename} 시기, {product_name} 보장 범위를 미리 확인해 두세요."
        sub = f"{ename} 대비 {product_name} 확인 포인트"
    return title.strip(), desc.strip(), sub.strip()


def lint_avoid(*texts):
    hit = []
    joined = " ".join(texts)
    for w in AVOID_ALL:
        if w in joined:
            hit.append(w)
    return hit


# ── fingerprint / cooldown ────────────────────────────
_STOP = {"하세요", "세요", "해요", "보세요", "두세요", "합니다", "확인", "안내", "미리",
         "범위", "시기", "관련", "소식", "점검", "포인트", "체크리스트", "좋습니다"}
# 토큰 끝에 붙는 어미(문장 어미만 바꾼 반복을 같은 fingerprint 로 묶기 위함)
_ENDINGS = ["했습니다", "해주세요", "하세요", "합니다", "보세요", "두세요", "되세요", "드세요",
            "해요", "한다", "했다", "하는", "하고", "해서", "하며", "하기", "합시다"]


def _strip_end(tok):
    for e in sorted(_ENDINGS, key=len, reverse=True):
        if tok.endswith(e) and len(tok) > len(e):
            return tok[:-len(e)]
    return tok


def _norm_tokens(*texts):
    out = set()
    for t in re.findall(r"[가-힣]{2,}", " ".join(texts)):
        s = _strip_end(t)
        if len(s) >= 2 and s not in _STOP:
            out.add(s)
    return sorted(out)


def fingerprint(product_key, event_id, purpose, title, desc):
    core = "|".join([product_key, event_id, purpose] + _norm_tokens(title, desc))
    return hashlib.sha1(core.encode("utf-8")).hexdigest()[:16]


def in_cooldown(fp, history, today):
    for h in history:
        if h.get("fp") == fp:
            d = _d(h.get("date"))
            if d and (today - d).days < COOLDOWN_DAYS:
                return True
    return False


# ── 추천 생성 ─────────────────────────────────────────
def _valid_window(ev, today):
    s, e = _d(ev.get("start")), _d(ev.get("end"))
    if s and e:
        return max(s, today).isoformat(), (e + timedelta(days=TAIL_DAYS)).isoformat()
    return today.isoformat(), (today + timedelta(days=30)).isoformat()


def _confidence(used, state):
    base = 0.1 + 0.3 * ("clips" in used) + 0.2 * ("signals" in used) + \
        0.2 * ("seasonal" in used or "calendar" in used) + 0.2 * ("volume" in used)
    if state in ("ended",):
        base *= 0.4
    if state in ("cooling", "upcoming"):
        base *= 0.8
    return round(min(base, 0.95), 2)


def make_reco(ev, product_key, bundle, today):
    if ev["state"] in ("ended", "unknown"):
        return None
    pname = _pname(bundle, product_key)
    facts, used = gather_facts(ev, product_key, bundle)
    if not facts:
        return None
    title, desc, sub = _copy(ev, pname, ev["state"])
    bad = lint_avoid(title, desc, sub)
    if bad:                       # 가드레일: 금지 표현 있으면 추천 자체를 만들지 않음
        return None
    purpose = PURPOSE_BY_STATE.get(ev["state"], "점검")
    fp = fingerprint(product_key, ev["id"], purpose, title, desc)
    vf, vt = _valid_window(ev, today)
    return {
        "fingerprint": fp,
        "fact": facts,
        "product": product_key, "product_name": pname,
        "event_id": ev["id"], "event_name": ev["name"], "event_type": ev["type"],
        "event_state": ev["state"],
        "title": title, "description": desc, "content_subhead": sub,
        "purpose": purpose,
        "reason": f"{ev['name']}({ev['state']}) 시기의 {pname} 선제/대비 소구",
        "data_used": used,
        "valid_from": vf, "valid_to": vt,
        "avoid_phrases": AVOID_ALL,
        "channels": CHANNEL_BY_TYPE.get(ev["type"], ["검색광고"]),
        "product_basis": "미확인",
        "review_status": "심의 검토 전 · 운영 후보",
        "confidence": _confidence(used, ev["state"]),
    }


# ── 미분류 큐 ─────────────────────────────────────────
def classify_news(bundle):
    """상품·이벤트·긴급 어디에도 확실히 매핑되지 않는 뉴스 → 검토 큐(자동 문구 X)."""
    products = bundle.get("products", {})
    ev_kws = set()
    for ev in bundle.get("calendar", []):
        ev_kws |= set(ev.get("keywords", []))
    for wins in (bundle.get("seasonal") or {}).values():
        for w in wins:
            ev_kws |= set(w.get("kws", []))
    prod_kws = []
    for p in products.values():
        prod_kws.append(p.get("newsQuery", ""))
        prod_kws += p.get("newsExtra") or []
    prod_kws = [k for k in prod_kws if k]

    out, seen = [], set()
    for it in _clip_items(bundle):
        t = it.get("t", "")
        url = it.get("url")
        if url in seen:
            continue
        seen.add(url)
        matched = any(k and k in t for k in prod_kws) or any(k in t for k in ev_kws) \
            or any(k in t for k in EMERGENCY_MAP)
        if not matched:
            out.append({"title": t, "src": it.get("src", ""), "date": it.get("date", ""),
                        "url": url, "reason": "상품·이벤트 매핑 불가 → 사람 분류 필요"})
    return out


# ── 실행 ─────────────────────────────────────────────
def run(bundle, today=None):
    today = today or datetime.now(KST).date()
    events = build_events(bundle, today)
    history = bundle.get("history", [])
    recos, suppressed = [], 0
    for ev in events:
        for pk in ev.get("products", []):
            r = make_reco(ev, pk, bundle, today)
            if not r:
                continue
            if in_cooldown(r["fingerprint"], history, today):
                suppressed += 1
                continue
            recos.append(r)
    # fingerprint 중복 제거(같은 상품+사건+목적+문구코어)
    uniq, fps = [], set()
    for r in sorted(recos, key=lambda x: -x["confidence"]):
        if r["fingerprint"] in fps:
            continue
        fps.add(r["fingerprint"])
        uniq.append(r)
    return {
        "asof": today.isoformat(),
        "counts": {"events": len(events), "recommendations": len(uniq),
                   "suppressed_cooldown": suppressed, "unclassified": 0},
        "events": [{"id": e["id"], "name": e["name"], "type": e["type"],
                    "state": e["state"], "products": e.get("products", []),
                    "source": e["source"]} for e in events],
        "recommendations": uniq,
        "unclassified": classify_news(bundle),
    }


def main(root=ROOT, out_rel="data/events/recommendations.json"):
    bundle = load_bundle(root)
    result = run(bundle)
    result["counts"]["unclassified"] = len(result["unclassified"])
    out = os.path.join(root, out_rel)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    c = result["counts"]
    print(f"✔ {out_rel} · 이벤트 {c['events']} · 추천 {c['recommendations']} · "
          f"cooldown억제 {c['suppressed_cooldown']} · 미분류 {c['unclassified']}")
    return result


if __name__ == "__main__":
    main()
