#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""데일리 비서 브리핑 — 텔레그램 발송.

오늘(한국시간)의 시즌 이슈(data/seasonal.json) + SERP 할일 + (선택)네이버 뉴스를
한 건의 텔레그램 메시지로 담당자에게 보낸다. GitHub Actions 일일 cron에서 실행.

필요 환경변수(Secrets):
  TELEGRAM_BOT_TOKEN   (필수) @BotFather 로 만든 봇 토큰
  TELEGRAM_CHAT_ID     (필수) 내 chat id (봇과 대화 후 getUpdates 로 확인)
  뉴스는 news-clip 워크플로가 만든 data/briefing/latest.json을 사용
표준 라이브러리만 사용.
"""
import os, json, sys, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_automation_health as cah   # 자동화 상태를 브리프 직전 재계산(저장 요약 미신뢰)
import event_engine as ee               # 시즌 span 일자 판정 공유(월 전체가 아닌 정확 기간)
import content_brief                     # 대시보드·텔레그램·이메일 공통 뉴스 분석

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

def latest_clip():
    """오늘(없으면 최근) 뉴스 클리핑 파일을 로드."""
    idx = load_opt("data/clips/index.json", {}) or {}
    for d in idx.get("dates", []):
        c = load_opt(f"data/clips/{d['date']}.json")
        if c:
            return c
    return None

def shared_digest(clip, products, main):
    """저장된 공통 브리프를 우선 사용하고, 최신 클리핑과 날짜가 다르면 즉시 재계산한다."""
    saved = load_opt("data/briefing/latest.json", {}) or {}
    if saved.get("date") == (clip or {}).get("date") and saved.get("stories"):
        return saved
    return content_brief.build_digest(clip or {}, products, main)

def esc(s):
    """텔레그램 HTML parse_mode용 이스케이프(제목·요약·URL 등 동적 텍스트)."""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

EMAIL_NEWS_N = 8   # 이메일 '주요 뉴스' 표시 개수(전체 통틀어, 카테고리별 아님) — 5~10 권장

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
    triggers = signals.get("triggers") or {}
    if not isinstance(triggers, dict):
        triggers = {}
    for key, t in triggers.items():
        if not isinstance(t, dict):
            continue
        lv = t.get("level")
        if lv in ("high", "medium"):
            icon = "🔥" if lv == "high" else "🌡"
            word = "급등" if lv == "high" else "상승"
            put(key, 0, f"{icon} {name(key)} — 검색수요 {word}: 소재·입찰 강화 + 랜딩 점검")
    weather = signals.get("weather") or {}
    active_weather = weather.get("active", []) if isinstance(weather, dict) else []
    if not isinstance(active_weather, list):
        active_weather = []
    for w in active_weather:
        if isinstance(w, dict):
            note = str(w.get("note") or w.get("name") or "기상 특보").strip()
        else:
            note = str(w).strip() or "기상 특보"
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

    ordered = sorted(actions.values(), key=lambda x: x[0])
    urgent = [txt for pri, txt in ordered if pri <= 0]
    serp = [txt for _, txt in ordered if "SERP" in txt]
    routine = [txt for pri, txt in ordered if pri > 0 and "SERP" not in txt]
    # 근거 변화가 없는 시즌 할 일을 매일 모두 반복하지 않고 하루 한 건만 순환한다.
    # 급등·기상 등 새로운 신호는 언제나 우선 노출한다.
    focus = [routine[now.toordinal() % len(routine)]] if routine else []
    return (urgent[:2] + focus + serp[:1])[:4]


def build_message():
    products, order, main, seasonal, signals, clip, now = _load_context()
    wd = "월화수목금토일"[now.weekday()]
    action_lines = [f"{i+1}. {t}" for i, t in enumerate(compute_action_lines(products, main, seasonal, signals, now))]
    digest = shared_digest(clip, products, main)
    news_lines = []
    for story in digest.get("stories", [])[:3]:
        link = f' · <a href="{esc(story.get("url"))}">원문</a>' if story.get("url") else ""
        news_lines.append(
            f"· <b>[{esc(story.get('tag'))}] {esc(story.get('title'))}</b>\n"
            f"  무슨 일 · {esc(story.get('what'))}\n"
            f"  왜 중요 · {esc(story.get('why'))}\n"
            f"  오늘 대응 · {esc(story.get('action'))}{link}"
        )

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
    구성: ① 핵심 동향(메인 3종+업계 요약) ② 주요 뉴스(전체 상위 N건)."""
    products, order, main, seasonal, signals, clip, now = _load_context()
    digest = shared_digest(clip, products, main)
    newsmon = digest.get("categories", {})
    wd = "월화수목금토일"[now.weekday()]
    part = "오전" if now.hour < 12 else "오후"
    subject = f"(장기CM사업부) {now.strftime('%y.%m.%d')} 뉴스 모니터링"
    ind_name = dict(INDUSTRY)
    name = lambda k: products.get(k, {}).get("name") or ind_name.get(k, k)
    S = _ES

    def trend_card(key, accent):
        """카테고리 동향 요약(헤드라인·시사점 없이 압축)."""
        nmn = newsmon.get(key, {})
        if not nmn.get("summary"):
            return ""
        cat_style = f"font-size:13.5px;font-weight:800;background:#f4f6f8;border-left:4px solid {accent};padding:7px 11px;border-radius:7px 7px 0 0;margin-top:12px;"
        return (f'<div style="{cat_style}">{esc(name(key))}</div>'
                f'<div style="{S["sumbox"]}border-radius:0;"><span style="{S["bg"]}">무슨 일</span>{esc(nmn["summary"])}</div>'
                f'<div style="{S["insbox"]}"><span style="{S["ba"]}">권장 대응</span>{esc(nmn.get("insight", "원문 근거를 확인한 뒤 반영 여부를 판단하세요."))}</div>')

    # ① 핵심 동향 — 메인 3종(★) + 업계 전반만(전체 카테고리 아님)
    focus = [k for k in main if k in newsmon] + (["ind_biz"] if "ind_biz" in newsmon else [])
    if not focus:
        focus = list(newsmon)[:4]
    trend_body = "".join(trend_card(k, "#b45309" if k == "ind_biz" else "#1f7a4d") for k in focus)
    trend_html = f'<h3 style="{S["h3"]}">📊 핵심 동향 <span style="font-size:12px;color:#6b7280;font-weight:600">· 메인 상품 + 업계 전반</span></h3>' + (trend_body or '<div style="font-size:12.5px;color:#6b7280">동향 데이터가 없습니다.</div>')

    # ② 주요 뉴스 — 전체 통틀어 상위 N건(카테고리별 아님)
    news = digest.get("stories", [])[:EMAIL_NEWS_N]
    if news:
        nrows = ""
        for it in news:
            tag = it.get("tag", "")
            t = esc(it.get("title", ""))
            g = esc(it.get("what", ""))
            src = esc(it.get("source", ""))
            dt = esc(it.get("date", ""))
            url = it.get("url", "")
            comp = tag.startswith("경쟁사")
            tag_style = f'font-size:10.5px;font-weight:800;white-space:nowrap;vertical-align:top;padding:7px 10px;border-bottom:1px solid #eef0f3;color:{"#9a6b12" if comp else "#1f7a4d"}'
            title = f'<a href="{esc(url)}" style="color:#1f2937;text-decoration:none;font-weight:600">{t}</a>' if url else f"<b>{t}</b>"
            gh = (f'<div style="color:#6b7280;font-size:11.5px;margin-top:3px">{g}</div>'
                  f'<div style="color:#9a6b12;font-size:11.5px;margin-top:3px"><b>왜 중요</b> · {esc(it.get("why", ""))}</div>'
                  f'<div style="color:#1f7a4d;font-size:11.5px;margin-top:3px"><b>권장 대응</b> · {esc(it.get("action", ""))}</div>')
            nrows += (f'<tr><td style="{tag_style}">{esc(tag)}</td>'
                      f'<td style="{S["td"]}">{title}{gh}</td>'
                      f'<td style="{S["tdr"]}">{src}<br>{dt}</td></tr>')
        news_tbl = (f'<table role="presentation" style="{S["tbl"]}"><tr>'
                    f'<th style="{S["th"]}">구분</th><th style="{S["th"]}">제목 · 요약</th>'
                    f'<th style="{S["th"]}">출처</th></tr>{nrows}</table>')
    else:
        news_tbl = '<div style="font-size:12.5px;color:#6b7280">행동가치 있는 주요 뉴스가 없습니다.</div>'
    news_html = f'<h3 style="{S["h3"]}">📰 주요 뉴스 <span style="font-size:12px;color:#6b7280;font-weight:600">· 전체 상위 {len(news)}건(경쟁사 우선)</span></h3>{news_tbl}'

    # 데이터 상태 + 푸터
    try:
        health = "<br>".join(esc(x) for x in cah.format_lines(cah.compute_health(now)))
    except Exception:
        health = "· 상태 확인 불가 · 자동수집이 정상이라고 단정할 수 없음"
    footer = (f'<div style="margin-top:24px;padding-top:12px;border-top:1px solid #eceef1;font-size:11px;color:#6b7280;line-height:1.6">'
              f'{health}<br><br>🔭 전체 대시보드 → <a href="https://{HUB}" style="color:#1f7a4d">{HUB}</a></div>')

    head = (f'<div style="{S["h2"]}">📮 (장기CM사업부) 뉴스 모니터링</div>'
            f'<div style="{S["sub"]}">{now.strftime("%Y.%m.%d")}({wd}) {part} · 핵심 동향 + 주요 뉴스 · 표로 한눈에</div>')
    html = f'<div style="{S["wrap"]}">{head}{trend_html}{news_html}{footer}</div>'

    # ── 텍스트 대체본(HTML 미지원 클라이언트용) ──
    P = [f"(장기CM사업부) {now.strftime('%y.%m.%d')} 뉴스 모니터링 · {wd}요일 {part}", ""]
    P += ["[핵심 동향]"]
    for k in focus:
        nmn = newsmon.get(k, {})
        if nmn.get("summary"):
            P.append(f"■ {name(k)}: {nmn['summary']}")
    P += ["", f"[주요 뉴스 · 전체 상위 {len(news)}건]"]
    for it in news:
        P.append(f"· ({it.get('tag','')}) {it.get('title','')} ({it.get('source','')}·{it.get('date','')})")
        P.append(f"  무슨 일 · {it.get('what','')}")
        P.append(f"  왜 중요 · {it.get('why','')}")
        P.append(f"  권장 대응 · {it.get('action','')}")
        if it.get("url"):
            P.append(f"  {it['url']}")
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
