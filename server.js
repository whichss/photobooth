const express = require('express');
const path = require('path');
const fs = require('fs');
const crypto = require('crypto');
const qrcode = require('qrcode');
const chokidar = require('chokidar');
// photo.py 연동 제거
// const photoIntegration = require('./photo-integration');
const ngrok = require('ngrok');

const app = express();
const PORT = process.env.PORT || 3000;
// 민감한 정보를 환경 변수로 대체
const NGROK_AUTH_TOKEN = process.env.NGROK_AUTH_TOKEN || '';
const NGROK_DOMAIN = process.env.NGROK_DOMAIN || '';

// ngrok 설정
async function setupNgrok() {
  try {
    // ngrok 인증 토큰이 제공된 경우에만 설정
    if (NGROK_AUTH_TOKEN) {
      await ngrok.authtoken(NGROK_AUTH_TOKEN);
      
      // 도메인이 설정된 경우 도메인 사용, 아니면 무작위 URL
      const options = { addr: PORT };
      if (NGROK_DOMAIN) {
        options.domain = NGROK_DOMAIN;
      }
      
      const url = await ngrok.connect(options);
      console.log('ngrok 터널이 생성되었습니다:', url);
      return url;
    } else {
      console.log('ngrok 인증 토큰이 설정되지 않았습니다. 로컬 서버만 활성화됩니다.');
      return null;
    }
  } catch (err) {
    console.error('ngrok 설정 중 오류 발생:', err);
    return null;
  }
}

// 서버 시작 시 ngrok 설정
setupNgrok().then(url => {
  if (url) {
    console.log('외부 접속 URL:', url);
  }
});

// 보안 헤더 추가
app.use((req, res, next) => {
  // XSS 방지
  res.setHeader('X-XSS-Protection', '1; mode=block');
  // 클릭재킹 방지
  res.setHeader('X-Frame-Options', 'SAMEORIGIN');
  // MIME 타입 스니핑 방지
  res.setHeader('X-Content-Type-Options', 'nosniff');
  // 참조자 정보 제한
  res.setHeader('Referrer-Policy', 'same-origin');
  next();
});

// API 요청 수 제한을 위한 간단한 미들웨어
const apiLimiter = {
  requests: {},
  maxRequests: 100, // 1분당 최대 요청 수
  resetInterval: 60 * 1000, // 1분
  
  middleware: function(req, res, next) {
    const ip = req.ip || req.connection.remoteAddress;
    
    // API 경로만 제한
    if (!req.path.startsWith('/api/')) {
      return next();
    }
    
    // 첫 요청인 경우 초기화
    if (!this.requests[ip]) {
      this.requests[ip] = {
        count: 0,
        resetTime: Date.now() + this.resetInterval
      };
    }
    
    // 리셋 시간이 지났으면 카운트 초기화
    if (Date.now() > this.requests[ip].resetTime) {
      this.requests[ip] = {
        count: 0,
        resetTime: Date.now() + this.resetInterval
      };
    }
    
    // 요청 카운트 증가
    this.requests[ip].count++;
    
    // 최대 요청 수 초과 시 오류 응답
    if (this.requests[ip].count > this.maxRequests) {
      return res.status(429).json({ error: '너무 많은 요청이 발생했습니다. 잠시 후 다시 시도해주세요.' });
    }
    
    next();
  }
};

// API 제한 적용
app.use((req, res, next) => apiLimiter.middleware(req, res, next));

// 템플릿 엔진 설정
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'templates'));

// 정적 파일 제공
app.use('/static', express.static(path.join(__dirname, 'static')));
app.use('/photos', express.static(path.join(__dirname, 'photos')));
app.use('/output', express.static(path.join(__dirname, 'output')));
app.use('/downloads', express.static(path.join(__dirname, 'downloads')));
app.use('/', express.static(path.join(__dirname, 'templates'))); // HTML 파일 직접 제공

// static 폴더 생성 (없는 경우)
const staticDir = path.join(__dirname, 'static');
if (!fs.existsSync(staticDir)) {
  fs.mkdirSync(staticDir, { recursive: true });
}

// downloads 폴더 생성 (없는 경우)
const downloadsDir = path.join(__dirname, 'downloads');
if (!fs.existsSync(downloadsDir)) {
  fs.mkdirSync(downloadsDir, { recursive: true });
}

