#!/usr/bin/env bash
# 사내/로컬 BSA 운영 파이프라인 (매일 cron 권장). 키는 환경변수로만.
#   ⚠️ 이 저장소는 public이라 GitHub Actions에서 돌리지 말 것(캠페인명·계약이 공개 로그/산출물에 노출).
#   반드시 사내 PC/서버에서 실행. 산출 CSV는 .gitignore로 커밋되지 않음.
#
# 사용:
#   export NAVER_SEARCHAD_API_KEY=... NAVER_SEARCHAD_SECRET_KEY=... NAVER_SEARCHAD_CUSTOMER_ID=...
#   (선택) export KAKAO_ACCESS_TOKEN=...   # on/off 변경 시 카카오 '나에게' 알림
#   ./run_bsa.sh
set -euo pipefail
cd "$(dirname "$0")"

: "${NAVER_SEARCHAD_API_KEY:?NAVER_SEARCHAD_API_KEY 환경변수를 설정하세요}"
: "${NAVER_SEARCHAD_SECRET_KEY:?NAVER_SEARCHAD_SECRET_KEY 환경변수를 설정하세요}"
: "${NAVER_SEARCHAD_CUSTOMER_ID:?NAVER_SEARCHAD_CUSTOMER_ID 환경변수를 설정하세요}"

echo "=== [1/4] BSA on/off 모니터 ==="
python3 bsa_onoff_monitor.py --notify

if [ -f bsa_contracts.csv ]; then
  echo "=== [2/4] 계약 D-day 검수 ==="
  python3 bsa_contract_review.py
  echo "=== [3/4] 브랜드검색 키워드 제안 ==="
  python3 bsa_keyword_suggest.py
  echo "=== [4/4] 검색량 우선순위 ==="
  python3 bsa_volume_priority.py
else
  echo "※ bsa_contracts.csv 없음 — 계약 원장을 준비하면(2~4) 계약검수·키워드·우선순위가 실행됩니다."
  echo "   cp bsa_contracts_sample.csv bsa_contracts.csv  # 후 실제 값으로 채우기"
fi
echo "=== 완료: $(date '+%F %H:%M') · 산출 CSV는 이 폴더에 생성(커밋 안 됨) ==="
