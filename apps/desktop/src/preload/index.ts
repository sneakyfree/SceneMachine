/**
 * Electron preload script.
 *
 * Exposes a safe, limited API to the renderer process.
 */

import { contextBridge, ipcRenderer } from 'electron';

// Type definitions for exposed API
interface ElectronAPI {
  backendRequest: <T>(method: string, params?: Record<string, unknown>) => Promise<T>;
  openFile: (options: OpenDialogOptions) => Promise<OpenDialogResult>;
  saveFile: (options: SaveDialogOptions) => Promise<SaveDialogResult>;
  getAppInfo: () => Promise<AppInfo>;
  platform: string;
}

interface OpenDialogOptions {
  title?: string;
  defaultPath?: string;
  filters?: FileFilter[];
  properties?: Array<'openFile' | 'openDirectory' | 'multiSelections'>;
}

interface OpenDialogResult {
  canceled: boolean;
  filePaths: string[];
}

interface SaveDialogOptions {
  title?: string;
  defaultPath?: string;
  filters?: FileFilter[];
}

interface SaveDialogResult {
  canceled: boolean;
  filePath?: string;
}

interface FileFilter {
  name: string;
  extensions: string[];
}

interface AppInfo {
  platform: string;
  versions: {
    node: string;
    electron: string;
    chrome: string;
  };
}

// Expose API to renderer
const electronAPI: ElectronAPI = {
  /**
   * Send a request to the Python backend.
   */
  backendRequest: <T>(method: string, params?: Record<string, unknown>): Promise<T> => {
    return ipcRenderer.invoke('backend:request', method, params);
  },

  /**
   * Open a file dialog.
   */
  openFile: (options: OpenDialogOptions): Promise<OpenDialogResult> => {
    return ipcRenderer.invoke('dialog:openFile', options);
  },

  /**
   * Open a save dialog.
   */
  saveFile: (options: SaveDialogOptions): Promise<SaveDialogResult> => {
    return ipcRenderer.invoke('dialog:saveFile', options);
  },

  /**
   * Get application info.
   */
  getAppInfo: (): Promise<AppInfo> => {
    return ipcRenderer.invoke('app:info');
  },

  /**
   * Current platform.
   */
  platform: process.platform,
};

// Expose in main world
contextBridge.exposeInMainWorld('electronAPI', electronAPI);

// Log preload completion
console.log('Preload script loaded');