// 로고 파일 확인
const defaultLogoPath = path.join(staticDir, 'default_logo.png');
if (!fs.existsSync(defaultLogoPath)) {
  console.log('기본 로고 파일이 없습니다. 기본 로고를 생성합니다.');
  try {
    // 로고 생성 스크립트 로드 및 실행
    require('./static/logo');
  } catch (err) {
    console.error('로고 생성 스크립트 로드 실패:', err);
    
    // 간단히 1x1 투명 PNG 생성 (대체 로고)
    const emptyPng = Buffer.from(
      'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=',
      'base64'
    );
    fs.writeFileSync(defaultLogoPath, emptyPng);
    console.log(`빈 로고 파일 생성: ${defaultLogoPath}`);
  }
}

// 오류 이미지 생성
try {
  require('./static/generate-error-image');
} catch (err) {
  console.error('오류 이미지 생성 스크립트 로드 실패:', err);
}

// 세션 저장소 (메모리)
const sessions = {};

// photo.py 연동 제거
// const photoModule = photoIntegration.init(sessions, {
//   serverUrl: getBaseUrl()
// });

// 세션별로 처리 상태 추적
const processedSessions = new Set(); // 이미 처리된 세션 ID 저장

// 유틸리티 함수
function generateHashFromFolderName(folderName) {
  return crypto.createHash('md5').update(folderName).digest('hex').substring(0, 12);
}

// QR 코드 저장 폴더 생성
const qrCodesDir = path.join(__dirname, 'qr_codes');
if (!fs.existsSync(qrCodesDir)) {
  fs.mkdirSync(qrCodesDir, { recursive: true });
}

// QR 코드 생성 함수 수정 - 깨지는 문제 해결
async function generateQRCode(url) {
  try {
    // QR 코드 옵션 추가
    const qrOptions = {
      errorCorrectionLevel: 'H',  // 높은 오류 수정 레벨
      type: 'image/png',
      quality: 0.92,
      margin: 1,
      color: {
        dark: '#000000',
        light: '#FFFFFF'
      },
      width: 300  // 더 큰 크기로 생성
    };
    
    const qr = await qrcode.toDataURL(url, qrOptions);
    return qr;
  } catch (err) {
    console.error('QR 코드 생성 오류:', err);
    throw err;
  }
}

// 포토 폴더 감시 설정
const photosDir = path.join(__dirname, 'photos');
if (!fs.existsSync(photosDir)) {
  fs.mkdirSync(photosDir, { recursive: true });
}

const watcher = chokidar.watch(photosDir, {
  ignored: /(^|[\/\\])\../, // 숨김 파일 무시
  persistent: true,
  depth: 1 // 바로 아래 폴더만 감시
});

// 기존 폴더 스캔
function scanExistingFolders() {
  console.log('기존 세션 폴더 스캔 시작...');
  
  // 1. photos 디렉토리 스캔
  if (fs.existsSync(photosDir)) {
    fs.readdirSync(photosDir).forEach(async (folder) => {
      const folderPath = path.join(photosDir, folder);
      if (fs.statSync(folderPath).isDirectory()) {
        await processNewFolder(folderPath);
      }
    });
  }
  
  // 2. output 디렉토리의 모든 파일 스캔
  const outputDir = path.join(__dirname, 'output');
  if (fs.existsSync(outputDir)) {
    console.log('출력 디렉토리 스캔 중...');
    
    // 모든 이미지 파일 검색
    const imageFiles = fs.readdirSync(outputDir)
      .filter(file => file.endsWith('.png'));
    
    // 세션 ID 추출 패턴
    const sessionPattern = /session_(\d+)_/;
    
    imageFiles.forEach(file => {
      const match = file.match(sessionPattern);
      if (match && match[1]) {
        const sessionId = match[1];
        
        // sessionId로 해시 생성
        const hash = generateHashFromFolderName(sessionId);
        
        // 세션이 없으면 새로 생성
        if (!sessions[hash]) {
          sessions[hash] = {
            folder: sessionId,
            hash: hash,
            qr_url: `${getBaseUrl()}/photo/${hash}`,
            created_at: Date.now() / 1000, // 생성 시간은 현재로
            photos: [],
            final_img: null
          };
          
          console.log(`출력 파일에서 새 세션 생성: ${sessionId} (해시: ${hash})`);
        }
        
        // 출력 파일 정보 저장
        const relativePath = path.join('output', file).replace(/\\/g, '/');
        
        if (file.includes('_final.png') || file.endsWith('.png')) {
          sessions[hash].final_img = relativePath;
          console.log(`세션 ${hash}에 최종 이미지 추가: ${file}`);
        }
        
        // 해당 세션ID로 photos 디렉토리 검색해 사진 추가
        const photoDirs = fs.readdirSync(photosDir)
          .filter(folder => folder.includes(sessionId))
          .map(folder => path.join(photosDir, folder));
        
        photoDirs.forEach(photoDir => {
          if (fs.existsSync(photoDir) && fs.statSync(photoDir).isDirectory()) {
            scanPhotosInFolder(photoDir, hash);
          }
        });
      }
    });
  }
  
  console.log(`기존 세션 스캔 완료. 총 ${Object.keys(sessions).length}개 세션 로드됨`);
}

