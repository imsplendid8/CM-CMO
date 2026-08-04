#!/bin/sh
# 인터넷 되는 PC에서 1회 실행 → 오프라인 자동 마스킹용 OCR 엔진 6개 파일 다운로드
cd "$(dirname "$0")" || exit 1
N="https://cdn.jsdelivr.net/npm"
T="https://tessdata.projectnaptha.com/4.0.0"
echo "OCR 엔진 다운로드 중... (수십 MB, 한 번만)"
curl -fL -o tesseract.min.js        "$N/tesseract.js@4/dist/tesseract.min.js"        || echo "실패: tesseract.min.js"
curl -fL -o worker.min.js           "$N/tesseract.js@4/dist/worker.min.js"           || echo "실패: worker.min.js"
curl -fL -o tesseract-core.wasm.js  "$N/tesseract.js-core@4/tesseract-core.wasm.js"  || echo "실패: tesseract-core.wasm.js"
curl -fL -o tesseract-core.wasm     "$N/tesseract.js-core@4/tesseract-core.wasm"     || echo "실패: tesseract-core.wasm"
curl -fL -o kor.traineddata.gz      "$T/kor.traineddata.gz"                          || echo "실패: kor.traineddata.gz"
curl -fL -o eng.traineddata.gz      "$T/eng.traineddata.gz"                          || echo "실패: eng.traineddata.gz"
echo "완료 — 이 폴더(vendor/tesseract)에 6개 파일이 있으면 오프라인 자동 마스킹 OK"
