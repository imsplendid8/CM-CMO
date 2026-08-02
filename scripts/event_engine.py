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
RECENT_NEWS_DAYS = 10   # follow_up 판정용 뉴스 최신성 임계(일) — 오래된 기사로 follow_up 승격 방지
SEASON_UPCOMING_DAYS = 45  # 시즌 span upcoming 허용 지평(일) — 이보다 먼 미래 인스턴스는 무시(연중 upcoming 방지)
STATES = ("upcoming", "emerging", "active", "cooling", "ended", "follow_up")

# 가드레일: 생성 금지 표현(공포 조장 / 사건 이용 압박 / 담보·보험금 단정 / 과장·최상급)
# 주의: 정상 표현("보장 내용/보장 범위 확인")까지 막지 않도록, 담보 단정은 다어절로만 지정한다.
AVOID_FEAR = ["끔찍", "참사", "비극", "당신도", "큰일", "불행", "공포", "눈앞의 위험", "지금 안 하면"]
AVOID_PRESSURE = ["이 사고 보고도", "더 늦기 전에 가입", "안 하면 후회", "지금 가입 안 하면", "서둘러 가입",
                  "꼭 가입", "즉시 가입", "사고 전에 가입", "피해 전에 가입", "안 들면 손해", "누구나 가입"]
AVOID_GUARANTEE = ["무조건", "반드시", "전액", "100%", "완벽 보장", "모두 보장", "가입 보장",
                   "보험금 확정", "보상 확정", "보장 확정", "즉시 보상", "최대 보장"]
AVOID_SUPERLATIVE = ["최저가", "업계 최고", "가장 저렴", "제일 싸", "필수 보험"]
AVOID_ALL = AVOID_FEAR + AVOID_PRESSURE + AVOID_GUARANTEE + AVOID_SUPERLATIVE

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

