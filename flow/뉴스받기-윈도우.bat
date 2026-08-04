@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================================
echo  손보 뉴스 실데이터 받기 (윈도우)
echo  - 공개 뉴스(Google News)에서 손해보험 가입/개편 기사를 모아
echo    newsdata.js 를 만듭니다. (카카오 설정 없이 동작)
echo  - 인터넷 필요. monitor.html 옆에 newsdata.js 가 생깁니다.
echo ============================================================
echo.

set "PY="
where python >nul 2>nul && set "PY=python"
if not defined PY ( where py >nul 2>nul && set "PY=py" )
if not defined PY (
  echo [오류] 파이썬을 찾지 못했습니다. python.org 에서 설치(Add to PATH 체크) 후 다시 실행하세요.
  pause & exit /b
)

%PY% news_watch.py --dry-run
echo.
if exist "newsdata.js" (
  echo ✅ 완료! newsdata.js 생성됨. 이제 monitor.html 을 열면 실데이터 뉴스가 보입니다.
) else (
  echo [오류] newsdata.js 가 만들어지지 않았습니다. 인터넷 연결을 확인하고 다시 실행하세요.
)
echo.
pause
