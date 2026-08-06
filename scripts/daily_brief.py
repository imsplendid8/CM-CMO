#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""데일리 비서 브리핑 — 텔레그램 발송.

오늘(한국시간)의 시즌 이슈(data/seasonal.json) + SERP 할일 + (선택)네이버 뉴스를
한 건의 텔레그램 메시지로 담당자에게 보낸다. GitHub Actions 일일 cron에서 실행.

필요 환경변수(Secrets):
  TELEGRAM_BOT_TOKEN   (필수) @BotFather 로 만든 봇 토큰
  TELEGRAM_CHAT_ID     (필수) 내 chat id (봇과 대화 후 getUpdates 로 확인)
  NAVER_CLIENT_ID/SECRET (선택) 있으면 메인 3종 최신 뉴스 1건씩 포함
표준 라이브러리만 사용.
"""
import os, json, sys, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_automation_health as cah   # 자동화 상태를 브리프 직전 재계산(저장 요약 미신뢰)
import event_engine as ee               # 시즌 span 일자 판정 공유(월 전체가 아닌 정확 기간)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HUB = "imsplendid8.github.io/CM-CMO"

def load(p):
    with open(os.path.join(ROOT, p), encoding="utf-8") as f:
        return json.load(f)

def load_opt(p, default=None):
    try:
        with open(os.path.join(ROOT, p), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def kst_now():
    return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=9)))

# 뉴스에서 '행동가치'가 있는 신호만 추림(단순 헤드라인 노이즈 제외)
# 경쟁사 상품·가격 움직임 + 수요 트리거 위주. 모든 기사에 최소 1개 요구.
ACTION_KW = ["출시", "개편", "리뉴얼", "신상품", "인상", "인하", "할인", "이벤트", "다이렉트",
             "점유", "1위", "리콜", "제재", "과징금", "손해율", "적자", "보험료",
             "사고", "화재", "폭우", "호우", "침수", "폭염", "한파", "급증"]

def latest_clip():
    """오늘(없으면 최근) 뉴스 클리핑 파일을 로드."""
    idx = load_opt("data/clips/index.json", {}) or {}
    for d in idx.get("dates", []):
        c = load_opt(f"data/clips/{d['date']}.json")
        if c:
            return c
    return None

def esc(s):
    """텔레그램 HTML parse_mode용 이스케이프(제목·요약·URL 등 동적 텍스트)."""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def pick_news(clip, products):
    """행동가치 있는 뉴스만 2~3건: [경쟁사 동향] / [트리거]. 요약(gist)+바로가기 링크 포함."""
    if not clip:
        return []
    comp_names = {"ind_samsung": "삼성화재", "ind_db": "DB손보", "ind_hyundai": "현대해상",
                  "ind_kb": "KB손보", "ind_meritz": "메리츠화재"}
    cands = []
    for key, cat in clip.get("categories", {}).items():
        is_comp = key in comp_names
        for it in cat.get("items", [])[:6]:
            t = it.get("t", "")
            hit = [w for w in ACTION_KW if w in t]
            if not hit:            # 행동 키워드 없는 단순 헤드라인은 제외
                continue
            if is_comp:
                tag = f"[경쟁사·{comp_names[key]}]"
                score = 2 + len(hit)   # 경쟁사 움직임 가중
            else:
                tag = f"[{cat.get('name', key)}]"
                score = len(hit)
            cands.append((score, it.get("date", ""), tag, t, it.get("src", ""),
                          it.get("url", ""), it.get("gist", "")))
    # 점수·최신 우선, 제목 앞부분 dedup
    cands.sort(key=lambda x: (x[0], x[1]), reverse=True)
    out, seen = [], set()
    for sc, dt, tag, t, src, url, gist in cands:
        k = t[:12]
        if k in seen:
            continue
        seen.add(k)
        line = f"· {esc(tag)} {esc(t[:44])} ({esc(src)})"
        g = str(gist).strip()
        if g:                                   # 요약(gist) 반영
            line += f"\n  ⤷ {esc(g[:88])}" + ("…" if len(g) > 88 else "")
        if url:                                 # 링크 텍스트를 '바로가기'로(HTML 하이퍼링크)
            line += f'\n  🔗 <a href="{esc(url)}">바로가기</a>'
        out.append(line)
        if len(out) >= 3:
            break
    return out

# 업계·경쟁사(뉴스 클리핑·news-tool INDUSTRY와 동일 키) — 이메일 동향 섹션 순서
INDUSTRY = [("ind_biz", "손보업계 전반"), ("ind_samsung", "삼성화재"), ("ind_db", "DB손해보험"),
            ("ind_hyundai", "현대해상"), ("ind_kb", "KB손해보험"), ("ind_meritz", "메리츠화재")]


def _load_context():
    pdata = load("data/products.json")
    products = {p["key"]: p for p in pdata["products"]}
    order = [p["key"] for p in pdata["products"]]
    main = pdata["main"]
    seasonal = load("data/seasonal.json")["seasonal"]
    signals = load_opt("data/signals.json", {}) or {}
    clip = latest_clip()
    now = kst_now()
    return products, order, main, seasonal, signals, clip, now


def compute_action_lines(products, main, seasonal, signals, now):
    """오늘 할 일(우선순위) 텍스트 목록 산출 — 번호 없이 반환(채널별로 번호 부여)."""
    m = now.month
    nm = m % 12 + 1  # 다음 달
    name = lambda k: products.get(k, {}).get("name", k)
    actions = {}  # key -> (priority, text)   낮을수록 우선

    def put(key, pri, text):
        if key not in actions or pri < actions[key][0]:
            actions[key] = (pri, text)

    # (1) 수요 신호 — 가장 시의성 높음
    for key, t in (signals.get("triggers") or {}).items():
        lv = t.get("level")
        if lv in ("high", "medium"):
            icon = "🔥" if lv == "high" else "🌡"
            word = "급등" if lv == "high" else "상승"
            put(key, 0, f"{icon} {name(key)} — 검색수요 {word}: 소재·입찰 강화 + 랜딩 점검")
    for w in (signals.get("weather", {}) or {}).get("active", []):
        note = w.get("note") or "기상 특보"
        put("hrmf", 0, f"🌧 {name('hrmf')} — {note}: 누수·풍수재 소구 시즌 대응")

    # (2) 시즌 이슈, 메인 우선. span(정확 일자) 있으면 엔진과 동일 기준(일자), 없으면 월 폴백.
    today = now.date()
    for key, wins in seasonal.items():
        for w in wins:
            span = w.get("span")
            if span:
                st = ee.state_from_span(today, span)
                if st in ("active", "cooling"):
                    pri = 1 if key in main else 2
                    put(key, pri, f"{'★' if key in main else '·'} {name(key)} — {w['tag']}(진행 중): 시즌 소재 등록·랜딩 점검")
                elif st in ("emerging", "upcoming") and key in main:
                    put(key, 3, f"★ {name(key)} — {w['tag']}(대비): 시즌 소재 미리 준비")
            else:
                if m in w["m"]:
                    pri = 1 if key in main else 2
                    put(key, pri, f"{'★' if key in main else '·'} {name(key)} — {w['tag']}(이번 달): 시즌 소재 등록·랜딩 점검")
                elif nm in w["m"] and key in main:
                    put(key, 3, f"★ {name(key)} — {w['tag']}(다음 달): 시즌 소재 미리 준비")

    # (3) SERP 상위노출 갭 — 메인 중 요일 순환 1건
    gaps = ["hrmf", "golf", "driver", "overseas"]
    g = gaps[now.day % len(gaps)]
    put(g, 4 if g in [k for k, _ in actions.items()] else 2.5,
        f"🔭 {name(g)} — SERP 상위노출 갭: 검색결과 점검·소구 보완")

    return [txt for _, txt in sorted(actions.values(), key=lambda x: x[0])[:5]]


def build_message():
    products, order, main, seasonal, signals, clip, now = _load_context()
    wd = "월화수목금토일"[now.weekday()]
    action_lines = [f"{i+1}. {t}" for i, t in enumerate(compute_action_lines(products, main, seasonal, signals, now))]
    news_lines = pick_news(clip, products)

    part = "오전" if now.hour < 12 else "오후"
    parts = [f"🗓️ Modooflow · {now.month}/{now.day}({wd}) {part} — 오늘 할 일 {len(action_lines)}", ""]
    parts += ["✅ 오늘 할 일 (우선순위)"] + (action_lines or ["· 오늘 특이 액션 없음 — 정기 점검만"])
    if news_lines:
        parts += ["", "📰 주목할 뉴스"] + news_lines
    # 자동화 수집 상태 — 저장된 요약을 믿지 않고 지금 다시 계산해 표시.
    # 상태 계산이 실패해도 브리프 전체가 중단되지 않도록 방어(실패 시 '상태 확인 불가').
    try:
        parts += [""] + cah.format_lines(cah.compute_health(now))
    except Exception:
        parts += ["", "[데이터 상태]", "· 상태 확인 불가",
                  "· 자동수집이 정상이라고 단정할 수 없음"]
    parts += ["", f"🔭 전체 대시보드 → https://{HUB}"]
    return "\n".join(parts)

def load_newsmon():
    """news-tool.html의 큐레이션 '동향 요약'·'마케팅 시사점'(단일 소스)을 키별 추출 → 이메일 재사용."""
    try:
        html = open(os.path.join(ROOT, "news-tool.html"), encoding="utf-8").read()
    except Exception:
        return {}
    import re
    pat = re.compile(r'(\w+):\{summary:"([^"]*)",\s*insight:"([^"]*)"', re.S)
    return {mm.group(1): {"summary": mm.group(2), "insight": mm.group(3)} for mm in pat.finditer(html)}


# ── 이메일(표 도식형) 스타일 토큰 — 인라인 CSS(메일 클라이언트 호환), 이미지 없음 ──
_ES = {
    "wrap": "max-width:720px;margin:0 auto;padding:20px 16px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Malgun Gothic','Apple SD Gothic Neo',sans-serif;color:#20242c;background:#ffffff;",
    "h2": "font-size:19px;font-weight:800;margin:0 0 3px;letter-spacing:-.02em;",
    "sub": "font-size:12.5px;color:#6b7280;margin:0 0 6px;",
    "h3": "font-size:15px;font-weight:800;margin:26px 0 10px;padding-bottom:6px;border-bottom:2px solid #eceef1;",
    "sumbox": "background:#e8f5ee;border:1px solid #cfe9db;padding:9px 12px;font-size:12.5px;line-height:1.65;",
    "insbox": "background:#fbf3e0;border:1px solid #f0e0bd;padding:9px 12px;font-size:12.5px;line-height:1.65;border-radius:0 0 7px 7px;margin-bottom:6px;",
    "bg": "display:inline-block;font-size:10px;font-weight:800;color:#1f7a4d;background:#d6efe0;padding:1px 7px;border-radius:99px;margin-right:6px;vertical-align:1px;",
    "ba": "display:inline-block;font-size:10px;font-weight:800;color:#9a6b12;background:#f6e6c2;padding:1px 7px;border-radius:99px;margin-right:6px;vertical-align:1px;",
    "tbl": "width:100%;border-collapse:collapse;margin:8px 0 4px;",
    "td": "padding:7px 10px;border-bottom:1px solid #eef0f3;font-size:12.5px;vertical-align:top;",
    "tdr": "padding:7px 10px;border-bottom:1px solid #eef0f3;font-size:11px;color:#6b7280;white-space:nowrap;vertical-align:top;text-align:right;",
    "th": "padding:6px 10px;text-align:left;font-size:11px;font-weight:800;color:#6b7280;background:#f8f9fa;border-bottom:1px solid #e6e8ec;",
}


def render_email():
    """데일리 브리핑을 표 도식형 이메일(HTML+텍스트)로 렌더. returns (subject, html, plain).
    구성: ① 보험별 동향(요약·시사점+헤드라인) ② 경쟁사·업계 동향 ③ 뉴스 캘린더(준비할 것)."""
    products, order, main, seasonal, signals, clip, now = _load_context()
    newsmon = load_newsmon()
    cats = (clip or {}).get("categories", {})
    wd = "월화수목금토일"[now.weekday()]
    part = "오전" if now.hour < 12 else "오후"
    subject = f"📮 Modooflow 데일리 브리핑 · {now.month}/{now.day}({wd}) {part}"
    name = lambda k: products.get(k, {}).get("name", k)
    S = _ES

    def cat_block(key, accent):
        nmn = newsmon.get(key, {})
        items = (cats.get(key) or {}).get("items", [])[:8]
        if not (nmn or items):
            return ""
        cat_style = f"font-size:14px;font-weight:800;background:#f4f6f8;border-left:4px solid {accent};padding:8px 11px;border-radius:7px 7px 0 0;margin-top:14px;"
        h = f'<div style="{cat_style}">{esc(name(key))} <span style="color:#6b7280;font-weight:600;font-size:11.5px">· 헤드라인 {len(items)}건</span></div>'
        if nmn.get("summary"):
            h += f'<div style="{S["sumbox"]}"><span style="{S["bg"]}">동향 요약</span>{esc(nmn["summary"])}</div>'
        if nmn.get("insight"):
            h += f'<div style="{S["insbox"]}"><span style="{S["ba"]}">마케팅 시사점</span>{esc(nmn["insight"])}</div>'
        if items:
            rows = ""
            for it in items:
                t = esc(it.get("t", ""))
                g = esc((it.get("gist") or "")[:110])
                src = esc(it.get("src", ""))
                dt = esc(it.get("date", ""))
                url = it.get("url", "")
                title = f'<a href="{esc(url)}" style="color:#1f2937;text-decoration:none;font-weight:600">{t}</a>' if url else f"<b>{t}</b>"
                gh = f'<div style="color:#6b7280;font-size:11.5px;margin-top:3px">{g}</div>' if g else ""
                rows += f'<tr><td style="{S["td"]}">{title}{gh}</td><td style="{S["tdr"]}">{src}<br>{dt}</td></tr>'
            h += f'<table role="presentation" style="{S["tbl"]}">{rows}</table>'
        return h

    # ① 보험별 동향(메인 ★ 우선)
    prod_keys = [k for k in main if k in products] + [k for k in order if k not in main]
    prod_body = "".join(cat_block(k, "#1f7a4d") for k in prod_keys)
    prod_html = f'<h3 style="{S["h3"]}">📊 보험별 동향 <span style="font-size:12px;color:#6b7280;font-weight:600">· 담당 상품 {len(products)}종</span></h3>' + (prod_body or '<div style="font-size:12.5px;color:#6b7280">수집된 헤드라인이 없습니다.</div>')

    # ② 경쟁사·업계 동향
    ind_body = "".join(cat_block(k, "#b45309") for k, _ in INDUSTRY)
    ind_html = f'<h3 style="{S["h3"]}">🏢 경쟁사·업계 동향 <span style="font-size:12px;color:#6b7280;font-weight:600">· 빅4/5 + 업계 전반</span></h3>' + (ind_body or '<div style="font-size:12.5px;color:#6b7280">수집된 헤드라인이 없습니다.</div>')

    # ③ 뉴스 캘린더 — 지금·곧 준비할 것 (시즌 이슈)
    m, nm, today = now.month, now.month % 12 + 1, now.date()
    cal = []
    for key, wins in seasonal.items():
        for w in wins:
            span = w.get("span")
            status, pr = None, 9
            if span:
                st = ee.state_from_span(today, span)
                if st in ("active", "cooling"):
                    status, pr = "진행 중", 0
                elif st in ("emerging", "upcoming"):
                    status, pr = "곧 · 대비", 1
            else:
                if m in w["m"]:
                    status, pr = "이번 달", 0
                elif nm in w["m"]:
                    status, pr = "다음 달", 1
            if status:
                cal.append((pr, 0 if key in main else 1, name(key), w.get("tag", ""), status, w.get("act", "")))
    cal.sort(key=lambda r: (r[0], r[1]))
    cal = cal[:14]
    if cal:
        crows = ""
        for pr, mn, nmk, tag, status, act in cal:
            star = "★ " if mn == 0 else ""
            crows += (f'<tr><td style="{S["td"]};font-weight:700;white-space:nowrap">{star}{esc(nmk)}</td>'
                      f'<td style="{S["td"]}">{esc(tag)}</td>'
                      f'<td style="{S["td"]};white-space:nowrap;color:#1f7a4d;font-weight:700">{esc(status)}</td>'
                      f'<td style="{S["td"]};color:#374151">{esc(act)}</td></tr>')
        cal_tbl = (f'<table role="presentation" style="{S["tbl"]}"><tr>'
                   f'<th style="{S["th"]}">상품</th><th style="{S["th"]}">시즌 이슈</th>'
                   f'<th style="{S["th"]}">시점</th><th style="{S["th"]}">준비할 것</th></tr>{crows}</table>')
    else:
        cal_tbl = '<div style="font-size:12.5px;color:#6b7280">이번·다음 달 준비할 시즌 이슈가 없습니다.</div>'
    cal_html = f'<h3 style="{S["h3"]}">🗓️ 뉴스 캘린더 — 지금·곧 준비할 것</h3>{cal_tbl}'

    # 데이터 상태 + 푸터
    try:
        health = "<br>".join(esc(x) for x in cah.format_lines(cah.compute_health(now)))
    except Exception:
        health = "· 상태 확인 불가 · 자동수집이 정상이라고 단정할 수 없음"
    footer = (f'<div style="margin-top:24px;padding-top:12px;border-top:1px solid #eceef1;font-size:11px;color:#6b7280;line-height:1.6">'
              f'{health}<br><br>🔭 전체 대시보드 → <a href="https://{HUB}" style="color:#1f7a4d">{HUB}</a></div>')

    head = (f'<div style="{S["h2"]}">📮 Modooflow 데일리 브리핑</div>'
            f'<div style="{S["sub"]}">{now.month}/{now.day}({wd}) {part} · 담당 상품 {len(products)}종 + 업계·경쟁사 · 표로 한눈에</div>')
    html = f'<div style="{S["wrap"]}">{head}{prod_html}{ind_html}{cal_html}{footer}</div>'

    # ── 텍스트 대체본(HTML 미지원 클라이언트용) ──
    P = [f"📮 Modooflow 데일리 브리핑 · {now.month}/{now.day}({wd}) {part}", ""]

    def cat_text(key):
        nmn = newsmon.get(key, {})
        items = (cats.get(key) or {}).get("items", [])[:8]
        if not (nmn or items):
            return []
        out = [f"■ {name(key)} (헤드라인 {len(items)}건)"]
        if nmn.get("summary"):
            out.append(f"  동향 요약: {nmn['summary']}")
        if nmn.get("insight"):
            out.append(f"  마케팅 시사점: {nmn['insight']}")
        for it in items:
            out.append(f"  · {it.get('t','')} ({it.get('src','')}·{it.get('date','')})")
            g = (it.get("gist") or "").strip()
            if g:
                out.append(f"    ⤷ {g[:110]}")
            if it.get("url"):
                out.append(f"    {it['url']}")
        return out + [""]

    P += ["[보험별 동향]"]
    for k in prod_keys:
        P += cat_text(k)
    P += ["[경쟁사·업계 동향]"]
    for k, _ in INDUSTRY:
        P += cat_text(k)
    P += ["[뉴스 캘린더 — 지금·곧 준비할 것]"]
    if cal:
        for pr, mn, nmk, tag, status, act in cal:
            P.append(f"- {'★ ' if mn == 0 else ''}{nmk} | {tag} | {status} | {act}")
    else:
        P.append("- 이번·다음 달 준비할 시즌 이슈 없음")
    P += ["", f"🔭 전체 대시보드 → https://{HUB}"]
    plain = "\n".join(P)

    return subject, html, plain


def recipients():
    """수신자 chat_id 목록. TELEGRAM_CHAT_IDS(콤마/줄바꿈 다중) 우선, 없으면 TELEGRAM_CHAT_ID(단일).
    chat_id 는 개인 식별자라 저장소에 커밋하지 않고 GitHub Secrets 로만 주입한다."""
    raw = os.environ.get("TELEGRAM_CHAT_IDS") or os.environ.get("TELEGRAM_CHAT_ID") or ""
    seen, out = set(), []
    for c in raw.replace("\n", ",").replace(";", ",").split(","):
        c = c.strip()
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def send_telegram(text):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chats = recipients()
    if not (token and chats):
        print("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_IDS(또는 TELEGRAM_CHAT_ID) 미설정", file=sys.stderr)
        sys.exit(2)
    if len(text) > 4000:                      # 텔레그램 메시지 한도(4096) 보호
        text = text[:3980] + "\n…(생략)"
    sent, failed = 0, 0
    for chat in chats:
        data = urllib.parse.urlencode({"chat_id": chat, "text": text,
                                       "parse_mode": "HTML",
                                       "disable_web_page_preview": "true"}).encode()
        req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                ok = json.load(r).get("ok")
        except Exception as e:                # 한 명 실패가 다른 수신자 발송을 막지 않게
            ok = False
            print(f"  · {chat}: 예외 {e}", file=sys.stderr)
        sent += 1 if ok else 0
        failed += 0 if ok else 1
    print(f"텔레그램 발송: 성공 {sent}/{len(chats)}" + (f" · 실패 {failed}" if failed else ""))
    if failed:                                # 일부라도 미수신이면 실패(exit≠0) — 스케줄 워크플로가 부분 발송을 감지·재시도
        sys.exit(1)

def email_recipients():
    """수신 이메일 목록. EMAIL_TO(콤마/줄바꿈/세미콜론 다중). 이메일은 개인정보라 커밋하지 않고 Secrets 로만 주입."""
    raw = os.environ.get("EMAIL_TO") or ""
    seen, out = set(), []
    for c in raw.replace("\n", ",").replace(";", ",").split(","):
        c = c.strip()
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def send_email():
    """데일리 브리핑을 표 도식형 이메일(SMTP)로 발송 — 텔레그램과 독립. Gmail SMTP 기본.
    필요 Secrets: SMTP_USER(발송 계정) · SMTP_PASS(앱 비밀번호) · EMAIL_TO(수신 메일·다중)
      선택: SMTP_HOST(기본 smtp.gmail.com) · SMTP_PORT(기본 587·STARTTLS, 465=SSL) · EMAIL_FROM(기본 SMTP_USER)"""
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.utils import formataddr, formatdate
    host = os.environ.get("SMTP_HOST") or "smtp.gmail.com"
    port = int(os.environ.get("SMTP_PORT") or "587")
    user = os.environ.get("SMTP_USER")
    pw = os.environ.get("SMTP_PASS")
    frm = os.environ.get("EMAIL_FROM") or user
    to = email_recipients()
    if not (user and pw and to):
        print("SMTP_USER / SMTP_PASS / EMAIL_TO 미설정", file=sys.stderr)
        sys.exit(2)
    subject, html, plain = render_email()
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = formataddr(("Modooflow 브리핑", frm))
    msg["To"] = ", ".join(to)
    msg["Date"] = formatdate(localtime=True)
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    try:
        if port == 465:
            server = smtplib.SMTP_SSL(host, port, timeout=30)
        else:
            server = smtplib.SMTP(host, port, timeout=30)
            server.ehlo()
            server.starttls()
            server.ehlo()
        server.login(user, pw)
        server.sendmail(frm, to, msg.as_string())
        server.quit()
    except Exception as e:
        print(f"이메일 발송 실패: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"이메일 발송: 성공 {len(to)}명 → {', '.join(to)}")


if __name__ == "__main__":
    if "--dry" in sys.argv:                       # 텔레그램 본문 미리보기
        print(build_message())
    elif "--email-preview" in sys.argv:           # 이메일(표 도식형) 미리보기 — 발송 없음
        subject, html, plain = render_email()
        out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None
        if out:
            with open(out, "w", encoding="utf-8") as f:
                f.write(f"<!-- Subject: {subject} -->\n" + html)
            print(f"제목: {subject}\nHTML 미리보기 저장 → {out}")
        else:
            print("제목:", subject, "\n")
            print(plain)
    elif "--email" in sys.argv:                   # 이메일 발송(SMTP)
        send_email()
    else:                                          # 텔레그램 발송(기본)
        send_telegram(build_message())
