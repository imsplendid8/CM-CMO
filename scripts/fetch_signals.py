#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수요 트리거 실데이터화 — 공공데이터(data.go.kr)로 상품별 실시간 수요 신호 산출.

출력: data/signals.json
  {
    "asof": "2026-07-23", "source": "data.go.kr" | "sample",
    "weather": {"active": ["호우", ...]},
    "travel":  {"overseas_ratio": 88.0, "avg": 61.0, "period": "2026-07-01"},  # 여행자보험 검색수요(데이터랩)
    "newreg":  {"count": 12345, "period": "2026-07", "mom": 4.2},  # 자동차 신규등록정보(통계누리)
    "triggers": { "hrmf": {"level":"high","note":"호우특보 발효 → 누수·침수 담보 수요"}, ... }
  }

- 상품 트리거 레벨(high/normal)을 미리 계산해두면, 뉴스툴은 그대로 읽어서 칩만 표시.
- 이 샌드박스는 외부망 차단 → 실제 호출은 GitHub Actions(signals.yml)에서. 로컬 미리보기는 --sample.
- 키: 환경변수 DATA_GO_KR_KEY (data.go.kr 마이페이지 > 인증키. 하나로 여러 서비스 사용).
- 관광 출입국 통계는 환경변수 TOUR_API_URL / TOUR_API_KEY 로 연결한다.
- 자동차 신규등록정보는 통계누리 URL이면 CAR_NEWREG_FORM_ID / CAR_NEWREG_STYLE_NUM까지,
  data.go.kr REST URL이면 CAR_NEWREG_API_URL / CAR_NEWREG_KEY만으로 연결한다.
  서비스별 고유 파라미터가 필요하면 CAR_NEWREG_EXTRA_PARAMS(JSON 객체)를 추가한다.

