# data/clips/ — 뉴스 클리핑 아카이브

`scripts/clip_news.py` + `.github/workflows/news-clip.yml`(하루 2회: 09·13시 KST)가 채웁니다.
- `<YYYY-MM-DD>.json` — 그날 클리핑(카테고리별 items + 일 요약). 오전·오후 병합·dedup.
- `index.json` — 날짜 목록 + 월별 집계. 뉴스툴 '클리핑 아카이브'가 로드(날짜검색·일/월 요약).
- 공개 뉴스 헤드라인·링크만 저장.
- **보관 기간: 최신 30일치**(`clip_news.py`의 `KEEP_DAYS`) — 초과한 이전 일자 파일은 매 실행 시 자동 정리됩니다. 카테고리 뉴스툴 카드는 최신 일자 클립을 헤드라인으로 자동 반영.
