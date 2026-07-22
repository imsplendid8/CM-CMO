#!/usr/bin/env bash
# 경로 B 원클릭 실행: 네이버(+구글) 실검색량 조회 → volume.json 생성
#   사용: bash scripts/run_keywords.sh [시드1 시드2 ...]   (생략 시 담당 10상품 시드)
set -uo pipefail
cd "$(dirname "$0")/.."

# .env 로드 (네이버 키)
if [ -f scripts/.env ]; then set -a; . scripts/.env; set +a; fi

if [ "$#" -gt 0 ]; then SEEDS=("$@"); else
  SEEDS=(암보험 운전자보험 치아보험 주택화재보험 골프보험 여성건강보험 태아보험 해외여행보험 해외장기체류보험 한화손보다이렉트)
fi

echo "▶ 네이버 검색광고 조회 (${#SEEDS[@]} 시드)..." >&2
if python3 scripts/naver_searchad_keywords.py "${SEEDS[@]}" > volume_naver.json 2>/dev/null; then
  echo "  ✔ volume_naver.json" >&2
else
  echo "  ✖ 네이버 실패 — scripts/.env 의 키 3개 확인" >&2
fi

if [ -f google-ads.yaml ]; then
  echo "▶ 구글 Keyword Planner 조회..." >&2
  python3 scripts/google_ads_keywords.py "${SEEDS[@]}" > volume_google.json 2>/dev/null \
    && echo "  ✔ volume_google.json" >&2 || echo "  ✖ 구글 실패 — google-ads.yaml 확인" >&2
fi

echo "▶ 병합..." >&2
python3 scripts/merge_volume.py volume_naver.json $( [ -f volume_google.json ] && echo volume_google.json ) > volume.json \
  && echo "✔ 완료: volume.json → 키워드 도구 '검색량 불러오기'에 붙여넣으세요" >&2
