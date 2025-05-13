/**
 * photo.py 연동 모듈
 * - 포토부스 소프트웨어(photo.py)와 웹 서버 연동
 * - 이벤트 처리 및 QR 코드 생성 자동화
 */

const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const crypto = require('crypto');
const qrcode = require('qrcode');

// 전역 설정
const config = {
  // photo.py 파일 경로
  photoPyPath: path.join(__dirname, 'photo.py'),
  
  // 폴더 경로
  photosDir: path.join(__dirname, 'photos'),
  outputDir: path.join(__dirname, 'output'),
  
  // 서버 URL (QR 코드용)
  serverUrl: 'http://localhost:3000',
  
  // 디버그 모드
  debug: true
};

// 세션 데이터 저장소 참조 (외부 제공)
let sessionsRef = null;

// 디버그 로그 함수
function debug(message, data = null) {
  if (config.debug) {
    if (data) {
      console.log(`[Photo Integration] ${message}`, data);
    } else {
      console.log(`[Photo Integration] ${message}`);
    }
  }
}

// photo.py가 설치되어 있는지 확인
function checkPhotoPyExists() {
  if (!fs.existsSync(config.photoPyPath)) {
    console.warn(`[Photo Integration] photo.py 파일이 경로에 없습니다: ${config.photoPyPath}`);
    return false;
  }
  return true;
}

// Python 실행 함수
function runPythonScript(scriptPath, args = []) {
  return new Promise((resolve, reject) => {
    // 'python' 대신 'py' 명령어 사용 (Windows에서 더 안정적)
    const pythonProcess = spawn('py', [scriptPath, ...args]);
    
    let output = '';
    let errorOutput = '';
    
    pythonProcess.stdout.on('data', (data) => {
      output += data.toString();
    });
    
    pythonProcess.stderr.on('data', (data) => {
      errorOutput += data.toString();
    });
    
    pythonProcess.on('close', (code) => {
      if (code !== 0) {
        debug(`Python 스크립트 실행 오류 (${code}): ${errorOutput}`);
        reject(new Error(`Python 오류: ${errorOutput}`));
      } else {
        resolve(output);
      }
    });
  });
}

// QR 코드 생성 함수
async function generateQRCode(url) {
  try {
    const qrDataURL = await qrcode.toDataURL(url);
    return qrDataURL.split(',')[1]; // Base64 부분만 반환
  } catch (err) {
    debug('QR 코드 생성 오류', err);
    throw err;
  }
}

// 새 세션 생성 (photo.py에서 호출 가능)
async function createSession(folderName, baseUrl = null) {
  if (!sessionsRef) {
    throw new Error('세션 저장소가 초기화되지 않았습니다');
  }
  
  const serverBaseUrl = baseUrl || config.serverUrl;
  const hash = crypto.createHash('md5').update(folderName).digest('hex').substring(0, 8);
  const qrUrl = `${serverBaseUrl}/photo/${hash}`;
  
  try {
    const qrBase64 = await generateQRCode(qrUrl);
    
    sessionsRef[hash] = {
      folder: folderName,
      hash: hash,
      qr_url: qrUrl,
      qr_b64: qrBase64,
      created_at: Date.now() / 1000,
      photos: [],
      final_img: null
    };
    
    debug(`새 세션 생성: ${folderName} (해시: ${hash})`);
    return { hash, qrUrl, qrBase64 };
  } catch (err) {
    debug('세션 생성 오류', err);
    throw err;
  }
}

// 초기화 함수
function init(sessions, customConfig = {}) {
  sessionsRef = sessions;
  
  // 설정 병합
  Object.assign(config, customConfig);
  
  // 필요한 디렉토리 확인 및 생성
  [config.photosDir, config.outputDir].forEach(dir => {
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
      debug(`디렉토리 생성: ${dir}`);
    }
  });
  
  // photo.py 존재 확인
  if (checkPhotoPyExists()) {
    debug('photo.py 파일 확인 완료');
  }
  
  return {
    createSession,
    config
  };
}

module.exports = {
  init
};