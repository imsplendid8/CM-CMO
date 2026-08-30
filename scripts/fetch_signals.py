#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수요 트리거 실데이터화 — 공공데이터(data.go.kr)로 상품별 실시간 수요 신호 산출.

출력: data/signals.json
  {
    "asof": "2026-07-23", "source": "data.go.kr" | "sample",
    "weather": {"active": ["호우", ...]},
    "travel":  {"overseas_ratio": 88.0, "avg": 61.0, "period": "2026-07-01"},  # 여행자보험 검색수요(데이터랩) + 출입국관광통계
    "triggers": { "hrmf": {"level":"high","note":"호우특보 발효 → 누수·침수 담보 수요"}, ... }
  }

- 상품 트리거 레벨(high/normal)을 미리 계산해두면, 뉴스툴은 그대로 읽어서 칩만 표시.
- 이 샌드박스는 외부망 차단 → 실제 호출은 GitHub Actions(signals.yml)에서. 로컬 미리보기는 --sample.
- 키: 환경변수 DATA_GO_KR_KEY (data.go.kr 마이페이지 > 인증키. 하나로 여러 서비스 사용).
- 관광 출입국 통계는 환경변수 TOUR_API_URL / TOUR_API_KEY 로 연결한다.

엔드포인트는 상수로 분리 — 첫 실행에서 응답 스키마에 맞춰 PARSE 부분만 조정하면 됩니다.
"""
import os, sys, json, datetime, urllib.parse, urllib.request, urllib.error, xml.etree.ElementTree as ET

try:
    from scripts.io_utils import atomic_json_write
except ModuleNotFoundError:  # python scripts/fetch_signals.py
    from io_utils import atomic_json_write

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "signals.json")
KEY = os.environ.get("DATA_GO_KR_KEY", "").strip()
TOUR_API_URL = os.environ.get("TOUR_API_URL", "").strip()
TOUR_API_KEY = os.environ.get("TOUR_API_KEY", "").strip()
TOUR_API_FORMAT = os.environ.get("TOUR_API_FORMAT", "json").strip().lower()
TOUR_API_START_DT = os.environ.get("TOUR_API_START_DT", "").strip()
TOUR_API_END_DT = os.environ.get("TOUR_API_END_DT", "").strip()
TOUR_API_PAGE_NO = os.environ.get("TOUR_API_PAGE_NO", "1").strip()
TOUR_API_NUM_OF_ROWS = os.environ.get("TOUR_API_NUM_OF_ROWS", "10").strip()
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
    """해외여행보험 수요 = 네이버 데이터랩 '여행자보험' 일간 검색수요(상대지수). 최근 7일 평균 vs 90일 평균으로 성수기 상승 판정.
    (출입국관광통계 openapi.tour.go.kr는 GitHub Actions에서 불통 → 확실히 닿는 네이버 DataLab로 대체.)"""
    nid = os.environ.get("NAVER_CLIENT_ID", "").strip()
    nsec = os.environ.get("NAVER_CLIENT_SECRET", "").strip()
    if not (nid and nsec):
        return {"overseas_ratio": None, "error": "NAVER_CLIENT_ID/SECRET 없음(데이터랩)"}
    end = datetime.date.today() - datetime.timedelta(days=1)                  # 어제(오늘은 미완)
    start = end - datetime.timedelta(days=95)                                 # 약 90일
    body = json.dumps({"startDate": start.isoformat(), "endDate": end.isoformat(), "timeUnit": "date",
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
        recent = ratios[-7:] or ratios
        r7 = round(sum(recent) / len(recent), 1)
        avg = round(sum(ratios) / len(ratios), 1)
        return {"overseas_ratio": r7, "period": data[-1]["period"], "avg": avg, "peak": round(max(ratios), 1), "basis": "최근 7일 평균 vs 90일"}
    except Exception as e:
        return {"overseas_ratio": None, "error": str(e)[:140]}

def _coerce_float(value):
    try:
        if value is None:
            return None
        text = str(value).strip().replace(",", "")
        if not text:
            return None
        return float(text)
    except Exception:
        return None

def _find_first_number(payload):
    if isinstance(payload, dict):
        for key in ("value", "cnt", "count", "total", "totalCount", "result", "data", "item", "items"):
            if key in payload:
                found = _find_first_number(payload[key])
                if found is not None:
                    return found
        for val in payload.values():
            found = _find_first_number(val)
            if found is not None:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = _find_first_number(item)
            if found is not None:
                return found
    else:
        return _coerce_float(payload)
    return None

def fetch_tour_exit():
    """출입국관광통계(국민해외관광객 등) 신호.

    정확한 API 요청 URL과 파라미터는 기관별로 조금씩 다를 수 있으므로,
    TOUR_API_URL / TOUR_API_KEY 를 환경변수로 받아서 유연하게 연결한다.
    응답이 JSON/ XML 어느 쪽이든 숫자 값을 최대한 찾아낸다.
    """
    if not (TOUR_API_URL and TOUR_API_KEY):
        return {
            "outbound_count": None,
            "error": "TOUR_API_URL/TOUR_API_KEY 없음",
            "source": "tourism-api",
        }

    params = {
        "serviceKey": TOUR_API_KEY,
        "pageNo": TOUR_API_PAGE_NO or "1",
        "numOfRows": TOUR_API_NUM_OF_ROWS or "10",
    }
    if TOUR_API_START_DT:
        params["startDt"] = TOUR_API_START_DT
    if TOUR_API_END_DT:
        params["endDt"] = TOUR_API_END_DT
    if TOUR_API_FORMAT == "json":
        params.setdefault("type", "json")
        params.setdefault("dataType", "JSON")

    q = urllib.parse.urlencode(params, safe="%")
    url = TOUR_API_URL + ("&" if "?" in TOUR_API_URL else "?") + q
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            raw = r.read()
            text = raw.decode("utf-8", errors="ignore").strip()

        if text.startswith("{") or text.startswith("["):
            payload = json.loads(text)
        else:
            # XML/HTML 응답도 숫자 추출 시도
            try:
                root = ET.fromstring(text)
                payload = {elem.tag: elem.text for elem in root.iter() if elem.text}
            except Exception:
                payload = {"raw": text[:2000]}

        count = _find_first_number(payload)
        if count is None:
            return {
                "outbound_count": None,
                "error": "관광 API 응답에서 수치 파싱 실패",
                "source": "tourism-api",
                "raw_hint": str(payload)[:260],
            }
        return {
            "outbound_count": round(count, 1) if isinstance(count, float) else count,
            "source": "tourism-api",
            "period": TOUR_API_END_DT or TODAY,
            "basis": "출입국관광통계 API",
        }
    except urllib.error.HTTPError as e:
        return {"outbound_count": None, "error": f"HTTP {e.code}", "source": "tourism-api"}
    except Exception as e:
        return {"outbound_count": None, "error": str(e)[:140], "source": "tourism-api"}

def build_triggers(weather, travel, exit_tour=None):
    """상품별 실시간 수요 신호 레벨 산출(정성 규칙). 여러 특보가 동시 발효면 사유를 누적."""
    w = set(weather.get("active", []))
    trg = {}
    # 주택화재: 특보별 위험을 누적(호우·태풍=누수/침수, 한파·대설=동파/난방화재, 건조=발화/산불, 폭염=전기과부하 화재)
    hrmf = []
    if {"호우", "태풍"} & w: hrmf.append("호우·태풍 → 누수·침수·풍수재")
    if {"한파", "대설"} & w: hrmf.append("한파·대설 → 동파·난방화재")
    if "건조" in w:          hrmf.append("건조 특보 → 전선·콘센트 발화·산불 위험")
    if "폭염" in w:          hrmf.append("폭염 → 전기과부하·에어컨 화재")
    if hrmf:
        trg["hrmf"] = {"level": "high", "note": "기상특보 발효 → " + " / ".join(hrmf) + " 담보 수요", "kinds": sorted(w & {"호우","태풍","한파","대설","건조","폭염"})}
    # 운전자: 대설·강풍·한파(빙판·사고)
    if {"대설", "강풍", "한파"} & w:
        trg["driver"] = {"level": "high", "note": "대설·강풍·한파 특보 → 빙판·사고 위험·운전자보험 관심↑", "kinds": sorted(w & {"대설","강풍","한파"})}
    # 해외여행: '여행자보험' 검색수요가 평균 대비 상승(성수기)하면 high
    lr, avg = travel.get("overseas_ratio"), travel.get("avg") or 0
    if lr is not None and avg and (lr >= avg * 1.15 or lr >= 75):
        trg["overseas"] = {"level": "high", "note": f"‘여행자보험’ 검색수요 상승({travel.get('period','')} 지수 {lr}/평균 {avg}) → 성수기 해외여행보험 대응"}
    if exit_tour and exit_tour.get("outbound_count") is not None:
        count = exit_tour.get("outbound_count")
        if isinstance(count, (int, float)) and count >= 100:
            trg["overseas_exit"] = {
                "level": "high",
                "note": f"출입국관광통계({exit_tour.get('period','')}) 수치 {count} → 해외여행보험 수요 모니터링",
                "basis": exit_tour.get("basis", "출입국관광통계 API"),
            }
    return trg

def sample():
    weather = {"active": ["호우", "폭염"]}
    travel = {"overseas_ratio": 88.0, "period": "2026-07-23", "avg": 61.0, "peak": 100.0, "basis": "최근 7일 평균 vs 90일"}
    exit_tour = {"outbound_count": 128.4, "period": "2026-07", "basis": "출입국관광통계 API"}
    return {"asof": TODAY, "source": "sample", "weather": weather, "travel": travel, "exit_tour": exit_tour,
            "triggers": build_triggers(weather, travel, exit_tour)}

def main():
    if "--sample" in sys.argv or not KEY:
        data = sample()
        if not KEY and "--sample" not in sys.argv:
            data["note"] = "DATA_GO_KR_KEY 미설정 → 샘플. Actions/로컬에서 키 설정 시 실데이터."
    else:
        weather, travel, exit_tour = fetch_weather(), fetch_travel(), fetch_tour_exit()
        data = {"asof": TODAY, "source": "data.go.kr", "weather": weather, "travel": travel, "exit_tour": exit_tour,
                "triggers": build_triggers(weather, travel, exit_tour)}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    atomic_json_write(OUT, data)
    print(f"✔ data/signals.json ({data['source']}) · 트리거 {len(data['triggers'])}개 · 특보 {data['weather'].get('active')}")

if __name__ == "__main__":
    main()
