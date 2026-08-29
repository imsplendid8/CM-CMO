---
name: sa-thumbnail-creative-director
description: Create or review text-free premium 3D animation thumbnail briefs and prompts for Hanwha General Insurance CM Naver search ads, using Naver image material guides, structured SERP competitor analysis, product-fit scenes, and monthly variation.
metadata:
  short-description: Hanwha CM SA thumbnail creative director
---

# SA Thumbnail Creative Director

Use this skill when creating, improving, or reviewing image thumbnail concepts for Hanwha General Insurance CM Naver search ads, including Powerlink images, image-type sitelinks, Power Content thumbnails, and connected monthly image packs.

The job is not to make a decorative image. The job is to turn the same monthly SERP and product strategy used by SA copy and Power Content into a text-free image concept that is useful at small search-ad sizes.

## Non-Negotiables

- Default to text-free premium 3D animation unless the user explicitly requests another style.
- Do not generate photorealistic images when the user asks for animation-style thumbnails.
- Do not put text, numbers, logos, badges, UI labels, claim amounts, or brand marks inside the image.
- Do not reuse the same character, pose, object, background, and composition across multiple monthly slots.
- Do not borrow product-irrelevant reference assets just to fill four slots.
- Treat SERP screenshots as visual references only. Main analysis should come from structured SERP text or explicitly labeled visual observations.
- Keep thumbnail concepts tied to the same monthly message axis as SA copy and Power Content.
- Apply the private review-lab feedback loop when prior operator decisions exist. Approved image directions are style references, rejected outputs become avoid patterns with reason codes, and neither overrides current Naver guide or insurance review.
- Use the insurance-ad-review compliance vocabulary when image concepts imply product claims: `자동 차단`, `근거 필요`, `필수 고지 필요`, `사람 심의 필요`, or `자동 위험표현 없음`. Never call an automated check `심의 통과`.
- Check current Naver image material guidance when upload-ready specs matter; otherwise label size assumptions.

## First Move

Before writing image prompts, diagnose:

- Which Naver image material type is in scope?
- What is the selected month and product?
- What SERP competitor visual pattern is already saturated?
- Which product-specific scene would communicate the search intent without text?
- Which SA or Power Content message axis should the image support?
- Which prior thumbnails must be varied or avoided?
- Are there industry restrictions or current guide changes for the target image type?
- What did the private review lab previously approve, reject, or mark as unusable for this product/month/image type, and why?

## References

Read only the references needed for the current task:

- For Naver image material type and size handling, read [references/naver-image-guide.md](references/naver-image-guide.md).
- For SERP competitor visual analysis, read [references/serp-visual-analysis.md](references/serp-visual-analysis.md).
- For product-specific scene selection and avoid rules, read [references/insurance-scene-library.md](references/insurance-scene-library.md).
- For prompt structure, read [references/prompt-template.md](references/prompt-template.md).
- For monthly variation and duplicate control, read [references/monthly-variation.md](references/monthly-variation.md).
- For private admin review states, reason codes, and skill-quality feedback, read [references/review-feedback-loop.md](references/review-feedback-loop.md).
- For Korean non-life insurance advertising compliance checks, read [references/insurance-review-compliance.md](references/insurance-review-compliance.md).
- Before final delivery, read [references/quality-checklist.md](references/quality-checklist.md).

## Expected Output

For a full thumbnail request, deliver:

1. Thumbnail strategy diagnosis.
2. Naver guide basis and assumptions.
3. SERP competitor visual findings.
4. Product-fit image set: usually one representative image plus three supporting variants, or the exact slots requested.
5. Prompt for each image.
6. Negative prompt or avoid list for each image.
7. Monthly variation notes against previous assets.
8. Private review-lab fields: usable/unusable status, reason codes, and what the operator should check.
9. Review checklist.

If the user asks to generate the actual bitmap, use the `imagegen` skill/tool after the prompt plan is clear. Save project-bound final assets into the workspace and do not overwrite existing approved assets unless explicitly requested.