# 상태 '전이(transition)' → 추천 목적. 전이가 감지되면 목적이 바뀌고 fingerprint 도 달라진다
# (특정 이벤트·날씨에 하드코딩하지 않고, 상태 델타로만 판정한다).
PURPOSE_BY_TRANSITION = {
    "onset": "본격 대응", "winddown": "마무리 전환", "resurge": "재점화 대응",
    "handoff": "전환 대응", "follow_up": "후속 점검 안내",
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
        "state_history": (_load(root, "data/events/state_history.json", {}) or {}).get("entries", []),
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


def _mmdd(s, year):
    """'MM-DD' + 연도 → date. 파싱 불가 시 None."""
    try:
        mm, dd = str(s).split("-")[:2]
        return date(year, int(mm), int(dd))
    except (ValueError, TypeError):
        return None


_SPAN_RANK = {"active": 4, "emerging": 3, "cooling": 2, "upcoming": 1, "ended": 0, "unknown": 0}


def state_from_span(today, spans):
    """연간 반복 날씨 구간(span=[["MM-DD","MM-DD"],...])을 **실제 일자**로 판정.
    월 전체가 아니라 정확 기간으로 upcoming/emerging/active/cooling을 계산한다.
    인접 연도 인스턴스(연말→연초 wrap 포함)까지 보고 '가장 진행에 가까운' 상태를 택한다."""
    best = "ended"
    for sp in spans or []:
        if not (isinstance(sp, (list, tuple)) and len(sp) == 2):
            continue
        for yr in (today.year - 1, today.year, today.year + 1):
            s = _mmdd(sp[0], yr)
            e = _mmdd(sp[1], yr)
            if not (s and e):
                continue
            if e < s:                       # 연말→연초 wrap: 종료는 다음 해
                e = _mmdd(sp[1], yr + 1)
            st = state_from_dates(today, s, e)
            # 너무 이른 미래 인스턴스(예: 내년 겨울)는 무시 — 연중 upcoming 방지(월 기준과 유사하게 경계)
            if st == "upcoming" and (s - today).days > SEASON_UPCOMING_DAYS:
                continue
            if _SPAN_RANK.get(st, 0) > _SPAN_RANK.get(best, 0):
                best = st
    return best


# ── 이벤트 통합 ───────────────────────────────────────
def build_events(bundle, today):
    """calendar + seasonal + 기상(signals) + 긴급뉴스(clips) → 이벤트 목록(상태 포함)."""
    events = []

    # 1) 예정 이벤트(calendar) — 누락 필드는 기본값으로 정규화(불완전 행에도 안전)
    for raw in bundle.get("calendar", []):
        ev = {"id": "", "type": "", "name": "", "keywords": [], "products": [], **raw}
        s, e = _d(ev.get("start")), _d(ev.get("end"))
        st = state_from_dates(today, s, e, ev.get("follow_up_days", 0),
                              ongoing=_has_recent_news(bundle, ev.get("keywords", []), today))
        events.append({**ev, "source": "calendar", "state": st})

    # 2) 계절(seasonal) — 상품별 시즌 이슈. span(정확 일자)이 있으면 일자 기준, 없으면 월 기준.
    for pkey, wins in (bundle.get("seasonal") or {}).items():
        for w in wins:
            span = w.get("span")
            st = state_from_span(today, span) if span else state_from_months(today, w.get("m", []))
            events.append({"id": f"season-{pkey}-{'-'.join(map(str, w.get('m', [])))}",
                           "type": "계절", "name": w.get("tag", ""), "months": w.get("m", []),
                           "span": span, "products": [pkey], "keywords": w.get("kws", []),
                           "source": "seasonal", "state": st})

    # 3) 기상특보(signals active) — active 이벤트
    for kind in (bundle.get("signals", {}).get("weather", {}) or {}).get("active", []):
        events.append({"id": f"weather-{kind}", "type": "기상", "name": f"{kind} 특보",
                       "products": _weather_products(kind),
                       "keywords": [kind], "source": "signal", "state": "active"})

    # 4) 긴급 뉴스(clips) — 매핑되는 것만 active(예방·점검 안내)
    for it, pk, topic in _emergency_news(bundle):
        events.append({"id": f"news-{_slug(it.get('t', ''))}", "type": "긴급뉴스", "name": topic,
                       "products": [pk], "keywords": [topic], "source": "news",
                       "state": "active", "news": it})
    return events


def _clip_items(bundle):
    out = []
    for cat in (bundle.get("clip") or {}).get("categories", {}).values():
        out += cat.get("items", [])
    return out


def _kw_hit(text, keywords):
    """텍스트가 키워드 중 하나를 포함하는지. 빈 문자열 키워드는 무시한다.
    (빈 키워드는 `"" in text` 가 항상 참이라 모든 뉴스를 매칭시켜, 미분류 큐를
    통째로 비우거나 잘못된 follow_up 승격을 일으키므로 반드시 걸러낸다.)"""
    return any(k and k in text for k in keywords)


def _has_recent_news(bundle, keywords, today):
    """이벤트 키워드에 매칭되면서 '최근(RECENT_NEWS_DAYS 이내)' 기사가 있는지.
    오래된 스냅샷 기사로 follow_up 승격되는 것을 막기 위해 날짜를 확인한다."""
    if not keywords:
        return False
    for it in _clip_items(bundle):
        if _kw_hit(it.get("t", ""), keywords):
            d = _d(it.get("date"))
            if d and 0 <= (today - d).days <= RECENT_NEWS_DAYS:
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


# 기상특보 종류 → 관련 상품(속성 기반 규칙 · 특정 종류에 하드코딩하지 않음).
# 재산/화재성 특보는 주택화재, 도로위험성 특보는 운전자에 매핑하고 교집합은 둘 다.
_WX_PROPERTY = "건조 호우 태풍 폭염 한파 대설 장마 침수".split()   # 재산·주거 위험(hrmf)
_WX_ROADRISK = "대설 강풍 한파 호우 태풍 장마 빙판".split()         # 도로·주행 위험(driver)


def _weather_products(kind):
    pk = []
    if kind in _WX_PROPERTY:
        pk.append("hrmf")
    if kind in _WX_ROADRISK:
        pk.append("driver")
    return pk or ["driver"]     # 미분류 특보는 보수적으로 운전자


def _weather_kind(event_id):
    return event_id[len("weather-"):] if event_id.startswith("weather-") else ""


# ── 근거(확인된 사실) ─────────────────────────────────
def gather_facts(ev, product_key, bundle):
    facts, used = [], []
    # 예정/계절
    if ev["source"] == "calendar":
        facts.append(f"예정: {ev['name']} {ev.get('start','')}~{ev.get('end','')}")
        used.append("calendar")
    elif ev["source"] == "seasonal":
        if ev.get("span"):      # 정확 일자 구간 우선 표기(월 전체 아님)
            rng = ", ".join(f"{a}~{b}" for a, b in ev["span"] if isinstance(a, str))
            facts.append(f"시즌: {ev['name']} (정확 기간 {rng})")
        else:
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
        if _kw_hit(it.get("t", ""), ev.get("keywords", [])):
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
def _valid_window(ev, today, state):
    """추천 유효기간을 상태 기준으로 산출.
    - emerging/active/cooling/follow_up: 지금 실행 가능하므로 valid_from=오늘
    - upcoming: 아직 이르므로 valid_from=이벤트 시작일
    - follow_up: valid_to 를 follow_up_days 만큼 연장(끝<시작 역전 방지)
    """
    s, e = _d(ev.get("start")), _d(ev.get("end"))
    fu = ev.get("follow_up_days", 0) or 0
    vf = s if (state == "upcoming" and s) else today
    if state == "follow_up" and e:
        vt = e + timedelta(days=TAIL_DAYS + fu)
    elif e:
        vt = e + timedelta(days=TAIL_DAYS)
    else:                                   # 계절(월) 이벤트 등 날짜 없음
        vt = today + timedelta(days=30)
    if vt < vf:                             # 안전장치: 역전 시 최소 7일 창
        vt = vf + timedelta(days=7)
    return vf.isoformat(), vt.isoformat()


def _confidence(used, state):
    base = 0.1 + 0.3 * ("clips" in used) + 0.2 * ("signals" in used) + \
        0.2 * ("seasonal" in used or "calendar" in used) + 0.2 * ("volume" in used)
    if state in ("ended",):
        base *= 0.4
    if state in ("cooling", "upcoming"):
        base *= 0.8
    return round(min(base, 0.95), 2)


def make_reco(ev, product_key, bundle, today, transition=None):
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
    # 전이가 감지되면 목적이 바뀐다 → fingerprint·유효기간도 자연히 달라짐
    if transition and transition.get("kind") in PURPOSE_BY_TRANSITION:
        purpose = PURPOSE_BY_TRANSITION[transition["kind"]]
    else:
        purpose = PURPOSE_BY_STATE.get(ev["state"], "점검")
    fp = fingerprint(product_key, ev["id"], purpose, title, desc)
    vf, vt = _valid_window(ev, today, ev["state"])
    if transition:
        used = sorted(set(used) | {"state_history"})
        reason = f"{ev['name']} 상태 전이({transition['from']}→{transition['to']})에 따른 {pname} {purpose}"
    else:
        reason = f"{ev['name']}({ev['state']}) 시기의 {pname} 선제/대비 소구"
    return {
        "fingerprint": fp,
        "fact": facts,
        "product": product_key, "product_name": pname,
        "event_id": ev["id"], "event_name": ev["name"], "event_type": ev["type"],
        "event_state": ev["state"],
        "transition": transition,
        "title": title, "description": desc, "content_subhead": sub,
        "purpose": purpose,
        "reason": reason,
        "data_used": used,
        "valid_from": vf, "valid_to": vt,
        "avoid_phrases": AVOID_ALL,
        "channels": CHANNEL_BY_TYPE.get(ev["type"], ["검색광고"]),
        "product_basis": "미확인",
        "review_status": "심의 검토 전 · 운영 후보",
        "confidence": _confidence(used, ev["state"]),
    }


# ── 상태 전이(transition/episode) ─────────────────────
def prev_states(state_history, today):
    """오늘 이전(가장 최근) 저널 스냅샷의 {event_id: state}. 없으면 빈 dict."""
    best = None
    for e in state_history:
        d = _d(e.get("date"))
        if d and d < today and (best is None or d > _d(best.get("date"))):
            best = e
    return dict(best.get("states", {})) if best else {}


def _transition_kind(frm, to):
    """상태 델타를 전이 종류로 (특정 이벤트에 하드코딩하지 않고 상태쌍으로만 판정)."""
    if to == "active":
        return "onset" if frm in ("upcoming", "emerging") else "resurge"
    if to == "cooling":
        return "winddown" if frm == "active" else "change"  # active를 실제로 거친 경우만
    if to == "follow_up":
        return "follow_up"
    if to == "ended":
        return "ended"
    return "change"


def detect_transitions(events, prev):
    """이전 스냅샷 대비 상태가 바뀐 이벤트를 전이로 산출.
    - 오늘 존재하며 상태 변화 → 해당 전이
    - 이전엔 있었으나 오늘 사라진 이벤트(예: 기상특보 해제) → lifted
    - 해제된 기상특보 ↔ 오늘 새로 활성인 기상특보가 상품을 공유 → handoff(전환)
    반환: (transitions[list], handoff{onset_event_id: transition})."""
    today_states = {e["id"]: e["state"] for e in events}
    trans = []
    for eid, st in today_states.items():
        p = prev.get(eid)
        if p and p != st:
            trans.append({"event_id": eid, "from": p, "to": st, "kind": _transition_kind(p, st)})
    lifted = []
    for eid, p in prev.items():
        if eid not in today_states and p not in ("ended", "lifted"):
            t = {"event_id": eid, "from": p, "to": "lifted", "kind": "lifted"}
            trans.append(t)
            if eid.startswith("weather-"):
                lifted.append(eid)
    # 핸드오프: 해제된 특보와 오늘 활성 특보가 상품을 공유하면 '전환'으로 승격
    lifted.sort()                        # dict 순서 비의존(결정론)
    handoff = {}
    for e in events:
        if e.get("source") == "signal" and e["state"] == "active":
            if prev.get(e["id"]) == "active":   # 이미 활성이던 특보는 '신규 활성'이 아니므로 전환 아님
                continue
            prods = set(e.get("products", []))
            for lw in lifted:
                if set(_weather_products(_weather_kind(lw))) & prods:
                    h = {"event_id": e["id"], "from": lw, "from_kind": _weather_kind(lw),
                         "to": "active", "kind": "handoff"}
                    handoff[e["id"]] = h
                    trans.append(h)
                    break
    trans.sort(key=lambda t: (t["event_id"], t["kind"]))
    return trans, handoff


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
        matched = _kw_hit(t, prod_kws) or _kw_hit(t, ev_kws) or _kw_hit(t, EMERGENCY_MAP)
        if not matched:
            out.append({"title": t, "src": it.get("src", ""), "date": it.get("date", ""),
                        "url": url, "reason": "상품·이벤트 매핑 불가 → 사람 분류 필요"})
    return out


# ── 실행 ─────────────────────────────────────────────
def run(bundle, today=None):
    today = today or datetime.now(KST).date()
    events = build_events(bundle, today)
    history = bundle.get("history", [])
    # 상태 전이 감지(이전 저널 스냅샷 대비) → 이벤트별 전이 매핑
    prev = prev_states(bundle.get("state_history", []), today)
    transitions, handoff = detect_transitions(events, prev)
    trans_map = {}
    for t in transitions:
        trans_map.setdefault(t["event_id"], t)
    trans_map.update(handoff)            # 핸드오프(전환)를 우선 적용
    recos, suppressed = [], 0
    for ev in events:
        for pk in ev.get("products", []):
            r = make_reco(ev, pk, bundle, today, transition=trans_map.get(ev["id"]))
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
    unclassified = classify_news(bundle)
    return {
        "asof": today.isoformat(),
        "counts": {"events": len(events), "recommendations": len(uniq),
                   "suppressed_cooldown": suppressed, "unclassified": len(unclassified),
                   "transitions": len(transitions)},
        "events": [{"id": e.get("id", ""), "name": e.get("name", ""), "type": e.get("type", ""),
                    "state": e.get("state", ""), "products": e.get("products", []),
                    "source": e.get("source", "")} for e in events],
        "transitions": transitions,
        "recommendations": uniq,
        "unclassified": unclassified,
    }


def append_state_history(root, result, keep=120):
    """오늘 상태 스냅샷을 저널에 기록(같은 날짜는 덮어써 멱등). 최근 keep개만 유지."""
    rel = "data/events/state_history.json"
    j = _load(root, rel, {"entries": []}) or {"entries": []}
    entries = [e for e in j.get("entries", []) if e.get("date") != result["asof"]]
    entries.append({"date": result["asof"],
                    "states": {e["id"]: e["state"] for e in result["events"]}})
    entries.sort(key=lambda e: e.get("date", ""))
    j["entries"] = entries[-keep:]
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(j, f, ensure_ascii=False, indent=1)
    return j


def main(root=ROOT, out_rel="data/events/recommendations.json"):
    bundle = load_bundle(root)
    result = run(bundle)                      # run() 이 counts.unclassified 를 이미 채운다
    out = os.path.join(root, out_rel)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    append_state_history(root, result)        # 오늘 상태 스냅샷 저널에 기록(전이 감지용)
    c = result["counts"]
    print(f"✔ {out_rel} · 이벤트 {c['events']} · 추천 {c['recommendations']} · "
          f"전이 {c['transitions']} · cooldown억제 {c['suppressed_cooldown']} · 미분류 {c['unclassified']}")
    return result


if __name__ == "__main__":
    main()
