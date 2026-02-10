# LabCV — Electron desktop wrapper

This repository now includes a minimal Electron wrapper that launches the Flask server and shows it inside a desktop window.

Quick start (Windows / PowerShell):

1. Create and activate a Python virtual environment:

```powershell
py -m venv .venv; .\\.venv\\Scripts\\Activate.ps1
```

2. Install Python dependencies:

```powershell
pip install -r requirements.txt
```

3. Install Node.js (if you don't have it) and then install dev dependencies for the Electron wrapper:

```powershell
# from project root
npm install --save-dev electron electron-builder
```

4. Start the desktop app (this launches Electron, which spawns the Flask process automatically):

```powershell
npm start
```

5. Build a Windows installer (requires `electron-builder`):

```powershell
npm run build
```

Notes:
- The Electron main script (`electron-main.js`) will spawn `python -u app.py`. On Windows it will use `python` from PATH; if you have `py` instead, set the `PYTHON` environment variable before running Electron (e.g. in PowerShell: `$env:PYTHON='py'`).
- The Flask server binds by default to `127.0.0.1:5000`. You can change the port with the `FLASK_PORT` environment variable before launching Electron.
- Packaging will include all files in the repo. If you need a smaller packaged app, add an explicit `files` list or `.electronignore` to exclude dataset/weights.
