#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
구글 Keyword Planner (Google Ads API · KeywordPlanIdeaService)로
월평균검색량·경쟁도를 조회해 keyword-tool.html '검색량 불러오기' JSON으로 출력.

준비:
  1) Google Ads 계정 + 개발자 토큰(developer token)  ※ 표준 액세스는 승인 심사
  2) pip install google-ads
  3) google-ads.yaml 작성(developer_token, client_id/secret, refresh_token, login_customer_id)
     https://developers.google.com/google-ads/api/docs/client-libs/python/configuration

실행:
  python3 scripts/google_ads_keywords.py 암보험 운전자보험 치아보험 > volume_google.json

메모: Keyword Planner UI에서 CSV로 [다운로드] 후 도구에 그대로 붙여넣어도 됩니다(API 불필요).
"""
import sys, json

CUSTOMER_ID = "0000000000"          # 하이픈 없는 10자리
LANGUAGE    = "languageConstants/1012"        # 한국어
GEO         = ["geoTargetConstants/2410"]     # 대한민국

def main(seeds):
    from google.ads.googleads.client import GoogleAdsClient   # pip install google-ads
    client = GoogleAdsClient.load_from_storage("google-ads.yaml")
    svc = client.get_service("KeywordPlanIdeaService")
    req = client.get_type("GenerateKeywordIdeasRequest")
    req.customer_id = CUSTOMER_ID
    req.language = LANGUAGE
    req.geo_target_constants.extend(GEO)
    req.include_adult_keywords = False
    req.keyword_seed.keywords.extend(seeds)

    comp_map = {0: "", 1: "낮음", 2: "중간", 3: "높음"}   # UNSPECIFIED/LOW/MEDIUM/HIGH
    out = {"keywords": {}}
    for idea in svc.generate_keyword_ideas(request=req):
        m = idea.keyword_idea_metrics
        out["keywords"][idea.text] = {
            "pc": 0,                                   # 구글은 PC/모바일 분리 없음
            "mobile": int(m.avg_monthly_searches or 0),  # 월평균검색량(합)
            "comp": comp_map.get(int(m.competition), ""),
            "bidLow":  int(getattr(m, "low_top_of_page_bid_micros", 0)) // 10000,   # 원 근사
            "bidHigh": int(getattr(m, "high_top_of_page_bid_micros", 0)) // 10000,
        }
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    seeds = sys.argv[1:] or ["암보험", "운전자보험", "치아보험", "주택화재보험", "해외여행보험"]
    try:
        main(seeds)
    except ImportError:
        sys.exit("pip install google-ads 후 google-ads.yaml 을 설정하세요. (또는 Keyword Planner CSV 다운로드 사용)")
