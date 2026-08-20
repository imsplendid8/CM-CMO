#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""네이버 검색광고 API(키워드도구) → 현재 검색량과 월별 스냅샷.

각 상품 대표 시드로 keywordstool을 호출해 연관키워드 + 월검색량(PC/모바일)·경쟁도를
상품별로 모아 data/volume.json 에 저장하고 data/volume-history.json 에 월별 스냅샷을
최대 13개월 보존한다. 키워드 도구(keyword-tool.html)는 두 파일을 함께 읽어 실검색량을
매핑하고 신규·급상승 후보를 계산한다(출처=검색광고).

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
HISTORY_MONTHS = 13

def load(p): return json.load(open(os.path.join(ROOT, p), encoding="utf-8"))

def _sign(ts, method, path):
    msg = f"{ts}.{method}.{path}"
    return base64.b64encode(hmac.new(SECRET.encode(), msg.encode(), hashlib.sha256).digest()).decode()

def _num(v):
    if isinstance(v, str):
        return 0 if "<" in v else int(v.replace(",", "") or 0)
    return int(v or 0)

def compact_products(products):
    """월간 비교에 필요한 합계·경쟁도만 남겨 이력 파일 크기를 줄인다."""
    compact = {}
    for product_key, product in (products or {}).items():
        keywords = {}
        for keyword, row in (product.get("keywords") or {}).items():
            keywords[keyword] = {
                "total": _num(row.get("pc")) + _num(row.get("mobile")),
                "comp": row.get("comp", ""),
            }
        compact[product_key] = {"keywords": keywords}
    return compact

def update_history(history, current, month_key, retention=HISTORY_MONTHS):
    """같은 달은 최신 주간값으로 교체하고 오래된 월은 보존 한도 밖에서 제거한다."""
    result = dict(history or {})
    result.update({
        "_comment": "네이버 검색광고 키워드도구 월검색량 스냅샷. 최신 13개월, PC+모바일 합계.",
        "source": "searchad",
        "retentionMonths": retention,
    })
    snapshots = dict(result.get("snapshots") or {})
    snapshots[month_key] = {
        "asof": current.get("asof"),
        "products": compact_products(current.get("products") or {}),
    }
    keep = sorted(snapshots)[-retention:]
    result["snapshots"] = {key: snapshots[key] for key in keep}
    return result

def write_json(relative_path, payload):
    with open(os.path.join(ROOT, relative_path), "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

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
        write_json("data/volume.json", out)
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
    write_json("data/volume.json", out)
    try:
        history = load("data/volume-history.json")
    except (FileNotFoundError, json.JSONDecodeError):
        history = {}
    month_key = out["asof"][:7]
    history = update_history(history, out, month_key)
    write_json("data/volume-history.json", history)
    tot = sum(len(v["keywords"]) for v in out["products"].values())
    print(f"✔ data/volume.json + volume-history.json({month_key}) — {len(out['products'])}개 상품 · 연관키워드 {tot}개")

if __name__ == "__main__":
    main()
