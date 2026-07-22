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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HUB = "imsplendid8.github.io/CM-CMO"

def load(p):
    return json.load(open(os.path.join(ROOT, p), encoding="utf-8"))

def kst_now():
    return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=9)))

def naver_news(query):
    cid, csec = os.environ.get("NAVER_CLIENT_ID"), os.environ.get("NAVER_CLIENT_SECRET")
    if not (cid and csec):
        return None
    q = urllib.parse.urlencode({"query": query, "display": 1, "sort": "date"})
    req = urllib.request.Request("https://openapi.naver.com/v1/search/news.json?" + q,
                                 headers={"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": csec})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            items = json.load(r).get("items", [])
        if items:
            import re
            return re.sub(r"<[^>]+>", "", items[0]["title"]).replace("&quot;", '"').replace("&amp;", "&")
    except Exception:
        return None
    return None

def build_message():
    products = {p["key"]: p for p in load("data/products.json")["products"]}
    main = load("data/products.json")["main"]
    seasonal = load("data/seasonal.json")["seasonal"]
    now = kst_now()
    m = now.month
    wd = "월화수목금토일"[now.weekday()]
    # 이번 달 시즌 이슈 (메인 우선)
    hits = []
    for key, wins in seasonal.items():
        for w in wins:
            if m in w["m"]:
                hits.append((key, w))
    hits.sort(key=lambda x: (0 if x[0] in main else 1))
    season_lines = []
    for key, w in hits[:5]:
        star = "★" if key in main else "·"
        name = products.get(key, {}).get("name", key)
        season_lines.append(f"{star} {name} — {w['tag']} ({', '.join(w['kws'][:3])})")
    # SERP 할일(한화 상위노출 갭 · 메인 위주)
    gaps = ["hrmf", "golf", "overseas"]
    gap_names = " · ".join(products.get(k, {}).get("name", k) for k in gaps)
    # 뉴스(선택) — 메인 상품 + 상품별 추가 키워드(예: 주택화재 '대형화재사고')
    news_lines = []
    for key in main:
        p = products[key]
        for q in [p["newsQuery"]] + p.get("newsExtra", []):
            t = naver_news(q)
            if t:
                tag = "" if q == p["newsQuery"] else f"[{q}] "
                news_lines.append(f"· {p['name']}: {tag}{t[:54]}")

    part = "오전" if now.hour < 12 else "오후"
    parts = [f"🗓️ Modooflow 데일리 비서 · {now.month}/{now.day}({wd}) {part}", ""]
    parts.append("☔ 오늘의 시즌 이슈")
    parts += (season_lines or ["· 특이 시즌 이슈 없음"])
    if news_lines:
        parts += ["", "📰 주요 뉴스(메인 3종)"] + news_lines
    parts += ["", f"🔭 SERP 할일 · 한화 상위노출 갭 점검: {gap_names}",
              "", f"→ https://{HUB}"]
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
