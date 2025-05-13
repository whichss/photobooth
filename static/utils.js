/**
 * 포토부스 서버 유틸리티 함수
 */

// 이미지 유효성 검사 (경로가 유효한지 확인)
function validateImagePath(imagePath) {
  if (!imagePath) return false;
  
  // 상대 경로 정규화
  const normalizedPath = imagePath.replace(/\\/g, '/');
  
  // 이미지 파일 확장자 확인
  const validExtensions = ['.jpg', '.jpeg', '.png', '.gif'];
  const hasValidExtension = validExtensions.some(ext => 
    normalizedPath.toLowerCase().endsWith(ext)
  );
  
  return hasValidExtension;
}

module.exports = {
  validateImagePath
}; 