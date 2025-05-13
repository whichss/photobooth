# 포토부스 시스템 (Photobooth System)

## 개요 (Introduction)

이 포토부스 시스템은 행사나 이벤트에서 간편하게 사진을 촬영하고, 즉시 인쇄 및 디지털 공유가 가능한 오픈소스 솔루션입니다. 
Python 기반의 카메라 제어 모듈과 Node.js 기반의 웹 서버로 구성되어 있어 QR 코드를 통해 촬영한 사진을 모바일 기기에서 다운로드할 수 있습니다.

### 주요 기능 (Features)
- 웹캠을 통한 실시간 사진 촬영
- 프레임 및 필터 적용
- 최대 4장의 사진 조합 및 레이아웃 제공
- QR 코드를 통한 다운로드 기능
- 관리자 페이지를 통한 촬영 이력 관리

## 시스템 요구 사항 (System Requirements)

### 하드웨어 (Hardware)
- 웹캠 또는 USB 카메라
- 프린터 (옵션)
- 터치스크린 (권장)

### 소프트웨어 (Software)
- Windows 10 이상
- Python 3.8 이상
- Node.js 14 이상
- ngrok (외부 접속용, 선택사항)

## 설치 방법 (Installation)

### 필수 소프트웨어 설치 (Required Software)
1. **Node.js 설치**
   - https://nodejs.org/ko/ 에서 LTS 버전 다운로드 및 설치

2. **Python 설치**
   - https://www.python.org/downloads/ 에서 다운로드 및 설치
   - "Add Python to PATH" 옵션을 반드시 체크

3. **ngrok 설치** (외부 접속 시 필요, 선택사항)
   - https://ngrok.com/download 에서 다운로드
   - 계정 생성 후 인증 토큰 설정

### 프로젝트 클론 및 설치 (Clone and Install)
1. 이 저장소를 클론합니다:
   ```
   git clone https://github.com/사용자이름/photobooth.git
   cd photobooth
   ```

2. **Node.js 패키지 설치**
   ```
   npm install
   ```

3. **Python 라이브러리 설치**
   ```
   pip install opencv-python pillow numpy tk qrcode
   ```

## 시스템 구성 (System Structure)

### 주요 파일 (Main Files)
- **photo.py**: 카메라 제어 및 UI 모듈
- **server.js**: 웹 서버 및 API
- **photo-integration.js**: Python과 Node.js 연동 모듈
- **start_photobooth.bat**: 원클릭 실행 스크립트

