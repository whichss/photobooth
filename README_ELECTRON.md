# 🎬 Masterpiece Photobooth - Electron App

웹 기반 포토부스 애플리케이션입니다. 깔끔한 디자인과 사용하기 쉬운 인터페이스를 제공합니다.

## ✨ 주요 기능

- 📸 **실시간 카메라 프리뷰** - 웹캠을 통한 라이브 뷰
- ⏱️ **자동/수동 카운트다운** - 30초 자동 또는 버튼 클릭으로 5초 카운트다운
- 🎨 **깔끔한 UI** - Tailwind CSS 기반의 모던한 디자인
- 💾 **자동 저장** - 촬영한 사진 자동 저장
- 📱 **반응형** - 다양한 화면 크기 지원

## 🚀 실행 방법

### 1. 의존성 설치

```bash
npm install
```

### 2. 앱 실행

**macOS/Linux:**
```bash
./start.sh
```

또는

```bash
npm run app
```

**Windows:**
```
start.bat
```

또는

```
npm run app
```

## 📦 스크립트 명령어

- `npm run start` - Express 서버만 실행
- `npm run electron` - Electron 앱만 실행
- `npm run app` - 서버 + Electron 동시 실행 ⭐ **추천**
- `npm run build` - 배포용 앱 빌드

## 🎮 사용 방법

1. 앱 실행 시 자동으로 촬영 화면이 열립니다
2. 카메라가 자동으로 켜집니다 (권한 허용 필요)
3. 30초 카운트다운이 자동으로 시작됩니다
4. 또는 "촬영하기" 버튼을 클릭하면 5초 카운트다운 시작
5. 촬영된 사진은 `/photos` 폴더에 자동 저장됩니다

## ⚙️ 설정

### 키오스크 모드 (전체화면 고정)

`electron.js` 파일에서:

```javascript
kiosk: true  // 키오스크 모드 활성화
```

### 개발자 도구 열기

`electron.js` 파일에서 주석 해제:

```javascript
mainWindow.webContents.openDevTools();
```

### 촬영 매수 변경

`templates/capture.html` 파일에서:

```javascript
let remainingPhotos = 6;  // 원하는 숫자로 변경
let totalPhotos = 6;      // 동일하게 변경
```

## 🗂️ 폴더 구조

```
photobooth-main/
├── electron.js           # Electron 메인 프로세스
├── server.js            # Express 서버
├── templates/           # HTML 템플릿
│   ├── capture.html    # 촬영 화면 ⭐
│   ├── index.html      # 홈 화면
│   ├── admin.html      # 관리자 화면
│   └── promo.html      # 갤러리 화면
├── photos/             # 촬영된 사진 저장
├── output/             # 최종 결과물
└── static/             # 정적 파일 (CSS, JS)
```

## 🔑 단축키

- **ESC** - 앱 종료
- **✕ 버튼** - 홈으로 돌아가기

## 📱 웹 브라우저에서도 사용 가능

Electron 없이 웹 브라우저에서도 사용할 수 있습니다:

```bash
npm run start
```

그 다음 브라우저에서: `http://localhost:3000/capture`

## 🐛 문제 해결

### 카메라가 안 켜져요
- 시스템 설정 > 개인정보 보호 및 보안 > 카메라에서 권한 허용

### 사진이 저장되지 않아요
- `/photos` 폴더가 존재하는지 확인
- 폴더 쓰기 권한 확인

### 포트 충돌 (EADDRINUSE)
- 3000 포트가 이미 사용 중입니다
- `server.js`에서 `PORT` 번호 변경

## 🎨 디자인 커스터마이징

`templates/capture.html` 파일에서 Tailwind CSS 클래스를 수정하여 디자인을 변경할 수 있습니다.

## 📦 배포 (앱 빌드)

macOS .app 또는 Windows .exe 파일 생성:

```bash
npm run build
```

빌드된 앱은 `/dist` 폴더에 생성됩니다.

## 📄 라이선스

MIT License

---

Made with ❤️ by Masterpiece Team
