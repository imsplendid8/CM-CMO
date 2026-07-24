#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CM·디지털 마케팅 논문 월간 아카이빙 — 네이버 전문자료(doc) 검색으로 신규 논문을 자동 적립.

동작:
  - 네이버 오픈API 전문자료 검색(/v1/search/doc.json)으로 지정 쿼리를 검색.
  - docs/논문-아카이브.md 의 기존 링크(doc_id)와 중복되지 않는 신규 논문만 선별.
  - "## 4. 디지털 마케팅·CM 채널 — 정기 자동 적립 (월 1회)" 섹션 맨 아래에
    "### ▪ <오늘날짜>" 소제목으로 (제목 / 🔗링크 / 요약 / 담당자 참고) 추가.

- 네이버 검색 API 사용: 환경변수 NAVER_CLIENT_ID / NAVER_CLIENT_SECRET (뉴스 클리핑과 동일).
- 이 샌드박스는 외부망 차단 → 실행은 GitHub Actions(papers.yml). 로컬 미리보기는 --sample.
- 원문은 링크만, 요약은 공개 서지(검색 description) 기반. 개인정보·영업비밀 미포함(데이터 거버넌스).
"""
import os, sys, re, json, datetime, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVE = os.path.join(ROOT, "docs", "논문-아카이브.md")
SECTION_H = "## 4. 디지털 마케팅·CM 채널 — 정기 자동 적립 (월 1회)"
FOOTER_MARK = "\n---\n\n_수집 경로:"
ID = os.environ.get("NAVER_CLIENT_ID", "").strip()
SECRET = os.environ.get("NAVER_CLIENT_SECRET", "").strip()
KST = datetime.timezone(datetime.timedelta(hours=9))
TODAY = datetime.datetime.now(KST).strftime("%Y-%m-%d")
MAX_ADD = 6  # 이번 회차 최대 적립 편수

# CM·디지털 마케팅 검색 쿼리
QUERIES = [
    "디지털 마케팅 보험",
    "다이렉트 보험 마케팅",
    "디지털 마케팅 소비자 구매의도",
    "인슈어테크 마케팅",
    "보험 디지털 전환 구매의도",
]

def strip(s):
    s = re.sub(r"<[^>]*>", "", str(s or ""))
    return (s.replace("&quot;", '"').replace("&amp;", "&").replace("&lt;", "<")
             .replace("&gt;", ">").replace("&#39;", "'").strip())

def doc_key(link):
    m = re.search(r"doc_id=(\d+)", link or "")
    return "doc_" + m.group(1) if m else (link or "").strip()

def naver_doc(q, display=5):
    url = "https://openapi.naver.com/v1/search/doc.json?" + urllib.parse.urlencode(
        {"query": q, "display": display, "sort": "sim"})
    req = urllib.request.Request(url, headers={
        "X-Naver-Client-Id": ID, "X-Naver-Client-Secret": SECRET})
    with urllib.request.urlopen(req, timeout=20) as r:
        d = json.loads(r.read().decode("utf-8"))
    out = []
    for it in d.get("items", []):
        link = it.get("link") or ""
        title = strip(it.get("title"))
        if not link or not title:
            continue
        out.append({"title": title, "link": link,
                    "desc": strip(it.get("description"))[:90], "q": q})
    return out

def existing_keys(md):
    keys = set()
    for m in re.finditer(r"https?://\S+", md):
        keys.add(doc_key(m.group(0).rstrip(").,")))
    return keys

def entry_md(p):
    desc = p["desc"] or "서지 정보는 원문 링크 참조."
    return (f"#### {p['title']}\n"
            f"- 🔗 {p['link']}\n"
            f"- **요약**: {desc}\n"
            f"- **담당자 참고**: 자동 수집(검색어: \"{p['q']}\") · 마케팅 시사점은 담당자 검토 후 보완.\n")

def collect():
    seen, picks = set(), []
    for q in QUERIES:
        try:
            items = naver_doc(q)
        except Exception as e:
            print(f"  ! 검색 실패({q}): {e}", file=sys.stderr)
            continue
        for it in items:
            k = doc_key(it["link"])
            if k in seen:
                continue
            seen.add(k)
            picks.append(it)
    return picks

def main():
    if not os.path.exists(ARCHIVE):
        print("아카이브 파일 없음:", ARCHIVE); sys.exit(1)
    md = open(ARCHIVE, encoding="utf-8").read()
    if SECTION_H not in md or FOOTER_MARK not in md:
        print("섹션/푸터 마커를 찾지 못함 — 문서 구조 확인 필요"); sys.exit(1)

    have = existing_keys(md)
    sample = "--sample" in sys.argv
    if sample:
        found = [{"title": "샘플 디지털 마케팅 보험 논문", "link": "https://academic.naver.com/article.naver?doc_id=999999999",
                  "desc": "샘플 설명", "q": "디지털 마케팅 보험"}]
    else:
        if not (ID and SECRET):
            print("NAVER_CLIENT_ID/SECRET 미설정 — GitHub Actions 시크릿 필요"); sys.exit(1)
        found = collect()

    new = [p for p in found if doc_key(p["link"]) not in have][:MAX_ADD]
    if not new:
        print("신규 논문 없음 — 변경 없음"); return

    block = f"\n### ▪ {TODAY}\n\n" + "\n".join(entry_md(p) for p in new)
    md = md.replace(FOOTER_MARK, block + FOOTER_MARK, 1)
    open(ARCHIVE, "w", encoding="utf-8").write(md)
    print(f"신규 {len(new)}편 적립({TODAY}):")
    for p in new:
        print("  -", p["title"])

if __name__ == "__main__":
    main()
