#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""docs/논문-아카이브.md → data/papers.json (대시보드 papers-tool.html용).

MD가 사람이 읽는 정본이라면, papers.json은 대시보드가 읽는 구조화본.
- fetch_papers.py가 신규 논문을 MD에 적립할 때 이 스크립트로 json도 갱신한다.
- 수동 재생성: python3 scripts/papers_to_json.py
표준 라이브러리만 사용.
"""
import os, re, json, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MD = os.path.join(ROOT, "docs", "논문-아카이브.md")
OUT = os.path.join(ROOT, "data", "papers.json")
KST = datetime.timezone(datetime.timedelta(hours=9))


GENERIC = {"관련 논문", "논문", "참고"}

def clean_topic(h):
    t = re.sub(r"^#+\s*\d+\.\s*", "", h).strip()
    t = re.sub(r"\s*\([^)]*\)\s*$", "", t).strip()   # 꼬리 괄호(요약/방법론/담당자 제공) 제거
    parts = [x.strip() for x in t.split("—") if x.strip()]
    cand = [x for x in parts if x not in GENERIC]     # '관련 논문' 같은 총칭 제외, 구체 주제 채택
    return (cand[0] if cand else (parts[0] if parts else t))


def parse(md):
    papers = []
    topic, date = "", ""
    cur = None
    for ln in md.splitlines():
        s = ln.strip()
        if s.startswith("## "):
            topic, date, cur = clean_topic(s), "", None
            continue
        m = re.match(r"^###\s*▪\s*(\d{4}-\d{2}-\d{2})", s)
        if m:
            date = m.group(1); cur = None; continue
        # 담당자 제공 원문 링크(제목 미확인) 표: | S1 | [원문 링크](url) | 출처 |
        # 실제 논문 상세 링크라 '논문'으로 유지(사라지지 않게) · 주제는 섹션 제목 · 제공자는 배지(auto=False)
        m = re.match(r"^\|\s*(S\d+)\s*\|\s*\[[^\]]+\]\((https?://[^)]+)\)\s*\|\s*([^|]+)\|", s)
        if m:
            papers.append({"title": f"참고자료 · {m.group(3).strip()} (제목 미확인)",
                           "link": m.group(2).strip(), "desc": "",
                           "note": "담당자 제공 원문 링크 · 제목/주제 확인 후 분류 예정",
                           "topic": topic, "date": "", "auto": False})
            continue
        # 논문 항목: '### 제목'(2·3장) 또는 '#### 제목'(4장). '### ▪ 날짜'는 위에서 처리됨.
        if s.startswith("#### ") or (s.startswith("### ") and "▪" not in s):
            title = s.lstrip("#").strip()
            cur = {"title": title, "link": "", "desc": "", "note": "",
                   "topic": topic, "date": date, "auto": bool(date)}
            papers.append(cur); continue
        if cur is None:
            continue
        m = re.match(r"^-\s*🔗\s*(\S+)", s)
        if m: cur["link"] = m.group(1); continue
        m = re.match(r"^-\s*\*\*요약\*\*:\s*(.+)", s)
        if m: cur["desc"] = m.group(1).strip(); continue
        m = re.match(r"^-\s*\*\*담당자 참고\*\*:\s*(.+)", s)
        if m: cur["note"] = m.group(1).strip(); continue
    return [p for p in papers if p.get("link")]


def build():
    md = open(MD, encoding="utf-8").read()
    papers = parse(md)
    topics = []
    for p in papers:
        if p["topic"] not in topics:
            topics.append(p["topic"])
    data = {"updated": datetime.datetime.now(KST).strftime("%Y-%m-%d"),
            "source": "네이버 학술(전문자료) 검색 · 요약은 공개 서지·초록 기반",
            "count": len(papers), "topics": topics, "papers": papers}
    return data


if __name__ == "__main__":
    data = build()
    json.dump(data, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"✔ data/papers.json · {data['count']}편 · 주제 {len(data['topics'])}개")
