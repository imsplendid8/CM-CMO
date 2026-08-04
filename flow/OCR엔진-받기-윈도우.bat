@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================================
echo  Modooflow 오프라인 OCR 엔진 받기 (윈도우)
echo  - 인터넷 되는 곳에서 "한 번만" 실행하세요.
echo  - 이후에는 인터넷 없이도 자동 마스킹(OCR)이 됩니다.
echo  - 받는 용량: 약 15~20MB
echo ============================================================
echo.

where curl >nul 2>nul || (
  echo [오류] curl 을 찾지 못했습니다. Windows 10 이상에서 실행하세요.
  pause & exit /b
)

if not exist "vendor\tesseract" mkdir "vendor\tesseract"
set "N=https://cdn.jsdelivr.net/npm"
set "T=https://tessdata.projectnaptha.com/4.0.0"

echo [1/6] tesseract.min.js ...
curl -fL -o "vendor\tesseract\tesseract.min.js"       "%N%/tesseract.js@4/dist/tesseract.min.js"        || goto err
echo [2/6] worker.min.js ...
curl -fL -o "vendor\tesseract\worker.min.js"          "%N%/tesseract.js@4/dist/worker.min.js"           || goto err
echo [3/6] tesseract-core.wasm.js ...
curl -fL -o "vendor\tesseract\tesseract-core.wasm.js" "%N%/tesseract.js-core@4/tesseract-core.wasm.js"  || goto err
echo [4/6] tesseract-core.wasm ...
curl -fL -o "vendor\tesseract\tesseract-core.wasm"    "%N%/tesseract.js-core@4/tesseract-core.wasm"     || goto err
echo [5/6] kor.traineddata.gz (한글) ...
curl -fL -o "vendor\tesseract\kor.traineddata.gz"     "%T%/kor.traineddata.gz"                          || goto err
echo [6/6] eng.traineddata.gz (영문) ...
curl -fL -o "vendor\tesseract\eng.traineddata.gz"     "%T%/eng.traineddata.gz"                          || goto err

echo.
echo ✅ 완료! vendor\tesseract 폴더에 6개 파일이 받아졌습니다.
echo    이제 인터넷 없이도 자동 마스킹(OCR)이 동작합니다.
echo.
pause
exit /b

:err
echo.
echo [오류] 다운로드 실패 — 인터넷 연결을 확인하고 다시 실행하세요.
echo.
pause
exit /b
