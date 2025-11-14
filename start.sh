#!/bin/bash

# Masterpiece Photobooth 실행 스크립트 (macOS/Linux)

echo "🎬 Masterpiece Photobooth 시작 중..."

# Node 모듈 설치 확인
if [ ! -d "node_modules" ]; then
    echo "📦 Node 모듈 설치 중..."
    npm install
fi

# 서버와 Electron 앱 동시 실행
echo "🚀 앱 실행 중..."
npm run app
