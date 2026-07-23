#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수요 트리거 실데이터화 — 공공데이터(data.go.kr)로 상품별 실시간 수요 신호 산출.

출력: data/signals.json
  {
    "asof": "2026-07-23", "source": "data.go.kr" | "sample",
    "weather": {"active": ["호우주의보", ...]},
    "travel":  {"airport_pax": 123456, "yoy_pct": 12.3},
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

# ── 공공데이터 엔드포인트 (data.go.kr) ─────────────────────────────
KMA_WARN = "http://apis.data.go.kr/1360000/WthrWrnInfoService/getWthrWrnList"   # 기상청 기상특보 목록
AIRPORT  = "http://apis.data.go.kr/B551177/StatsAirTransport/getFlightStatsList"  # 인천공항 여객/운항 통계(예시)
# 소방청 화재통계는 월별 집계 성격 → 필요 시 확장

def _get(url, params, timeout=20):
    params = dict(params); params["serviceKey"] = KEY; params.setdefault("dataType", "JSON")
    q = urllib.parse.urlencode(params, safe="%")  # serviceKey는 이미 인코딩된 경우 그대로
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
    """공항 여객 최근 실적(전년비). 스키마는 서비스에 맞춰 조정."""
    try:
        d = _get(AIRPORT, {"numOfRows": 12, "pageNo": 1})
        items = (((d or {}).get("response", {}).get("body", {}) or {}).get("items", {}) or {}).get("item", [])
        if isinstance(items, dict): items = [items]
        pax = None
        for it in items:
            for k in ("pax", "passenger", "여객", "totalPax"):
                if it.get(k) is not None:
                    pax = int(str(it[k]).replace(",", "")); break
            if pax is not None: break
        return {"airport_pax": pax}
    except Exception as e:
        return {"airport_pax": None, "error": str(e)[:120]}

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
    # 해외여행: 공항 여객 신호(있으면)
    if travel.get("airport_pax"):
        trg["overseas"] = {"level": "high", "note": f"공항 여객 실적 반영 → 해외여행보험 수요 지표({travel['airport_pax']:,}명)"}
    return trg

def sample():
    weather = {"active": ["호우", "폭염"]}
    travel = {"airport_pax": 1842300, "yoy_pct": 12.3}
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
