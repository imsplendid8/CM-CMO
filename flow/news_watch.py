#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
손해보험 가입 프로세스/퍼널 리뉴얼 뉴스 감지 → 카카오톡 '나에게 보내기' 알림.

설계(안전):
  - 경쟁사 사이트를 직접 스크래핑하지 않는다. 공개 뉴스 검색(Google News RSS)으로
    '손해보험 + 키워드' 신규 기사만 감지한다. (약관·정보통신망법 리스크 회피)
  - 감지 시 카카오톡 '나에게 보내기'로 알림만 보낸다. 실제 경쟁사 가입화면 점검은 사람이 수동으로.
  - 결과를 newsdata.js(window.NEWS)로 저장 → 대시보드 '뉴스 감지' 탭에서도 표시.
  - 외부 통신: 뉴스 RSS + 카카오 API. (대시보드 본체는 그대로 로컬)

준비물 (카카오 개발자):
  1) developers.kakao.com 에서 앱 생성 → REST API 키
  2) 카카오 로그인 동의항목에 'talk_message'(카카오톡 메시지 전송) 권한 추가/허용
  3) 사용자 토큰 발급 → access_token (만료 ~6h) + refresh_token
  환경변수:
    KAKAO_ACCESS_TOKEN   (필수: 보낼 때 사용)
    KAKAO_REST_API_KEY   (선택: refresh로 토큰 자동 갱신 시)
    KAKAO_REFRESH_TOKEN  (선택: refresh로 토큰 자동 갱신 시)

사용:
  python3 news_watch.py            # 1회 실행 (cron에 등록 권장: 매시간 등)
  python3 news_watch.py --dry-run  # 카카오 전송 없이 감지만(테스트)
  python3 news_watch.py --interval 3600   # 직접 반복(3600초마다)
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime

# ── 모니터링 설정 ──
BASE = "손해보험"
KEYWORDS = ["가입 프로세스", "퍼널", "리뉴얼", "개편", "런칭", "간편가입", "UX 개선", "다이렉트 개편"]
# 회사명이 제목에 있으면 태깅 (필터용, 없어도 통과)
COMPANIES = ["삼성", "현대", "DB", "KB", "메리츠", "한화", "롯데", "흥국", "AXA", "캐롯", "하나"]

STATE_FILE = "news_seen.json"        # 이미 알림 보낸 기사 기록(중복 방지)
OUT_JS = "newsdata.js"               # 대시보드용 (window.NEWS)
KAKAO_SEND_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
# 실제 브라우저 UA (Google News RSS가 단순 UA를 403 처리하는 경우가 있어 정식 UA 사용)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def norm_date(raw):
    """RFC822 pubDate('Mon, 28 May 2026 09:00:00 GMT') → 'YYYY-MM-DD'. 실패 시 오늘."""
    try:
        return parsedate_to_datetime(raw).strftime("%Y-%m-%d")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d")


def clean_title(title):
    """Google News 제목은 '제목 - 언론사' 형태 → (제목, 언론사)로 분리."""
    src = ""
    m = re.search(r"\s-\s([^-]+)$", title)
    if m:
        src = m.group(1).strip()
        title = title[: m.start()].strip()
    return title, src


def fetch_rss(query):
    """Google News RSS 검색 → [(title, link, source, date_YYYY-MM-DD)]"""
    url = ("https://news.google.com/rss/search?q="
           + urllib.parse.quote(query) + "&hl=ko&gl=KR&ceid=KR:ko")
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/rss+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = r.read()
    root = ET.fromstring(raw)
    items = []
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        date = norm_date((it.findtext("pubDate") or "").strip())
        src_el = it.find("source")
        source = (src_el.text.strip() if src_el is not None and src_el.text else "")
        title, src_from_title = clean_title(title)
        if not source:
            source = src_from_title
        if title and link:
            items.append((title, link, source, date))
    return items


def load_seen():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def save_seen(seen):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(seen), f, ensure_ascii=False, indent=0)


