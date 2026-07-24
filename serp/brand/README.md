# serp/brand/ — 타사 브랜드검색 모니터링 (PC + 모바일)

`scripts/capture_brand.mjs` + `.github/workflows/serp-capture.yml`(매주 월요일)가 채웁니다.
- 경쟁사: 삼성·KB·현대·DB 다이렉트 × 상품(운전자·주택화재·골프·암·해외여행)
- 파일: `<경쟁사>-<상품>-<pc|mo>-<YYYY-MM-DD>.png` · 인덱스: `manifest.json`
- 브랜드검색 영역·파워링크·소구 문구를 PC/모바일로 비교. 네이버 공개 검색결과(PII 없음).

## 분석 요약 제안
캡쳐본을 근거로 cm-news-analysis/SERP 관점 스킬이 경쟁사 소구포인트·문구 변화를 요약·제안합니다(요청 시).
