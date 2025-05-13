const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const fs = require('fs');

function createWindow() {
    const win = new BrowserWindow({
        width: 1200,
        height: 800,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false
        }
    });

    win.loadFile(path.join(__dirname, 'index.html'));
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        createWindow();
    }
});

// 이미지 처리 관련 IPC 이벤트 핸들러
ipcMain.handle('process-image', async (event, imagePath) => {
    try {
        // 이미지 처리 로직
        return { success: true };
    } catch (error) {
        return { success: false, error: error.message };
    }
});

// QR 코드 생성 관련 IPC 이벤트 핸들러
ipcMain.handle('generate-qr', async (event, data) => {
    try {
        // QR 코드 생성 로직
        return { success: true };
    } catch (error) {
        return { success: false, error: error.message };
    }
}); 