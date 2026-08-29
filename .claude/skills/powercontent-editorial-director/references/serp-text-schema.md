# SERP Text Schema

Power Content should not be planned from a visual impression of a SERP screenshot. Use structured SERP text when available.

## Minimum Fields

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
  "autocomplete": [],
  "related_keywords": [],
  "monthly_diff": {
    "new_brands": [],
    "dropped_brands": [],
    "rising_angles": [],
    "declining_angles": []
  }
}
```

## Editorial Use

- Use repeated competitor wording as saturated language to avoid.
- Use common extensions as table stakes.
- Use autocomplete and related keywords to infer reader tasks.
- Use monthly diff to justify why this month's article differs from last month.
- Keep capture date, keyword, and device visible when presenting the rationale.
