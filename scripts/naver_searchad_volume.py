#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""네이버 검색광고 API(키워드도구) → data/volume.json (키워드 도구 자동 반영용).

각 상품 대표 시드로 keywordstool을 호출해 연관키워드 + 월검색량(PC/모바일)·경쟁도를
상품별로 모아 data/volume.json 에 저장한다. 키워드 도구(keyword-tool.html)가 이 파일을
불러와 검색량·경쟁도를 자동 매핑하고 연관키워드를 병합한다(출처=검색광고).

필요 Secrets(검색광고 API · 검색/데이터랩 키와 '다름'):
  NAVER_AD_API_KEY   (액세스라이선스)
  NAVER_AD_SECRET    (비밀키)
  NAVER_AD_CUSTOMER  (CUSTOMER ID)
발급: searchad.naver.com → 도구 → API 사용 관리. 표준 라이브러리만 사용(HMAC 서명).
"""
import os, sys, time, hmac, hashlib, base64, json, urllib.parse, urllib.request
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://api.searchad.naver.com"
API_KEY = os.environ.get("NAVER_AD_API_KEY")
SECRET = os.environ.get("NAVER_AD_SECRET")
CUSTOMER = os.environ.get("NAVER_AD_CUSTOMER")
TOP_PER_PRODUCT = 80

def load(p): return json.load(open(os.path.join(ROOT, p), encoding="utf-8"))

def _sign(ts, method, path):
    msg = f"{ts}.{method}.{path}"
    return base64.b64encode(hmac.new(SECRET.encode(), msg.encode(), hashlib.sha256).digest()).decode()

def _num(v):
    if isinstance(v, str):
        return 0 if "<" in v else int(v.replace(",", "") or 0)
    return int(v or 0)

def keywordstool(hint):
    path = "/keywordstool"
    ts = str(int(time.time() * 1000))
    q = urllib.parse.urlencode({"hintKeywords": hint, "showDetail": "1"})
    req = urllib.request.Request(f"{BASE}{path}?{q}", headers={
        "X-Timestamp": ts, "X-API-KEY": API_KEY, "X-Customer": str(CUSTOMER),
        "X-Signature": _sign(ts, "GET", path)})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)

def main():
    products = load("data/products.json")["products"]
    out = {"_comment": "키워드 도구 자동 반영용 검색광고 실검색량. source=searchad(실측)/none(키 없음).",
           "asof": date.today().isoformat(), "source": "searchad", "products": {}}
    if not (API_KEY and SECRET and CUSTOMER):
        out["source"] = "none"
        with open(os.path.join(ROOT, "data/volume.json"), "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print("검색광고 키(NAVER_AD_*) 미설정 — data/volume.json(source=none) 생성", file=sys.stderr)
        return
    for p in products:
        seed = (p.get("serpKw") or p["core"][0]).replace(" ", "")
        try:
            data = keywordstool(seed)
        except Exception as e:
            print(f"[warn] {p['key']}({seed}): {e}", file=sys.stderr)
            continue
        rows = data.get("keywordList", [])
        rows.sort(key=lambda r: _num(r.get("monthlyPcQcCnt")) + _num(r.get("monthlyMobileQcCnt")), reverse=True)
        kws = {}
        for row in rows[:TOP_PER_PRODUCT]:
            kw = row.get("relKeyword", "")
            if not kw:
                continue
            kws[kw] = {"pc": _num(row.get("monthlyPcQcCnt")),
                       "mobile": _num(row.get("monthlyMobileQcCnt")),
                       "comp": row.get("compIdx", "")}
        out["products"][p["key"]] = {"keywords": kws}
        time.sleep(0.3)
    with open(os.path.join(ROOT, "data/volume.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    tot = sum(len(v["keywords"]) for v in out["products"].values())
    print(f"✔ data/volume.json — {len(out['products'])}개 상품 · 연관키워드 {tot}개")

if __name__ == "__main__":
    main()