// 세션 생성 시 토큰 생성 함수
function generateAccessToken() {
  return crypto.randomBytes(32).toString('hex');
}

// 새 폴더 처리 함수 수정
async function processNewFolder(dirPath) {
  if (dirPath === photosDir) return;
  
  const folderName = path.basename(dirPath);
  if (!/^\d{8}_\d{6}$/.test(folderName) && !/^\d{12}$/.test(folderName)) return;
  
  const hash = generateHashFromFolderName(folderName);
  const accessToken = generateAccessToken();
  const qrUrl = `${getBaseUrl()}/download?img=output/session_${folderName.replace(/[^0-9]/g, '')}_final.png`;
  
  if (sessions[hash] || processedSessions.has(folderName)) return;
  
  processedSessions.add(folderName);
  
  try {
    // QR 코드 생성 및 저장
    const qrBase64 = await generateQRCode(qrUrl);
    const qrPath = path.join(qrCodesDir, `qr_${hash}.png`);
    const qrData = qrBase64.replace(/^data:image\/png;base64,/, '');
    fs.writeFileSync(qrPath, qrData, 'base64');
      
    // 세션 생성
    sessions[hash] = {
      folder: folderName,
      hash: hash,
      access_token: accessToken,
      qr_url: qrUrl,
      qr_path: path.relative(__dirname, qrPath).replace(/\\/g, '/'),
      created_at: Date.now() / 1000,
      photos: [],
      final_img: null
    };
    
    // 사진 스캔
    scanPhotosInFolder(dirPath, hash);
    
    // 출력 이미지 확인
    checkForOutputFiles(folderName, hash);
    
    console.log(`세션 생성 완료: ${folderName} (${hash})`);
  } catch (err) {
    console.error(`세션 생성 오류 (${folderName}):`, err);
  }
}

// 폴더 내 사진 스캔
function scanPhotosInFolder(folderPath, hash) {
  if (!fs.existsSync(folderPath)) return;
  
  const sessionSuffix = `_${hash.substring(0, 4)}`;
  let photoCount = 0;
  
  fs.readdirSync(folderPath).forEach(file => {
    if (file.endsWith('.jpg') || file.endsWith('.png')) {
      const photoPath = path.join(folderPath, file);
      const relativePath = path.relative(__dirname, photoPath).replace(/\\/g, '/');
      
      if (!sessions[hash].photos.includes(relativePath)) {
        sessions[hash].photos.push(relativePath);
        photoCount++;
      }
    }
  });
  
  console.log(`폴더 스캔 완료: ${path.basename(folderPath)} -> ${hash}, 사진 ${photoCount}개 발견`);
  
  // 사진이 있으면 일단 세션 유효함
  if (photoCount > 0 && !sessions[hash].final_img) {
    // 사진이 있는데 최종 이미지가 없으면 첫 번째 사진을 임시로 사용
    sessions[hash].final_img = sessions[hash].photos[0];
    console.log(`최종 이미지가 없어 첫 번째 사진을 사용합니다: ${sessions[hash].photos[0]} -> 세션 ${hash}`);
  }
}

