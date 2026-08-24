#!/usr/bin/env python3
"""GitHub Pages에 필요한 공개 파일만 별도 디렉터리로 구성한다."""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "_site"

PUBLIC_DATA = (
    "data/signals.json",
    "data/volume.json",
    "data/volume-history.json",
    "data/seasonal.json",
    "data/trends.json",
    "data/briefing/latest.json",
    "data/adcopy/serp-candidates.json",
    "data/events/recommendations.json",
    "data/seo/faq-opportunities.json",
    "data/adcopy/powercontent-title-opportunities.json",
)
PUBLIC_SERP_JSON = (
    "serp/manifest.json",
    "serp/ad_analysis.json",
    "serp/ad_observations.json",
    "serp/brand/manifest.json",
)
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
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)

    for source in root.glob("*.html"):
        copy_file(root, destination, source.relative_to(root))
    copy_file(root, destination, "site.webmanifest")
    for folder in ("shared", "icons"):
        shutil.copytree(root / folder, destination / folder)
    for relative in (*PUBLIC_DATA, *PUBLIC_SERP_JSON):
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
