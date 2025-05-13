const fs = require('fs');
const path = require('path');

// static 폴더 경로
const staticDir = path.join(__dirname);
const errorImagePath = path.join(staticDir, 'image-error.png');

// 이미지 오류 표시용 Base64 인코딩 PNG (200x300 빨간색 배경에 흰색 X 표시)
const errorImageBase64 = 'iVBORw0KGgoAAAANSUhEUgAAAMgAAAEsAQMAAABc3r/9AAAABlBMVEXuBATuBASSF0AIAAAAAnRSTlP/AOW3MEoAAAEVSURBVGje7dexCcMwEAXQT6NkApdZQODSaLKBi6ziIovYxdW7m0uuOB8RxAE/1eFQcXrFIcT/xmQymeybUpZFPJ0HT0hb0+y2vIcCfnGUSX1wktk5yxbwiiMZyWQymUwmk8lkMplMJpPJZDKZTCaTyWQymUwmk8lkMplMJpPJZDKZTCaTyWQymUwmk8lkMplM5olm1gGSzgCTzgCTzgCTzgBz9UxwHZeS/W9r6Q5rzTSTyWQymUwm0/B5MZkDk8lkMplMJpPJZDKZTCaTyWQymUwmk8lkMplMJpPJZDKZTCaTyWQymUwmk8lkMplM5nUzMdLOAJPNAJPNAJPNAJPNAHPs3N2g0xy7oc79MSvYZDKZO+ULXT6GVnQiKLkAAAAASUVORK5CYII=';

// 이미지 생성 함수
function createErrorImage() {
  try {
    const imageBuffer = Buffer.from(errorImageBase64, 'base64');
    fs.writeFileSync(errorImagePath, imageBuffer);
    console.log(`이미지 오류 기본 이미지 생성 완료: ${errorImagePath}`);
  } catch (err) {
    console.error('이미지 오류 기본 이미지 생성 실패:', err);
  }
}

// 파일이 없으면 생성
if (!fs.existsSync(errorImagePath)) {
  createErrorImage();
}

module.exports = {
  createErrorImage
};