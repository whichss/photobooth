const { app, BrowserWindow } = require('electron');
const path = require('path');

let mainWindow;

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1920,
        height: 1080,
        fullscreen: true,
        frame: false,  // 프레임 없음
        kiosk: false,  // 개발 중에는 false, 배포 시 true
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            enableRemoteModule: false
        },
        backgroundColor: '#FFFFFF'
    });

    // Express 서버 URL 로드 - 시작 화면부터
    mainWindow.loadURL('http://localhost:3000/app/start');

    // 개발자 도구 (개발 중에만)
    // mainWindow.webContents.openDevTools();

    // ESC 키로 종료 가능하게
    mainWindow.on('closed', () => {
        mainWindow = null;
    });

    // ESC 키 바인딩
    mainWindow.webContents.on('before-input-event', (event, input) => {
        if (input.key === 'Escape') {
            app.quit();
        }
    });
}

app.whenReady().then(() => {
    createWindow();

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

// GPU 가속 비활성화 (안정성)
app.disableHardwareAcceleration();
