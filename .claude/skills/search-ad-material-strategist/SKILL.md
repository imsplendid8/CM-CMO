---
name: search-ad-material-strategist
description: Create or review Korean Naver search ad materials for Hanwha General Insurance CM using structured SERP text, news context, ad guide limits, review-draft examples, Power Content linkage, history checks, and a final humanized copy pass.
metadata:
  short-description: Hanwha CM Naver SA material strategist
---

# Search Ad Material Strategist

Use this skill when creating, improving, or reviewing Naver search ad materials for Hanwha General Insurance CM. The goal is not to produce many similar headlines. The goal is to build operator-ready SA material sets from structured SERP text, news context, Naver material constraints, review-draft examples, Power Content strategy, and past material history.

The first rule is: read the market as text, then write. SERP screenshots may explain layout, but they are not enough for material strategy. Convert SERP observations into structured fields before using them.

## Non-Negotiables

- Treat SERP images as secondary evidence. Main analysis must use structured text fields such as rank, brand, title, description, extensions, CTA, repeated angles, and monthly diff.
- Do not copy competitor phrasing. Competitor materials become table stakes, saturated patterns, or whitespace signals.
- Do not use generic formulas such as `갑작스러운 사고에 대비하세요`, `든든한 보장`, `담보를 보장하세요`, `꼼꼼히 확인하세요`, `지금 바로 가입`, or product-name-swapped versions.
- Exclude Direct Home, TM, telemarketing, auto insurance, and unrelated business lines unless the user explicitly changes scope.
- Do not assert guaranteed claim payment, guaranteed eligibility, lowest price, best status, no review, or immediate enrollment.
- Use news context only to explain search intent, seasonality, or risk awareness. Do not turn incident news into fear-based copy.
- Keep Power Content, image thumbnail, and SA materials connected through the same monthly message axis.
- For thumbnail generation or review, use the same standards as `sa-thumbnail-creative-director`: text-free premium 3D animation, product-fit scenes, current Naver guide assumptions, and monthly variation.
- Apply the private review-lab feedback loop when prior operator decisions exist. Approved examples are style references, rejected examples become avoid patterns with reason codes, and neither overrides product/compliance review.
- Use the insurance-ad-review compliance vocabulary for every final material: `자동 차단`, `근거 필요`, `필수 고지 필요`, `사람 심의 필요`, or `자동 위험표현 없음`. Never call an automated check `심의 통과`.
- Apply humanize-Korean style cleanup only at the end, and never change facts, figures, product names, policy terms, or review-sensitive meaning.

## Required First Pass

Before drafting copy, produce or mentally complete this diagnosis:

- What is the searcher deciding now?
- Which phrases are already overused in SERP?
- Which details are expected table stakes?
- Which questions or rider details are under-explained?
- Which news or seasonal context is valid for the selected month?
- Which review-draft tones are usable, and which expressions should be retired?
- Which Power Content concept should this SA material point to?
- What past material overlap or cannibalization risk exists?
- What did the private review lab previously approve, reject, or mark as unusable for this product/month/channel, and why?

## References

Read only the references needed for the current task:

- For SERP storage and analysis fields, read [references/serp-text-schema.md](references/serp-text-schema.md).
- For copy generation axes and output package, read [references/sa-material-method.md](references/sa-material-method.md).
- For Naver material constraints, read [references/naver-material-limits.md](references/naver-material-limits.md).
- For insurance safety, review-draft use, and prohibited phrasing, read [references/review-and-copy-guardrails.md](references/review-and-copy-guardrails.md).
- For the final AI-tell reduction pass, read [references/humanize-final-pass.md](references/humanize-final-pass.md).
- For linking to Power Content and image briefs, read [references/cross-channel-linkage.md](references/cross-channel-linkage.md).
- For private admin review states, reason codes, and skill-quality feedback, read [references/review-feedback-loop.md](references/review-feedback-loop.md).
- For Korean non-life insurance advertising compliance checks, read [references/insurance-review-compliance.md](references/insurance-review-compliance.md).
- For image thumbnail specifics, read the installed `sa-thumbnail-creative-director` skill when the task includes thumbnail prompts, actual image generation, or image QA.
- Before final delivery, read [references/quality-checklist.md](references/quality-checklist.md).

## Expected Output

For a full SA request, deliver:

1. SERP diagnosis.
2. Monthly material strategy.
3. Phrases to retire and phrases to keep.
4. Five SA material sets.
5. Power Content linkage.
6. Image thumbnail linkage idea.
7. Product/compliance review flags.
8. Private review-lab fields: usable/unusable status, reason codes, and what the operator should check.
9. Duplication and cannibalization check.
10. Final recommended set.

Keep the result practical for search advertising operations. If the user asks for code or automation, implement the same logic in the repository instead of only writing copy.
