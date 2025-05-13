@echo off
chcp 65001 > nul

echo 포토부스 서버 시작 중...

REM Node.js 버전 확인
node -v > nul 2>&1
if errorlevel 1 (
    echo Node.js가 설치되어 있지 않습니다.
    echo https://nodejs.org/ko/ 에서 Node.js를 설치해주세요.
    pause
    exit /b 1
)

REM 필요한 모듈 설치 확인
echo 필요한 모듈 설치 확인 중...
call npm install ngrok express path fs crypto qrcode chokidar

REM 사용자 설정 - 필요시 여기 값을 변경하세요
REM 관리자 비밀번호 설정 (기본값: photobooth)
set ADMIN_PASSWORD=photobooth

REM ngrok 설정 - 사용하려면 여기에 토큰과 도메인을 추가하세요
REM 1. ngrok.com에서 계정 생성 후 인증 토큰 발급
REM 2. 유료 계정의 경우 고정 도메인 설정 가능
set NGROK_AUTH_TOKEN=
set NGROK_DOMAIN=

REM 기존 ngrok 프로세스 종료
taskkill /F /IM ngrok.exe > nul 2>&1

REM ngrok 로그 파일 초기화
echo. > ngrok.log

REM Ngrok 실행 (백그라운드에서)
echo Ngrok 시작 중...
if defined NGROK_AUTH_TOKEN (
    if defined NGROK_DOMAIN (
        echo 고정 도메인으로 ngrok 시작...
        start /b ngrok http 3000 --authtoken %NGROK_AUTH_TOKEN% --domain %NGROK_DOMAIN% --log=stdout > ngrok.log
    ) else (
        echo 임시 URL로 ngrok 시작...
        start /b ngrok http 3000 --authtoken %NGROK_AUTH_TOKEN% --log=stdout > ngrok.log
    )
    REM 10초 대기 (Ngrok이 시작되어 URL이 생성될 때까지)
    echo Ngrok 초기화 대기 중...
    timeout /t 10 /nobreak
    
    REM Ngrok URL 가져오기 (log 파일에서)
    for /f "tokens=*" %%a in ('findstr /C:"url=" ngrok.log') do (
        set NGROK_URL=%%a
    )
    
    set NGROK_URL=%NGROK_URL:*url=https:%
    for /f "delims=> tokens=1" %%a in ("%NGROK_URL%") do set NGROK_URL=%%a
    
    echo Ngrok URL: %NGROK_URL%
) else (
    echo Ngrok 토큰이 설정되지 않았습니다. 로컬 접속만 가능합니다.
    set NGROK_URL=http://localhost:3000
)

echo.
echo =============================================
echo 보안 정보 (외부 접속용)
echo - 관리자 페이지: %NGROK_URL%/admin
echo - 관리자 비밀번호: %ADMIN_PASSWORD%
echo =============================================
echo.

REM 서버 시작 (외부 URL 설정)
set EXTERNAL_URL=%NGROK_URL%
start %NGROK_URL%/admin?auth=%ADMIN_PASSWORD%

REM Node.js 서버 시작
echo Node.js 서버 시작 중...
start /b node server.js

REM 5초 대기 (서버가 시작될 때까지)
timeout /t 5 /nobreak

REM Python 스크립트 시작
echo 포토부스 시작 중...
start /b python photo.py

echo 모든 서비스가 시작되었습니다.
echo 문제가 발생하면 로그를 확인하세요.
pause 