// 출력 파일 확인 함수 수정
function checkForOutputFiles(folderName, hash) {
  const outputDir = path.join(__dirname, 'output');
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
    return;
  }
  
  const numericFolderName = folderName.replace(/[^0-9]/g, '');
  
  if (!sessions[hash]) {
    sessions[hash] = {
      folder: folderName,
      hash: hash,
      qr_url: `${getBaseUrl()}/photo/${hash}`,
      created_at: Date.now() / 1000,
      photos: [],
      final_img: null
    };
  }
  
  fs.readdirSync(outputDir).forEach(file => {
    const isSessionFile = file.includes('session_') && 
      (file.includes(numericFolderName) || file.includes(hash.substring(0, 4)));
    
    const isFinalImg = file.endsWith('_final.png');
    
    if (isSessionFile && isFinalImg) {
      const relativePath = path.join('output', file).replace(/\\/g, '/');
      sessions[hash].final_img = relativePath;
      console.log(`최종 이미지 확인: ${file} -> 세션 ${hash}`);
    }
  });
}

// 폴더 감시 이벤트
watcher.on('addDir', async (dirPath) => {
  await processNewFolder(dirPath);
});

// 새 사진 파일 감지
watcher.on('add', (filePath) => {
  if (!filePath.endsWith('.jpg') && !filePath.endsWith('.png')) return;
  
  const dirPath = path.dirname(filePath);
  const folderName = path.basename(dirPath);
  
  // 날짜 형식 or 세션 형식 확인
  const isDateFormat = /^\d{8}_\d{6}$/.test(folderName) || /^\d{12}$/.test(folderName);
  const isSessionFormat = /session_\d+/.test(folderName);
  
  if (!isDateFormat && !isSessionFormat) return;
  
  const hash = generateHashFromFolderName(folderName);
  
  // 세션이 없으면 생성
  if (!sessions[hash]) {
    sessions[hash] = {
      folder: folderName,
      hash: hash,
      qr_url: `${getBaseUrl()}/photo/${hash}`,
      qr_b64: null, // QR 코드는 나중에 생성
      created_at: Date.now() / 1000,
      photos: [],
      final_img: null
    };
    
    console.log(`새 세션 생성: ${folderName} (해시: ${hash})`);
    
    // 다른 사진들도 스캔
    scanPhotosInFolder(dirPath, hash);
    
    // QR 코드 생성 (비동기)
    generateQRCode(`${getBaseUrl()}/photo/${hash}`)
      .then(qrBase64 => {
        sessions[hash].qr_b64 = qrBase64;
        console.log(`QR 코드 생성 완료: ${hash}`);
      })
      .catch(err => {
        console.error(`QR 코드 생성 실패: ${hash}, 오류: ${err.message}`);
      });
  }
  
  const relativePath = path.relative(__dirname, filePath).replace(/\\/g, '/');
  if (!sessions[hash].photos.includes(relativePath)) {
    sessions[hash].photos.push(relativePath);
    console.log(`새 사진 추가: ${path.basename(filePath)} -> ${hash}`);
    
    // 최종 이미지가 없으면 이 사진을 사용
    if (!sessions[hash].final_img) {
      sessions[hash].final_img = relativePath;
      console.log(`최종 이미지 없음 - 임시로 사용: ${relativePath}`);
    }
  }
});

// 출력 파일 감시
const outputDir = path.join(__dirname, 'output');
if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
}

const outputWatcher = chokidar.watch(outputDir, {
  ignored: /(^|[\/\\])\../, // 숨김 파일 무시
  persistent: true
});

