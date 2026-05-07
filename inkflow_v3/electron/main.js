/**
 * InkFlow v3 — Electron Main Process
 *
 * Backend strategy: runs backend/main.py with embedded Python
 * (portable Python in resources/python/ — no install needed)
 *
 * File layout after install:
 *   resources/
 *     python/           ← embedded Python 3.11 (portable zip)
 *       python.exe
 *       Lib/
 *       ...
 *     backend/          ← plain .py files
 *       main.py
 *       api/
 *       engine/
 *       ...
 *     data/             ← user data (profiles, exports)
 */

const { app, BrowserWindow, ipcMain, shell, dialog, nativeTheme } = require("electron");
const path = require("path");
const fs = require("fs");
const http = require("http");
const { spawn, execSync } = require("child_process");

// FIX: Prevent DPI scaling issues so 1 pixel in Electron = 1 pixel on monitor
app.commandLine.appendSwitch("force-device-scale-factor", "1");

const BACKEND_PORT = 8000;
const MAX_WAIT_MS = 60000;
const POLL_MS = 800;

const IS_PACKAGED = app.isPackaged;
const RESOURCES_DIR = IS_PACKAGED ? process.resourcesPath : path.join(__dirname, "..");
const DATA_DIR = path.join(app.getPath("userData"), "data");
const PROFILES_DIR = path.join(DATA_DIR, "profiles");
const EXPORTS_DIR = path.join(DATA_DIR, "exports");
const LOG_FILE = path.join(app.getPath("userData"), "backend.log");

let mainWindow = null;
let calOverlay = null;
let backendProc = null;
let ready = false;

function log(msg) {
  const line = `[${new Date().toISOString()}] ${msg}\n`;
  process.stdout.write(line);
  try { fs.appendFileSync(LOG_FILE, line); } catch (_) { }
}

function findPython() {
  // 1. Embedded Python (packaged app)
  const embedded = [
    path.join(RESOURCES_DIR, "python", "python.exe"),  // Windows
    path.join(RESOURCES_DIR, "python", "python3"),     // Linux/Mac
    path.join(RESOURCES_DIR, "python", "python"),
  ];
  for (const p of embedded) {
    if (fs.existsSync(p)) { log("Python (embedded): " + p); return p; }
  }

  // 2. System Python (dev mode)
  const system = ["python", "python3", "py"];
  for (const cmd of system) {
    try {
      execSync(`${cmd} --version`, { stdio: "ignore" });
      log("Python (system): " + cmd);
      return cmd;
    } catch (_) { }
  }
  return null;
}

function findBackendMain() {
  const candidates = [
    path.join(RESOURCES_DIR, "backend", "main.py"),
    path.join(__dirname, "..", "backend", "main.py"),
  ];
  for (const p of candidates) {
    if (fs.existsSync(p)) { log("Backend: " + p); return p; }
  }
  return null;
}

function spawnBackend() {
  fs.mkdirSync(PROFILES_DIR, { recursive: true });
  fs.mkdirSync(EXPORTS_DIR, { recursive: true });

  const python = findPython();
  const mainPy = findBackendMain();

  if (!python || !mainPy) {
    log("ERROR: Python or backend not found");
    log("  Python: " + (python || "NOT FOUND"));
    log("  main.py: " + (mainPy || "NOT FOUND"));
    log("  RESOURCES_DIR: " + RESOURCES_DIR);
    try {
      log("  resources contents: " + fs.readdirSync(RESOURCES_DIR).join(", "));
    } catch (_) { }
    return;
  }

  const backendDir = path.dirname(mainPy);
  const env = Object.assign({}, process.env, {
    INKFLOW_PROFILES_DIR: PROFILES_DIR,
    INKFLOW_EXPORTS_DIR: EXPORTS_DIR,
    INKFLOW_PORT: String(BACKEND_PORT),
    PYTHONPATH: backendDir,
    PYTHONUNBUFFERED: "1",
  });

  // For embedded Python: add Lib/site-packages to PYTHONPATH
  const sitePackages = path.join(RESOURCES_DIR, "python", "Lib", "site-packages");
  if (fs.existsSync(sitePackages)) {
    env.PYTHONPATH = backendDir + path.delimiter + sitePackages;
  }

  log("Starting backend: " + python + " " + mainPy);
  backendProc = spawn(python, [mainPy], {
    cwd: backendDir,
    env: env,
    detached: false,
    stdio: ["ignore", "pipe", "pipe"],
  });

  backendProc.stdout.on("data", d => log("[out] " + d.toString().trim()));
  backendProc.stderr.on("data", d => log("[err] " + d.toString().trim()));
  backendProc.on("exit", c => { log("Backend exit: " + c); ready = false; });
  backendProc.on("error", e => { log("Backend spawn error: " + e.message); });
}

function waitForBackend() {
  return new Promise((resolve, reject) => {
    const start = Date.now();
    let isResolved = false;
    function check() {
      if (isResolved) return;
      const req = http.get(`http://127.0.0.1:${BACKEND_PORT}/api/health`, { timeout: 1500 }, res => {
        res.on('data', () => { }); // Consume body to free socket
        res.on('end', () => {
          if (res.statusCode === 200 && !isResolved) {
            isResolved = true;
            ready = true;
            log("Backend ready!");
            resolve();
          } else if (!isResolved) {
            retry();
          }
        });
      });
      req.on("error", () => {
        if (!isResolved) retry();
      });
      req.on("timeout", function () {
        req.destroy(); // Will trigger 'error' event
      });
    }
    function retry() {
      if (isResolved) return;
      if (Date.now() - start > MAX_WAIT_MS) reject(new Error("Backend timeout"));
      else setTimeout(check, POLL_MS);
    }
    check();
  });
}

