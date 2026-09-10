#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Google Trends와 Google Ads 키워드 플래너 → 월별 검색 트렌드와 검색량.

각 상품 대표 시드로 Google Trends API를 호출해 월별 관심도 변화와
Google Ads 키워드 플래너 데이터를 수집해 data/google-volume.json에 저장.
키워드 도구(keyword-tool.html)는 이 파일과 네이버 데이터를 함께 비교 표시.

필요 라이브러리:
  pip install pytrends google-ads

필요 Secrets(Google Ads API · 네이버 SearchAd와 '다름'):
  GOOGLE_ADS_DEVELOPER_TOKEN
  GOOGLE_ADS_CLIENT_ID
  GOOGLE_ADS_CLIENT_SECRET
  GOOGLE_ADS_REFRESH_TOKEN
  GOOGLE_ADS_CUSTOMER_ID
"""
import os, sys, json, csv, time
from datetime import date, timedelta
from collections import defaultdict

try:
    from scripts.io_utils import atomic_json_write
except ModuleNotFoundError:
    from io_utils import atomic_json_write

try:
    from pytrends.request import TrendReq
except ImportError:
    print("WARNING: pytrends not installed. Install with: pip install pytrends")
    TrendReq = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load(p):
    return json.load(open(os.path.join(ROOT, p), encoding="utf-8"))

def get_google_trends(keywords, region="KR"):
    """Google Trends에서 월별 관심도 수집."""
    if not TrendReq:
        return {}

    try:
        pytrends = TrendReq(hl="ko-KR", tz=540)  # Korean timezone
        results = {}

        for keyword in keywords[:5]:  # 5개씩 (API 제한)
            try:
                # 1년 데이터 수집
                pytrends.build_payload(
                    kw_list=[keyword],
                    timeframe="today 12-m",
                    geo=region
                )

                # 월별 데이터
                monthly = pytrends.interest_over_time()
                if not monthly.empty:
                    results[keyword] = {
                        "source": "google_trends",
                        "region": region,
                        "monthly": monthly[keyword].tolist()[-12:],  # 최근 12개월
                        "asof": date.today().isoformat()
                    }

                time.sleep(2)  # Rate limiting
            except Exception as e:
                print(f"  Error fetching {keyword}: {e}")
                continue

        return results
    except Exception as e:
        print(f"Google Trends API error: {e}")
        return {}

def get_google_ads_volume(keywords):
    """Google Ads 키워드 플래너 데이터 수집 (수동 파일 기반).

    실제 API는 매우 복잡하므로, 키워드 플래너에서 CSV로 내보낸 파일을
    data/google-ads-manual.csv로 두고 읽어서 처리.
    """
    csv_path = os.path.join(ROOT, "data", "google-ads-manual.csv")
    if not os.path.exists(csv_path):
        print(f"  {csv_path} not found. Skipping Google Ads data.")
        return {}

    results = {}
    try:
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                keyword = row.get("Keyword") or row.get("키워드")
                if not keyword:
                    continue

                # 평균 월검색량, 경쟁도
                monthly_searches = row.get("Avg. monthly searches") or row.get("평균 월검색량")
                competition = row.get("Competition") or row.get("경쟁도")

                if keyword in keywords:
                    results[keyword] = {
                        "source": "google_ads",
                        "monthly_volume": int(monthly_searches.replace(",", "")) if monthly_searches else 0,
                        "competition": competition or "—",
                        "asof": date.today().isoformat()
                    }
    except Exception as e:
        print(f"  Error reading Google Ads CSV: {e}")

    return results

def main():
    products = load("data/products.json")

    # 모든 상품의 검색어 수집
    all_keywords = []
    for product in products:
        q = product.get("q", "")
        extra = product.get("extra", [])
        if q:
            all_keywords.extend([q] + extra)

    all_keywords = list(set(all_keywords))[:50]  # 중복 제거, 상위 50개

    print(f"수집할 키워드: {len(all_keywords)}개")

    result = {
        "source": "google",
        "asof": date.today().isoformat(),
        "products": {}
    }

    # Google Trends 수집
    print("\n1️⃣  Google Trends 데이터 수집 중...")
    trends_data = get_google_trends(all_keywords)

    # Google Ads 수집
    print("2️⃣  Google Ads 키워드 플래너 데이터 수집 중...")
    ads_data = get_google_ads_volume(all_keywords)

    # 상품별로 정렬
    for product in products:
        key = product.get("key")
        q = product.get("q", "")
        extra = product.get("extra", [])
        keywords = [q] + extra if q else []

        result["products"][key] = {
            "name": product.get("name"),
            "keywords": {}
        }

        for keyword in keywords:
            google_result = {}

            if keyword in trends_data:
                google_result.update(trends_data[keyword])

            if keyword in ads_data:
                google_result.update(ads_data[keyword])

            if google_result:
                result["products"][key]["keywords"][keyword] = google_result

    # 저장
    output_path = os.path.join(ROOT, "data", "google-volume.json")
    atomic_json_write(output_path, result, indent=2, ensure_ascii=False)

    print(f"\n✅ {output_path} 저장 완료")
    print(f"   - Trends: {len(trends_data)}개")
    print(f"   - Ads: {len(ads_data)}개")

if __name__ == "__main__":
    main()
