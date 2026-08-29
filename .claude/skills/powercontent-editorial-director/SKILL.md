---
name: powercontent-editorial-director
description: Produce high-quality Korean Naver Power Content plans for Hanwha General Insurance CM, using editorial reasoning, SERP signals, seasonal fit, policy-safe copy, image briefs, and SA material linkage. Use when asked to create, review, improve, or diagnose insurance power content quality.
metadata:
  short-description: Editorial-quality Hanwha CM power content
---

# Power Content Editorial Director

Use this skill when creating or reviewing Naver Power Content material for Hanwha General Insurance CM. The goal is not to produce a bundle of ad copy. The goal is to make an operator-ready editorial package with a clear reader problem, useful decision criteria, SERP-informed differentiation, practical image briefs, and search ad material that follows from the same idea.

Write like an editor and strategist, not like a template generator. The content should feel closer to a financial product magazine or product blog than an insurance ad sheet.

## Non-Negotiables

- Do not use generic fear or reassurance formulas such as `갑작스러운 사고에 대비하세요`, `든든한 보장`, `담보를 보장하세요`, `꼼꼼히 확인하세요`, or product-name-swapped variants.
- Do not propose out-of-month seasonal copy. Moving holidays and annual events need the selected month or exact event dates.
- Exclude Direct Home, TM, telemarketing, auto insurance, and other out-of-scope business areas unless the user explicitly changes the scope.
- Do not assert claim outcomes, guaranteed coverage, eligibility, price superiority, review results, or claim payment certainty.
- Mark review-sensitive expressions as needing product/compliance review instead of presenting them as final approved copy.
- Avoid copying competitor wording. Use SERP observations only to identify saturated patterns, table stakes, and whitespace.
- Treat SERP screenshots as secondary references. Prefer structured SERP text with rank, brand, title, description, extensions, CTA, repeated angles, and monthly diff.
- For image briefs, maintain text-free premium 3D animation unless the user explicitly requests another style.
- For SA thumbnail prompts or actual thumbnail QA, use the same standards as `sa-thumbnail-creative-director`.
- Apply the private review-lab feedback loop when prior operator decisions exist. Approved examples are style references, rejected examples become avoid patterns with reason codes, and neither overrides product/compliance review.
- Use the insurance-ad-review compliance vocabulary for every final article, CTA, SA linkage, and image brief: `자동 차단`, `근거 필요`, `필수 고지 필요`, `사람 심의 필요`, or `자동 위험표현 없음`. Never call an automated check `심의 통과`.
- Apply humanize-style cleanup only after strategy, safety, and factual checks. Do not change product terms, figures, dates, or review-sensitive meaning.

## First Move

Before drafting material, diagnose why the content should exist:

- What is the reader trying to decide after searching this product?
- What language is already overused in SERP or past material?
- Which product or rider details can become useful decision criteria?
- What seasonal context is valid for the selected month?
- What past content or keyword overlap creates cannibalization risk?
- What visual scene would help the reader understand the product without text overlays?
- What did the private review lab previously approve, reject, or mark as unusable for this product/month/channel, and why?

If required inputs are missing, continue with clearly labeled assumptions only when the gap does not change the strategy. Ask the user when missing product terms, selected month, or target product would materially change the output.

## References

Read only the references needed for the current task:

- For full content planning or article writing, read [references/editorial-standard.md](references/editorial-standard.md).
- For using SERP, related keywords, autocomplete, or monthly monitoring, read [references/serp-to-content-method.md](references/serp-to-content-method.md).
- For structured SERP input fields shared with SA work, read [references/serp-text-schema.md](references/serp-text-schema.md).
- For insurance compliance-safe copy and review flags, read [references/insurance-copy-guardrails.md](references/insurance-copy-guardrails.md).
- For linking Power Content to SA title, description, additional description, promotion, and sitelinks, read [references/sa-linkage-contract.md](references/sa-linkage-contract.md).
- For thumbnail, body image, or CTA banner briefs, read [references/image-brief-standard.md](references/image-brief-standard.md).
- For private admin review states, reason codes, and skill-quality feedback, read [references/review-feedback-loop.md](references/review-feedback-loop.md).
- For Korean non-life insurance advertising compliance checks, read [references/insurance-review-compliance.md](references/insurance-review-compliance.md).
- For Naver SA thumbnail-specific sizing, SERP visual analysis, and generation prompts, read the installed `sa-thumbnail-creative-director` skill.
- Before final delivery, read [references/quality-checklist.md](references/quality-checklist.md).

## Expected Package

For a full Power Content request, deliver:

1. Root-cause or opportunity diagnosis.
2. Three content directions with title, main keyword, 8-15 supporting keywords, search intent, SERP differentiation, cannibalization risk, recommendation status, and monthly rationale.
3. One final recommended concept with a concrete reader question, editorial structure, comparison logic, and official CTA.
4. A publishable Korean draft of at least 1,500 characters when the user asks for content, not just topics.
5. Image material briefs: one hero thumbnail, three body images, and one bottom CTA banner.
6. SA material linkage: title, description, additional description, promo, and sublink candidates.
7. Private review-lab fields: usable/unusable status, reason codes, and what the operator should check.
8. A final anti-AI-tell cleanup that preserves facts and compliance meaning.
9. A self-check that calls out remaining review risks and weak spots.

Keep the output practical enough for a search advertising or content review meeting.
