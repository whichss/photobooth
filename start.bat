@echo off
REM Masterpiece Photobooth 실행 스크립트 (Windows)

echo 🎬 Masterpiece Photobooth 시작 중...

REM Node 모듈 설치 확인
if not exist node_modules (
    echo 📦 Node 모듈 설치 중...
    call npm install
)

REM 서버와 Electron 앱 동시 실행
echo 🚀 앱 실행 중...
call npm run app