outputWatcher.on('add', (filePath) => {
  const fileName = path.basename(filePath);
  const match = fileName.match(/session_(\d+)_(final)\.(png)/);
  
  if (!match) {
    // 세션 ID 추출 패턴을 더 완화
    const sessionMatch = fileName.match(/session_(\d+)/);
    if (sessionMatch && sessionMatch[1]) {
      const sessionId = sessionMatch[1];
      const hash = generateHashFromFolderName(sessionId);
      const relativePath = path.relative(__dirname, filePath).replace(/\\/g, '/');
      
      // 세션이 없으면 생성
      if (!sessions[hash]) {
        sessions[hash] = {
          folder: sessionId,
          hash: hash,
          qr_url: `${getBaseUrl()}/photo/${hash}`,
          created_at: Date.now() / 1000,
          photos: [],
          final_img: null
        };
        console.log(`출력 파일에서 새 세션 생성: ${sessionId} (해시: ${hash})`);
      }
      
      // 파일 유형 결정
      if (fileName.endsWith('.png')) {
        sessions[hash].final_img = relativePath;
        console.log(`최종 이미지 추가: ${fileName} -> ${hash}`);
      }
      
      return;
    }
    
    return; // 패턴에 맞지 않으면 처리하지 않음
  }
  
  const sessionId = match[1];
  const fileType = match[2];
  const extension = match[3];
  
  // 해당 세션 ID에 해당하는 해시값 찾기 (정확히 일치하거나 포함 관계 모두 검사)
  let targetHash = null;
  
  // 1. 정확한 해시 먼저 시도
  targetHash = generateHashFromFolderName(sessionId);
  
  // 2. 정확한 해시가 없으면 포함 관계 검색
  if (!sessions[targetHash]) {
    for (const hash in sessions) {
      const sessionFolderName = sessions[hash].folder;
      if (sessionFolderName && (
          sessionId.includes(sessionFolderName.replace(/[^0-9]/g, '')) || 
          sessionFolderName.replace(/[^0-9]/g, '').includes(sessionId)
      )) {
        targetHash = hash;
        break;
      }
    }
  }
  
  // 3. 그래도 없으면 새로 생성
  if (!targetHash || !sessions[targetHash]) {
    targetHash = generateHashFromFolderName(sessionId);
    sessions[targetHash] = {
      folder: sessionId,
      hash: targetHash,
      qr_url: `${getBaseUrl()}/photo/${targetHash}`,
      created_at: Date.now() / 1000,
      photos: [],
      final_img: null
    };
    console.log(`출력 파일에서 새 세션 생성: ${sessionId} (해시: ${targetHash})`);
  }
  
  // 파일 정보 저장
  const relativePath = path.relative(__dirname, filePath).replace(/\\/g, '/');
  
  if (fileType === 'final' && extension === 'png') {
    sessions[targetHash].final_img = relativePath;
    console.log(`최종 이미지 추가: ${fileName} -> ${targetHash}`);
  }
});

// 간단한 인증 확인 미들웨어
function checkAdminAuth(req, res, next) {
  const authPassword = req.query.auth;
  const adminPassword = process.env.ADMIN_PASSWORD || '!dlscjsdmsgP1';
  
  if (authPassword === adminPassword) {
    next();
  } else {
    res.status(401).json({ error: '인증 실패', success: false });
  }
}

// API 라우트
app.get('/api/photos', (req, res) => {
  // output 폴더를 다시 스캔하여 세션 업데이트
  Object.keys(sessions).forEach(hash => {
    if (sessions[hash] && sessions[hash].folder) {
      checkForOutputFiles(sessions[hash].folder, hash);
    }
  });
  
  // 최종 이미지가 있는 세션만 반환 (temp_ 포함하지 않는 것만)
  const validSessions = Object.values(sessions)
    .filter(s => s.final_img && !s.final_img.includes('temp_'))
    .sort((a, b) => b.created_at - a.created_at);
  
  console.log(`API 응답: ${validSessions.length}개 세션 반환`);
  res.json(validSessions);
});

// QR 코드 생성 API
app.get('/api/generate-qr/:hash', async (req, res) => {
  const hash = req.params.hash;
  if (!sessions[hash]) {
    return res.status(404).json({ error: '세션을 찾을 수 없습니다', success: false });
  }
  
  try {
    // 이미 QR 코드가 있으면 그대로 반환
    if (sessions[hash].qr_b64) {
      return res.json({ 
        success: true, 
        qr_b64: sessions[hash].qr_b64,
        qr_url: sessions[hash].qr_url
      });
    }
    
    // 없으면 새로 생성
    const qrUrl = sessions[hash].qr_url || `${getBaseUrl()}/photo/${hash}`;
    const qrBase64 = await generateQRCode(qrUrl);
    
    // 세션 업데이트
    sessions[hash].qr_b64 = qrBase64;
    sessions[hash].qr_url = qrUrl;
    
    res.json({ 
      success: true, 
      qr_b64: qrBase64,
      qr_url: qrUrl
    });
  } catch (err) {
    console.error('QR 코드 생성 오류:', err);
    res.status(500).json({ error: '서버 오류', success: false });
  }
});

