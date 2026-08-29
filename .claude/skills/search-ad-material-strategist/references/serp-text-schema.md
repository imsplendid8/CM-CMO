# SERP Text Schema

SERP screenshots are visual references, not the primary input. Store SERP observations as text before deriving copy.

## Minimum JSON Shape

```json
{
  "keyword": "운전자보험",
  "captured_at": "2026-08-29",
  "device": "mobile",
  "ads": [
    {
      "rank": 1,
      "brand": "브랜드명",
      "title": "광고 제목",
      "description": "광고 설명",
      "extensions": {
        "additional_titles": [],
        "additional_descriptions": [],
        "promotions": [],
        "sitelinks": []
      },
      "detected_angles": ["보험료", "형사합의금", "변호사선임비용"],
      "cta": ["계산", "확인", "가입"],
      "risk_flags": []
    }
  ],
  "autocomplete": ["운전자보험 1일", "운전자보험 해지", "운전자보험 청구"],
  "related_keywords": [],
  "monthly_diff": {
    "new_brands": [],
    "dropped_brands": [],
    "rising_angles": [],
    "declining_angles": []
  }
}
```

## Derived Fields

After reading raw SERP text, derive:

- table_stakes: expected messages many advertisers include;
- saturated_patterns: phrases that are too common to reuse plainly;
- whitespace_angles: useful questions or conditions competitors under-explain;
- cta_patterns: repeated verbs such as `계산`, `확인`, `조회`, `상담`, `가입`;
- extension_patterns: how additional titles, descriptions, promotions, and sitelinks are used;
- new_or_changed_signals: brands or angles that changed from the previous month.

## Rules

- Do not infer exact competitor performance from rank alone.
- Do not claim a SERP observation is live unless it was captured in the current workflow.
- If only an image is available, extract text first and label uncertain fields.
- Keep source date, keyword, and device with every material recommendation.
