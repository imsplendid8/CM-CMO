#!/bin/bash
# 손보 뉴스 실데이터 받기 (Mac) — 공개 뉴스에서 모아 newsdata.js 생성 (카카오 설정 불필요).
# 처음엔 파일 우클릭 → 열기 → 열기.
cd "$(dirname "$0")"
echo "============================================================"
echo " 손보 뉴스 실데이터 받기 (Mac) · 인터넷 필요"
echo "============================================================"
if ! command -v python3 >/dev/null 2>&1; then
  echo "[오류] python3 를 찾지 못했습니다. python.org 에서 설치 후 다시 실행하세요."
  read -n 1 -s; exit 1
fi
python3 news_watch.py --dry-run
echo ""
if [ -f newsdata.js ]; then
  echo "✅ 완료! newsdata.js 생성됨. monitor.html 을 열면 실데이터 뉴스가 보입니다."
else
  echo "[오류] newsdata.js 생성 실패 — 인터넷 연결 확인 후 다시 실행하세요."
fi
echo "(아무 키나 누르면 닫힙니다)"
read -n 1 -s
