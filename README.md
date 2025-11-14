# Masterpiece Photobooth

## 개요 (Introduction)

특별한 순간을 담는 프로페셔널 포토부스 시스템입니다.
Node.js + Express 기반의 웹 서버와 Electron 데스크톱 애플리케이션으로 구성되어 있으며, QR 코드를 통해 촬영한 사진을 모바일 기기에서 즉시 다운로드할 수 있습니다.

### 주요 기능 (Features)
- 웹캠을 통한 실시간 사진 촬영
- 다양한 프레임 및 필터 적용
- 최대 4장의 사진 조합 및 레이아웃
- QR 코드를 통한 다운로드 기능
- 모던한 UI/UX
- 갤러리 페이지를 통한 실시간 공유
- 관리자 페이지를 통한 촬영 이력 관리
- ngrok을 통한 외부 접속 지원

## 시스템 요구 사항 (System Requirements)

### 하드웨어 요구사항 (Hardware Requirements)
- **프로세서**: Intel Core i5 이상 또는 동급 AMD 프로세서
- **메모리(RAM)**: 8GB 이상 (16GB 권장)
- **저장 공간**: SSD 256GB 이상
- **디스플레이**: 최소 1280x720 해상도
- **카메라**: 웹캠 (720p 이상 권장)

### 소프트웨어 요구사항 (Software Requirements)
- **운영 체제**: Windows 10 이상 또는 macOS 10.15 이상
- **Node.js**: 16.x 이상
- **npm**: Node.js와 함께 설치됨

## 설치 방법 (Installation)

### 1. Node.js 설치
1. https://nodejs.org/ 에서 LTS 버전 다운로드 및 설치
2. 설치 확인:
```bash
node --version
npm --version
```

### 2. 프로젝트 클론 (Clone Project)
```bash
git clone https://github.com/사용자이름/photobooth.git
cd photobooth
```

### 3. 의존성 설치 (Install Dependencies)
```bash
npm install
```

## 시스템 구성 (System Structure)

