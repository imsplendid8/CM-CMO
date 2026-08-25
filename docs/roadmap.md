# 로드맵 · 고도화

## 진행 현황 (도구 7종 + SA/BSA 솔루션)
- [x] 1. 테크니컬 SEO 콘솔 (+ 상품별 월간 FAQ 4개·FAQPage JSON-LD)
- [x] 2. 검색광고 키워드 추출 (+ 실시간 검색량 프록시 · **네이버 대량등록 파일**)
- [x] 3. 카테고리 뉴스 모니터링 (+ 실시간 갱신 · **클리핑 아카이브**)
- [x] 4. 검색결과 주간 아카이브 (+ 경쟁사 소구포인트 · **브랜드검색 갤러리**)
- [x] 5. 연간 시즈널 이슈 캘린더
- [x] 6. 검색광고 소재 (파워링크 소재 6블록·확장소재 규격 검수·엑셀 + **주차별 소재 캘린더** + **경쟁사 브랜드검색** 탭)
- [x] 7. 파워콘텐츠 소재 (검색수요 기반 전체 키워드셋 Excel + 콘텐츠 3안 + 본문·FAQ·광고 문안)
- ▶ **검색광고(SA)·BSA 솔루션** → [검색광고-BSA-로드맵.md](검색광고-BSA-로드맵.md): A1·A2·B2·B3 완료 (BSA 운영 CLI는 민감데이터라 **부서 전용 private 저장소**로 분리)

### 다음 후보 (SA/BSA 로드맵 외)
- 랜딩/카피 A·B 테스트 요건정의 생성기
- 전환 퍼널·GA/데이터스튜디오 링크 통합 뷰
- 경쟁사 상품/담보 비교표(포지셔닝 맵)

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
- ✅ **단일 상품 마스터**(1순위 완료): `data/products.json`을 캐노니컬 소스로, `scripts/check_products_sync.py`가 CI(`ci.yml`)에서 상품 기반 7개 도구 인라인 PRODUCTS의 드리프트를 검사. (시즌은 `data/seasonal.json`, 데일리 브리핑이 소비)
- **자동 캡처 파이프라인**: SERP 주간 캡처를 self-hosted 러너/사내 PC의 Playwright로 자동화(네이버 봇차단 회피). 결과를 `serp_archive/`에 커밋 → 도구가 매니페스트로 표시.
- **회귀 테스트**: Playwright 렌더/문법 체크를 Actions로 상시화.
- **통합 검색·즐겨찾기**, 산출물 일괄 내보내기(PPT/Excel), 접근 로그.

### C. 운영 자동화 (구현됨/진행)
- ✅ **데일리 텔레그램 비서** — 하루 2회(오전·오후) 브리핑(시즌+뉴스+SERP). 설정: [daily-brief.md](daily-brief.md).
- ✅ **데일리 이메일 브리프**(2026-08-07, 2026-08-24 간소화) — 매일 08:30 KST, 모바일 대응 1열 카드(주요 뉴스 요약 상위 8건). `daily-email.yml`·`daily_brief.py --email`. 텔레그램과 별도(SMTP 시크릿).
- ✅ **자동화 상태 점검**(2026-08-07) — `automation-status.yml`(07:40·13:40) + 브리프 실행 시 실시간 재계산(healthy/stale/missing/unknown 분리).
- ✅ **긴급 대형화재 감시**(2026-08-07, 2026-08-19 보강) — `fire_watch.py`+`fire-watch.yml`: 대형화재·산불 뉴스 감지 시 정기 브리프와 별개로 텔레그램 알림(기본 dry-run·옵트인 발송). 최근 발행시각·제목의 사건 종류·발생성 문구를 함께 요구하고 회고·작품·행사 문맥은 제외한다.
- ✅ **일일 파이프라인 재정비·보안**(2026-08-07) — 순서 06:30→07:20→07:40→08:00 등, 공유 레인 직렬화 / 브라우저 API 키 입력·저장 제거 + 워커 인증·요청허용 정책(Origin 화이트리스트·시크릿 전용·라우트/메서드 제한·레이트리밋).
- ✅ **네이버 데이터랩 트렌드** — 시즌 실측 검증(`trends.yml` 월 1회 → `data/trends.json`).
- ✅ **네이버 검색광고 월검색량** — 키워드·연간플랜·SEO·소재 도구 자동 반영(`searchad.yml` 주 1회 → 현재값 `data/volume.json` + 월 이력 `data/volume-history.json`, 검색광고 API 키 `NAVER_AD_*`). 월 이력으로 신규·급상승 후보를 계산한다. 키 없으면 미반영.
- 후보: 경쟁사 리뉴얼 키워드 뉴스 감지 → 카카오 알림(사내 news_watch 패턴 이식).

## 우선순위 진행
1. ✅ `data/products.json` 단일 마스터화 + CI 드리프트 가드.
2. ✅ SERP 전/후 **시각 diff 자동 변화 감지** — canvas 픽셀 비교(pixelmatch 방식, 외부 라이브러리 0)로 바뀐 영역 붉게 하이라이트 + 변화율%·민감도 슬라이더·길이변화 경고. `serp-tool.html`.
3. ✅ 시즌 캘린더 **데이터랩 실측 검증** 연동 — `scripts/naver_trends.py`가 네이버 데이터랩 검색어 트렌드(월별 24개월)를 받아 `data/trends.json` 생성, `.github/workflows/trends.yml`(월 1회) 자동 갱신. 시즌 도구가 상품별 **실측 월별 추세 막대 + 피크월 + 시즌이슈 일치(✓/⚠)** 표시(검색 API와 동일 키). 키 미설정 시 샘플 근사 표시.
