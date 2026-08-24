#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""긴급 대형화재 감시 — 최신 화재 뉴스를 감지해 '별도' 텔레그램 알림(정기 브리프와 분리).

왜: 대형화재·산불은 주택화재보험 검색·가입이 급증하는 메인 수요 트리거. 하루 2회 정기
    브리프를 기다리지 않고, 뜨는 즉시 담당자에게 알려 소재·검색광고를 선제 대응하기 위함.

동작:
  - 네이버 뉴스 검색 API로 화재 키워드를 조회(최신순) → 최근 N시간(FIRE_WINDOW_HOURS, 기본 4)
    이내 기사만 추림 → '사건 특화 문구'(대형 화재·산불·아파트 화재 등)로 필터(회사명 '삼성화재'
    같은 오탐 회피) → 제목 dedup → 심각도 점수순.
  - 기본 **dry-run**: 발송하지 않고 감지 결과만 출력(로그). 실제 발송은 --send 또는 FIRE_ALERT_SEND=1.
  - 상태 파일 없음(무커밋). 최근 N시간 창으로 중복을 억제(실행 주기 ≤ 창).

필요 환경변수(Secrets):
  NAVER_CLIENT_ID / NAVER_CLIENT_SECRET   (필수, 뉴스 조회)
  TELEGRAM_BOT_TOKEN                        (발송 시)
  FIRE_TELEGRAM_CHAT_IDS 또는 TELEGRAM_CHAT_IDS/TELEGRAM_CHAT_ID  (발송 대상)
