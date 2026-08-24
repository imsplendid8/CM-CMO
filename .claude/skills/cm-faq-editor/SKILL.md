---
name: cm-faq-editor
description: SearchAd 검색량과 선택적 Search Console 검색어에서 실제 고객 질문형 FAQ 기회를 발굴하고 보험 상품 근거로 답변 가능 여부를 판정한다. FAQ SEO, 질문 발굴, 콘텐츠 공백, FAQ JSON-LD 초안 요청에 사용한다.
---

# 고객 질문형 FAQ 편집

1. `scripts/faq_opportunity_agent.py`를 실행해 검색 질문 기회를 만든다.
2. 월 이름이나 내부 업무 용어를 질문에 억지로 넣지 않는다.
3. 동일 의도를 중복 제거하고 상품별 상위 4개 기회를 우선한다.
4. 승인된 `faq` 채널 claim이 없으면 질문만 제안하고 답변은 생성하지 않는다.
5. 답변은 첫 문장에서 직접 답하고 다음 문장에서 조건·예외·확인 경로를 설명한다.
6. 화면 FAQ와 JSON-LD 문구는 동일하게 유지한다.
7. 상품 담당·준법·광고심의 전에는 게시 가능 상태로 바꾸지 않는다.

선택적 GSC 입력은 `data/search-console.json`의 `rows[{query, impressions, clicks, page}]` 형식이다. 해당 파일이 없으면 SearchAd만 사용하고 `search_console_connected=false`를 명시한다.
`scripts/fetch_search_console.py`는 OAuth Secret이 모두 있을 때만 이 비공개 입력을 갱신한다.
