@echo off
chcp 65001 >nul
echo ==========================================
echo 스윙매매 테스터 - 빠른 시작
echo ==========================================
echo.

REM Python 확인
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python이 설치되어 있지 않습니다.
    echo https://www.python.org/downloads/ 에서 Python을 설치하세요.
    pause
    exit /b 1
)

echo [1/3] 필수 패키지 설치 중...
pip install -r requirements.txt

echo.
echo [2/3] 설정 파일 생성 중...
if not exist config\config.yaml (
    copy config\config.yaml.example config\config.yaml
    echo ✓ config.yaml 생성 완료
) else (
    echo ✓ config.yaml 이미 존재
)

echo.
echo [3/3] output 폴더 생성 중...
if not exist output mkdir output
if not exist output\charts mkdir output\charts
if not exist output\reports mkdir output\reports
echo ✓ 폴더 생성 완료

echo.
echo ==========================================
echo ✅ 설정 완료!
echo ==========================================
echo.
echo 다음 명령어로 백테스트를 실행하세요:
echo   python run_backtest.py --help
echo.
pause
