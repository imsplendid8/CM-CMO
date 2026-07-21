#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
네이버 검색광고 API — 키워드 도구(keywordstool)로 월검색량·경쟁도 조회
결과를 keyword-tool.html '검색량 불러오기'에 붙여넣을 JSON으로 출력합니다.

키 발급: 네이버 검색광고(https://searchad.naver.com) > 도구 > API 사용 관리
  - 액세스라이선스(API_KEY), 비밀키(SECRET), 로그인 계정 CUSTOMER_ID

환경변수(.env, 절대 커밋 금지):
  NAVER_AD_API_KEY, NAVER_AD_SECRET, NAVER_AD_CUSTOMER

실행:
  export NAVER_AD_API_KEY=... NAVER_AD_SECRET=... NAVER_AD_CUSTOMER=...
  python3 scripts/naver_searchad_keywords.py 암보험 운전자보험 치아보험 > volume.json
"""
import os, sys, time, hmac, hashlib, base64, json, urllib.parse, urllib.request

BASE = "https://api.searchad.naver.com"
API_KEY  = os.environ.get("NAVER_AD_API_KEY")
SECRET   = os.environ.get("NAVER_AD_SECRET")
CUSTOMER = os.environ.get("NAVER_AD_CUSTOMER")

def _sign(ts: str, method: str, path: str) -> str:
    msg = f"{ts}.{method}.{path}"
    dig = hmac.new(SECRET.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).digest()
    return base64.b64encode(dig).decode("utf-8")

def _headers(method: str, path: str) -> dict:
    ts = str(int(time.time() * 1000))
    return {
        "X-Timestamp": ts,
        "X-API-KEY": API_KEY,
        "X-Customer": str(CUSTOMER),
        "X-Signature": _sign(ts, method, path),
    }

def _num(v):
    # 검색수는 '< 10' 같은 문자열로 올 수 있음 → 0 처리
    if isinstance(v, str):
        return 0 if "<" in v else int(v.replace(",", "") or 0)
    return int(v or 0)

def keywordstool(hint_keywords):
    """최대 5개 시드로 연관키워드+월검색량 조회"""
    path = "/keywordstool"
    q = urllib.parse.urlencode({"hintKeywords": ",".join(hint_keywords), "showDetail": "1"})
    req = urllib.request.Request(f"{BASE}{path}?{q}", headers=_headers("GET", path))
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)

def main():
    seeds = sys.argv[1:] or ["암보험", "운전자보험", "치아보험", "주택화재보험", "해외여행보험"]
    out = {"keywords": {}}
    for i in range(0, len(seeds), 5):                       # keywordstool은 시드 5개까지
        batch = seeds[i:i+5]
        try:
            data = keywordstool(batch)
        except Exception as e:
            print(f"[warn] {batch}: {e}", file=sys.stderr)
            continue
        for row in data.get("keywordList", []):
            kw = row.get("relKeyword", "")
            out["keywords"][kw] = {
                "pc":     _num(row.get("monthlyPcQcCnt")),
                "mobile": _num(row.get("monthlyMobileQcCnt")),
                "comp":   row.get("compIdx", ""),             # 낮음 / 중간 / 높음
                "clkPc":  _num(row.get("monthlyAvePcClkCnt")),
                "clkMo":  _num(row.get("monthlyAveMobileClkCnt")),
            }
        time.sleep(0.3)                                       # rate limit 여유
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    if not (API_KEY and SECRET and CUSTOMER):
        sys.exit("환경변수 NAVER_AD_API_KEY / NAVER_AD_SECRET / NAVER_AD_CUSTOMER 를 설정하세요.")
    main()
