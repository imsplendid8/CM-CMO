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
import html
import os, json, sys, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_automation_health as cah   # 자동화 상태를 브리프 직전 재계산(저장 요약 미신뢰)
import event_engine as ee               # 시즌 span 일자 판정 공유(월 전체가 아닌 정확 기간)
import humanize_korean as hk             # im-not-ai light 호환 한국어 후처리
import content_brief                     # 대시보드·텔레그램·이메일 공통 뉴스 분석
from telegram_utils import split_html_message

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
    """저장된 공통 브리프를 우선 사용한다.

    브리프 발송은 속도가 중요하므로, 기본값은 data/briefing/latest.json을 그대로 쓰고
    명시적으로 재계산이 필요할 때만 BRIEF_REFRESH_DIGEST=1 로 갱신한다.
    """
    saved = load_opt("data/briefing/latest.json", {}) or {}
    if saved.get("stories") and os.environ.get("BRIEF_REFRESH_DIGEST") != "1":
        return saved
    if saved.get("date") == (clip or {}).get("date") and saved.get("stories"):
        return saved
    return content_brief.build_digest(clip or {}, products, main)

def esc(s):
    """텔레그램·이메일 HTML의 동적 텍스트와 속성값을 안전하게 이스케이프한다."""
    return html.escape(str(s or ""), quote=True)

