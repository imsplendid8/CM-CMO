@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================================
echo  Modooflow 로컬 실행 (윈도우)
echo ============================================================
echo.

REM 파이썬 명령 자동 탐지 (python 또는 py)
set "PY="
where python >nul 2>nul && set "PY=python"
if not defined PY ( where py >nul 2>nul && set "PY=py" )

if not defined PY (
  echo [오류] 파이썬을 찾지 못했습니다.
  echo  python.org 에서 파이썬을 설치할 때 "Add Python to PATH" 를 꼭 체크하세요.
  echo.
  pause
  exit /b
)

REM 1) 서버를 별도 창에서 먼저 띄움 (이 창은 계속 켜둬야 함)
start "Modooflow 서버 (닫지 마세요)" cmd /k "%PY% -m http.server 8000"

REM 2) 서버가 준비될 때까지 약 2초 대기
ping -n 3 127.0.0.1 >nul

REM 3) 브라우저 두 탭 열기
start "" "http://localhost:8000/mask-tool.html"
start "" "http://localhost:8000/index.html"

echo 브라우저가 곧 열립니다.
echo 안 열리면, 브라우저 주소창에 아래를 직접 입력하세요:
echo   http://localhost:8000/mask-tool.html   (관리자 - 캡쳐/마스킹/기록)
echo   http://localhost:8000/index.html        (대시보드 - 결과 보기)
echo.
echo 이 창은 닫아도 됩니다. 서버는 "Modooflow 서버" 라는 다른 검은 창에서 계속 돌아갑니다.
echo 테스트를 끝내려면 그 "Modooflow 서버" 창을 닫으세요.
echo.
pause
