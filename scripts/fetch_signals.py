#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수요 트리거 실데이터화 — 공공데이터(data.go.kr)로 상품별 실시간 수요 신호 산출.

출력: data/signals.json
  {
    "asof": "2026-07-23", "source": "data.go.kr" | "sample",
    "weather": {"active": ["호우", ...]},
    "travel":  {"overseas_ratio": 88.0, "avg": 61.0, "period": "2026-07-01"},  # 여행자보험 검색수요(데이터랩)
    "triggers": { "hrmf": {"level":"high","note":"호우특보 발효 → 누수·침수 담보 수요"}, ... }
  }

- 상품 트리거 레벨(high/normal)을 미리 계산해두면, 뉴스툴은 그대로 읽어서 칩만 표시.
- 이 샌드박스는 외부망 차단 → 실제 호출은 GitHub Actions(signals.yml)에서. 로컬 미리보기는 --sample.
- 키: 환경변수 DATA_GO_KR_KEY (data.go.kr 마이페이지 > 인증키. 하나로 여러 서비스 사용).

엔드포인트는 상수로 분리 — 첫 실행에서 응답 스키마에 맞춰 PARSE 부분만 조정하면 됩니다.
"""
import os, sys, json, datetime, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "signals.json")
KEY = os.environ.get("DATA_GO_KR_KEY", "").strip()
TODAY = datetime.date.today().isoformat()

# ── 엔드포인트 ─────────────────────────────
KMA_WARN = "http://apis.data.go.kr/1360000/WthrWrnInfoService/getWthrWrnList"   # 기상청 기상특보 (JSON · data.go.kr)
# 해외여행 수요 = 네이버 데이터랩 '여행자보험' 검색수요(openapi.naver.com · NAVER_CLIENT 키)
# (출입국관광통계 openapi.tour.go.kr는 GitHub Actions에서 네트워크 불통 → 대체)

def _get(url, params, timeout=20):   # JSON 응답용(기상청)
    params = dict(params); params["serviceKey"] = KEY; params.setdefault("dataType", "JSON")
    q = urllib.parse.urlencode(params, safe="%")
    with urllib.request.urlopen(url + "?" + q, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def fetch_weather():
    """발효 중인 기상특보 종류 목록. 스키마: response.body.items.item[].title/other."""
    try:
        d = _get(KMA_WARN, {"numOfRows": 50, "pageNo": 1})
        items = (((d or {}).get("response", {}).get("body", {}) or {}).get("items", {}) or {}).get("item", [])
        if isinstance(items, dict): items = [items]
        kinds = set()
        for it in items:
            t = str(it.get("title") or it.get("t6") or "")
            for k in ("호우", "태풍", "대설", "한파", "폭염", "강풍", "건조"):
                if k in t: kinds.add(k)
        return {"active": sorted(kinds)}
    except Exception as e:
        return {"active": [], "error": str(e)[:120]}

def fetch_travel():
    """해외여행보험 수요 = 네이버 데이터랩 '여행자보험' 월별 검색수요(상대지수). 최근월 vs 12개월 평균으로 상승 판정.
    (출입국관광통계 openapi.tour.go.kr는 GitHub Actions에서 불통 → 확실히 닿는 네이버 DataLab로 대체.)"""
    nid = os.environ.get("NAVER_CLIENT_ID", "").strip()
    nsec = os.environ.get("NAVER_CLIENT_SECRET", "").strip()
    if not (nid and nsec):
        return {"overseas_ratio": None, "error": "NAVER_CLIENT_ID/SECRET 없음(데이터랩)"}
    end = datetime.date.today().replace(day=1) - datetime.timedelta(days=1)   # 지난달 말
    start = end.replace(day=1) - datetime.timedelta(days=400)                 # 약 13개월 전
    body = json.dumps({"startDate": start.isoformat(), "endDate": end.isoformat(), "timeUnit": "month",
                       "keywordGroups": [{"groupName": "여행자보험", "keywords": ["여행자보험", "해외여행보험", "여행보험"]}]}).encode("utf-8")
    try:
        req = urllib.request.Request("https://openapi.naver.com/v1/datalab/search", data=body,
              headers={"X-Naver-Client-Id": nid, "X-Naver-Client-Secret": nsec, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.loads(r.read().decode("utf-8"))
        data = (d.get("results") or [{}])[0].get("data") or []
        if not data:
            return {"overseas_ratio": None, "error": "데이터랩 결과 없음"}
        ratios = [x["ratio"] for x in data]
        latest = data[-1]
        avg = round(sum(ratios) / len(ratios), 1)
        return {"overseas_ratio": round(latest["ratio"], 1), "period": latest["period"], "avg": avg, "peak": round(max(ratios), 1)}
    except Exception as e:
        return {"overseas_ratio": None, "error": str(e)[:140]}

def build_triggers(weather, travel):
    """상품별 실시간 수요 신호 레벨 산출(정성 규칙)."""
    w = set(weather.get("active", []))
    trg = {}
    # 주택화재: 호우·태풍(누수·침수) / 한파·대설(동파)
    if {"호우", "태풍"} & w:
        trg["hrmf"] = {"level": "high", "note": "호우·태풍 특보 발효 → 누수·침수 담보 수요 급증"}
    elif {"한파", "대설"} & w:
        trg["hrmf"] = {"level": "high", "note": "한파·대설 특보 → 동파·난방화재 담보 수요"}
    # 운전자: 대설·강풍(빙판·사고)
    if {"대설", "강풍"} & w:
        trg["driver"] = {"level": "high", "note": "대설·강풍 특보 → 사고 위험·운전자보험 관심↑"}
    # 해외여행: '여행자보험' 검색수요가 평균 대비 상승(성수기)하면 high
    lr, avg = travel.get("overseas_ratio"), travel.get("avg") or 0
    if lr is not None and avg and (lr >= avg * 1.15 or lr >= 75):
        trg["overseas"] = {"level": "high", "note": f"‘여행자보험’ 검색수요 상승({travel.get('period','')} 지수 {lr}/평균 {avg}) → 성수기 해외여행보험 대응"}
    return trg

def sample():
    weather = {"active": ["호우", "폭염"]}
    travel = {"overseas_ratio": 88.0, "period": "2026-07-01", "avg": 61.0, "peak": 100.0}
    return {"asof": TODAY, "source": "sample", "weather": weather, "travel": travel,
            "triggers": build_triggers(weather, travel)}

def main():
    if "--sample" in sys.argv or not KEY:
        data = sample()
        if not KEY and "--sample" not in sys.argv:
            data["note"] = "DATA_GO_KR_KEY 미설정 → 샘플. Actions/로컬에서 키 설정 시 실데이터."
    else:
        weather, travel = fetch_weather(), fetch_travel()
        data = {"asof": TODAY, "source": "data.go.kr", "weather": weather, "travel": travel,
                "triggers": build_triggers(weather, travel)}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✔ data/signals.json ({data['source']}) · 트리거 {len(data['triggers'])}개 · 특보 {data['weather'].get('active')}")

if __name__ == "__main__":
    main()
