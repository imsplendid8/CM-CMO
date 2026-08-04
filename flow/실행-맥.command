#!/bin/bash
# Modooflow 로컬 실행 (Mac) — 더블클릭하면 서버가 켜지고 브라우저가 열립니다.
# 처음 더블클릭 시 "확인되지 않은 개발자" 경고가 뜨면: 파일 우클릭 → 열기 → 열기.
cd "$(dirname "$0")"
echo "============================================================"
echo " Modooflow 로컬 실행 (Mac)"
echo " - 이 창은 서버입니다. 테스트하는 동안 켜두세요."
echo " - 끝내려면 이 창에서 Ctrl+C 또는 창을 닫으세요."
echo "============================================================"

if ! command -v python3 >/dev/null 2>&1; then
  echo "[오류] python3 를 찾지 못했습니다. python.org 에서 설치 후 다시 실행하세요."
  read -n 1 -s
  exit 1
fi

# 서버가 준비된 뒤(2초) 브라우저 두 탭 열기
( sleep 2; open "http://localhost:8000/mask-tool.html"; open "http://localhost:8000/index.html" ) &

# 파이썬3 간단 서버 실행 (이 창을 닫으면 서버도 종료)
python3 -m http.server 8000
