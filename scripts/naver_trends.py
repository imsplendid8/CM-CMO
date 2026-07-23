#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""네이버 데이터랩 검색어 트렌드 → data/trends.json (시즌 캘린더 실측 검증용).

각 상품 대표키워드의 월별 검색 추세(최근 24개월)를 받아, 달력월(1~12) 평균 프로필로
집계하고 피크월을 계산해 data/trends.json 에 저장한다. 시즌 캘린더가 이 파일을 읽어
계절 이슈가 실제 검색 피크와 일치하는지 표시한다.

- 실측: NAVER_CLIENT_ID/SECRET 있으면 데이터랩 API 호출 (검색 API와 동일 키)
- 샘플: 키 없거나 --sample 이면 data/seasonal.json 의 시즌 윈도우로 근사 프로필 생성
표준 라이브러리만 사용. 데이터랩 API도 CORS로 브라우저 직접호출 불가 → 서버/Actions에서 실행.
"""
import os, sys, json, urllib.request
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load(p): return json.load(open(os.path.join(ROOT, p), encoding="utf-8"))

def month_range(months=24):
    today = date.today().replace(day=1)
    end = today - timedelta(days=1)              # 지난달 말일(완결 월)
    start = end.replace(day=1)
    for _ in range(months - 1):
        start = (start - timedelta(days=1)).replace(day=1)
    return start.isoformat(), end.isoformat()

def datalab(cid, csec, groups):
    start, end = month_range(24)
    body = json.dumps({"startDate": start, "endDate": end, "timeUnit": "month",
                       "keywordGroups": groups}, ensure_ascii=False).encode()
    req = urllib.request.Request("https://openapi.naver.com/v1/datalab/search", data=body,
        headers={"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": csec,
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)

def profile_from_points(points):
    # points: [{period:'YYYY-MM-01', ratio:float}] → 12개월 평균(1~12), 0~100 정규화
    by_m = [[] for _ in range(12)]
    for p in points:
        m = int(p["period"][5:7]) - 1
        by_m[m].append(float(p.get("ratio", 0)))
    prof = [round(sum(v) / len(v), 1) if v else 0.0 for v in by_m]
    mx = max(prof) or 1
    prof = [round(x / mx * 100, 1) for x in prof]
    return prof

def peaks(prof, thr=0.85):
    mx = max(prof) or 1
    return [i + 1 for i, x in enumerate(prof) if x >= mx * 100 / 100 * thr and x > 0]

def real_trends(products, cid, csec):
    out = {}
    items = [(p["key"], p.get("serpKw") or p["newsQuery"]) for p in products]
    for i in range(0, len(items), 5):
        batch = items[i:i + 5]
        groups = [{"groupName": k, "keywords": [kw]} for k, kw in batch]
        data = datalab(cid, csec, groups)
        for res in data.get("results", []):
            key = res.get("title")
            prof = profile_from_points(res.get("data", []))
            out[key] = {"months": prof, "peakMonths": peaks(prof)}
    return out

def sample_trends(products, seasonal):
    out = {}
    for p in products:
        wins = seasonal.get(p["key"], [])
        prof = [22.0] * 12
        for w in wins:
            for m in w["m"]:
                prof[m - 1] += 60
        mx = max(prof) or 1
        prof = [round(x / mx * 100, 1) for x in prof]
        out[p["key"]] = {"months": prof, "peakMonths": peaks(prof)}
    return out

def main():
    products = load("data/products.json")["products"]
    cid, csec = os.environ.get("NAVER_CLIENT_ID"), os.environ.get("NAVER_CLIENT_SECRET")
    use_real = cid and csec and "--sample" not in sys.argv
    if use_real:
        try:
            trends = real_trends(products, cid, csec); source = "datalab"
        except Exception as e:
            print(f"[warn] 데이터랩 호출 실패 → 샘플로 대체: {e}", file=sys.stderr)
            trends = sample_trends(products, load("data/seasonal.json")["seasonal"]); source = "sample"
    else:
        trends = sample_trends(products, load("data/seasonal.json")["seasonal"]); source = "sample"
    out = {"_comment": "시즌 캘린더 실측 검증용 월별 검색추세(0~100 정규화). source=datalab(실측)/sample(근사).",
           "asof": date.today().isoformat(), "source": source, "products": trends}
    with open(os.path.join(ROOT, "data/trends.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"✔ data/trends.json ({source}) — {len(trends)}개 상품")

if __name__ == "__main__":
    main()