### 주요 파일 (Main Files)
- **server.js**: Express 웹 서버 (포트: 3000)
- **electron.js**: Electron 데스크톱 애플리케이션
- **package.json**: 프로젝트 설정 및 의존성 관리
- **templates/**: EJS 템플릿 파일
  - `index.ejs`: 메인 촬영 페이지
  - `admin.ejs`: 관리자 페이지
  - `promotion.ejs`: 갤러리 페이지
  - `result_mobile.ejs`: 모바일 다운로드 페이지
- **static/**: 정적 리소스 (CSS, JavaScript, 이미지)
- **.gitignore**: Git에서 제외할 파일 목록

### 폴더 구조 (Directory Structure)
다음 디렉토리들은 프로그램 실행 시 자동으로 생성됩니다:

```
photobooth/
├── server.js              # Express 서버
├── electron.js            # Electron 앱
├── package.json           # 프로젝트 설정
├── photos/                # 촬영된 원본 사진 (자동 생성)
├── output/                # 최종 이미지 (자동 생성)
├── qr_codes/              # 생성된 QR 코드 (자동 생성)
├── downloads/             # 다운로드 파일 (자동 생성)
├── frames/                # 사진 프레임 이미지
├── static/                # 정적 리소스
│   ├── css/              # 스타일시트
│   ├── js/               # 클라이언트 JavaScript
│   └── images/           # 이미지 파일
└── templates/             # EJS 템플릿
```

> **참고**: `photos/`, `output/`, `qr_codes/`, `downloads/` 디렉토리는 `.gitignore`에 포함되어 Git에 업로드되지 않습니다.

## 실행 방법 (Running the Application)

### Windows에서 실행

#### 방법 1: 배치 파일 사용 (간편)
```cmd
start.bat
```

#### 방법 2: 명령 프롬프트 사용
```cmd
# 웹 서버만 실행
npm start

# 자동 재시작 모드
npm run dev

# Electron 앱 실행
npm run electron

# 서버 + Electron 동시 실행
npm run app
```

### macOS/Linux에서 실행

#### 방법 1: 쉘 스크립트 사용 (간편)
```bash
./start.sh
```

#### 방법 2: 터미널 사용
```bash
# 웹 서버만 실행
npm start

# 자동 재시작 모드
npm run dev

# Electron 앱 실행
npm run electron

# 서버 + Electron 동시 실행
npm run app
```

> **참고**: macOS에서 `start.sh` 실행 시 권한 오류가 발생하면 `chmod +x start.sh` 명령으로 실행 권한을 부여하세요.

### 실행 시 동작
프로그램이 시작되면:
1. Express 서버가 포트 3000에서 시작됩니다
2. Electron 창이 자동으로 열립니다 (`npm run app` 사용 시)
3. 필요한 디렉토리가 자동으로 생성됩니다

### 웹 페이지 접속
- **메인 페이지**: http://localhost:3000
- **관리자 페이지**: http://localhost:3000/admin
- **갤러리**: http://localhost:3000/promotion

## 배포 (Build & Distribution)

### Electron 앱 빌드
```bash
npm run build
```

빌드된 파일은 `dist/` 폴더에 생성됩니다:
- **Windows**: `.exe` 설치 파일
- **macOS**: `.dmg` 또는 `.app` 파일

## 사용 방법 (Usage)

### 촬영 화면 (Photo Capture)
1. 메인 화면(`http://localhost:3000`)에 접속합니다
2. "촬영 시작" 버튼을 클릭합니다
3. 브라우저에서 웹캠 권한을 허용합니다
4. 프레임과 필터를 선택합니다 (선택 사항)
5. "촬영하기" 버튼으로 사진을 촬영합니다
6. 최대 4장까지 촬영 가능합니다
7. "완료" 버튼을 클릭하면 QR 코드가 생성됩니다

### 사진 다운로드 (Photo Download)
1. 생성된 QR 코드를 휴대폰으로 스캔합니다
2. 자동으로 다운로드 페이지로 이동합니다
3. "사진 다운로드" 버튼을 클릭하여 저장합니다

### 관리자 기능 (Admin Features)
1. `http://localhost:3000/admin`에 접속합니다
2. 촬영 이력 조회, 세션 관리, 삭제 등의 기능을 이용할 수 있습니다
3. 통계 정보 확인 가능

### 갤러리 기능 (Gallery)
1. `http://localhost:3000/promotion`에 접속합니다
2. 촬영된 사진들이 실시간으로 갤러리에 표시됩니다
3. 행사장에서 대형 화면에 표시하여 사용할 수 있습니다

## 외부 접속 설정 (External Access)

### ngrok 사용
프로젝트에는 ngrok이 포함되어 있어 외부에서도 접속 가능합니다.

```bash
# server.js에서 ngrok 설정 활성화
# ngrok 관련 코드의 주석을 해제하면 자동으로 터널이 생성됩니다
```

ngrok이 활성화되면:
- 콘솔에 외부 접속 URL이 표시됩니다
- QR 코드가 자동으로 외부 URL로 생성됩니다
- 어디서든 모바일로 사진을 다운로드할 수 있습니다

## 주요 설정 변경 (Configuration)

### 서버 포트 변경
`server.js`에서 포트 번호 수정:
```javascript
const PORT = 3000; // 원하는 포트 번호로 변경
```

### 프레임 추가
1. `frames/` 폴더에 PNG 형식의 프레임 이미지를 추가합니다
2. 이미지는 투명 배경(알파 채널)을 지원합니다
3. 권장 해상도: 1200x1600 이상

### 프레임 설정 파일
`frame_configs/` 폴더의 JSON 파일로 프레임별 레이아웃을 설정할 수 있습니다.

### 디자인 커스터마이징
- **CSS**: `static/css/style.css` 수정
- **템플릿**: `templates/*.ejs` 파일 수정
- **클라이언트 로직**: `static/js/` 파일 수정

## Git 사용 가이드 (Git Usage)

### .gitignore 설정
이 프로젝트는 다음 항목들이 자동으로 제외됩니다:

**생성된 파일:**
- `photos/` - 촬영된 사진
- `qr_codes/` - 생성된 QR 코드
- `output/` - 결과물 이미지
- `downloads/` - 다운로드 파일
- `dist/` - 빌드 결과물

**의존성 및 설정:**
- `node_modules/` - Node.js 패키지
- `package-lock.json` - 의존성 잠금 파일
- `config.json` - 개인 설정
- `sessions.json` - 세션 데이터

**시스템 파일:**
- `.DS_Store` - macOS 메타데이터
- `.env` - 환경 변수
- `*.log` - 로그 파일

### 처음 설치하는 경우
1. 저장소를 클론합니다
2. `npm install`로 의존성을 설치합니다
3. `npm start` 또는 `npm run app`으로 실행합니다
4. 프로그램이 자동으로 필요한 디렉토리를 생성합니다

## 문제 해결 (Troubleshooting)

### 웹캠이 작동하지 않는 경우
- 브라우저에서 카메라 권한을 허용했는지 확인합니다
- 다른 프로그램에서 카메라를 사용 중인지 확인합니다
- HTTPS 또는 localhost에서만 웹캠 접근이 가능합니다

### 포트가 이미 사용 중인 경우
```bash
# 다른 포트로 변경하거나, 사용 중인 프로세스 종료
# Windows
netstat -ano | findstr :3000
taskkill /PID <프로세스ID> /F

# macOS/Linux
lsof -i :3000
kill -9 <프로세스ID>
```

### npm install 오류
```bash
# 캐시 삭제 후 재설치
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

### Sharp 모듈 오류 (이미지 처리)
Sharp는 네이티브 모듈이므로 플랫폼에 맞게 재설치가 필요할 수 있습니다:
```bash
npm rebuild sharp
```

### Electron 빌드 오류
- Node.js 버전이 호환되는지 확인 (16.x 이상)
- 빌드 도구가 설치되어 있는지 확인:
  - **Windows**: Visual Studio Build Tools
  - **macOS**: Xcode Command Line Tools

### QR 코드 스캔 시 접속 불가
- 휴대폰과 컴퓨터가 같은 Wi-Fi 네트워크에 있는지 확인
- 방화벽에서 3000번 포트가 차단되어 있는지 확인
- 외부 네트워크에서 접속하려면 ngrok 사용

## 기술 스택 (Tech Stack)

### Backend
- **Node.js**: JavaScript 런타임
- **Express**: 웹 프레임워크
- **EJS**: 템플릿 엔진
- **Multer**: 파일 업로드
- **Sharp**: 이미지 처리
- **QRCode**: QR 코드 생성
- **ngrok**: 터널링

### Frontend
- **HTML5/CSS3**: 마크업 및 스타일
- **JavaScript (ES6+)**: 클라이언트 로직
- **MediaDevices API**: 웹캠 접근
- **Canvas API**: 이미지 처리 및 프리뷰

### Desktop
- **Electron**: 크로스 플랫폼 데스크톱 앱
- **electron-builder**: 앱 빌드 및 배포

### Development
- **Nodemon**: 자동 재시작
- **Concurrently**: 병렬 스크립트 실행
- **wait-on**: 서버 대기

## 라이선스 (License)

이 프로젝트는 MIT 라이선스 하에 공개되어 있습니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

### 사용된 라이브러리 라이선스
- **Express.js**: MIT 라이선스
- **Node.js**: MIT 라이선스
- **Electron**: MIT 라이선스
- **Sharp**: Apache 2.0 라이선스
- **QRCode**: MIT 라이선스
- **ngrok**: 상업적 사용 시 라이선스 확인 필요

## 기여하기 (Contributing)

기여를 환영합니다! 다음과 같은 방법으로 참여하실 수 있습니다:

1. **이슈 등록**: 버그 리포트, 기능 요청, 질문 등
2. **Pull Request**: 코드 개선, 버그 수정, 새 기능 등
3. **문서 개선**: README, 주석, 가이드 작성

### 개발 가이드라인
- 코드 스타일을 일관되게 유지해주세요
- 주요 변경사항은 이슈로 먼저 논의해주세요
- 커밋 메시지는 명확하게 작성해주세요

## 버전 히스토리 (Version History)

### v2.0 (Current)
- Node.js + Express 기반으로 전환
- Electron 데스크톱 앱 추가
- 웹 기반 촬영 시스템
- ngrok 통합
- 관리자 페이지 개선

### v1.0
- Python + CustomTkinter 기반
- Flask 웹 서버
- 기본 촬영 및 QR 코드 기능

## 감사의 말 (Acknowledgements)

이 프로젝트를 사용해주셔서 감사합니다.
개선 사항이나 제안이 있으시면 언제든지 이슈를 등록해주세요.

---

**Masterpiece Photobooth** | v2.0 | MIT License

