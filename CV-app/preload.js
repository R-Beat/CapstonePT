// Preload script for Electron renderer. Keep minimal and secure.
const { contextBridge } = require('electron');

// Expose a minimal safe API if needed in the future
contextBridge.exposeInMainWorld('electronAPI', {
  // placeholder
});
