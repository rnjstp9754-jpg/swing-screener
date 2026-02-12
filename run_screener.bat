@echo off
setlocal

:: UTF-8 인코딩 설정
chcp 65001 > nul

cd /d "%~dp0"

echo [START] 주식 스크리너 실행 중...
echo %DATE% %TIME%

:: 가상환경 활성화 (있다면)
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

:: 스크리너 실행
python full_screener.py

if %ERRORLEVEL% EQU 0 (
    echo [SUCCESS] 스크리닝 완료
) else (
    echo [ERROR] 스크리닝 실패 (에러코드: %ERRORLEVEL%)
    pause
    exit /b %ERRORLEVEL%
)

:: 5초 대기 후 종료
timeout /t 5 > nul
endlocal
