# SERP 텍스트 관측 스키마 v2

네이버 검색광고 소재 판단은 스크린샷 이미지가 아니라 구조화된 텍스트 관측을 1차 입력으로 사용한다. 이미지는 레이아웃·썸네일 톤 확인용 보조 자료다.

## 필수 관측 단위

```json
{
  "product": "driver",
  "keyword": "운전자보험",
  "captured_at": "2026-08-29",
  "date": "2026-08-29",
  "device": "mobile",
  "rank": 1,
  "brand": "브랜드명",
  "title": "광고 제목",
  "description": "광고 설명",
  "desc": "기존 호환용 광고 설명",
  "extensions": {
    "additional_titles": [],
    "additional_descriptions": [],
    "promotions": [],
    "sitelinks": []
  },
  "covers": ["형사합의금", "변호사선임비용"],
  "detected_angles": ["형사합의금", "변호사선임비용"],
  "cta_terms": ["계산", "확인"],
  "risk_flags": []
}
```

## 상품별 분석 산출물

`scripts/serp_analysis.py`는 기존 `soju`, `common_soju`, `promos`, `cta`, `prices`를 유지하면서 아래 필드를 추가한다.

- `schema_version`: SERP 분석 산출물 버전
- `required_observation_fields`: 신규 관측에 필요한 필드 목록
- `observed_ads[].source_observation_id`: 관측 항목 fingerprint
- `observed_ads[].description`: `desc`와 함께 쓰는 명확한 설명 필드
- `observed_ads[].extensions`: 추가제목·추가설명·홍보문구·서브링크 분리
- `observed_ads[].detected_angles`: 담보/소구/질문 축
- `observed_ads[].cta_terms`: 계산·확인·비교 등 행동어
- `observed_ads[].risk_flags`: 최상급·즉시가입·공포소구 등 주의 표현
- `monthly_diff`: 최신 관측일과 직전 관측일의 신규/이탈 브랜드 및 상승/하락 소구

## 운영 메모

- 경쟁사 문구는 복사하지 않는다. 반복 소구와 공백 소구를 분리하는 근거로만 사용한다.
- 자동완성어·연관 검색어는 키워드 제안에 저장하고, SERP 관측에는 광고 소재 구조만 남긴다.
- 뉴스 맥락은 시즌성 판단 보조자료다. 사고 뉴스를 공포 소구 문구로 바꾸지 않는다.
- 반려된 소재는 `소재제작소 Admin`에서 로컬 검수 후 `data/adcopy/material-feedback-rules.json`으로 환류한다.