### 폴더 구조 (Directory Structure)
- **photos/**: 촬영된 원본 사진 저장
- **output/**: 최종 이미지 저장
- **templates/**: 웹 페이지 템플릿
- **static/**: 정적 리소스 파일
- **frames/**: 사진 프레임 이미지
- **qr_codes/**: 생성된 QR 코드 저장

## 환경 설정 (Configuration)

### ngrok 및 관리자 설정
`start_photobooth.bat` 파일을 열어 다음 설정을 변경하세요:

```bat
REM 관리자 비밀번호 설정 (기본값: photobooth)
set ADMIN_PASSWORD=photobooth

REM ngrok 설정 - 사용하려면 여기에 토큰과 도메인을 추가하세요
set NGROK_AUTH_TOKEN=your_token_here
set NGROK_DOMAIN=your_domain_here  (선택사항)
```

## 실행 방법 (Running the Application)

### 원클릭 실행 (One-click Start)
1. `start_photobooth.bat` 파일을 더블클릭합니다.
2. 자동으로 서버와 ngrok이 시작되고 브라우저가 관리자 페이지로 열립니다.
3. 기본 관리자 비밀번호: `photobooth`

### 수동 실행 (Manual Start)
1. 명령 프롬프트에서 Node.js 서버 실행:
   ```
   node server.js
   ```
2. 별도 명령 프롬프트에서 ngrok 실행 (외부 접속 필요 시):
   ```
   ngrok http 3000
   ```
3. Python 애플리케이션 실행:
   ```
   python photo.py
   ```

## 사용 방법 (Usage)

### 촬영 화면 (Photo Capture)
1. 메인 화면에서 "촬영 시작" 버튼을 클릭합니다.
2. 프레임과 필터를 선택합니다.
3. 카운트다운 후 자동으로 사진이 촬영됩니다.
4. 원하는 만큼 사진을 촬영한 후 "완료" 버튼을 클릭합니다.
5. 최종 결과물에 사용할 사진들을 선택합니다.
6. 인쇄 또는 저장 옵션을 선택합니다.
7. QR 코드가 표시됩니다.

### 사진 다운로드 (Photo Download)
1. 휴대폰으로 QR 코드를 스캔합니다.
2. 자동으로 다운로드 페이지로 이동합니다.
3. "사진 다운로드" 버튼을 클릭하여 저장합니다.

### 관리자 기능 (Admin Features)
1. `http://localhost:3000/admin` 또는 ngrok URL + `/admin`에 접속합니다.
2. 세션 관리, 삭제, QR 코드 생성 등의 기능을 이용할 수 있습니다.

## 외부 접속 설정 (External Access)

### ngrok을 통한 임시 접속 (Temporary Access via ngrok)
- `start_photobooth.bat`가 자동으로 ngrok URL을 설정합니다.
- 콘솔에 표시되는 URL을 사용하여 외부에서 접속 가능합니다.
- URL 형식: `https://xxxx.ngrok.io`

### 포트 포워딩 (영구적 설정 시) (Port Forwarding for Permanent Setup)
1. 공유기 관리 페이지에 접속합니다.
2. 포트 포워딩 설정에서 3000번 포트를 내부 IP로 연결합니다.
3. 서버 시작 시 환경 변수 설정:
   ```
   EXTERNAL_URL=http://외부IP:3000 node server.js
   ```

## 주요 설정 변경 (Configuration Changes)

### 카메라 설정 (Camera Settings)
- **photo.py** 파일의 `Config` 클래스에서:
  - `camera_port`: 카메라 장치 번호 (기본값: 0)
  - `camera_width`, `camera_height`: 카메라 해상도

### 타이머 설정 (Timer Settings)
- `countdown_time`: 카운트다운 시간 (기본값: 5초)
- `default_countdown`: 자동 타이머 시간 (기본값: 30초)

### 사용자 지정 (Customization)
- **로고 변경**: `static/logo.png` 파일을 교체합니다.
- **색상 테마 변경**: **photo.py** 파일의 `initialize_styles` 함수에서 색상 코드 수정
- **프레임 추가**: `frames` 폴더에 PNG 형식의 프레임 이미지 추가 (투명 배경 필요)

## 문제 해결 (Troubleshooting)

### 카메라가 작동하지 않는 경우 (Camera Not Working)
- 다른 카메라 인덱스 시도 (0, 1, 2 등)
- 카메라 드라이버 재설치
- 관리자 권한으로 실행

### 이미지가 표시되지 않는 경우 (Images Not Displaying)
- 브라우저 콘솔(F12)에서 오류 확인
- 상대 경로 문제일 가능성이 높습니다.
- 서버 재시작 시도

### QR 코드 스캔 시 접속 불가 (QR Code Access Issues)
- ngrok URL이 만료되었을 수 있습니다 (8시간 제한)
- 서버를 재시작하여 새 URL 생성
- 네트워크 연결 확인

## 기여하기 (Contributing)

기여를 환영합니다! 다음과 같은 방법으로 참여하실 수 있습니다:

1. 이슈 등록: 버그 리포트, 기능 요청, 질문 등
2. Pull Request: 코드 개선, 버그 수정, 새 기능 등 

## 라이선스 (License)

이 프로젝트는 MIT 라이선스 하에 공개되어 있습니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 감사의 말 (Acknowledgements)

- 사용된 오픈소스 라이브러리: OpenCV, Express, Node.js, ngrok 등
- 코드리뷰 파일을 같이 첨부합니다. 

---

© 2025 photobooth | v2.0 