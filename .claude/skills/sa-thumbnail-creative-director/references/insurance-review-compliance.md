# Insurance Advertising Review Compliance

Use this reference for SA thumbnails, Powerlink images, image-type sitelinks, Power Content thumbnails, body images, and CTA banners in Korean non-life insurance contexts. It adapts the repository's `insurance-ad-review` skill guide into this skill's workflow.

## Basis and limits

Use the following hierarchy as the working basis:

1. 금융소비자보호법 제22조.
2. 금융소비자보호법 시행령 제18조~제20조.
3. 금융소비자 보호에 관한 감독규정 제17조~제19조.
4. 손해보험협회 광고심의 운영 기준 and company compliance standards.
5. The latest product disclosure documents, policy terms, sales channel, and landing page.

Automated review is only a conservative pre-check. It is not 손해보험협회 approval, 준법감시인 approval, or 심의필.

## Required status language

Use only these statuses:

- `자동 차단`: exclude from draft generation.
- `근거 필요`: objective evidence or product source is needed before use.
- `필수 고지 필요`: renewal, refund, limitation, exclusion, deductible, or condition must be paired with the claim.
- `사람 심의 필요`: product terms, landing, channel, layout, or medium exception needs human judgment.
- `자동 위험표현 없음`: no automated risk was found; this is not approval.

## Image-specific checks

- Image concept, search keyword, product, copy, and landing must match.
- Do not visually imply guaranteed payout, unlimited protection, no review, lowest price, or superior benefits.
- Avoid fear-based accident sensationalism. Risk scenes can be concrete but should not exploit shock.
- Do not include text, numbers, logos, badges, claim amounts, or official-looking certificates inside generated images unless the user and current guide explicitly require it.
- If a visual claim depends on a rider, limitation, payout condition, or exclusion, mark `사람 심의 필요`.
- Revised prompts and regenerated images must be checked again.

## Output requirement

For each final image brief or prompt, include:

- status,
- risky visual implication if any,
- why it matters,
- safer visual direction or next check,
- required product material, landing, Naver guide, or review owner.
