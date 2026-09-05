#!/usr/bin/env python3
"""Claude API를 사용하여 SA 썸네일 자동 생성

SA(검색광고) 소재의 썸네일 이미지를 Claude API로 자동 생성한다.
- 검색 신호와 시즌 데이터 기반 콘텐츠 생성
- 팀원들의 수동 작업 최소화
- 자동화 완료된 소재는 adcopy-tool.html에 표시

사용법:
  python3 scripts/generate_sa_thumbnails.py [--limit 8] [--product driver] [--force]

환경 변수:
  ANTHROPIC_API_KEY - Claude API 키 (필수)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import anthropic
except ImportError:
    print("❌ anthropic 라이브러리가 필요합니다: pip install anthropic")
    sys.exit(1)

ROOT = Path(__file__).resolve().parents[1]
PRODUCTS_FILE = ROOT / "data" / "products.json"
ADCOPY_FILE = ROOT / "data" / "adcopy" / "material-generation-guide.json"
OUTPUT_DIR = ROOT / "data" / "adcopy"
THUMBNAILS_INDEX = OUTPUT_DIR / "thumbnail-index.json"


def load_products() -> dict[str, Any]:
    """상품 마스터 로드"""
    if not PRODUCTS_FILE.exists():
        print(f"⚠️ {PRODUCTS_FILE} 파일을 찾을 수 없습니다")
        return {}

    with open(PRODUCTS_FILE) as f:
        return json.load(f)


def load_adcopy_guide() -> dict[str, Any]:
    """광고소재 가이드 로드"""
    if not ADCOPY_FILE.exists():
        print(f"⚠️ {ADCOPY_FILE} 파일을 찾을 수 없습니다")
        return {}

    with open(ADCOPY_FILE) as f:
        return json.load(f)


def load_thumbnail_index() -> dict[str, Any]:
    """기존 썸네일 인덱스 로드"""
    if THUMBNAILS_INDEX.exists():
        with open(THUMBNAILS_INDEX) as f:
            return json.load(f)
    return {"generated": [], "failed": [], "updated_at": None}


def save_thumbnail_index(index: dict[str, Any]) -> None:
    """썸네일 인덱스 저장"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    index["updated_at"] = datetime.now().isoformat()

    with open(THUMBNAILS_INDEX, "w") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(f"✓ 썸네일 인덱스 저장: {THUMBNAILS_INDEX}")


