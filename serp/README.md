# serp/ — 네이버 SERP 자동 캡쳐 아카이브

`scripts/capture_serp.mjs` + `.github/workflows/serp-capture.yml`(주간)가 채웁니다.
- 파일: `<상품key>-<YYYY-MM-DD>.png` (네이버 PC 통합검색 상단 1280×1600)
- 인덱스: `manifest.json` (상품별 캡쳐 히스토리 — SERP 아카이브 툴이 로드)
- SERP는 공개 검색결과라 PII 없음 → 캡쳐본 커밋 가능

## 수동 실행(로컬)
```bash
npm install playwright && npx playwright install chromium
node scripts/capture_serp.mjs           # 전체
ONLY=hrmf,golf node scripts/capture_serp.mjs   # 일부만
```
