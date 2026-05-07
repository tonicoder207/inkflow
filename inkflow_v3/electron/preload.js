const { contextBridge, ipcRenderer } = require("electron");
contextBridge.exposeInMainWorld("inkflow", {
  getAppInfo:        () => ipcRenderer.invoke("get-app-info"),
  getBackendStatus:  () => ipcRenderer.invoke("backend-status"),
  openExportsFolder: () => ipcRenderer.invoke("open-exports-folder"),
  showSaveDialog: o  => ipcRenderer.invoke("show-save-dialog", o),
  setAlwaysOnTop: (flag, level) => ipcRenderer.invoke("set-always-on-top", flag, level),
  setFullscreen: flag => ipcRenderer.invoke("set-fullscreen", flag),
  
  // Calibration overlay
  startCalibration: () => ipcRenderer.invoke("start-calibration"),
  onCalibrationPoints: (cb) => {
    ipcRenderer.on("calibration-points", (_, points) => cb(points));
  },
  onCalibrationCancelled: (cb) => {
    ipcRenderer.on("calibration-cancelled", () => cb());
  },
  removeCalibrationListeners: () => {
    ipcRenderer.removeAllListeners("calibration-points");
    ipcRenderer.removeAllListeners("calibration-cancelled");
  },

  // Escape to Cancel Writing
  registerEscCancel: () => ipcRenderer.send("register-esc-cancel"),
  unregisterEscCancel: () => ipcRenderer.send("unregister-esc-cancel"),
  onEscPressed: (cb) => {
    ipcRenderer.on("esc-pressed", () => cb());
  },
  removeEscListeners: () => {
    ipcRenderer.removeAllListeners("esc-pressed");
  },

  platform:  process.platform,
  isDesktop: true,
});
