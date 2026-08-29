# SEO Intelligence Schema

This repository uses a structured SEO observation feed so technical SEO analysis can behave more like an operator dashboard than a one-off checklist.

## Core idea

- `seo-audit.html` can ingest JSON produced by a crawler, Advertools-style export, or manual review.
- `site:` domain queries are stored separately from page crawl rows, so domain signals and on-page diagnostics do not get mixed.
- Ended events, expired products, and sales-ended landing pages are filtered out by default, but they remain visible as review evidence if the operator wants them.

## Recommended fields

```json
{
  "schema_version": 2,
  "asof": "2026-08-30",
  "observations": [
    {
      "domain": "www.carrotins.com",
      "site_query": "site:www.carrotins.com 운전자보험",
      "query": "site:www.carrotins.com 운전자보험",
      "url": "https://www.carrotins.com/driver",
      "title": "운전자보험 안내",
      "description": "상품 안내 페이지",
      "status": "active",
      "flags": ["indexed"],
      "source": "advertools",
      "captured_at": "2026-08-30"
    }
  ],
  "site_queries": [],
  "domain_queries": [],
  "monthly_diff": {
    "latest": "2026-08-30",
    "previous": "2026-07-30",
    "new_domains": [],
    "dropped_domains": [],
    "new_queries": [],
    "dropped_queries": [],
    "rising_angles": [],
    "declining_angles": []
  },
  "default_filters": {
    "exclude_flags": ["ended_event", "expired_product", "sales_ended", "noindex", "redirect_chain"],
    "exclude_status": ["ended", "expired", "closed", "sold_out", "discontinued"]
  }
}
```

## Notes

- `observations[]` is the main list.
- `site_queries[]` and `domain_queries[]` may be used if the upstream crawler groups results by query.
- `site_query` keeps the exact `site:` search string that produced the observation.
- `flags[]` should carry review and exclusion signals.
- The dashboard should treat screenshots as supporting evidence only; text fields are the primary input.
