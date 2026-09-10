#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Google Trends → 월별 검색 트렌드 지수 수집 (무료).

각 상품 대표 키워드로 Google Trends에서 12개월 관심도 변화를 수집.
키워드 도구(keyword-tool.html)는 이 파일과 네이버 검색광고 데이터를 함께 비교.

필요 라이브러리:
  pip install pytrends

데이터 경로: data/google-volume.json
"""
import os, sys, json, time
from datetime import date, datetime, timedelta

try:
    from scripts.io_utils import atomic_json_write
except ModuleNotFoundError:
    from io_utils import atomic_json_write

try:
    from pytrends.request import TrendReq
except ImportError:
    print("ERROR: pytrends not installed. Run: pip install pytrends")
    sys.exit(1)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load(p):
    return json.load(open(os.path.join(ROOT, p), encoding="utf-8"))

def get_google_trends(keywords, region="KR"):
    """Google Trends에서 12개월 관심도 수집 (무료)."""
    try:
        pytrends = TrendReq(hl="ko-KR", tz=540)
        results = {}

        # 키워드별 수집 (요청 간 지연으로 rate limit 회피)
        for i, keyword in enumerate(keywords):
            try:
                print(f"  [{i+1}/{len(keywords)}] {keyword}...", end=" ", flush=True)

                # 12개월 데이터 요청
                pytrends.build_payload(
                    kw_list=[keyword],
                    timeframe="today 12-m",
                    geo=region,
                    cat=0
                )

                # 월별 시계열 데이터
                monthly = pytrends.interest_over_time()
                if not monthly.empty and keyword in monthly.columns:
                    # 0~100 정규화된 값
                    values = monthly[keyword].tolist()
                    max_val = max(values) if values else 100

                    results[keyword] = {
                        "source": "google_trends",
                        "region": region,
                        "values": values[-12:],  # 최근 12개월
                        "dates": [d.isoformat()[:7] for d in monthly.index[-12:]],  # YYYY-MM
                        "max_value": int(max_val),
                        "asof": date.today().isoformat()
                    }
                    print("✓")
                else:
                    print("—")

                time.sleep(1.5)  # Rate limit 회피

            except Exception as e:
                print(f"✗ ({str(e)[:40]})")
                time.sleep(2)
                continue

        return results

    except Exception as e:
        print(f"ERROR: Google Trends 수집 실패: {e}")
        return {}

def main():
    print("🔍 Google Trends 데이터 수집 시작...\n")

    # 상품 마스터 로드
    try:
        data = load("data/products.json")
        products = data.get("products", [])
    except Exception as e:
        print(f"ERROR: data/products.json 로드 실패: {e}")
        sys.exit(1)

    # 모든 상품의 검색어 수집 (serpKw 대표키워드 + core 핵심어)
    all_keywords = []
    for product in products:
        kw = product.get("serpKw", "")
        if kw:
            all_keywords.append(kw)
        # core 키워드들도 추가 (최대 5개까지)
        core = product.get("core", [])
        if isinstance(core, list):
            all_keywords.extend(core[:3])

    all_keywords = list(dict.fromkeys(all_keywords))  # 중복 제거 (순서 유지)
    print(f"총 {len(all_keywords)}개 키워드 수집 대상\n")

    # Google Trends 데이터 수집
    trends_data = get_google_trends(all_keywords)
    print(f"\n✅ {len(trends_data)}개 키워드 수집 완료")

    # 결과 구조화
    result = {
        "source": "google",
        "asof": date.today().isoformat(),
        "keywords": trends_data,
        "count": len(trends_data)
    }

    # 저장
    output_path = os.path.join(ROOT, "data", "google-volume.json")
    try:
        atomic_json_write(output_path, result, indent=2)
        print(f"📁 {output_path} 저장 완료")
    except Exception as e:
        print(f"ERROR: 저장 실패: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

