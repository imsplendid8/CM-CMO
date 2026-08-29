# Insurance Advertising Review Compliance

Use this reference for Power Content and connected SA materials in Korean non-life insurance contexts. It adapts the repository's `insurance-ad-review` skill guide into this skill's workflow.

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

## Power Content-specific checks

- Article title, body, CTA, image brief, SA linkage, keyword target, and landing must describe the same product and sales channel.
- `다이렉트` can be used only when the direct-sales route and landing are verified.
- Do not assert guaranteed payment, unlimited coverage, eligibility, no review, fastest enrollment, lowest price, ranking, or superiority.
- Numbers, time, premium, comparison, refund, discount, gift, and benefit claims require source, date, scope, and display conditions.
- Do not hide limitations by placing attractive benefits in the headline and leaving exclusions only in a later vague checklist.
- Product terms and rider names must be connected to reader decisions, not used as loose advertising decoration.
- Revised copy must be checked again after editing.

## Output requirement

For each final concept or article package, include:

- status,
- risky expression if any,
- why it matters,
- safer rewrite or next check,
- required product material, landing, or review owner.
