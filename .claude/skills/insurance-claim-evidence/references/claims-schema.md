# Claim schema

필수 키: `claim_id`, `product_key`, `claim_type`, `claim`, `source`, `review_status`, `allowed_channels`.

승인 상태는 출처 경로, 효력 시작일, 허용 채널, 실제 검토자가 모두 있어야 한다. 허용 채널은 `faq`, `sa_title`, `sa_description`, `landing`, `power_content` 중에서 선택한다. 초깃값은 `needs_product_review`이며 자동 생성물이 이를 `approved`로 바꾸면 안 된다.

수정·재승인·반려 시 `review_history[{from_status, action, reviewer, reviewed_at, reason}]`를 보존한다. 날짜는 `YYYY-MM-DD`이며 만료일은 시작일보다 빠를 수 없다. 자동화는 후보 문장과 의미상 관련된 승인 claim ID만 연결해야 하며, 같은 상품의 다른 claim이 있다는 이유만으로 후보를 검증 상태로 바꾸면 안 된다.
