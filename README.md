# Masterpiece Photobooth

Masterpiece Photobooth is a kiosk-style photo booth application built with Node.js, Express, Sharp, and Electron. It supports guided capture, frame selection, automatic QR download links, admin management, external frame folders, basic printer integration, and camera profiles for different layouts.

## Features

- Kiosk-friendly capture flow
- Browser and Electron desktop app modes
- Camera device selection and automatic fallback
- Layout-aware camera profiles for `2x2` and `1x4`
- Manual and automatic countdown capture
- Six-shot capture flow with four-photo selection
- Automatic frame discovery from the `frames/` folder
- PNG, JPG, JPEG, and WEBP frame support
- Sharp-based final image composition
- QR code generation for mobile download
- Admin dashboard for sessions and frames
- Server-side `settings.json` for operator/device settings
- External camera folder watch mode
- Basic OS printer listing and auto-print hooks
- Windows and macOS/Linux run scripts

## Requirements

### Hardware

- CPU: Intel Core i5 or equivalent recommended
- Memory: 8 GB minimum, 16 GB recommended
- Storage: SSD recommended
- Display: 1280 x 720 minimum
- Camera: webcam, USB camera, capture card, or camera software that can save into a watched folder
- Optional: OS-installed photo printer

### Software

- Windows 10 or later, or macOS 10.15 or later
- Node.js 16 or later
- npm

## Installation

```bash
git clone https://github.com/whichss/photobooth.git
cd photobooth
npm install
```

If the project is already on the Desktop:

```bash
cd ~/Desktop/photobooth
npm install
```

## Running

### Web Server

```bash
npm start
```

Open:

```text
http://localhost:3000/app/start
```

### Electron App

```bash
npm run app
```

### Development Mode

```bash
npm run dev
```

### Build Installer

```bash
npm run build
```

Build outputs are created in `dist/`.

## Windows

From Command Prompt or PowerShell:

```bat
cd photobooth
npm install
npm run app
```

You can also run:

```bat
start.bat
```

Printer and external camera behavior should be tested on the actual event PC because Windows drivers, printer names, and capture-card drivers vary by device.

## macOS/Linux

```bash
cd photobooth
npm install
npm run app
```

Or:

```bash
./start.sh
```

If needed:

```bash
chmod +x start.sh
```

## Main URLs

- Kiosk start: `http://localhost:3000/app/start`
- Settings: `http://localhost:3000/app/settings`
- Admin: `http://localhost:3000/admin`
- Gallery: `http://localhost:3000/promotion`

## Project Structure

```text
photobooth/
├── electron.js
├── server.js
├── package.json
├── settings.json          # generated locally, ignored by git
├── frames/
│   ├── 2x2/
│   └── 1x4/
├── photos/                # generated locally, ignored by git
├── output/                # generated locally, ignored by git
├── qr_codes/              # generated locally, ignored by git
├── static/
│   ├── css/
│   └── js/
└── templates/
    ├── app/
    ├── admin.html
    ├── admin_login.html
    └── promo.html
```

## Operator Settings

The app stores operator settings in `settings.json`, which is generated automatically and ignored by git.

Settings include:

- Camera selection mode
- Selected camera device ID
- Preview fit mode
- `2x2` camera profile
- `1x4` camera profile
- Capture count
- Countdown time
- Mirror mode
- Flash effect
- Printer name
- Auto-print option
- QR options
- External camera watched folder

Open settings at:

```text
http://localhost:3000/app/settings
```

## Camera Setup

The app supports two camera modes:

- `Automatic`: use the browser/Electron default camera with layout-aware constraints.
- `Selected camera`: prefer a specific device ID selected in Settings.

If the selected camera fails, the capture screen tries fallback constraints automatically:

1. Selected camera with the layout profile
2. Same profile without exact device binding
3. 1280 x 720 fallback
4. Browser default camera

For best reliability on event PCs:

1. Open Settings.
2. Click camera permission/request scan controls.
3. Select or auto-pick the camera.
4. Test the camera.
5. Save settings.

## Layout Camera Profiles

`2x2` defaults to a portrait-style camera profile.

`1x4` defaults to a landscape-style camera profile.

You can change either profile in Settings:

- Auto
- Portrait
- Landscape
- Square

## External Camera Mode

For DSLR or mirrorless workflows, the easiest integration is folder watching.

1. Use your camera software, capture card utility, Lightroom, Capture One, or vendor tool to save images into a folder.
2. Open Settings.
3. Enable external capture folder watching.
4. Set the watched folder path.
5. Save settings.

New images in that folder are copied into the app photo directory.

## Frame Management

Frames are discovered automatically from:

```text
frames/2x2/
frames/1x4/
```

Supported frame formats:

- PNG
- JPG
- JPEG
- WEBP

Recommended sizes:

- `2x2`: 1230 x 1820 px
- `1x4`: 630 x 1820 px

Transparent PNG frames are used as overlays. Non-transparent frames are used as background frames.

## Printing

The app includes basic printer listing and auto-print hooks.

On macOS/Linux it uses CUPS commands such as `lpstat` and `lp`.

On Windows it uses PowerShell printer APIs where available.

For production use, always test printing on the actual printer and event PC. Photo printers often require vendor-specific drivers, media settings, and paper-size presets.

## QR Downloads

Final images are stored in `output/`, and QR codes point to the generated download route.

For LAN events, phones must be on the same network as the kiosk PC.

For external access, set:

```bash
EXTERNAL_URL=http://your-domain-or-ip npm start
```

## Security Notes

- Do not expose the admin route publicly without changing `ADMIN_PASSWORD`.
- Do not commit `settings.json`; it can contain local device names and paths.
- Review npm audit output before public deployment.
- Avoid `npm audit fix --force` unless you have tested breaking dependency updates.

## Scripts

- `npm start`: start Express server
- `npm run dev`: start server with nodemon
- `npm run electron`: start Electron only
- `npm run app`: start server and Electron together
- `npm run build`: build distributable app

## License

MIT License
