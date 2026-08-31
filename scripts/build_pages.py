#!/usr/bin/env python3
"""GitHub Pages에 필요한 공개 파일만 별도 디렉터리로 구성한다."""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "dist"

PUBLIC_DATA = (
    "data/signals.json",
    "data/volume.json",
    "data/volume-history.json",
    "data/keyword-autocomplete.json",
    "data/seasonal.json",
    "data/trends.json",
    "data/briefing/latest.json",
    "data/adcopy/serp-candidates.json",
    "data/adcopy/image-generation-queue.json",
    "data/adcopy/material-feedback-rules.json",
    "data/seo/site-observations.json",
    "data/events/recommendations.json",
    "data/seo/faq-opportunities.json",
    "data/adcopy/powercontent-title-opportunities.json",
    "data/adcopy/powercontent-history.json",
)
PUBLIC_SERP_JSON = (
    "serp/manifest.json",
    "serp/ad_analysis.json",
    "serp/ad_observations.json",
    "serp/brand/manifest.json",
)
# 최초 배포본처럼 월간 생성 큐가 아직 없는 커밋도 Pages를 배포할 수 있게 한다.
# 큐가 생성되면 일반 공개 데이터와 동일하게 dist/data에 포함된다.
OPTIONAL_PUBLIC_DATA = {"data/adcopy/image-generation-queue.json"}
FORBIDDEN_PARTS = {".github", "scripts", "docs", "handoff", "evidence"}
FORBIDDEN_NAMES = {"search-console.json", "search-console.example.json", "copy_history.json", "state_history.json"}


def copy_file(root: Path, destination: Path, relative: str | Path) -> None:
    source = root / relative
    if not source.exists():
        raise FileNotFoundError(f"공개 사이트 필수 파일 누락: {relative}")
    target = destination / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def build(root: Path = ROOT, destination: Path = DEST) -> list[Path]:
    resolved_root = root.resolve()
    resolved_destination = destination.resolve()
    if resolved_destination == resolved_root or resolved_destination.name not in {"dist", "site", "_site"}:
        raise ValueError(f"공개 빌드 삭제 대상이 안전한 산출물 경로가 아님: {resolved_destination}")
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)

    for source in root.glob("*.html"):
        copy_file(root, destination, source.relative_to(root))
    copy_file(root, destination, "site.webmanifest")
    for folder in ("shared", "icons", "fonts"):
        shutil.copytree(root / folder, destination / folder, dirs_exist_ok=True)
    shutil.copytree(root / "assets/insurance", destination / "assets/insurance", dirs_exist_ok=True)
    for relative in (*PUBLIC_DATA, *PUBLIC_SERP_JSON):
        if relative in OPTIONAL_PUBLIC_DATA and not (root / relative).exists():
            continue
        copy_file(root, destination, relative)
    for source in (root / "data/clips").glob("*.json"):
        copy_file(root, destination, source.relative_to(root))
    for source in (root / "serp").glob("*.png"):
        copy_file(root, destination, source.relative_to(root))
    for source in (root / "serp/brand").glob("*.png"):
        copy_file(root, destination, source.relative_to(root))

    files = [path for path in destination.rglob("*") if path.is_file()]
    for path in files:
        relative = path.relative_to(destination)
        if FORBIDDEN_PARTS.intersection(relative.parts) or relative.name in FORBIDDEN_NAMES:
            raise ValueError(f"비공개 파일이 Pages 산출물에 포함됨: {relative}")
    return files


def main() -> int:
    files = build()
    print(f"[OK] Pages 공개 산출물 {len(files)}개 → {DEST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