// 세션 삭제 API 수정
app.delete('/api/delete-session/:hash', checkAdminAuth, async (req, res) => {
  const hash = req.params.hash;
  if (!sessions[hash]) {
    return res.status(404).json({ error: '세션을 찾을 수 없습니다', success: false });
  }
  
  try {
    const session = sessions[hash];
    let successCount = 0;
    let errorCount = 0;
    let errorMessages = [];
    
    // 1. QR 코드 파일 삭제
    if (session.qr_path) {
      try {
        const qrPath = path.join(__dirname, session.qr_path);
        if (fs.existsSync(qrPath)) {
          fs.unlinkSync(qrPath);
          successCount++;
          console.log(`QR 코드 삭제: ${session.qr_path}`);
        }
      } catch (err) {
        errorCount++;
        errorMessages.push(`QR 코드 삭제 실패: ${err.message}`);
      }
    }
    
    // 2. 최종 이미지 파일 삭제
    if (session.final_img) {
      try {
        const finalImgPath = path.join(__dirname, session.final_img);
        if (fs.existsSync(finalImgPath)) {
          fs.unlinkSync(finalImgPath);
          successCount++;
          console.log(`최종 이미지 삭제: ${session.final_img}`);
        }
      } catch (err) {
        errorCount++;
        errorMessages.push(`최종 이미지 삭제 실패: ${err.message}`);
      }
    }
    
    // 3. 사진 파일들 삭제
    for (const photoPath of (session.photos || [])) {
      try {
        const fullPhotoPath = path.join(__dirname, photoPath);
        if (fs.existsSync(fullPhotoPath)) {
          fs.unlinkSync(fullPhotoPath);
          successCount++;
          console.log(`사진 삭제: ${photoPath}`);
        }
      } catch (err) {
        errorCount++;
        errorMessages.push(`사진 삭제 실패 (${photoPath}): ${err.message}`);
      }
    }
    
    // 4. 메모리에서 세션 삭제
    delete sessions[hash];
    console.log(`세션 삭제 완료: ${hash}`);
    
    res.json({ 
      success: true, 
      message: `${successCount}개 파일 삭제 완료, ${errorCount}개 파일 삭제 실패`, 
      errors: errorMessages
    });
  } catch (err) {
    console.error('세션 삭제 오류:', err);
    res.status(500).json({ error: '서버 오류', success: false });
  }
});

// 특정 해시의 세션 정보 반환
app.get('/api/session/:hash', (req, res) => {
  const hash = req.params.hash;
  if (!sessions[hash]) {
    return res.status(404).json({ error: '세션을 찾을 수 없습니다' });
  }
  
  res.json(sessions[hash]);
});

// 사진 상세 정보 API (모바일 페이지용)
app.get('/api/photo/:hash', (req, res) => {
  const hash = req.params.hash;
  const token = req.query.token;
  const session = sessions[hash];
  
  if (!session) {
    return res.status(404).render('error', { message: '사진을 찾을 수 없습니다.' });
  }
  
  // 토큰 검증
  if (!token || token !== session.access_token) {
    return res.status(403).render('error', { message: '접근 권한이 없습니다.' });
  }
  
  // 세션 데이터를 템플릿에 전달
  res.render('result_mobile', {
    final_img: session.final_img,
    session: {
      hash: session.hash,
      qr_b64: session.qr_b64,
      gif_path: session.gif_path,
      created_at: session.created_at
    },
    made_by: 'Masterpiece',
    date: new Date(session.created_at * 1000).toLocaleString('ko-KR')
  });
});

// Output 폴더 파일 목록 제공 (갤러리 폴백 용)
app.get('/output-list', (req, res) => {
  try {
    if (!fs.existsSync(outputDir)) {
      return res.json([]);
    }
    
    const files = fs.readdirSync(outputDir)
      .filter(file => file.endsWith('.png'))
      .sort((a, b) => {
        // 최신 파일을 먼저 정렬 (mtime 내림차순)
        const statA = fs.statSync(path.join(outputDir, a));
        const statB = fs.statSync(path.join(outputDir, b));
        return statB.mtime.getTime() - statA.mtime.getTime();
      });
    
    res.json(files);
  } catch (err) {
    console.error('output 폴더 읽기 오류:', err);
    res.status(500).json({ error: 'output 폴더를 읽을 수 없습니다' });
  }
});

// 다운로드 페이지 라우트 추가
app.get('/download', (req, res) => {
  console.log('다운로드 페이지 접근');
  res.sendFile(path.join(__dirname, 'templates', 'result_mobile.html'));
});