공개 뉴스 헤드라인·링크만 사용(데이터 거버넌스). 표준 라이브러리만.
"""
import os, sys, json, re, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta
from telegram_utils import split_html_message

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HUB = "imsplendid8.github.io/CM-CMO"
KST = timezone(timedelta(hours=9))
ID = os.environ.get("NAVER_CLIENT_ID", "").strip()
SECRET = os.environ.get("NAVER_CLIENT_SECRET", "").strip()

# 조회 질의(넓게) → 아래 STRONG 문구로 정밀 필터
QUERIES = ["대형화재", "산불", "아파트 화재", "공장 화재", "물류창고 화재"]
# 사건 특화 문구: 공백 포함/사건 단어라 회사명(삼성화재·화재보험 상품명)엔 매칭되지 않음
STRONG = ["대형화재", "대형 화재", "산불", "들불", "아파트 화재", "공장 화재", "창고 화재",
          "물류창고 화재", "주택 화재", "상가 화재", "빌딩 화재", "화재 사망", "화재 참사",
          "화재 대피", "화재로 대피", "화재로 숨", "전소", "연쇄 화재", "야산 화재"]
SEVERITY = ["사망", "숨진", "부상", "실종", "대피", "이재민", "전소", "참사", "완전 소실", "전체 소실"]
# '화재'가 과거 사건·작품·행사 문맥에 언급된 기사까지 긴급 신호로 잡지 않도록
# 실제 사고 진행을 나타내는 말이 하나 이상 있어야 한다. 회고/행사성 문맥은 명시적으로 제외한다.
INCIDENT = ["발생", "불이 나", "불이 났", "화재가", "진화", "대피", "사망", "숨진", "숨져",
            "부상", "전소", "소방 당국", "소방당국", "번져", "확산", "불길", "잔불"]
TITLE_EVENT = ["화재", "산불", "들불", "전소", "불이 나", "불이 났", "불길", "진화"]
NON_INCIDENT = ["재건", "기념", "추모", "북토크", "소설", "작품", "토론회", "세미나", "캠페인",
                "예방 교육", "대피 훈련", "피해 복구 지원", "후손 도움", "지난해 산불로"]


def kst_now():
    return datetime.now(timezone.utc).astimezone(KST)


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def strip(s):
    return re.sub(r"<[^>]*>", "", str(s or "")).replace("&quot;", '"').replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&#39;", "'").strip()


def host(u):
    try:
        return urllib.parse.urlparse(u).hostname.replace("www.", "")
    except Exception:
        return ""


def naver_news(q, display=30):
    url = "https://openapi.naver.com/v1/search/news.json?" + urllib.parse.urlencode({"query": q, "display": display, "sort": "date"})
    req = urllib.request.Request(url, headers={"X-Naver-Client-Id": ID, "X-Naver-Client-Secret": SECRET})
    with urllib.request.urlopen(req, timeout=20) as r:
        d = json.loads(r.read().decode("utf-8"))
    out = []
    for it in d.get("items", []):
        u = it.get("link") or it.get("originallink")
        if not u:
            continue
        dt = None
        try:
            dt = datetime.strptime(it.get("pubDate", "")[:31].strip(), "%a, %d %b %Y %H:%M:%S %z")
        except Exception:
            dt = None
        out.append({"t": strip(it.get("title")), "src": host(it.get("originallink") or u),
                    "url": u, "gist": strip(it.get("description"))[:90], "dt": dt})
    return out


def same_event_title(a, b):
    """띄어쓰기·조사 차이가 있어도 장소/시설/사건 단어 3개 이상이 겹치면 같은 사건으로 본다."""
    def terms(value):
        return {x for x in re.findall(r"[가-힣A-Za-z0-9]+", value.lower()) if len(x) >= 2}

    left, right = terms(a), terms(b)
    matched = 0
    used = set()
    for x in sorted(left, key=len, reverse=True):
        for y in sorted(right, key=len, reverse=True):
            if y in used:
                continue
            if x in y or y in x:
                used.add(y)
                matched += 1
                break
    return matched >= 3


def detect(items, now, window_hours):
    """사건 문구·발생성 필터 + 최근 window 시간 + 제목 dedup + 심각도 점수순."""
    cutoff = now - timedelta(hours=window_hours)
    future_limit = now + timedelta(minutes=10)
    hits = []
    for it in items:
        title = it.get("t", "")
        text = title + " " + it.get("gist", "")
        strong = [w for w in STRONG if w in text]
        if not strong:
            continue
        if not any(w in text for w in INCIDENT):
            continue
        if any(w in text for w in NON_INCIDENT):
            continue
        # 긴급 알림은 제목 자체에도 사건 종류가 드러나야 한다. 본문에서 과거 화재를
        # 배경으로만 언급한 문화·후원·정책 기사는 여기서 빠진다.
        if not any(w in title for w in TITLE_EVENT):
            continue
        dt = it.get("dt")
        if dt is None or dt < cutoff or dt > future_limit:  # 시각 불명·오래됨·비정상 미래 시각은 fail-closed
            continue
        sev = [w for w in SEVERITY if w in text]
        it = dict(it, score=len(strong) * 2 + len(sev), kw=strong + sev)
        hits.append(it)
    hits.sort(key=lambda x: (x["score"], x.get("dt") or now), reverse=True)
    out, seen = [], set()
    for h in hits:
        k = h["t"][:14]
        if k in seen or any(same_event_title(h["t"], prev["t"]) for prev in out):
            continue
        seen.add(k)
        out.append(h)
    return out


def build_alert(hits, now):
    wd = "월화수목금토일"[now.weekday()]
    parts = [f"🚨 [대형화재 감시] {now.month}/{now.day}({wd}) {now.strftime('%H:%M')} — 감지 {len(hits)}건",
             "주택화재보험 수요 급증 트리거 — 누수·풍수재·잔존물제거 소구·검색광고 선제 점검", ""]
    for h in hits[:6]:
        line = f"· {esc(h['t'][:52])} ({esc(h['src'])})"
        g = str(h.get("gist") or "").strip()
        if g:
            line += f"\n  ⤷ {esc(g[:80])}"
        if h.get("url"):
            line += f'\n  🔗 <a href="{esc(h["url"])}">바로가기</a>'
        parts.append(line)
    parts += ["", f"🔭 뉴스 모니터링 → https://{HUB}/news-tool.html"]
    return "\n".join(parts)


def fire_recipients():
    raw = os.environ.get("FIRE_TELEGRAM_CHAT_IDS") or os.environ.get("TELEGRAM_CHAT_IDS") or os.environ.get("TELEGRAM_CHAT_ID") or ""
    seen, out = set(), []
    for c in raw.replace("\n", ",").replace(";", ",").split(","):
        c = c.strip()
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def send_telegram(text):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chats = fire_recipients()
    if not (token and chats):
        print("TELEGRAM_BOT_TOKEN / (FIRE_)TELEGRAM_CHAT_IDS 미설정 — 발송 생략", file=sys.stderr)
        return False
    chunks = split_html_message(text)
    ok_all = True
    for recipient_no, chat in enumerate(chats, 1):
        recipient_ok = True
        for chunk in chunks:
            data = urllib.parse.urlencode({"chat_id": chat, "text": chunk, "parse_mode": "HTML",
                                           "disable_web_page_preview": "true"}).encode()
            req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
            try:
                with urllib.request.urlopen(req, timeout=15) as r:
                    ok = json.load(r).get("ok")
            except Exception as e:
                ok = False
                print(f"  · 수신자 {recipient_no}: {type(e).__name__}", file=sys.stderr)
            recipient_ok = recipient_ok and bool(ok)
            if not ok:
                break
        ok_all = ok_all and recipient_ok
    return ok_all


def gather():
    seen, items = set(), []
    for q in QUERIES:
        try:
            for it in naver_news(q):
                if it["url"] in seen:
                    continue
                seen.add(it["url"])
                items.append(it)
        except Exception as e:
            print(f"  · 조회 실패 '{q}': {e}", file=sys.stderr)
    return items


def main():
    now = kst_now()
    window = int(os.environ.get("FIRE_WINDOW_HOURS") or "4")
    send = ("--send" in sys.argv) or (os.environ.get("FIRE_ALERT_SEND") == "1")
    if not (ID and SECRET):
        print("NAVER_CLIENT_ID/SECRET 미설정 — 감시 불가", file=sys.stderr)
        sys.exit(2)
    hits = detect(gather(), now, window)
    if not hits:
        print(f"✔ 대형화재 신규 신호 없음 (최근 {window}시간 · {now.strftime('%Y-%m-%d %H:%M')} KST)")
        return
    msg = build_alert(hits, now)
    if send:
        ok = send_telegram(msg)
        print(f"🚨 대형화재 알림 발송 {'성공' if ok else '실패/생략'} · {len(hits)}건\n{msg}")
        if not ok:
            sys.exit(1)
    else:
        print("[dry-run · 발송 안 함 — 실제 발송은 --send 또는 FIRE_ALERT_SEND=1]\n" + msg)


if __name__ == "__main__":
    main()
