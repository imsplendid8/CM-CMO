#!/bin/bash
# Modooflow 오프라인 OCR 엔진 받기 (Mac) — 인터넷 되는 곳에서 한 번만 실행.
# 처음엔 파일 우클릭 → 열기 → 열기.
cd "$(dirname "$0")"
echo "============================================================"
echo " Modooflow 오프라인 OCR 엔진 받기 (Mac)"
echo " - 인터넷 되는 곳에서 한 번만 실행하세요 (약 15~20MB)"
echo "============================================================"

mkdir -p vendor/tesseract
N="https://cdn.jsdelivr.net/npm"
T="https://tessdata.projectnaptha.com/4.0.0"

curl -fL -o vendor/tesseract/tesseract.min.js       "$N/tesseract.js@4/dist/tesseract.min.js"       && \
curl -fL -o vendor/tesseract/worker.min.js          "$N/tesseract.js@4/dist/worker.min.js"          && \
curl -fL -o vendor/tesseract/tesseract-core.wasm.js "$N/tesseract.js-core@4/tesseract-core.wasm.js" && \
curl -fL -o vendor/tesseract/tesseract-core.wasm    "$N/tesseract.js-core@4/tesseract-core.wasm"    && \
curl -fL -o vendor/tesseract/kor.traineddata.gz     "$T/kor.traineddata.gz"                         && \
curl -fL -o vendor/tesseract/eng.traineddata.gz     "$T/eng.traineddata.gz"                         && \
echo "" && echo "✅ 완료! 이제 인터넷 없이도 자동 마스킹(OCR)이 됩니다." \
|| echo "[오류] 다운로드 실패 — 인터넷 연결 확인 후 다시 실행하세요."

echo "(아무 키나 누르면 닫힙니다)"
read -n 1 -s