// 다운로드 페이지 (특정 세션)
app.get('/download/:hash', (req, res) => {
  const hash = req.params.hash;
  const session = sessions[hash];
  
  if (!session) {
    return res.status(404).sendFile(path.join(__dirname, 'templates', 'error.html'));
  }
  
  // 세션 데이터를 템플릿에 전달
  res.render('result_mobile', {
    final_img: session.final_img,
    session: {
      hash: session.hash,
      qr_b64: session.qr_b64,
      gif_path: session.gif_path,
      created_at: session.created_at
    },
    made_by: 'Masterpiece',
    date: new Date(session.created_at * 1000).toLocaleString('ko-KR')
  });
});

// 웹 라우트
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'templates/index.html'));
});

// 관리자 페이지
app.get('/admin', (req, res) => {
  const authPassword = req.query.auth;
  // 간단한 비밀번호 보호 - 실제 환경에서는 더 강력한 인증 사용 권장
  const adminPassword = process.env.ADMIN_PASSWORD || '!dlscjsdmsgP1';
  
  if (authPassword === adminPassword) {
    res.sendFile(path.join(__dirname, 'templates/admin.html'));
  } else {
    res.sendFile(path.join(__dirname, 'templates/admin_login.html'));
  }
});

// 홍보용 페이지
app.get('/promotion', (req, res) => {
  res.sendFile(path.join(__dirname, 'templates/promo.html'));
});

// 랜덤 이미지 제공 API
app.get('/promo/random', (req, res) => {
  const validSessions = Object.values(sessions).filter(s => s.final_img);
  
  if (validSessions.length === 0) {
    return res.status(404).send('사진이 없습니다');
  }
  
  const randomSession = validSessions[Math.floor(Math.random() * validSessions.length)];
  
  // 쿼리 파라미터가 있으면 캐시 방지용으로 무시
  res.redirect(`/${randomSession.final_img}`);
});

// 개별 사진 페이지
app.get('/photo/:hash', (req, res) => {
  const hash = req.params.hash;
  const token = req.query.token;
  const session = sessions[hash];
  
  if (!session) {
    return res.status(404).render('error', { message: '사진을 찾을 수 없습니다.' });
  }
  
  // 토큰 검증
  if (!token || token !== session.access_token) {
    return res.status(403).render('error', { message: '접근 권한이 없습니다.' });
  }
  
  // 세션 데이터를 템플릿에 전달
  res.render('result_mobile', {
    final_img: session.final_img,
    session: {
      hash: session.hash,
      qr_b64: session.qr_b64,
      gif_path: session.gif_path,
      created_at: session.created_at
    },
    made_by: 'Masterpiece',
    date: new Date(session.created_at * 1000).toLocaleString('ko-KR')
  });
});

// 세션 생성 API
app.post('/api/create-session', express.json(), (req, res) => {
  const { folder_name, session_id } = req.body;
  
  if (!folder_name || !session_id) {
    return res.status(400).json({ 
      error: '필수 파라미터가 누락되었습니다', 
      success: false 
    });
  }
  
  const hash = generateHashFromFolderName(folder_name);
  const accessToken = generateAccessToken();
  const qrUrl = `${getBaseUrl()}/photo/${hash}?token=${accessToken}`;
  
  // 이미 존재하는 세션인지 확인
  if (sessions[hash]) {
    return res.status(409).json({ 
      error: '이미 존재하는 세션입니다', 
      success: false 
    });
  }
  
  try {
    // 세션 생성
    sessions[hash] = {
      folder: folder_name,
      hash: hash,
      access_token: accessToken,
      qr_url: qrUrl,
      created_at: Date.now() / 1000,
      photos: [],
      final_img: null
    };
    
    // QR 코드 생성
    generateQRCode(qrUrl).then(qrBase64 => {
      sessions[hash].qr_b64 = qrBase64;
      
      // QR 코드 파일 저장
      const qrPath = path.join(qrCodesDir, `qr_${hash}.png`);
      const qrData = qrBase64.replace(/^data:image\/png;base64,/, '');
      fs.writeFileSync(qrPath, qrData, 'base64');
      sessions[hash].qr_path = path.relative(__dirname, qrPath).replace(/\\/g, '/');
      
      console.log(`새 세션 생성 완료: ${folder_name} (${hash})`);
    }).catch(err => {
      console.error(`QR 코드 생성 실패: ${hash}`, err);
    });
    
    res.json({ 
      success: true,
      hash: hash,
      qr_url: qrUrl
    });
  } catch (err) {
    console.error('세션 생성 오류:', err);
    res.status(500).json({ 
      error: '서버 오류', 
      success: false 
    });
  }
});