엔드포인트는 상수로 분리 — 첫 실행에서 응답 스키마에 맞춰 PARSE 부분만 조정하면 됩니다.
"""
import os, sys, json, re, datetime, urllib.parse, urllib.request, urllib.error, xml.etree.ElementTree as ET

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
CAR_NEWREG_API_URL = os.environ.get("CAR_NEWREG_API_URL", "http://stat.molit.go.kr/portal/openapi/service/rest/getList.do").strip()
CAR_NEWREG_KEY = os.environ.get("CAR_NEWREG_KEY", "").strip()
CAR_NEWREG_FORM_ID = os.environ.get("CAR_NEWREG_FORM_ID", "").strip()
CAR_NEWREG_STYLE_NUM = os.environ.get("CAR_NEWREG_STYLE_NUM", "").strip()
CAR_NEWREG_START_DT = os.environ.get("CAR_NEWREG_START_DT", "").strip()
CAR_NEWREG_END_DT = os.environ.get("CAR_NEWREG_END_DT", "").strip()
CAR_NEWREG_PAGE_NO = os.environ.get("CAR_NEWREG_PAGE_NO", "1").strip()
CAR_NEWREG_NUM_OF_ROWS = os.environ.get("CAR_NEWREG_NUM_OF_ROWS", "100").strip()
CAR_NEWREG_EXTRA_PARAMS = os.environ.get("CAR_NEWREG_EXTRA_PARAMS", "").strip()
MOJ_EXIT_API_KEY = os.environ.get("MOJ_EXIT_API_KEY", "").strip()
TODAY = datetime.date.today().isoformat()

# DEBUG
if not MOJ_EXIT_API_KEY:
    print(f"[WARN] MOJ_EXIT_API_KEY not set")
    print(f"[DEBUG] All env keys: {', '.join(sorted([k for k in os.environ.keys() if 'MOJ' in k or 'TOUR' in k or 'API' in k]))}")

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

def _extract_tour_series(payload):
    """출입국 통계 API 응답에서 월별·국가별 시계열 추출 시도.
    응답 구조가 다양하므로 가능한 범위 내에서 유연하게 수집."""
    series = []
    months = {}

    def walk(node, key_path=""):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{key_path}/{k}")
        elif isinstance(node, list):
            for i, item in enumerate(node):
                walk(item, f"{key_path}[{i}]")
        else:
            text = str(node or "").strip()
            # 기간 찾기 (202607, 2026-07, 2026-07-01, etc.)
            if re.match(r"\d{6,8}", text):
                period = re.match(r"(\d{6,8})", text).group(1)
                if len(period) == 8:
                    period = period[:6]
                # 같은 기간 내에서 가장 큰 숫자 찾기
                if period not in months:
                    months[period] = 0

    # 중복 제거 및 정렬
    for period in sorted(months.keys()):
        series.append({"period": period, "data": months[period]})

    return series

def fetch_exit_entry_stats():
    """법무부 출입국심사월별 통계(data.go.kr).

    해외여행보험·해외장기체류보험의 수요를 파악하기 위해 월별 출국자 통계를 수집한다.
    - 출국 국민(국민외국인구분=국민, 출입국구분=출국) → 해외여행보험 수요
    - 입국 외국인(국민외국인구분=외국인, 출입국구분=입국) → 외래관광 증가 신호

    API: data.go.kr의 월별 엔드포인트 (MofJustice_2_YYYYMM)
    응답: {page, perPage, totalCount, data: [{년, 월, 국민외국인구분, 출입국구분, 출입국자수}, ...]}
    """
    if not MOJ_EXIT_API_KEY:
        return {
            "outbound_count": None,
            "error": "MOJ_EXIT_API_KEY 없음",
            "source": "moj-exit-api",
            "note": "GitHub Secrets에서 MOJ_EXIT_API_KEY 설정 필요 (data.go.kr 마이페이지 > 인증키)",
        }

    # 데이터 지연(보통 1-2개월) 고려해서 최신 가용 월 계산
    current_month = datetime.date.today().strftime("%Y%m")
    latest_month = _subtract_months(current_month, 2)
    if not latest_month:
        latest_month = current_month

    # 6개월 데이터 수집 (월별 엔드포인트에서)
    months_to_fetch = [_subtract_months(latest_month, i) for i in range(6)]
    months_to_fetch = [m for m in months_to_fetch if m]
    months_to_fetch.reverse()  # 오래된 순서로 정렬

    series = {}
    all_errors = []

    for month in months_to_fetch:
        # data.go.kr API: /api/15099985/v1/odataservice/법무부_2_YYYYMM
        endpoint = f"https://api.odcloud.kr/api/15099985/v1/odataservice/법무부_2_{month}"
        params = {"serviceKey": MOJ_EXIT_API_KEY, "$top": "1000"}
        url = endpoint + "?" + urllib.parse.urlencode(params, safe="%")

        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                payload = json.loads(r.read().decode("utf-8"))

            # 응답 구조: {page, perPage, totalCount, data: [...]}
            data_list = payload.get("data") or []
            if isinstance(data_list, dict):
                data_list = [data_list]

            period_key = month  # YYYYMM
            if period_key not in series:
                series[period_key] = {"outbound_korean": 0, "inbound_foreign": 0}

            for record in data_list:
                # 필드 추출 (한글 키)
                year = record.get("년")
                month_val = record.get("월")
                nationality = record.get("국민외국인구분", "")
                direction = record.get("출입국구분", "")
                count = _coerce_float(record.get("출입국자수"))

                if not (year and month_val and count):
                    continue

                # 출국 국민 (해외여행보험 수요 신호)
                if nationality == "국민" and direction == "출국":
                    series[period_key]["outbound_korean"] += int(count)

                # 입국 외국인 (외래관광 증가 신호)
                if nationality == "외국인" and direction == "입국":
                    series[period_key]["inbound_foreign"] += int(count)

        except urllib.error.HTTPError as e:
            all_errors.append(f"Month {month}: HTTP {e.code}")
        except Exception as e:
            all_errors.append(f"Month {month}: {str(e)[:60]}")

    if not series:
        return {
            "outbound_count": None,
            "error": "출입국 통계 응답 파싱 실패",
            "source": "moj-exit-api",
            "debug": " | ".join(all_errors[-3:]) if all_errors else "No data",
        }

    # 최신 월 데이터
    latest_data = series.get(latest_month)
    if not latest_data:
        latest_month = sorted(series.keys())[-1] if series else None
        latest_data = series.get(latest_month) if latest_month else {}

    outbound = latest_data.get("outbound_korean", 0)
    inbound_foreign = latest_data.get("inbound_foreign", 0)

    # 트렌드 계산 (출국 국민 기준)
    trend_series = [
        {"period": m, "count": series[m].get("outbound_korean", 0)}
        for m in sorted(series.keys())
    ]
    trend = _calculate_trend(trend_series) if trend_series else {}

    return {
        "outbound_count": outbound,
        "inbound_foreign": inbound_foreign,
        "period": latest_month,
        "source": "moj-exit-api",
        "basis": "법무부 출입국심사 월별 통계",
        "trend": trend,
        "series": [
            {"period": m, "outbound_korean": series[m].get("outbound_korean", 0)}
            for m in sorted(series.keys())
        ],
    }

def fetch_tour_exit():
    """출입국관광통계 통합 진입점. 법무부 API 우선 사용, 없으면 기존 TOUR_API_URL 폴백."""
    # 법무부 출입국심사 API 우선 시도
    if MOJ_EXIT_API_KEY:
        return fetch_exit_entry_stats()

    # 폴백: 기존 TOUR_API_URL 기반 API (유지보수용)
    if not (TOUR_API_URL and TOUR_API_KEY):
        return {
            "outbound_count": None,
            "error": "MOJ_EXIT_API_KEY / TOUR_API_URL 모두 없음",
            "source": "tourism-api",
            "note": "GitHub Secrets에서 MOJ_EXIT_API_KEY 추가 필요",
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
            try:
                root = ET.fromstring(text)
                payload = {elem.tag: elem.text for elem in root.iter() if elem.text}
            except Exception:
                payload = {"raw": text[:2000]}

        count = _find_first_number(payload)
        series = _extract_tour_series(payload) if isinstance(payload, (dict, list)) else []

        if count is None:
            return {
                "outbound_count": None,
                "error": "관광 API 응답에서 수치 파싱 실패",
                "source": "tourism-api",
                "raw_hint": str(payload)[:260],
                "series": series,
            }

        trend = _calculate_trend(series) if series else {}
        return {
            "outbound_count": round(count, 1) if isinstance(count, float) else count,
            "source": "tourism-api",
            "period": TOUR_API_END_DT or TODAY,
            "basis": "출입국관광통계 API",
            "trend": trend,
            "series": series[-12:] if series else [],
        }
    except urllib.error.HTTPError as e:
        return {"outbound_count": None, "error": f"HTTP {e.code}", "source": "tourism-api", "note": "API 응답 오류. TOUR_API_URL 연결성 확인 필요"}
    except Exception as e:
        return {"outbound_count": None, "error": str(e)[:140], "source": "tourism-api"}

def _looks_like_number(s):
    if s is None:
        return False
    text = str(s).strip().replace(",", "")
    if not text:
        return False
    try:
        float(text)
        return True
    except Exception:
        return False

def _month_int(ym):
    text = str(ym or "").strip()
    if len(text) >= 6 and text[:6].isdigit():
        return text[:6]
    return ""

def _subtract_months(yyyymm_str, months):
    """YYYYMM 형식의 월에서 N개월 뺀다."""
    if not yyyymm_str or len(str(yyyymm_str)) < 6:
        return None
    try:
        year = int(str(yyyymm_str)[:4])
        month = int(str(yyyymm_str)[4:6])
        total_months = year * 12 + month - months
        if total_months < 1:
            return None
        new_year = (total_months - 1) // 12
        new_month = (total_months - 1) % 12 + 1
        return f"{new_year:04d}{new_month:02d}"
    except (ValueError, IndexError):
        return None

def _extract_molit_count(payload):
    """stat.molit 공통 응답에서 카운트성 숫자를 가능한 한 보수적으로 추출한다."""
    candidates = []

    def walk(node, key_hint=""):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, str(k))
        elif isinstance(node, list):
            for item in node:
                walk(item, key_hint)
        else:
            if not _looks_like_number(node):
                return
            key = key_hint.lower()
            val = str(node).strip().replace(",", "")
            # 날짜/시계열 값은 제외, 카운트처럼 보이는 필드만 수집
            if any(tok in key for tok in ("date", "dt", "ym", "year", "month", "ymd", "time", "period")):
                return
            if key in ("status_code",):
                return
            candidates.append(float(val))

    walk(payload)
    if not candidates:
        return None
    # 보통 표 내부의 카운트는 숫자 필드 중 가장 의미 있는 값이므로 마지막/최대보다
    # 전체 범위를 놓치지 않도록 첫 번째 큰 숫자 후보를 채택한다.
    candidates.sort(reverse=True)
    return candidates[0]

def _extract_molit_regions(payload):
    """시도별 자동차 신규등록 데이터 추출. 응답에서 지역명·등록대수 쌍을 찾는다."""
    regions = {}
    region_tokens = ("지역", "지명", "시도", "광역시", "도", "province", "region", "area", "sido")
    count_tokens = ("count", "cnt", "total", "regist", "register", "newreg", "value", "num")

    def walk(node, path=""):
        if isinstance(node, dict):
            # 현재 노드에서 지역명·개수 쌍 찾기
            region_key = None
            count_key = None
            region_val = None
            count_val = None

            for key, value in node.items():
                normalized_key = re.sub(r"[^a-z0-9]", "", str(key).lower())
                if any(tok in normalized_key for tok in region_tokens):
                    region_key = key
                    region_val = str(value).strip() if value else None
                if any(tok in normalized_key for tok in count_tokens):
                    if not any(skip in normalized_key for skip in ("code", "date", "month", "year", "period", "ym")):
                        count_key = key
                        count_val = _coerce_float(value)

            if region_val and count_val is not None and region_val and len(region_val) <= 20:
                # 지역명 정규화 (동일 지역의 다양한 표기 통합)
                normalized_region = region_val.replace(" ", "").replace("시", "").replace("도", "").strip()
                if normalized_region:
                    regions[region_val] = count_val

            # 재귀 탐색
            for value in node.values():
                walk(value, f"{path}/{key}" if key else path)
        elif isinstance(node, list):
            for i, item in enumerate(node):
                walk(item, f"{path}[{i}]")

    walk(payload)
    return regions if regions else {}

def _extract_molit_series(payload):
    """월별 응답 행에서 기간·등록대수를 함께 찾는다(필드명은 기관별 변형 허용)."""
    rows = []
    period_tokens = ("ym", "yyyymm", "registym", "month", "date", "period", "stdde")
    count_tokens = ("count", "cnt", "total", "regist", "register", "newreg", "value", "num")

    def period_value(node):
        if not isinstance(node, dict):
            return ""
        for key, value in node.items():
            normalized = re.sub(r"[^a-z0-9]", "", str(key).lower())
            if any(token in normalized for token in period_tokens):
                text = str(value or "").strip()
                digits = re.sub(r"[^0-9]", "", text)
                if len(digits) >= 6:
                    return digits[:8] if len(digits) >= 8 else digits[:6]
        return ""

    def count_value(node):
        if not isinstance(node, dict):
            return None
        candidates = []
        for key, value in node.items():
            normalized = re.sub(r"[^a-z0-9]", "", str(key).lower())
            if not any(token in normalized for token in count_tokens):
                continue
            if any(token in normalized for token in ("code", "date", "month", "year", "period", "page", "size", "ym", "yyyymm", "registym", "stdde")):
                continue
            number = _coerce_float(value)
            if number is not None:
                candidates.append(number)
        return max(candidates) if candidates else None

    def walk(node):
        if isinstance(node, dict):
            period = period_value(node)
            count = count_value(node)
            if period and count is not None:
                rows.append({"period": period, "count": count})
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(payload)
    unique = {}
    for row in rows:
        unique[(row["period"], row["count"])] = row
    return sorted(unique.values(), key=lambda row: row["period"])

def _calculate_trend(series):
    """시계열 데이터로부터 성장률과 방향성을 계산한다.
    입력: [{"period": "202607", "count": 12000}, {"period": "202608", "count": 13200}, ...]
    출력: {"growth_3m": 8.3, "growth_6m": 12.5, "direction": "up", "strength": "strong"}
    """
    if not series or len(series) < 2:
        return {}

    counts = [float(row.get("count") or 0) for row in series]
    valid_counts = [c for c in counts if c > 0]

    if len(valid_counts) < 2:
        return {}

    result = {}

    # 3개월 성장률 (있으면)
    if len(valid_counts) >= 3:
        avg_3m = sum(valid_counts[-3:-1]) / 2 if len(valid_counts) >= 3 else valid_counts[-1]
        latest = valid_counts[-1]
        if avg_3m > 0:
            growth_3m = round((latest - avg_3m) / avg_3m * 100, 1)
            result["growth_3m"] = growth_3m

    # 6개월 성장률 (있으면)
    if len(valid_counts) >= 6:
        avg_6m = sum(valid_counts[-6:-1]) / 5
        latest = valid_counts[-1]
        if avg_6m > 0:
            growth_6m = round((latest - avg_6m) / avg_6m * 100, 1)
            result["growth_6m"] = growth_6m

    # 방향성: 최근 3개월 vs 그 전 3개월 비교
    if len(valid_counts) >= 6:
        recent_3m = sum(valid_counts[-3:]) / 3
        prev_3m = sum(valid_counts[-6:-3]) / 3
        if prev_3m > 0:
            direction_pct = (recent_3m - prev_3m) / prev_3m * 100
            if direction_pct > 3:
                result["direction"] = "up"
                result["strength"] = "strong" if direction_pct > 10 else "moderate"
            elif direction_pct < -3:
                result["direction"] = "down"
                result["strength"] = "strong" if direction_pct < -10 else "moderate"
            else:
                result["direction"] = "flat"
                result["strength"] = "stable"
    elif len(valid_counts) >= 2:
        # 2개월 데이터로도 방향성만 파악
        if valid_counts[-1] > valid_counts[-2]:
            result["direction"] = "up"
        elif valid_counts[-1] < valid_counts[-2]:
            result["direction"] = "down"
        else:
            result["direction"] = "flat"

    return result

def _extract_status(payload):
    if not isinstance(payload, dict):
        return None, None
    status = payload.get("status_code") or payload.get("statusCode")
    message = payload.get("message") or payload.get("msg") or payload.get("errorMessage")
    if status or message:
        return str(status).strip() if status is not None else None, str(message).strip() if message is not None else None
    # XML 단일 레벨 dict가 아닐 때도 재귀적으로 한 번 더 찾는다.
    for v in payload.values():
        if isinstance(v, dict):
            s, m = _extract_status(v)
            if s or m:
                return s, m
    return None, None

def _is_data_go_url(url):
    host = urllib.parse.urlparse(str(url or "")).netloc.lower()
    return host.endswith("data.go.kr") or host.endswith("data.go.kr:443") or host.endswith("data.go.kr:80")

def _extra_params(raw):
    """서비스별 파라미터를 Secret(JSON)으로 받되 키·값을 평탄화한다."""
    if not raw:
        return {}, None
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        return {}, "CAR_NEWREG_EXTRA_PARAMS는 JSON 객체여야 합니다"
    if not isinstance(value, dict):
        return {}, "CAR_NEWREG_EXTRA_PARAMS는 JSON 객체여야 합니다"
    out = {}
    for key, item in value.items():
        key = str(key).strip()
        if not key or item is None:
            continue
        if isinstance(item, (dict, list)):
            return {}, "CAR_NEWREG_EXTRA_PARAMS의 값은 문자열·숫자만 허용합니다"
        out[key] = str(item)
    return out, None

def fetch_car_newreg():
    """한국교통안전공단_자동차종합정보 신규등록정보 서비스.

    승인된 통계누리 API를 바로 붙여서 운전자보험 수요 분석용 신호로 사용한다.
    전체 등록대수/누적 통계는 나중에 같은 패턴으로 추가 가능하도록 구조를 맞춘다.
    """
    if not (CAR_NEWREG_API_URL and CAR_NEWREG_KEY):
        return {
            "count": None,
            "period": None,
            "mom": None,
            "source": "stat.molit",
            "error": "CAR_NEWREG_API_URL/CAR_NEWREG_KEY 필요",
        }

    data_go = _is_data_go_url(CAR_NEWREG_API_URL)
    if not data_go and not (CAR_NEWREG_FORM_ID and CAR_NEWREG_STYLE_NUM):
        return {
            "count": None,
            "period": None,
            "mom": None,
            "source": "stat.molit",
            "error": "통계누리 URL은 CAR_NEWREG_FORM_ID/CAR_NEWREG_STYLE_NUM 필요 (data.go.kr REST URL은 두 값 불필요)",
        }

    params = {
        ("serviceKey" if data_go else "key"): CAR_NEWREG_KEY,
        "pageNo": CAR_NEWREG_PAGE_NO,
        "numOfRows": CAR_NEWREG_NUM_OF_ROWS,
    }
    if not data_go:
        params.update({"form_id": CAR_NEWREG_FORM_ID, "style_num": CAR_NEWREG_STYLE_NUM})
    else:
        params["dataType"] = "JSON"
    extras, extra_error = _extra_params(CAR_NEWREG_EXTRA_PARAMS)
    if extra_error:
        return {"count": None, "period": None, "mom": None, "source": "stat.molit" if not data_go else "data.go.kr", "error": extra_error}
    params.update(extras)
    # 통계누리는 start_dt/end_dt 필수, data.go.kr은 서비스별로 필드명이 다름
    current_month = datetime.date.today().strftime("%Y%m")
    if CAR_NEWREG_START_DT and CAR_NEWREG_END_DT:
        start_dt = CAR_NEWREG_START_DT
        end_dt = CAR_NEWREG_END_DT
    elif not data_go:
        # 통계누리: 데이터 지연(보통 1-2개월) 고려해서 자동 계산
        # 최신 가용 월 = 현월 - 2개월
        latest_month = _subtract_months(current_month, 2)
        if latest_month:
            start_dt = _subtract_months(latest_month, 5)  # 6개월 데이터
            end_dt = latest_month
        else:
            start_dt = ""
            end_dt = ""
    else:
        # data.go.kr: 필드명이 서비스별로 다르므로 미설정
        start_dt = ""
        end_dt = ""
    if start_dt:
        params["startDt" if data_go else "start_dt"] = start_dt
    if end_dt:
        params["endDt" if data_go else "end_dt"] = end_dt
    url = CAR_NEWREG_API_URL + "?" + urllib.parse.urlencode(params, safe="%")
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            raw = r.read()
            text = raw.decode("utf-8", errors="ignore").strip()
        if text.startswith("{") or text.startswith("["):
            payload = json.loads(text)
        else:
            try:
                root = ET.fromstring(text)
                payload = {elem.tag: elem.text for elem in root.iter() if elem.text}
            except Exception:
                payload = {"raw": text[:2000]}
        status, message = _extract_status(payload)
        series = _extract_molit_series(payload)
        latest = series[-1] if series else None
        count = latest["count"] if latest else _extract_molit_count(payload)
        period = latest["period"] if latest else (end_dt or TODAY)
        mom = None
        if len(series) >= 2 and series[-2]["count"]:
            mom = round((series[-1]["count"] - series[-2]["count"]) / series[-2]["count"] * 100, 2)
        trend = _calculate_trend(series) if series else {}
        if count is None:
            return {
                "count": None,
                "period": period,
                "mom": mom,
                "trend": trend,
                "source": "data.go.kr" if data_go else "stat.molit",
                "error": "신규등록정보 응답에서 수치 파싱 실패",
                "status_code": status,
                "message": message,
                "request": {"protocol": "data.go.kr" if data_go else "stat.molit", "form_id": CAR_NEWREG_FORM_ID or None, "style_num": CAR_NEWREG_STYLE_NUM or None, "start_dt": start_dt, "end_dt": end_dt},
                "series": series[-24:],
                "raw_hint": str(payload)[:260],
            }
        return {
            "count": round(count, 1) if isinstance(count, float) else count,
            "period": period,
            "mom": mom,
            "trend": trend,
            "source": "data.go.kr" if data_go else "stat.molit",
            "basis": "신규등록정보 서비스",
            "status_code": status,
            "message": message,
            "request": {"protocol": "data.go.kr" if data_go else "stat.molit", "form_id": CAR_NEWREG_FORM_ID or None, "style_num": CAR_NEWREG_STYLE_NUM or None, "start_dt": start_dt, "end_dt": end_dt},
            "series": series[-24:],
        }
    except urllib.error.HTTPError as e:
        return {"count": None, "period": end_dt or TODAY, "mom": None, "source": "data.go.kr" if data_go else "stat.molit", "error": f"HTTP {e.code}", "request": {"protocol": "data.go.kr" if data_go else "stat.molit", "form_id": CAR_NEWREG_FORM_ID or None, "style_num": CAR_NEWREG_STYLE_NUM or None, "start_dt": start_dt, "end_dt": end_dt}}
    except Exception as e:
        return {"count": None, "period": end_dt or TODAY, "mom": None, "source": "data.go.kr" if data_go else "stat.molit", "error": str(e)[:140], "request": {"protocol": "data.go.kr" if data_go else "stat.molit", "form_id": CAR_NEWREG_FORM_ID or None, "style_num": CAR_NEWREG_STYLE_NUM or None, "start_dt": start_dt, "end_dt": end_dt}}

def build_triggers(weather, travel, exit_tour=None, newreg=None):
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
    if newreg and newreg.get("count") is not None:
        count = newreg.get("count")
        if isinstance(count, (int, float)) and count >= 1000:
            trend = newreg.get("trend", {})
            trend_str = ""
            if trend.get("direction") == "up":
                trend_strength = "📈 강한" if trend.get("strength") == "strong" else "📈 완만한"
                trend_str = f" / {trend_strength} 상승세"
                if trend.get("growth_6m") is not None:
                    trend_str += f"(6개월 +{trend['growth_6m']}%)"
            elif trend.get("direction") == "down":
                trend_strength = "📉 급락" if trend.get("strength") == "strong" else "📉 하락"
                trend_str = f" / {trend_strength}"

            # 시도별 상위 지역 정보 추가
            region_str = ""
            by_region = newreg.get("by_region", {})
            if by_region:
                top_regions = sorted(by_region.items(), key=lambda x: x[1].get("count", 0), reverse=True)[:3]
                region_notes = [f"{region} +{data.get('ratio', 0)}%" for region, data in top_regions]
                region_str = f" · 지역: {' / '.join(region_notes)}"

            note = f"자동차 신규등록({newreg.get('period','')}) {count}대{trend_str}{region_str} → 운전자보험 수요 점검"
            if "driver" in trg and isinstance(trg["driver"], dict):
                prev = str(trg["driver"].get("note") or "").strip()
                trg["driver"]["note"] = prev + (" / " if prev else "") + note
                trg["driver"].setdefault("basis", [])
                if not isinstance(trg["driver"]["basis"], list):
                    trg["driver"]["basis"] = [str(trg["driver"]["basis"])]
                trg["driver"]["basis"].append(newreg.get("basis", "신규등록정보 서비스"))
            else:
                trg["driver"] = {
                    "level": "high",
                    "note": note,
                    "basis": [newreg.get("basis", "신규등록정보 서비스")],
                }
    elif newreg and newreg.get("error"):
        trg["driver_newreg_issue"] = {
            "level": "medium",
            "note": f"자동차 신규등록 API 확인 필요: {newreg.get('error')}",
            "basis": newreg.get("request") or {},
        }
    return trg

def sample():
    weather = {"active": ["호우", "폭염"]}
    travel = {"overseas_ratio": 88.0, "period": "2026-07-23", "avg": 61.0, "peak": 100.0, "basis": "최근 7일 평균 vs 90일"}
    exit_tour = {
        "outbound_count": 128400,
        "inbound_foreign": 215700,
        "period": "202607",
        "basis": "법무부 출입국심사 월별 통계",
        "trend": {"direction": "up", "strength": "moderate", "growth_6m": 8.5},
        "series": [
            {"period": "202602", "outbound_korean": 95200},
            {"period": "202603", "outbound_korean": 98100},
            {"period": "202604", "outbound_korean": 102300},
            {"period": "202605", "outbound_korean": 110500},
            {"period": "202606", "outbound_korean": 115200},
            {"period": "202607", "outbound_korean": 128400},
        ],
        "source": "moj-exit-api",
    }
    newreg = {
        "count": 17422,
        "period": "2026-07",
        "mom": 5.3,
        "basis": "신규등록정보 서비스",
        "trend": {"direction": "up", "strength": "strong", "growth_6m": 12.8, "growth_3m": 9.2},
        "by_region": {
            "경기": {"count": 3200, "ratio": 18.4},
            "서울": {"count": 2100, "ratio": 12.1},
            "부산": {"count": 1500, "ratio": 8.6},
            "인천": {"count": 1200, "ratio": 6.9},
            "대구": {"count": 1050, "ratio": 6.0},
        },
        "series": [
            {"period": "202601", "count": 14200},
            {"period": "202602", "count": 14800},
            {"period": "202603", "count": 15100},
            {"period": "202604", "count": 15900},
            {"period": "202605", "count": 16500},
            {"period": "202606", "count": 16550},
            {"period": "202607", "count": 17422},
        ],
        "source": "stat.molit",
    }
    return {"asof": TODAY, "source": "sample", "weather": weather, "travel": travel, "exit_tour": exit_tour, "newreg": newreg,
            "triggers": build_triggers(weather, travel, exit_tour, newreg)}

def main():
    if "--sample" in sys.argv or not KEY:
        data = sample()
        if not KEY and "--sample" not in sys.argv:
            data["note"] = "DATA_GO_KR_KEY 미설정 → 샘플. Actions/로컬에서 키 설정 시 실데이터."
    else:
        weather, travel, exit_tour, newreg = fetch_weather(), fetch_travel(), fetch_tour_exit(), fetch_car_newreg()
        data = {"asof": TODAY, "source": "data.go.kr", "weather": weather, "travel": travel, "exit_tour": exit_tour, "newreg": newreg,
                "triggers": build_triggers(weather, travel, exit_tour, newreg)}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    atomic_json_write(OUT, data)
    print(f"✔ data/signals.json ({data['source']}) · 트리거 {len(data['triggers'])}개 · 특보 {data['weather'].get('active')}")

if __name__ == "__main__":
    main()
