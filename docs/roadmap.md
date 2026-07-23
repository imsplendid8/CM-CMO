# 로드맵 · 고도화

## 진행 현황 (5/10)
- [x] 1. 테크니컬 SEO 콘솔
- [x] 2. 검색광고 키워드 추출 (+ 네이버 키워드도구 .xlsx 병합)
- [x] 3. 카테고리 뉴스 모니터링 (+ 실시간 갱신)
- [x] 4. 검색결과 주간 아카이브 (+ 경쟁사 소구포인트)
- [x] 5. 연간 시즈널 이슈 캘린더
- [ ] 6~10. 미정 — 사용자 지정 시 착수

### 6~10번 후보 아이디어
- 랜딩/카피 A·B 테스트 요건정의 생성기
- 광고 소재(배너·문구) 관리·광고심의 체크리스트
- 전환 퍼널·GA/데이터스튜디오 링크 통합 뷰
- 경쟁사 상품/담보 비교표(포지셔닝 맵)
- 상품별 FAQ·AEO(생성형 검색) 대응 콘텐츠 생성기

---

## 고도화 아이디어 (검수 결과)

### A. 오픈소스(타인의 레포) 활용 — 도구별
| 도구 | 활용 가능한 OSS | 고도화 효과 |
|---|---|---|
| SEO | [advertools](https://github.com/eliasdabbas/advertools)(sitemap·SERP·crawl) · Google [Lighthouse CI](https://github.com/GoogleChrome/lighthouse-ci) · schema.org JSON-LD | robots/sitemap 자동 생성·검증, 성능·SEO 점수 자동 측정, 구조화데이터 |
| 키워드 | advertools kw_generate · [pytrends](https://github.com/GeneralMills/pytrends) · [KeyBERT](https://github.com/MaartenGr/KeyBERT) · [sentence-transformers](https://github.com/UKPLab/sentence-transformers) | 페이지 본문 키워드 추출, **임베딩 클러스터링으로 광고그룹 자동 편성** |
| 뉴스 | [trafilatura](https://github.com/adbar/trafilatura)/newspaper3k · [feedparser](https://github.com/kurtmckee/feedparser) | 기사 본문 추출로 요약 정확도↑, 경쟁사 보도자료 RSS 수집 |
| SERP | [Playwright](https://github.com/microsoft/playwright) · [pixelmatch](https://github.com/mapbox/pixelmatch)/[resemble.js](https://github.com/rsmbl/Resemble.js) · SerpApi | **전/후 스크린샷 시각 diff 자동 변화 감지**(하이라이트) |
| 시즌 | pytrends · 네이버 데이터랩 API · [Prophet](https://github.com/facebook/prophet) | 계절성 실측 자동 검증, 수요 피크 시계열 예측 |

### B. 크로스커팅(공통) 고도화
- ✅ **단일 상품 마스터**(1순위 완료): `data/products.json`을 캐노니컬 소스로, `scripts/check_products_sync.py`가 CI(`ci.yml`)에서 5개 도구 인라인 PRODUCTS의 드리프트를 검사. 자체완결 HTML 원칙을 지키면서 단일 기준 확보. (시즌은 `data/seasonal.json`, 데일리 브리핑이 소비)
- **자동 캡처 파이프라인**: SERP 주간 캡처를 self-hosted 러너/사내 PC의 Playwright로 자동화(네이버 봇차단 회피). 결과를 `serp_archive/`에 커밋 → 도구가 매니페스트로 표시.
- **회귀 테스트**: Playwright 렌더/문법 체크를 Actions로 상시화.
- **통합 검색·즐겨찾기**, 산출물 일괄 내보내기(PPT/Excel), 접근 로그.

### C. 운영 자동화 (구현됨/진행)
- ✅ **데일리 텔레그램 비서** — 하루 2회(오전·오후) 브리핑(시즌+뉴스+SERP). 설정: [daily-brief.md](daily-brief.md).
- ✅ **네이버 데이터랩 트렌드** — 시즌 실측 검증(`trends.yml` 월 1회 → `data/trends.json`).
- ✅ **네이버 검색광고 실검색량** — 키워드 도구 자동 반영(`searchad.yml` 주 1회 → `data/volume.json`, 검색광고 API 키 `NAVER_AD_*`). 상품별 연관키워드+월검색량·경쟁도 병합(출처=검색광고). 키 없으면 미반영.
- 후보: 경쟁사 리뉴얼 키워드 뉴스 감지 → 카카오 알림(사내 news_watch 패턴 이식).

## 우선순위 진행
1. ✅ `data/products.json` 단일 마스터화 + CI 드리프트 가드.
2. ✅ SERP 전/후 **시각 diff 자동 변화 감지** — canvas 픽셀 비교(pixelmatch 방식, 외부 라이브러리 0)로 바뀐 영역 붉게 하이라이트 + 변화율%·민감도 슬라이더·길이변화 경고. `serp-tool.html`.
3. ✅ 시즌 캘린더 **데이터랩 실측 검증** 연동 — `scripts/naver_trends.py`가 네이버 데이터랩 검색어 트렌드(월별 24개월)를 받아 `data/trends.json` 생성, `.github/workflows/trends.yml`(월 1회) 자동 갱신. 시즌 도구가 상품별 **실측 월별 추세 막대 + 피크월 + 시즌이슈 일치(✓/⚠)** 표시(검색 API와 동일 키). 키 미설정 시 샘플 근사 표시.