// 404 에러 처리
app.use((req, res) => {
  console.log('404 에러:', req.url);
  res.status(404).sendFile(path.join(__dirname, 'templates/error.html'));
});

// 에러 처리 미들웨어
app.use((err, req, res, next) => {
  console.error('서버 에러:', err);
  res.status(500).sendFile(path.join(__dirname, 'templates/error.html'));
});

// getBaseUrl 함수 수정
function getBaseUrl() {
  return `https://${NGROK_DOMAIN}`;  // ngrok 도메인 사용
}

// 접속 가능한 URL 및 네트워크 정보 로그
function logNetworkInfo() {
  const interfaces = require('os').networkInterfaces();
  console.log('\n===== 네트워크 접속 정보 =====');
  console.log('다음 URL로 접속할 수 있습니다:');
  
  // localhost
  console.log(`- 이 컴퓨터에서: http://localhost:${PORT}`);
  
  // 모든 네트워크 인터페이스 출력
  for (const name of Object.keys(interfaces)) {
    for (const iface of interfaces[name]) {
      if (iface.family === 'IPv4' && !iface.internal) {
        console.log(`- 로컬 네트워크에서: http://${iface.address}:${PORT}`);
      }
    }
  }
  
  console.log('\n외부에서 QR 코드로 접속하려면:');
  console.log('1. QR 코드는 위의 로컬 네트워크 IP 주소를 사용합니다.');
  console.log('2. 공유기 설정에서 포트 포워딩을 설정하면 인터넷에서 접속할 수 있습니다.');
  console.log('3. 고정 IP가 없다면 DDNS 서비스를 사용해 보세요.');
  console.log('4. 환경 변수 EXTERNAL_URL을 설정하면 해당 URL로 QR 코드를 생성합니다.');
  console.log('   (예: EXTERNAL_URL=http://example.com node server.js)');
  console.log('===============================\n');
}

// 서버 시작 - 포트 충돌 처리 추가
function startServer(port) {
  const server = app.listen(port, () => {
    console.log(`서버가 시작되었습니다: ${getBaseUrl()}`);
    console.log('사용 가능한 URL:');
    console.log(`- 메인 페이지: ${getBaseUrl()}/`);
    console.log(`- 관리자 페이지: ${getBaseUrl()}/admin`);
    console.log(`- 홍보 페이지: ${getBaseUrl()}/promotion`);
    console.log(`- 다운로드 페이지: ${getBaseUrl()}/download`);
    
    // 네트워크 접속 정보 로그
    logNetworkInfo();
    
    // 인화기 연결 확인
    checkPrinter();
  }).on('error', (err) => {
    if (err.code === 'EADDRINUSE') {
      console.log(`포트 ${port}가 이미 사용 중입니다. 다른 포트를 시도합니다...`);
      startServer(port + 1); // 다음 포트 번호 시도
    } else {
      console.error('서버 시작 오류:', err);
    }
  });
}

// 시작 시 기존 폴더 스캔
scanExistingFolders();

// 서버 시작
startServer(PORT);

// 프린터 연결 확인 함수
function checkPrinter() {
  try {
    const { exec } = require('child_process');
    
    if (process.platform === 'win32') {
      // Windows 환경
      exec('wmic printer list status', (error, stdout, stderr) => {
        if (error) {
          console.error('프린터 정보 확인 실패:', error);
          return;
        }
        
        console.log('\n===== 프린터 연결 상태 =====');
        console.log(stdout);
        console.log('===========================\n');
      });
    } else if (process.platform === 'darwin') {
      // macOS 환경
      exec('lpstat -p', (error, stdout, stderr) => {
        if (error) {
          console.error('프린터 정보 확인 실패:', error);
          return;
        }
        
        console.log('\n===== 프린터 연결 상태 =====');
        console.log(stdout || '연결된 프린터가 없습니다.');
        console.log('===========================\n');
      });
    } else {
      // Linux 등 기타 환경
      exec('lpstat -v', (error, stdout, stderr) => {
        if (error) {
          console.error('프린터 정보 확인 실패:', error);
          return;
        }
        
        console.log('\n===== 프린터 연결 상태 =====');
        console.log(stdout || '연결된 프린터가 없습니다.');
        console.log('===========================\n');
      });
    }
  } catch (err) {
    console.error('프린터 정보 확인 중 오류:', err);
  }
}