function killBackend() {
  if (!backendProc) return;
  try {
    if (process.platform === "win32")
      execSync(`taskkill /PID ${backendProc.pid} /T /F`, { stdio: "ignore" });
    else backendProc.kill("SIGTERM");
  } catch (_) { }
  backendProc = null;
}

function createWindow() {
  nativeTheme.themeSource = "dark";
  mainWindow = new BrowserWindow({
    width: 1300, height: 860, minWidth: 960, minHeight: 640,
    title: "InkFlow", backgroundColor: "#0c0c1a", show: false,
    webPreferences: {
      nodeIntegration: false, contextIsolation: true,
      preload: path.join(__dirname, "preload.js"),
    },
  });

  // Find index.html
  const candidates = [
    path.join(__dirname, "..", "frontend", "dist", "index.html"),
    path.join(RESOURCES_DIR, "app", "frontend", "dist", "index.html"),
  ];
  let loaded = false;
  for (const p of candidates) {
    log("Frontend check: " + p + (fs.existsSync(p) ? " FOUND" : " missing"));
    if (fs.existsSync(p)) { mainWindow.loadFile(p); loaded = true; break; }
  }
  if (!loaded) { log("Dev fallback: localhost:5173"); mainWindow.loadURL("http://localhost:5173"); }

  mainWindow.once("ready-to-show", () => { mainWindow.show(); mainWindow.focus(); });
  mainWindow.webContents.setWindowOpenHandler(({ url }) => { shell.openExternal(url); return { action: "deny" }; });
  
  // Deny geolocation and other sensitive permissions
  mainWindow.webContents.session.setPermissionRequestHandler((webContents, permission, callback) => {
    if (permission === "geolocation") {
      log("Blocked geolocation request");
      return callback(false);
    }
    callback(true);
  });

  mainWindow.on("closed", () => { mainWindow = null; });
}

// IPC
ipcMain.handle("get-app-info", () => ({ version: app.getVersion(), profilesDir: PROFILES_DIR, exportsDir: EXPORTS_DIR, backendReady: ready }));
ipcMain.handle("backend-status", () => ({ ready, url: `http://127.0.0.1:${BACKEND_PORT}` }));
ipcMain.handle("open-exports-folder", () => shell.openPath(EXPORTS_DIR));
ipcMain.handle("show-save-dialog", async (_, o) => dialog.showSaveDialog(mainWindow, o));
ipcMain.handle("set-always-on-top", (_, flag, level) => {
  if (mainWindow) mainWindow.setAlwaysOnTop(!!flag, level || "screen-saver");
});
ipcMain.handle("set-fullscreen", (_, flag) => {
  if (mainWindow) mainWindow.setFullScreen(!!flag);
});
ipcMain.handle("get-cursor-screen-point", () => {
  const { screen } = require("electron");
  return screen.getCursorScreenPoint();
});

// ── Calibration Overlay ──────────────────────────────────────────────────
ipcMain.handle("start-calibration", () => {
  if (calOverlay) return; // already open

  // Minimize main window so user can see OneNote
  if (mainWindow) mainWindow.minimize();

  const { screen } = require("electron");
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width, height, x, y } = primaryDisplay.bounds;

  calOverlay = new BrowserWindow({
    width, height,
    x, y,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    resizable: false,
    skipTaskbar: true,
    fullscreen: true,
    hasShadow: false,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
    },
  });

  calOverlay.setAlwaysOnTop(true, "screen-saver");
  calOverlay.setVisibleOnAllWorkspaces(true);

  // Load the overlay HTML
  const overlayPath = path.join(__dirname, "calibration-overlay.html");
  calOverlay.loadFile(overlayPath);

  calOverlay.on("closed", () => { calOverlay = null; });
  log("Calibration overlay opened");
});

ipcMain.on("calibration-testing-start", () => {
  if (calOverlay) {
    // Let clicks pass through to OneNote for the test square
    calOverlay.setIgnoreMouseEvents(true, { forward: true });
    log("Calibration testing started - ignoring mouse events");
  }
});

ipcMain.on("calibration-testing-end", () => {
  if (calOverlay) {
    // Restore normal behavior to capture clicks on buttons
    calOverlay.setIgnoreMouseEvents(false);
    log("Calibration testing ended - restoring mouse events");
  }
});

// Points received from overlay
ipcMain.on("calibration-done", (_, points) => {
  log("Calibration points received: " + JSON.stringify(points));
  if (mainWindow) {
    mainWindow.restore();
    mainWindow.focus();
    mainWindow.webContents.send("calibration-points", points);
  }
  if (calOverlay) { calOverlay.close(); calOverlay = null; }
});

ipcMain.on("calibration-cancel", () => {
  log("Calibration cancelled");
  if (mainWindow) {
    mainWindow.restore();
    mainWindow.focus();
    mainWindow.webContents.send("calibration-cancelled");
  }
  if (calOverlay) { calOverlay.close(); calOverlay = null; }
});

app.whenReady().then(async () => {
  log("=== InkFlow v3 starting ===");
  log("Packaged: " + IS_PACKAGED + " | Resources: " + RESOURCES_DIR);
  spawnBackend();
  try { await waitForBackend(); } catch (e) { log("Backend warn: " + e.message); }
  createWindow();
  app.on("activate", () => { if (!BrowserWindow.getAllWindows().length) createWindow(); });
});

app.on("window-all-closed", () => { killBackend(); if (process.platform !== "darwin") app.quit(); });
app.on("before-quit", () => killBackend());
app.on("will-quit", () => killBackend());
