# 실검색량·경쟁도 API 연동 (네이버 검색광고 / 구글 Keyword Planner)

키워드 추출 도구(`keyword-tool.html`)는 후보 키워드를 만들고 분류합니다.
**실검색량·경쟁도·입찰가**는 각 광고 플랫폼 API로 채웁니다.

> ⚠️ 정적 대시보드(브라우저)에서 API를 **직접 호출할 수 없습니다** — CORS 차단 + API 키가 클라이언트에 노출됩니다.
> 그래서 **키는 서버/로컬에만 두고 → 결과 JSON을 도구가 불러오는** 구조를 씁니다(마스킹·newsdata.js와 같은 이 프로젝트의 정적 원칙).

## 흐름
```
키워드 도구(CSV 시드) ─▶ [로컬/서버] API 호출(키 보관) ─▶ volume.json ─▶ 도구 "검색량 불러오기" 붙여넣기
```
도구가 읽는 JSON 형식:
```json
{ "keywords": {
    "암보험":        { "pc": 9000, "mobile": 76000, "comp": "높음" },
    "암보험 비교":   { "pc": 250,  "mobile": 1900,  "comp": "중간" }
} }
```

## 1) 네이버 검색광고 API — 키워드 도구
- 엔드포인트: `GET https://api.searchad.naver.com/keywordstool` (`hintKeywords`=시드 최대 5개)
- 반환: `relKeyword`, `monthlyPcQcCnt`, `monthlyMobileQcCnt`, `compIdx`(낮음/중간/높음), 클릭수 등
- 인증: HMAC-SHA256 서명 헤더 `X-Timestamp`·`X-API-KEY`·`X-Customer`·`X-Signature`
- 키 발급: **검색광고 → 도구 → API 사용 관리** (액세스라이선스·비밀키·CUSTOMER_ID)
- 실행:
  ```bash
  export NAVER_AD_API_KEY=... NAVER_AD_SECRET=... NAVER_AD_CUSTOMER=...
  python3 scripts/naver_searchad_keywords.py 암보험 운전자보험 치아보험 > volume.json
  ```
  → `scripts/naver_searchad_keywords.py` 포함(서명·파싱 구현 완료). 결과를 도구에 붙여넣으면 월검색량·경쟁도 열이 추가됩니다.

## 2) 구글 Keyword Planner — Google Ads API
- Keyword Planner UI의 데이터는 **Google Ads API**로 제공: `KeywordPlanIdeaService`
  - `generateKeywordIdeas` (아이디어+지표), `generateKeywordHistoricalMetrics` (특정 키워드 지표)
  - 반환: `avg_monthly_searches`, `competition`, `competition_index`, `low/high_top_of_page_bid_micros`
- 인증: OAuth2 + **개발자 토큰(developer token)** — Google Ads 계정 필요, 표준 액세스는 승인 심사
- 파이썬: `google-ads` 패키지
  ```python
  # pip install google-ads  (google-ads.yaml 에 developer_token·OAuth 설정)
  from google.ads.googleads.client import GoogleAdsClient
  client = GoogleAdsClient.load_from_storage("google-ads.yaml")
  svc = client.get_service("KeywordPlanIdeaService")
  req = client.get_type("GenerateKeywordIdeasRequest")
  req.customer_id = "CUSTOMER_ID"
  req.language = "languageConstants/1012"        # 한국어
  req.geo_target_constants.append("geoTargetConstants/2410")  # 대한민국
  req.keyword_seed.keywords.extend(["암보험", "운전자보험"])
  for idea in svc.generate_keyword_ideas(request=req):
      m = idea.keyword_idea_metrics
      print(idea.text, m.avg_monthly_searches, m.competition.name)
  ```
  → 위 결과를 같은 `{"keywords": {...}}` 형식(예: `pc`=검색수, `comp`=competition)으로 저장해 도구에 로드.

## 참고 오픈소스
- [eliasdabbas/advertools](https://github.com/eliasdabbas/advertools) — kw_generate(키워드 조합)·SERP·crawl
- [GeneralMills/pytrends](https://github.com/GeneralMills/pytrends) — 구글 트렌드(수요 추세 검증)
- [MaartenGr/KeyBERT](https://github.com/MaartenGr/KeyBERT) — 페이지 본문에서 키워드 추출

## 보안
- API 키·토큰은 **환경변수/.env**로만. **절대 저장소에 커밋 금지**(`.gitignore`).
- 자동화는 **로컬 또는 사내 서버**에서. GitHub Actions 사용 시 키는 **Secrets**로 주입.
