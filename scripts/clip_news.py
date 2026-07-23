#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""뉴스 클리핑 — 카테고리별 최신 뉴스를 날짜별로 적립(하루 2회: 09·13시).

출력:
  data/clips/<YYYY-MM-DD>.json   — 그날의 클리핑(카테고리별 items + 일 요약). 같은 날 재실행 시 병합·dedup.
  data/clips/index.json          — 날짜 목록 + 일/월 집계(뉴스툴 아카이브·날짜검색·월요약용).

- 네이버 검색 API(개발자센터) 사용: 환경변수 NAVER_CLIENT_ID / NAVER_CLIENT_SECRET.
- 이 샌드박스는 외부망 차단 → 실행은 GitHub Actions(news-clip.yml). 로컬 미리보기는 --sample.
- 공개 뉴스 헤드라인·링크만 저장(데이터 거버넌스).
"""
import os, sys, json, re, datetime, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIPS = os.path.join(ROOT, "data", "clips")
ID = os.environ.get("NAVER_CLIENT_ID", "").strip()
SECRET = os.environ.get("NAVER_CLIENT_SECRET", "").strip()
KST = datetime.timezone(datetime.timedelta(hours=9))
NOW = datetime.datetime.now(KST)
TODAY = NOW.strftime("%Y-%m-%d")
PART = "오전" if NOW.hour < 12 else "오후"

# 상품 카테고리(products.json) + 업계·경쟁사
def load_cats():
    p = json.load(open(os.path.join(ROOT, "data", "products.json"), encoding="utf-8"))
    items = p if isinstance(p, list) else p.get("products", [])
    cats = [{"key": x["key"], "name": x["name"], "q": x.get("newsQuery") or x.get("serpKw") or x["name"]} for x in items]
    cats += [
        {"key": "ind_biz", "name": "손보업계 전반", "q": "손해보험"},
        {"key": "ind_samsung", "name": "삼성화재", "q": "삼성화재"},
        {"key": "ind_db", "name": "DB손해보험", "q": "DB손해보험"},
        {"key": "ind_hyundai", "name": "현대해상", "q": "현대해상"},
        {"key": "ind_kb", "name": "KB손해보험", "q": "KB손해보험"},
        {"key": "ind_meritz", "name": "메리츠화재", "q": "메리츠화재"},
    ]
    return cats

def strip(s): return re.sub(r"<[^>]*>", "", str(s or "")).replace("&quot;", '"').replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&#39;", "'").strip()
def host(u):
    try: return urllib.parse.urlparse(u).hostname.replace("www.", "")
    except Exception: return ""

def naver_news(q, display=10):
    url = "https://openapi.naver.com/v1/search/news.json?" + urllib.parse.urlencode({"query": q, "display": display, "sort": "date"})
    req = urllib.request.Request(url, headers={"X-Naver-Client-Id": ID, "X-Naver-Client-Secret": SECRET})
    with urllib.request.urlopen(req, timeout=20) as r:
        d = json.loads(r.read().decode("utf-8"))
    out = []
    for it in d.get("items", []):
        u = it.get("link") or it.get("originallink")
        if not u: continue
        pd = it.get("pubDate", "")
        try: dt = datetime.datetime.strptime(pd[:25], "%a, %d %b %Y %H:%M:%S").strftime("%Y-%m-%d")
        except Exception: dt = TODAY
        out.append({"t": strip(it.get("title")), "src": host(it.get("originallink") or u), "date": dt, "url": u, "gist": strip(it.get("description"))[:80]})
    return out

def build_sample(cats):
    cl = {}
    for c in cats[:3]:
        cl[c["key"]] = {"name": c["name"], "q": c["q"], "items": [{"t": f"[샘플] {c['name']} 관련 최신 이슈", "src": "sample", "date": TODAY, "url": "https://search.naver.com", "gist": "실행 시 네이버 실뉴스로 채워짐"}]}
    return cl

def main():
    os.makedirs(CLIPS, exist_ok=True)
    cats = load_cats()
    sample = "--sample" in sys.argv or not (ID and SECRET)
    clip_cats = {}
    if sample:
        clip_cats = build_sample(cats)
        src = "sample"
    else:
        src = "naver"
        for c in cats:
            try:
                items = naver_news(c["q"])
                if items: clip_cats[c["key"]] = {"name": c["name"], "q": c["q"], "items": items}
            except Exception as e:
                clip_cats[c["key"]] = {"name": c["name"], "q": c["q"], "items": [], "error": str(e)[:100]}

    # 같은 날 파일 병합(오전+오후) · url dedup
    fpath = os.path.join(CLIPS, f"{TODAY}.json")
    prev = {}
    try: prev = json.load(open(fpath, encoding="utf-8"))
    except Exception: pass
    merged = prev.get("categories", {})
    for k, v in clip_cats.items():
        base = merged.get(k, {"name": v["name"], "q": v["q"], "items": []})
        seen = {it["url"] for it in base["items"]}
        for it in v["items"]:
            if it["url"] not in seen: base["items"].append(it); seen.add(it["url"])
        base["items"].sort(key=lambda x: x.get("date", ""), reverse=True)
        base["name"], base["q"] = v["name"], v["q"]
        merged[k] = base

    total = sum(len(v["items"]) for v in merged.values())
    by = {k: len(v["items"]) for k, v in merged.items() if v["items"]}
    top = sorted([it for v in merged.values() for it in v["items"]], key=lambda x: x.get("date", ""), reverse=True)[:6]
    runs = sorted(set(prev.get("runs", []) + [PART]))
    day = {"date": TODAY, "source": src, "runs": runs, "asof": NOW.strftime("%Y-%m-%d %H:%M"),
           "summary": {"total": total, "byCat": by, "top": top}, "categories": merged}
    json.dump(day, open(fpath, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # index.json 갱신
    ipath = os.path.join(CLIPS, "index.json")
    idx = {"dates": [], "months": {}}
    try: idx = json.load(open(ipath, encoding="utf-8"))
    except Exception: pass
    dates = {d["date"]: d for d in idx.get("dates", [])}
    dates[TODAY] = {"date": TODAY, "total": total, "runs": runs}
    idx["dates"] = sorted(dates.values(), key=lambda x: x["date"], reverse=True)[:400]
    months = {}
    for d in idx["dates"]:
        m = d["date"][:7]; months.setdefault(m, {"total": 0, "days": 0}); months[m]["total"] += d["total"]; months[m]["days"] += 1
    idx["months"] = months
    idx["updated"] = TODAY
    json.dump(idx, open(ipath, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"✔ data/clips/{TODAY}.json ({src}) · {PART} · 총 {total}건 · 카테고리 {len(by)}개")

if __name__ == "__main__":
    main()
