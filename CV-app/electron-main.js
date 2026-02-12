const { app, BrowserWindow, Menu, Tray } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');

let pyProc = null;
let mainWindow = null;
let tray = null;

function getPort() {
  return process.env.FLASK_PORT || '5000';
}

function startPython() {
  // Try bundled backend first
  const bundledBackend = path.join(__dirname, 'labcv_backend.exe');
  if (fs.existsSync(bundledBackend)) {
    console.log('Using bundled backend executable');
    const env = Object.assign({}, process.env);
    env.FLASK_PORT = getPort();
    env.FLASK_HOST = '127.0.0.1';
    env.FLASK_DEBUG = 'False';
    
    pyProc = spawn(bundledBackend, [], { 
      env,
      windowsHide: true, // prevent console window
      stdio: ['ignore', 'pipe', 'pipe'] // redirect stdout/stderr but hide stdin
    });
  } else {
    console.log('Bundled backend not found, using Python interpreter');
    const script = path.join(__dirname, 'app.py');
    // Prefer an explicit PYTHON env var, otherwise try the project's venv python, then fall back to 'python'
    const venvPython = path.join(__dirname, '.venv', 'Scripts', 'python.exe');
    const python = process.env.PYTHON || (fs.existsSync(venvPython) ? venvPython : 'python');
    const env = Object.assign({}, process.env);
    env.FLASK_PORT = getPort();
    env.FLASK_HOST = '127.0.0.1';
    env.FLASK_DEBUG = 'False';

    pyProc = spawn(python, ['-u', script], { env });
  }

  pyProc.stdout?.on('data', (data) => {
    console.log(`[backend stdout] ${data}`);
  });

  pyProc.stderr?.on('data', (data) => {
    console.error(`[backend stderr] ${data}`);
  });

  pyProc.on('close', (code) => {
    console.log(`backend process exited with code ${code}`);
    pyProc = null;
  });
}

function waitForServer(port, timeout = 30000) {
  const start = Date.now();
  const url = `http://127.0.0.1:${port}/`;
  return new Promise((resolve, reject) => {
    const check = () => {
      http.get(url, (res) => {
        resolve();
      }).on('error', (err) => {
        if (Date.now() - start > timeout) {
          reject(new Error('timeout waiting for Flask server'));
        } else {
          setTimeout(check, 200);
        }
      });
    };
    check();
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1000,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js')
    }
  });

  const url = `http://127.0.0.1:${getPort()}`;
  // Wait for Flask to be ready before loading the URL
  waitForServer(getPort(), 30000).then(() => {
    mainWindow.loadURL(url);
  }).catch((err) => {
    console.error('Server did not start in time:', err);
    mainWindow.loadURL(url); // attempt anyway
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function createTray() {
  // Check if icon file exists, otherwise skip tray (optional feature)
  const iconPath = path.join(__dirname, 'icon.png');
  if (!fs.existsSync(iconPath)) {
    console.warn('icon.png not found, skipping system tray');
    return;
  }

  tray = new Tray(iconPath);
  const contextMenu = Menu.buildFromTemplate([
    { 
      label: 'Show Window', 
      click: () => {
        if (mainWindow === null) {
          createWindow();
        } else {
          mainWindow.show();
        }
      }
    },
    { 
      label: 'Hide Window',
      click: () => mainWindow?.hide()
    },
    { type: 'separator' },
    { 
      label: 'Quit', 
      click: () => {
        if (pyProc) {
          try { pyProc.kill(); } catch (e) { console.warn('failed to kill backend', e); }
        }
        app.quit();
      }
    }
  ]);

  tray.setToolTip('LabCV');
  tray.setContextMenu(contextMenu);

  // Double click on tray icon shows window
  tray.on('double-click', () => {
    if (mainWindow === null) {
      createWindow();
    } else {
      mainWindow.show();
    }
  });
}

app.on('ready', () => {
  startPython();
  createWindow();
  createTray();
});

// Hide window to tray instead of closing
app.on('window-all-closed', (e) => {
  if (mainWindow) {
    e.preventDefault();
    mainWindow.hide();
  }
});

app.on('activate', () => {
  if (mainWindow === null) {
    createWindow();
  }
});

app.on('before-quit', () => {
  if (pyProc) {
    try { pyProc.kill(); } catch (e) { console.warn('failed to kill backend', e); }
  }
});
