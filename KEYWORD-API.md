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

## 빠른 시작 — 내 계정으로 붙이기 (2가지 경로)

### 경로 A. CSV 다운로드 → 붙여넣기 (개발 불필요, 가장 빠름) ✅
1. **네이버 검색광고**(searchad.naver.com) → **도구 > 키워드 도구** → 시드 키워드 입력 → 조회 → **[다운로드]**
   (또는 **구글 Keyword Planner** → 키워드 아이디어 → **[키워드 아이디어 다운로드]**)
2. 다운로드한 표(엑셀/CSV)를 열어 **헤더 포함 복사**
3. 키워드 도구 상단 **"📊 실검색량·경쟁도 불러오기"** 열고 붙여넣기 → **적용**
   → 월검색량·경쟁도 열이 붙고 검색량순 정렬됩니다. (컬럼명 자동 인식: 연관키워드/월간검색수/경쟁정도 · Keyword/Avg. monthly searches/Competition)

### 경로 B-0. 실시간 연동 (가장 쉬움 · 명령어 1줄, 나머지는 페이지에서) ⭐
> 브라우저는 보안(CORS)상 네이버 API를 직접 못 부릅니다. 그래서 내 PC에 작은 '연동 서버'를 띄우고, 페이지가 그 서버를 통해 네이버에 요청합니다. 키는 내 PC 밖으로 안 나갑니다.
```bash
python3 scripts/naver_local_server.py     # 1) 이 한 줄 실행 (pip 불필요)
# 2) 브라우저에서 http://localhost:8787/keyword-tool.html 열기
# 3) '🔌 네이버 실시간 연동'에 키 3개 입력 → 버튼 클릭 → 검색량이 표에 채워짐
```
'이 브라우저에 키 저장'을 체크하면 다음부턴 키 입력도 생략됩니다.

### 경로 B. API 자동화 (반복·대량) — 구체 절차

원클릭 실행(키만 넣으면 됨):
```bash
cp scripts/.env.example scripts/.env      # 네이버 키 3개 채우기
bash scripts/run_keywords.sh              # 네이버(+구글) 조회 → 병합 → volume.json
# → volume.json 내용을 키워드 도구 '검색량 불러오기'에 붙여넣기
```

**B-1. 네이버 검색광고 (바로 발급, 무료)**
1. https://searchad.naver.com 로그인 → 우측 상단 **도구 > API 사용 관리**
2. **네이버 검색광고 API** 화면에서:
   - **CUSTOMER ID**(숫자) 확인 → `NAVER_AD_CUSTOMER`
   - **[액세스라이선스 발급]** → `NAVER_AD_API_KEY`
   - **[비밀키 발급]** → `NAVER_AD_SECRET`
3. `scripts/.env`에 3개 입력
4. 실행: `python3 scripts/naver_searchad_keywords.py 암보험 운전자보험 > volume_naver.json`
   - 내부적으로 `/keywordstool` 을 시드 5개씩 배치 호출(HMAC 서명은 스크립트가 처리)
   - 반환: 연관키워드 + `monthlyPcQcCnt`/`monthlyMobileQcCnt`/`compIdx`(낮음·중간·높음)

**B-2. 구글 Ads (개발자 토큰 승인 필요)**
1. **Google Ads** 계정 + **관리자(MCC) 계정** → 도구 > **API Center** → **개발자 토큰** 신청
   - 처음엔 *테스트 액세스* → 실데이터는 *Basic 액세스* 신청(폼·승인)
2. **Google Cloud Console** → OAuth 클라이언트(데스크톱) 생성 → `client_id`/`client_secret` → refresh token 발급
3. 레포 루트에 **`google-ads.yaml`** 작성:
   ```yaml
   developer_token: "..."
   client_id: "..."
   client_secret: "..."
   refresh_token: "..."
   login_customer_id: "1234567890"   # MCC, 하이픈 제거
   ```
4. `pip install google-ads` 후 실행:
   `python3 scripts/google_ads_keywords.py 암보험 운전자보험 > volume_google.json`
   - `KeywordPlanIdeaService.generate_keyword_ideas` (언어=한국어, 지역=대한민국)

**B-3. 병합 → 적용**
```bash
python3 scripts/merge_volume.py volume_naver.json volume_google.json > volume.json
```
`volume.json` → 도구 상단 **"검색량 불러오기"** 붙여넣기 → 월검색량·경쟁도 열 표시.

> ⚠️ `scripts/.env`·`google-ads.yaml`·`volume*.json` 은 `.gitignore` 로 커밋 차단됨. 자동화(스케줄)는 로컬/사내 서버 또는 GitHub Actions **Secrets** 로.

---

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
