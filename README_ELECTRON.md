# Electron App Guide

Masterpiece Photobooth can run as a desktop-style kiosk application through Electron. The Electron shell loads the local Express server and opens the kiosk start screen.

## Run the Desktop App

```bash
npm run app
```

This command starts:

1. Express server
2. Electron window after `http://localhost:3000` is ready

## Run Server and Electron Separately

Terminal 1:

```bash
npm start
```

Terminal 2:

```bash
npm run electron
```

## Start URL

Electron opens:

```text
http://localhost:3000/app/start
```

## Kiosk Behavior

The Electron window is configured in `electron.js`.

Important options:

- `fullscreen`: starts in fullscreen mode
- `frame`: controls native window frame visibility
- `kiosk`: can be enabled for stricter event operation
- `contextIsolation`: enabled for safer renderer behavior
- `nodeIntegration`: disabled in the renderer

For production kiosk operation, consider:

- Enable `kiosk: true`
- Disable developer tools
- Configure the OS to launch the app at login
- Disable screen sleep
- Pre-install camera and printer drivers
- Test with the exact event camera and printer

## Build Desktop Installers

```bash
npm run build
```

The project uses `electron-builder`.

Expected targets:

- Windows: NSIS installer
- macOS: app/DMG depending on builder environment

Windows icon path:

```text
assets/icon.ico
```

macOS icon path:

```text
assets/icon.icns
```

Make sure these files exist before creating production installers.

## Camera Notes

Electron uses Chromium camera APIs. Any device that appears as a webcam to the OS should be available in Settings.

For DSLR or mirrorless cameras, use one of these approaches:

- HDMI capture card that appears as a webcam
- Vendor software saving images into the watched folder
- Capture One, Lightroom, or similar software saving into the watched folder

## Printer Notes

Printing is delegated to the operating system.

- macOS/Linux: CUPS commands
- Windows: PowerShell/Windows printer integration

Always test the selected printer on the target machine before an event.

## Troubleshooting

### Camera does not appear

1. Open Settings.
2. Request camera permission.
3. Rescan devices.
4. Test the camera.
5. Save settings.

If the selected camera fails during capture, the app automatically retries with fallback constraints.

### Electron opens but server is unavailable

Run:

```bash
npm start
```

Then check:

```text
http://localhost:3000/app/start
```

### Port is already in use

The server tries the next port if the configured port is busy, but Electron expects port `3000`. For production, keep port `3000` available.

## Recommended Production Setup

1. Install Node.js LTS.
2. Install camera and printer drivers.
3. Run `npm install`.
4. Open Settings and test devices.
5. Run `npm run app`.
6. Configure OS login item/startup task.
7. Keep a wired power/network setup where possible.