EMAIL_NEWS_N = 8   # 이메일 '주요 뉴스' 표시 개수(전체 통틀어, 카테고리별 아님) — 5~10 권장


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

    exit_tour = signals.get("exit_tour") or {}
    if isinstance(exit_tour, dict):
        outbound = exit_tour.get("outbound_count")
        if outbound is not None:
            try:
                outbound_num = float(str(outbound).replace(",", ""))
            except Exception:
                outbound_num = None
            if outbound_num is not None and outbound_num >= 100:
                period = str(exit_tour.get("period") or signals.get("asof") or "").strip()
                put("overseas_exit", 0, f"🛫 해외여행보험 — 출입국관광통계 {period} 수치 {outbound_num:g}: 해외여행보험 수요 점검")

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
        source = esc(story.get("source"))
        date = esc(story.get("date"))
        meta = " · ".join(value for value in (source, date) if value)
        link = f'<a href="{esc(story.get("url"))}">원문</a>' if story.get("url") else ""
        trail = " · ".join(value for value in (meta, link) if value)
        news_lines.append(
            f"· <b>[{esc(story.get('tag'))}] {esc(story.get('title'))}</b>\n"
            f"  {esc(hk.humanize(story.get('what', '')))}"
            + (f"\n  {trail}" if trail else "")
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

# ── 이메일 스타일 토큰 — 인라인 CSS(메일 클라이언트 호환), 이미지 없음 ──
_ES = {
    "wrap": "width:100%;max-width:680px;margin:0;padding:20px 14px;box-sizing:border-box;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Malgun Gothic','Apple SD Gothic Neo',sans-serif;color:#20242c;background:#ffffff;text-align:left;overflow-wrap:anywhere;word-break:keep-all;",
    "h2": "font-size:19px;font-weight:800;margin:0 0 3px;letter-spacing:-.02em;text-align:left;overflow-wrap:anywhere;word-break:keep-all;",
    "sub": "font-size:12.5px;color:#6b7280;margin:0 0 6px;line-height:1.55;text-align:left;overflow-wrap:anywhere;",
    "h3": "font-size:15px;font-weight:800;margin:26px 0 10px;padding-bottom:6px;border-bottom:2px solid #eceef1;text-align:left;overflow-wrap:anywhere;",
    "card": "width:100%;box-sizing:border-box;border:1px solid #e6e8ec;border-radius:8px;padding:11px 12px;margin:0 0 9px;background:#ffffff;text-align:left;overflow-wrap:anywhere;word-break:keep-all;",
    "tag": "display:inline-block;font-size:10.5px;font-weight:800;padding:2px 7px;border-radius:99px;margin:0 0 6px;vertical-align:1px;",
    "title": "display:block;color:#1f2937;text-decoration:none;font-size:13px;font-weight:700;line-height:1.55;white-space:normal;overflow-wrap:anywhere;word-break:keep-all;",
    "summary": "color:#5f6774;font-size:12px;line-height:1.65;margin-top:5px;overflow-wrap:anywhere;word-break:keep-all;",
    "meta": "color:#8a919e;font-size:11px;line-height:1.55;margin-top:6px;overflow-wrap:anywhere;word-break:break-word;",
}


def render_email():
    """데일리 브리핑을 반응형 이메일(HTML+텍스트)로 렌더한다.

    뉴스는 제목·요약·출처만 표시하고, 좁은 메일 앱에서도 잘리지 않도록 모든 항목을
    한 열로 쌓는다. returns (subject, html, plain).
    """
    products, order, main, seasonal, signals, clip, now = _load_context()
    digest = shared_digest(clip, products, main)
    wd = "월화수목금토일"[now.weekday()]
    part = "오전" if now.hour < 12 else "오후"
    subject = f"(장기CM사업부) {now.strftime('%y.%m.%d')} 뉴스 모니터링"
    S = _ES

    # 주요 뉴스 — 전체 통틀어 상위 N건을 제목·요약·출처만 한 열로 표시한다.
    news = digest.get("stories", [])[:EMAIL_NEWS_N]
    if news:
        cards = ""
        for it in news:
            tag = it.get("tag", "")
            t = esc(it.get("title", ""))
            g = esc(hk.humanize(it.get("what", "")))
            src = esc(it.get("source", ""))
            dt = esc(it.get("date", ""))
            url = it.get("url", "")
            comp = tag.startswith("경쟁사")
            tag_style = S["tag"] + f'color:{"#9a6b12" if comp else "#1f7a4d"};background:{"#fbf3e0" if comp else "#e8f5ee"};'
            title = f'<a href="{esc(url)}" style="{S["title"]}">{t}</a>' if url else f'<div style="{S["title"]}">{t}</div>'
            meta = " · ".join(value for value in (src, dt) if value)
            source_link = f'<a href="{esc(url)}" style="color:#1f7a4d;text-decoration:underline">원문 보기</a>' if url else ""
            source_line = " · ".join(value for value in (meta, source_link) if value)
            cards += (f'<div style="{S["card"]}">'
                      f'<span style="{tag_style}">{esc(tag)}</span>'
                      f'{title}<div style="{S["summary"]}">{g}</div>'
                      f'<div style="{S["meta"]}">{source_line}</div></div>')
        news_body = cards
    else:
        news_body = '<div style="font-size:12.5px;color:#6b7280">주요 뉴스가 없습니다.</div>'
    news_html = f'<h3 style="{S["h3"]}">📰 주요 뉴스 <span style="font-size:12px;color:#6b7280;font-weight:600">· 전체 상위 {len(news)}건</span></h3>{news_body}'

    # 데이터 상태 + 푸터
    try:
        health = "<br>".join(esc(x) for x in cah.format_lines(cah.compute_health(now)))
    except Exception:
        health = "· 상태 확인 불가 · 자동수집이 정상이라고 단정할 수 없음"
    footer = (f'<div style="margin-top:24px;padding-top:12px;border-top:1px solid #eceef1;font-size:11px;color:#6b7280;line-height:1.6">'
              f'{health}<br><br>🔭 전체 대시보드 → <a href="https://{HUB}" style="color:#1f7a4d">{HUB}</a></div>')

    head = (f'<div style="{S["h2"]}">📮 (장기CM사업부) 뉴스 모니터링</div>'
            f'<div style="{S["sub"]}">{now.strftime("%Y.%m.%d")}({wd}) {part} · 주요 뉴스 요약 {len(news)}건</div>')
    html = ('<!doctype html><html><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '</head><body style="margin:0;padding:0;background:#ffffff;text-align:left">'
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
            'align="left" style="width:100%;table-layout:fixed;border-collapse:collapse;text-align:left"><tr>'
            '<td align="left" style="padding:0;text-align:left">'
            f'<div style="{S["wrap"]}">{head}{news_html}{footer}</div>'
            '</td></tr></table></body></html>')

    # ── 텍스트 대체본(HTML 미지원 클라이언트용) ──
    P = [f"(장기CM사업부) {now.strftime('%y.%m.%d')} 뉴스 모니터링 · {wd}요일 {part}", ""]
    P += [f"[주요 뉴스 요약 · 전체 상위 {len(news)}건]"]
    for it in news:
        P.append(f"· ({it.get('tag','')}) {it.get('title','')} ({it.get('source','')}·{it.get('date','')})")
        P.append(f"  {hk.humanize(it.get('what',''))}")
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
    chunks = split_html_message(text)
    sent, failed = 0, 0
    for recipient_no, chat in enumerate(chats, 1):
        recipient_ok = True
        for chunk in chunks:
            data = urllib.parse.urlencode({"chat_id": chat, "text": chunk,
                                           "parse_mode": "HTML",
                                           "disable_web_page_preview": "true"}).encode()
            req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
            try:
                with urllib.request.urlopen(req, timeout=15) as r:
                    ok = json.load(r).get("ok")
            except Exception as e:            # 한 명 실패가 다른 수신자 발송을 막지 않게
                ok = False
                print(f"  · 수신자 {recipient_no}: {type(e).__name__}", file=sys.stderr)
            recipient_ok = recipient_ok and bool(ok)
            if not ok:
                break
        sent += 1 if recipient_ok else 0
        failed += 0 if recipient_ok else 1
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
        print(f"이메일 발송 실패 ({type(e).__name__})", file=sys.stderr)
        sys.exit(1)
    print(f"이메일 발송: 성공 {len(to)}명")


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