def generate_thumbnail_with_claude(
    client: anthropic.Anthropic,
    product_key: str,
    product_name: str,
    material_guidance: dict[str, Any],
) -> dict[str, Any]:
    """Claude API를 사용한 SA 썸네일 생성

    Args:
        client: Anthropic API 클라이언트
        product_key: 상품 코드 (예: 'driver')
        product_name: 상품명
        material_guidance: 소재 가이드 데이터

    Returns:
        생성된 썸네일 메타데이터
    """
    system_prompt = """당신은 한화손해보험의 SA(검색광고) 크리에이티브 담당자입니다.

다음 지침을 따라 검색광고 썸네일 이미지 생성 프롬프트를 작성하세요:

1. 시각적 표현:
   - 상품의 핵심 가치를 한눈에 알 수 있도록 표현
   - 실제 고객 장면/감정을 담은 일상 시나리오
   - 한화손해보험의 클린한 SaaS 디자인 톤 (깔끔함, 신뢰성)

2. 색상 및 스타일:
   - 주색: 흰 배경, 검은색/진회색 텍스트
   - 강조색: 연한 분홍색(#ef7a9c) 또는 파란색(#2563eb)
   - 폰트: 깔끔한 고딕체 (Pretendard)
   - 레이아웃: 3:2 비율, 최소 로고/텍스트 추가

3. 마케팅 메시지:
   - 상품명과 핵심 가입 이유 포함
   - 긍정적이고 신뢰할 수 있는 톤
   - 불필요한 과장이나 위험 표현 제외

응답은 다음 JSON 형식으로 작성하세요:
{
  "prompt": "생성할 이미지의 영문 프롬프트",
  "title": "썸네일 제목",
  "description": "한국어 설명",
  "style": "생성 스타일 (예: 3D illustration, realistic photo)",
  "appeal": "시각적 핵심 메시지"
}
"""

    user_prompt = f"""상품: {product_name} ({product_key})

마케팅 핵심 포인트:
{json.dumps(material_guidance, ensure_ascii=False, indent=2)}

이 상품의 SA 썸네일 이미지 생성 프롬프트를 작성해주세요.
고객의 검색 의도와 상품의 가치를 시각적으로 표현하세요."""

    try:
        message = client.messages.create(
            model="claude-opus-5",
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        response_text = message.content[0].text
        result = json.loads(response_text)

        return {
            "product_key": product_key,
            "product_name": product_name,
            "generated_at": datetime.now().isoformat(),
            "status": "generated",
            "prompt": result.get("prompt"),
            "title": result.get("title"),
            "description": result.get("description"),
            "style": result.get("style"),
            "appeal": result.get("appeal"),
        }

    except (json.JSONDecodeError, KeyError, IndexError) as e:
        print(f"❌ {product_name} 생성 실패: {e}")
        return {
            "product_key": product_key,
            "product_name": product_name,
            "generated_at": datetime.now().isoformat(),
            "status": "failed",
            "error": str(e),
        }


def main() -> int:
    """메인 처리 함수"""
    parser = argparse.ArgumentParser(
        description="Claude API로 SA 썸네일 자동 생성"
    )
    parser.add_argument("--limit", type=int, default=8, help="생성할 최대 수 (기본: 8)")
    parser.add_argument("--product", default="", help="특정 상품만 생성 (예: driver)")
    parser.add_argument("--force", action="store_true", help="기존 이미지도 재생성")
    args = parser.parse_args()

    # API 키 확인
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY 환경 변수가 설정되지 않았습니다")
        return 1

    # 데이터 로드
    products = load_products()
    adcopy_guide = load_adcopy_guide()
    thumbnail_index = load_thumbnail_index()

    if not products:
        print("⚠️ 상품 데이터를 로드할 수 없습니다")
        return 1

    # 생성 대상 상품 선정
    target_products = []
    for product_key, product_info in products.items():
        # 필터링
        if args.product and product_key != args.product:
            continue

        # 이미 생성됨
        if not args.force and any(
            t.get("product_key") == product_key and t.get("status") == "generated"
            for t in thumbnail_index.get("generated", [])
        ):
            continue

        target_products.append((product_key, product_info["name"]))

    # 개수 제한
    target_products = target_products[: args.limit]

    if not target_products:
        print("⚠️ 생성할 상품이 없습니다")
        return 0

    print(f"🚀 {len(target_products)}개 상품의 SA 썸네일 생성 시작")
    print(f"   제한: {args.limit}, 강제 재생성: {args.force}")

    # Claude API 클라이언트 초기화
    client = anthropic.Anthropic(api_key=api_key)

    # 썸네일 생성
    generated = []
    failed = []

    for i, (product_key, product_name) in enumerate(target_products, 1):
        print(f"\n[{i}/{len(target_products)}] {product_name} ({product_key})...")

        # 해당 상품의 가이드 데이터 조회
        guidance = adcopy_guide.get(product_key, {})

        # 생성
        result = generate_thumbnail_with_claude(client, product_key, product_name, guidance)

        if result.get("status") == "generated":
            print(f"  ✓ 생성 완료")
            generated.append(result)
        else:
            print(f"  ✗ 생성 실패")
            failed.append(result)

    # 결과 저장
    thumbnail_index["generated"] = thumbnail_index.get("generated", []) + generated
    thumbnail_index["failed"] = thumbnail_index.get("failed", []) + failed

    save_thumbnail_index(thumbnail_index)

    # 요약 출력
    print(f"\n{'='*60}")
    print(f"✓ 생성 완료: {len(generated)}개")
    print(f"✗ 생성 실패: {len(failed)}개")
    print(f"{'='*60}")

    if generated:
        print("\n📊 생성된 썸네일:")
        for item in generated:
            print(f"  • {item['product_name']}: {item['title']}")

    if failed:
        print("\n⚠️ 실패한 항목:")
        for item in failed:
            print(f"  • {item['product_name']}: {item.get('error')}")

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