def refresh_access_token():
    """선택: refresh_token으로 access_token 자동 갱신 (cron 운영용)."""
    key = os.environ.get("KAKAO_REST_API_KEY")
    refresh = os.environ.get("KAKAO_REFRESH_TOKEN")
    if not (key and refresh):
        return None
    data = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "client_id": key,
        "refresh_token": refresh,
    }).encode()
    req = urllib.request.Request(KAKAO_TOKEN_URL, data=data,
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            out = json.load(r)
        return out.get("access_token")
    except Exception as e:
        print(f"  (토큰 갱신 실패: {e})", file=sys.stderr)
        return None


def kakao_send(token, title, link, source, date):
    """카카오톡 '나에게 보내기' 텍스트 메시지."""
    template = {
        "object_type": "text",
        "text": f"[손보 뉴스 감지] {title}\n{source} · {date}\n\n→ 경쟁사 가입화면 점검 필요 여부 확인",
        "link": {"web_url": link, "mobile_web_url": link},
        "button_title": "기사 보기",
    }
    data = urllib.parse.urlencode({"template_object": json.dumps(template, ensure_ascii=False)}).encode()
    req = urllib.request.Request(
        KAKAO_SEND_URL, data=data,
        headers={"Authorization": "Bearer " + token,
                 "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=20) as r:
        out = json.load(r)
    # 성공 시 {"result_code":0}
    if out.get("result_code") != 0:
        raise RuntimeError(f"카카오 응답 이상: {out}")


def tag_company(title):
    for c in COMPANIES:
        if c in title:
            return c
    return "기타"


def run_once(dry_run=False):
    token = os.environ.get("KAKAO_ACCESS_TOKEN")
    if not dry_run:
        fresh = refresh_access_token()
        if fresh:
            token = fresh
        if not token:
            sys.exit("KAKAO_ACCESS_TOKEN이 없습니다. (--dry-run으로 전송 없이 감지만 가능)")

    seen = load_seen()
    detected, new_count = [], 0
    for kw in KEYWORDS:
        try:
            items = fetch_rss(f"{BASE} {kw}")
        except Exception as e:
            print(f"  (검색 실패 '{kw}': {e})", file=sys.stderr)
            continue
        for (title, link, source, date) in items:
            key = link
            is_new = key not in seen
            co = tag_company(title)
            detected.append({"id": key[-40:], "co": co, "title": title,
                             "src": source, "date": date, "kws": [kw],
                             "st": "new" if is_new else "done"})
            if is_new:
                new_count += 1
                if dry_run:
                    # 미리보기(dry-run)는 실제 전송이 아니므로 seen에 넣지 않음 → 실제 실행 때 알림 보장
                    print(f"  [신규] {co} · {title} ({source})")
                else:
                    try:
                        kakao_send(token, title, link, source, date)
                        seen.add(key)   # 전송 성공 후에만 seen 등록 → 일시적 실패 시 다음 실행에서 재시도
                        print(f"  [알림전송] {co} · {title}")
                    except Exception as e:
                        print(f"  (전송 실패: {e})", file=sys.stderr)

    # 대시보드용 newsdata.js (중복 링크 병합 + 키워드 합치기 + 최신순)
    by_id, order = {}, []
    for d in detected:
        if d["id"] in by_id:
            for k in d["kws"]:
                if k not in by_id[d["id"]]["kws"]:
                    by_id[d["id"]]["kws"].append(k)
        else:
            by_id[d["id"]] = d; order.append(d["id"])
    uniq = [by_id[i] for i in order]
    uniq.sort(key=lambda d: d.get("date", ""), reverse=True)
    with open(OUT_JS, "w", encoding="utf-8") as f:
        f.write("/* news_watch.py 생성 · 공개 뉴스(Google News) · "
                + datetime.now().strftime("%Y-%m-%d %H:%M") + " */\n")
        f.write("window.NEWS = " + json.dumps(uniq[:60], ensure_ascii=False, indent=1) + ";\n")
    if not dry_run:
        save_seen(seen)
    print(f"[{datetime.now():%Y-%m-%d %H:%M}] 감지 {len(detected)}건 · 신규 {new_count}건 → {OUT_JS}")
    return new_count


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="카카오 전송 없이 감지만")
    ap.add_argument("--interval", type=int, default=0, help="초 단위 반복 실행(0=1회)")
    args = ap.parse_args()
    if args.interval > 0:
        print(f"반복 실행 시작 (간격 {args.interval}s). Ctrl+C로 종료.")
        while True:
            run_once(args.dry_run)
            time.sleep(args.interval)
    else:
        run_once(args.dry_run)


if __name__ == "__main__":
    main()
