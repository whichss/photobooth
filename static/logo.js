const fs = require('fs');
const path = require('path');

// static 폴더 경로
const staticDir = path.join(__dirname);
const logoPath = path.join(staticDir, 'default_logo.png');

// 기본 로고 생성
function createDefaultLogo() {
  try {
    // 1x1 픽셀 투명 PNG 생성 (대체 로고)
    const emptyPng = Buffer.from(
      'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=',
      'base64'
    );
    fs.writeFileSync(logoPath, emptyPng);
    console.log(`기본 로고 파일 생성: ${logoPath}`);
  } catch (err) {
    console.error('로고 생성 실패:', err);
  }
}

// 로고 파일이 없으면 생성
if (!fs.existsSync(logoPath)) {
  createDefaultLogo();
}

module.exports = {
  createDefaultLogo
}; 