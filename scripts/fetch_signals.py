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
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "signals.json")
KEY = os.environ.get("DATA_GO_KR_KEY", "").strip()
TODAY = datetime.date.today().isoformat()

# ── 공공데이터 엔드포인트 ─────────────────────────────
KMA_WARN = "http://apis.data.go.kr/1360000/WthrWrnInfoService/getWthrWrnList"   # 기상청 기상특보 목록 (JSON)
# 한국문화관광연구원 출입국관광통계 — 국민 해외관광객(출국, ED_CD=E) = 해외여행보험 수요 지표 (XML)
# openapi.tour.go.kr는 GitHub Actions에서 https가 자주 먹통 → http 우선, https 폴백
TOUR_BASES = ["http://openapi.tour.go.kr/openapi/service/EdrcntTourismStatsService/getEdrcntTourismStatsList",
              "https://openapi.tour.go.kr/openapi/service/EdrcntTourismStatsService/getEdrcntTourismStatsList"]
# 소방청 화재통계는 월별 집계 성격 → 필요 시 확장

def _get(url, params, timeout=20):   # JSON 응답용(기상청)
    params = dict(params); params["serviceKey"] = KEY; params.setdefault("dataType", "JSON")
    q = urllib.parse.urlencode(params, safe="%")
    with urllib.request.urlopen(url + "?" + q, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def _get_xml(url, params, timeout=45):   # XML 응답용(출입국관광통계 · openapi.tour.go.kr는 느릴 수 있음)
    params = dict(params); params["serviceKey"] = KEY
    q = urllib.parse.urlencode(params, safe="%")
    req = urllib.request.Request(url + "?" + q, headers={"User-Agent": "Mozilla/5.0 (Modooflow signals)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8")

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

def _ym(n_back):
    y, m = datetime.date.today().year, datetime.date.today().month - n_back
    while m <= 0: m += 12; y -= 1
    return f"{y}{m:02d}"

def fetch_travel():
    """국민 해외관광객(출국) 최근월 총계 → 해외여행보험 수요. (출입국관광통계 · XML · 통계 1~2개월 지연)."""
    last_err = ""
    for back in (2, 3):   # 통계 지연 감안 최근월 탐색
        ym = _ym(back)
        xml = None
        for base in TOUR_BASES:   # http 우선, https 폴백
            try:
                xml = _get_xml(base, {"YM": ym, "ED_CD": "E", "numOfRows": 100, "pageNo": 1}, timeout=30)  # ED_CD=E: 국민 해외관광객
                break
            except Exception as e:
                last_err = str(e)[:140]
        if xml is None: continue
        try:
            root = ET.fromstring(xml)
        except Exception as e:
            last_err = "XML 파싱 실패: " + str(e)[:80]; continue
        total, cnt = 0, 0
        for it in root.iter("item"):
            v = it.findtext("num")
            if not v: continue
            try: total += int(str(v).replace(",", "")); cnt += 1
            except Exception: pass
        if cnt:
            return {"outbound_total": total, "ym": ym, "countries": cnt}
        msg = root.findtext(".//returnAuthMsg") or root.findtext(".//errMsg") or root.findtext(".//resultMsg") or root.findtext(".//returnReasonCode")
        if msg: last_err = msg
    return {"outbound_total": None, "error": last_err or "item 없음(ED_CD/YM 확인)"}

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
    # 해외여행: 국민 해외관광객(출국) 신호(있으면)
    if travel.get("outbound_total"):
        trg["overseas"] = {"level": "high", "note": f"국민 해외관광객 {travel['outbound_total']:,}명({travel.get('ym','')}) → 해외여행보험 수요"}
    return trg

def sample():
    weather = {"active": ["호우", "폭염"]}
    travel = {"outbound_total": 2384100, "ym": "202605"}
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
