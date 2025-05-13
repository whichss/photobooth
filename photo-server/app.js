const express = require('express');
const path = require('path');
const fs = require('fs');
const app = express();

// 정적 파일 제공
app.use(express.static(path.join(__dirname, '..', 'templates')));
app.use('/output', express.static(path.join(__dirname, '..', 'output')));
app.use('/gifs', express.static(path.join(__dirname, '..', 'gifs')));
app.use('/photos', express.static(path.join(__dirname, '..', 'photos')));
app.use('/frames', express.static(path.join(__dirname, '..', 'frames')));

// 라우트 등록 확인
console.log('라우트 등록 시작...');

// 기본 라우트
app.get('/', (req, res) => {
    console.log('루트 페이지 접근');
    res.sendFile(path.join(__dirname, '..', 'templates', 'index.html'));
});

// 프로모션 페이지
app.get('/promotion', (req, res) => {
    console.log('프로모션 페이지 접근');
    res.sendFile(path.join(__dirname, '..', 'templates', 'promo.html'));
});

// 프로모션 그리드 페이지
app.get('/promo/grid', (req, res) => {
    console.log('프로모션 그리드 페이지 접근');
    res.sendFile(path.join(__dirname, '..', 'templates', 'promo_grid.html'));
});

// 사진 보기 페이지
app.get('/photo/:hash', (req, res) => {
    console.log('사진 보기 페이지 접근:', req.params.hash);
    res.sendFile(path.join(__dirname, '..', 'templates', 'photos.html'));
});

// 다운로드 페이지
app.get('/download', (req, res) => {
    console.log('다운로드 페이지 접근');
    res.sendFile(path.join(__dirname, '..', 'templates', 'result_mobile.html'));
});

// 관리자 페이지
app.get('/admin', (req, res) => {
    console.log('관리자 페이지 접근');
    res.sendFile(path.join(__dirname, '..', 'templates', 'admin.html'));
});

// 404 에러 처리
app.use((req, res, next) => {
    console.log('404 에러:', req.url);
    res.status(404).send('페이지를 찾을 수 없습니다');
});

// 에러 처리 미들웨어
app.use((err, req, res, next) => {
    console.error('서버 에러:', err);
    res.status(500).send('서버 에러가 발생했습니다');
});

// 서버 시작
const PORT = process.env.PORT || 5000;
app.listen(PORT, () => {
    console.log('=================================');
    console.log(`서버가 http://localhost:${PORT} 에서 실행중입니다`);
    console.log('등록된 라우트:');
    console.log('- /');
    console.log('- /promotion');
    console.log('- /promo/grid');
    console.log('- /photo/:hash');
    console.log('- /download');
    console.log('- /admin');
    console.log('=================================');
}); 