#!/usr/bin/env python3
"""보험 상품 근거 원장 검증·조회. 표준 라이브러리만 사용한다."""
import argparse
import copy
import json
import os
from datetime import datetime, timezone
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATH = ROOT / "data/evidence/claims.json"
CHANNELS = {"faq", "sa_title", "sa_description", "landing", "power_content"}
STATUSES = {"needs_product_review", "approved", "expired", "rejected"}


def load(path=DEFAULT_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate(data, product_keys):
    errors, seen = [], set()
    for i, claim in enumerate(data.get("claims") or []):
        prefix = f"claims[{i}]"
        cid = claim.get("claim_id")
        if not cid or cid in seen:
            errors.append(f"{prefix}: claim_id 누락 또는 중복")
        seen.add(cid)
        if claim.get("product_key") not in product_keys:
            errors.append(f"{prefix}: 알 수 없는 product_key")
        if claim.get("review_status") not in STATUSES:
            errors.append(f"{prefix}: 잘못된 review_status")
        channels = set(claim.get("allowed_channels") or [])
        if not channels <= CHANNELS:
            errors.append(f"{prefix}: 잘못된 allowed_channels")
        if claim.get("review_status") == "approved":
            source = claim.get("source") or {}
            if not source.get("path") or not claim.get("effective_from") or not channels or not claim.get("reviewer"):
                errors.append(f"{prefix}: approved claim은 출처·시작일·채널·검토자가 필수")
        for field in ("effective_from", "valid_until"):
            if claim.get(field):
                try:
                    date.fromisoformat(claim[field])
                except (TypeError, ValueError):
                    errors.append(f"{prefix}: {field}는 YYYY-MM-DD 형식이어야 함")
        if claim.get("effective_from") and claim.get("valid_until"):
            try:
                if date.fromisoformat(claim["valid_until"]) < date.fromisoformat(claim["effective_from"]):
                    errors.append(f"{prefix}: valid_until이 effective_from보다 빠름")
            except (TypeError, ValueError):
                pass
    return errors


def active_claims(data, product_key, channel, today=None):
    today = today or date.today()
    out = []
    for c in data.get("claims") or []:
        if c.get("product_key") != product_key or c.get("review_status") != "approved":
            continue
        if channel not in (c.get("allowed_channels") or []):
            continue
        start, end = c.get("effective_from"), c.get("valid_until")
        if start and date.fromisoformat(start) > today:
            continue
        if end and date.fromisoformat(end) < today:
            continue
        out.append(c)
    return out


def review_claim(data, claim_id, action, reviewer, **values):
    """검토 이력을 보존한 새 dict를 반환한다. 입력 data는 변경하지 않는다."""
    if not str(reviewer or "").strip():
        raise ValueError("실제 검토자 --reviewer가 필요합니다")
    updated = copy.deepcopy(data)
    claim = next((c for c in updated.get("claims", []) if c.get("claim_id") == claim_id), None)
    if not claim:
        raise ValueError("claim_id를 찾을 수 없습니다")
    now = datetime.now(timezone.utc).isoformat()
    history = claim.setdefault("review_history", [])
    history.append({"from_status": claim.get("review_status"), "action": action,
                    "reviewer": reviewer.strip(), "reviewed_at": now, "reason": values.get("reason") or None})
    if action == "approve":
        channels = values.get("channels") or []
        if not values.get("source_path") or not values.get("effective_from") or not channels:
            raise ValueError("승인에는 --source-path, --effective-from, --channels가 필요합니다")
        claim.update(review_status="approved", reviewer=reviewer.strip(), effective_from=values["effective_from"],
                     valid_until=values.get("valid_until"), allowed_channels=channels,
                     required_disclosure=values.get("disclosure") or claim.get("required_disclosure") or "")
        claim.setdefault("source", {})["path"] = values["source_path"]
        claim.pop("rejection_reason", None)
    elif action == "reject":
        if not values.get("reason"):
            raise ValueError("반려에는 --reason이 필요합니다")
        claim.update(review_status="rejected", reviewer=reviewer.strip(), rejection_reason=values["reason"], allowed_channels=[])
    else:
        raise ValueError("지원하지 않는 검토 action")
    claim["reviewed_at"] = now
    updated["updated"] = now[:10]
    return updated


def atomic_write(path, data):
    path = Path(path); temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("validate", "list", "approve", "reject"), nargs="?", default="validate")
    parser.add_argument("--product")
    parser.add_argument("--channel", choices=sorted(CHANNELS), default="faq")
    parser.add_argument("--claim-id")
    parser.add_argument("--reviewer")
    parser.add_argument("--source-path")
    parser.add_argument("--effective-from")
    parser.add_argument("--valid-until")
    parser.add_argument("--channels", help="쉼표 구분 허용 채널")
    parser.add_argument("--reason")
    parser.add_argument("--disclosure")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    products = load(ROOT / "data/products.json")
    data = load()
    changed = args.command in {"approve", "reject"}
    if changed:
        try:
            data = review_claim(data, args.claim_id, args.command, args.reviewer,
                source_path=args.source_path, effective_from=args.effective_from, valid_until=args.valid_until,
                channels=[x.strip() for x in (args.channels or "").split(",") if x.strip()],
                reason=args.reason, disclosure=args.disclosure)
        except ValueError as exc:
            raise SystemExit(str(exc))
    errors = validate(data, {p["key"] for p in products["products"]})
    if errors:
        raise SystemExit("\n".join("✘ " + e for e in errors))
    if changed and not args.dry_run:
        atomic_write(DEFAULT_PATH, data)
    if args.command == "list":
        print(json.dumps(active_claims(data, args.product, args.channel), ensure_ascii=False, indent=2))
    else:
        print(f"✔ 상품 근거 원장 · {len(data.get('claims') or [])}건 · 승인 근거 {sum(c.get('review_status') == 'approved' for c in data.get('claims') or [])}건")

if __name__ == "__main__":
    main()
