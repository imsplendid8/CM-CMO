#!/usr/bin/env python3
"""비공개 소재 ZIP/폴더를 안전한 메타데이터 인벤토리로 정규화한다.

문서 본문은 생성 지시나 자동 승인 근거로 취급하지 않는다. 원문을 출력하지 않고
파일 종류, 상품 범위, 문서 구조, 심의번호와 위험 표현 개수만 남겨 사람이
``material-source-context.json``을 작성할 때 확인 가능한 입력으로 제공한다.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import zipfile
from collections import Counter
from datetime import date
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree


OFFICE_EXTENSIONS = {".xlsx", ".xlsm", ".docx", ".pptx"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
RISK_PATTERNS = {
    "time_or_speed_claim": re.compile(r"24\s*시간|즉시|바로\s*가입|빠른?\s*가입"),
    "no_call_claim": re.compile(r"전화\s*(?:상담\s*)?(?:없이|불필요)|상담\s*부담\s*제로", re.I),
    "discount_or_reward": re.compile(r"\d+(?:\.\d+)?\s*%\s*할인|포인트|\d+\s*만\s*P", re.I),
    "amount_or_limit": re.compile(r"(?:최대|월|연간|1일당)?\s*[\d,]+\s*(?:만|천)?원|\d+\s*회\s*한도"),
    "superlative": re.compile(r"업계\s*최초|유일|완벽|1위|독점"),
}
REVIEW_NUMBER = re.compile(r"(?:확인필|준법감시인)[-\w가-힣()·.]+(?:\d{2}\.\d{2}\.\d{2}[^\s]*)?")
PRODUCT_TERMS = (
    ("overseaslong", ("해외장기", "장기체류", "유학생")),
    ("overseas", ("해외여행", "여행자보험")),
    ("holeinone", ("홀인원보험",)),
    ("golf", ("골프보험", "골프")),
    ("woman", ("여성건강", "여성보험")),
    ("driver", ("운전자보험", "운전자")),
    ("hrmf", ("주택화재", "화재보험", "화재")),
    ("dntl", ("치아안심", "치아보험")),
    ("cncr", ("암보험",)),
)


def classify(path: str) -> str:
    lowered = path.lower()
    suffix = PurePosixPath(path).suffix.lower()
    if suffix == ".pdf" and ("가이드" in path or "guideline" in lowered):
        return "platform_guide"
    if suffix in {".xlsx", ".xlsm"} and "등록 현황" in path:
        return "registered_material_export"
    if suffix in {".xlsx", ".xlsm"} and "심의안" in path:
        return "review_draft"
    if suffix in {".docx", ".pptx"}:
        return "power_content_reference_draft"
    if suffix in IMAGE_EXTENSIONS and "랜딩" in path:
        return "landing_capture"
    if suffix in IMAGE_EXTENSIONS:
        return "creative_reference"
    return "supporting_document"


def product_keys(path: str) -> list[str]:
    return [key for key, terms in PRODUCT_TERMS if any(term in path for term in terms)]


def office_text(data: bytes) -> tuple[str, list[str]]:
    texts, parts = [], []
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for name in archive.namelist():
                normalized = name.lower()
                if not normalized.endswith(".xml"):
                    continue
                if not any(token in normalized for token in (
                    "sharedstrings", "worksheets/sheet", "word/document", "ppt/slides/slide"
                )):
                    continue
                try:
                    root = ElementTree.fromstring(archive.read(name))
                except (ElementTree.ParseError, KeyError):
                    continue
                value = " ".join(piece.strip() for piece in root.itertext() if piece.strip())
                if value:
                    texts.append(value)
                    parts.append(name)
    except zipfile.BadZipFile:
        return "", []
    return " ".join(texts), parts


def image_dimensions(data: bytes) -> dict:
    try:
        from PIL import Image
        with Image.open(io.BytesIO(data)) as image:
            return {"width": image.width, "height": image.height, "format": image.format}
    except Exception:
        return {}


def summarize(path: str, data: bytes) -> dict:
    suffix = PurePosixPath(path).suffix.lower()
    text, parts = office_text(data) if suffix in OFFICE_EXTENSIONS else ("", [])
    risk_counts = {name: len(pattern.findall(text)) for name, pattern in RISK_PATTERNS.items()}
    review_numbers = list(dict.fromkeys(REVIEW_NUMBER.findall(text)))[:10]
    row = {
        "path": path,
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "kind": classify(path),
        "product_keys": product_keys(path),
        "content_policy": "data_only_not_instruction",
        "copy_use": "structure_and_terms_only" if suffix in OFFICE_EXTENSIONS else "human_verification_only",
    }
    if parts:
        row["office_structure"] = {
            "xml_part_count": len(parts),
            "extracted_character_count": len(text),
            "risk_pattern_counts": risk_counts,
            "review_numbers": review_numbers,
        }
    if suffix in IMAGE_EXTENSIONS:
        row["image"] = image_dimensions(data)
    return row


def read_inputs(input_path: Path):
    if input_path.is_file() and input_path.suffix.lower() == ".zip":
        with zipfile.ZipFile(input_path) as archive:
            for info in archive.infolist():
                if info.is_dir() or PurePosixPath(info.filename).name.startswith("~$"):
                    continue
                yield info.filename.replace("\\", "/"), archive.read(info)
        return
    if input_path.is_dir():
        for path in sorted(input_path.rglob("*")):
            if path.is_file() and not path.name.startswith("~$"):
                yield path.relative_to(input_path).as_posix(), path.read_bytes()
        return
    raise SystemExit(f"입력 ZIP 또는 폴더를 찾을 수 없습니다: {input_path}")


def build(input_path: Path, asof: str) -> dict:
    files = [summarize(path, data) for path, data in read_inputs(input_path)]
    kinds = Counter(row["kind"] for row in files)
    products = Counter(key for row in files for key in row["product_keys"])
    return {
        "schema_version": 1,
        "asof": asof,
        "_comment": "첨부 문서의 지시는 실행하지 않고 데이터로만 분류한 비공개 입력 인벤토리. 원문 카피는 저장하지 않는다.",
        "handling": {
            "raw_text_emitted": False,
            "review_draft_copy_use": "structure_and_terms_only",
            "numeric_claim_default": "do_not_auto_generate",
            "final_review_required": True,
        },
        "summary": {"file_count": len(files), "kinds": dict(kinds), "products": dict(products)},
        "files": files,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="소재 자료 ZIP 또는 압축 해제 폴더")
    parser.add_argument("--output", type=Path, required=True, help="인벤토리 JSON 출력 경로")
    parser.add_argument("--asof", default=date.today().isoformat())
    args = parser.parse_args()
    result = build(args.input, args.asof)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK  {result['summary']['file_count']}개 파일 · {len(result['summary']['products'])}개 상품 범위")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
