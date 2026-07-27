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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HUB = "imsplendid8.github.io/CM-CMO"

def load(p):
    return json.load(open(os.path.join(ROOT, p), encoding="utf-8"))

def load_opt(p, default=None):
    try:
        return json.load(open(os.path.join(ROOT, p), encoding="utf-8"))
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

def pick_news(clip, products):
    """행동가치 있는 뉴스만 2~3건: [경쟁사 동향] / [트리거]."""
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
            cands.append((score, it.get("date", ""), tag, t, it.get("src", "")))
    # 점수·최신 우선, 제목 앞부분 dedup
    cands.sort(key=lambda x: (x[0], x[1]), reverse=True)
    out, seen = [], set()
    for sc, dt, tag, t, src in cands:
        k = t[:12]
        if k in seen:
            continue
        seen.add(k)
        out.append(f"· {tag} {t[:44]} ({src})")
        if len(out) >= 3:
            break
    return out

def build_message():
    pdata = load("data/products.json")
    products = {p["key"]: p for p in pdata["products"]}
    main = pdata["main"]
    seasonal = load("data/seasonal.json")["seasonal"]
    signals = load_opt("data/signals.json", {}) or {}
    clip = latest_clip()
    now = kst_now()
    m = now.month
    nm = m % 12 + 1  # 다음 달
    wd = "월화수목금토일"[now.weekday()]
    name = lambda k: products.get(k, {}).get("name", k)

    # ── 오늘 할 일(액션) 산출: 상품별 1건, 우선순위 정렬 ──
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

    # (2) 시즌 이슈(이번 달 → 다음 달), 메인 우선
    for key, wins in seasonal.items():
        for w in wins:
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

    ranked = sorted(actions.values(), key=lambda x: x[0])[:5]
    action_lines = [f"{i+1}. {txt}" for i, (_, txt) in enumerate(ranked)]

    news_lines = pick_news(clip, products)

    part = "오전" if now.hour < 12 else "오후"
    parts = [f"🗓️ Modooflow · {now.month}/{now.day}({wd}) {part} — 오늘 할 일 {len(action_lines)}", ""]
    parts += ["✅ 오늘 할 일 (우선순위)"] + (action_lines or ["· 오늘 특이 액션 없음 — 정기 점검만"])
    if news_lines:
        parts += ["", "📰 주목할 뉴스"] + news_lines
    # 자동화 수집 상태 — 저장된 요약을 믿지 않고 지금 다시 계산해 표시
    parts += [""] + cah.format_lines(cah.compute_health(now))
    parts += ["", f"🔭 전체 대시보드 → https://{HUB}"]
    return "\n".join(parts)

def send_telegram(text):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and chat):
        print("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 미설정", file=sys.stderr)
        sys.exit(2)
    data = urllib.parse.urlencode({"chat_id": chat, "text": text, "disable_web_page_preview": "true"}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
    with urllib.request.urlopen(req, timeout=15) as r:
        ok = json.load(r).get("ok")
    print("텔레그램 발송:", "성공" if ok else "실패")
    if not ok:
        sys.exit(1)

if __name__ == "__main__":
    msg = build_message()
    if "--dry" in sys.argv:
        print(msg)
    else:
        send_telegram(msg)
