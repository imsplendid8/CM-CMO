---
name: cm-serp-copy-strategist
description: CM-CMO의 공개 경쟁사 SERP 관측, 네이버 검색량, 승인된 상품 claim을 결합해 복제 없는 검색광고 제목·설명 세트를 만든다. 경쟁사 소재 변화 분석, SA 후보 생성, 차별 소구, 검색광고 문구 검토 요청에 사용한다.
---

# SERP 검색광고 전략

1. `scripts/serp_analysis.py`로 최신 관측 창을 집계한다.
2. `scripts/serp_copy_agent.py`로 후보를 생성한다.
3. 경쟁 문구는 복사하지 않고 공통 소구와 브랜드 진입·이탈을 관측 신호로만 사용한다.
4. 실측 검색어의 의도, 경쟁사가 덜 쓰는 상품 주제, 비교 행동 순서로 후보를 만든다.
5. 제목 15자 이하, 설명 20~45자, 금칙어·중복 검사를 통과한 세트만 남긴다.
6. 승인 claim이 없으면 `product_evidence_required`, 있더라도 `human_review_required`로 반환한다.
7. 가격·할인·1위·가입 가능 여부는 승인 claim 없이는 제안하지 않는다.

`serp/dom_observations.json`은 캡처 시 자동 추출한 검토 큐다. `needs_review` 항목을 사실로 사용하거나 승인 관측에 자동 병합하지 않는다.

산출물은 `data/adcopy/serp-candidates.json`이며 화면·내보내기의 입력으로만 사용한다.
