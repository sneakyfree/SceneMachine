/**
 * Type definitions for Electron API exposed via preload.
 */

interface FileFilter {
  name: string;
  extensions: string[];
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

interface AppInfo {
  platform: string;
  versions: {
    node: string;
    electron: string;
    chrome: string;
  };
}

interface ElectronAPI {
  backendRequest: <T>(method: string, params?: Record<string, unknown>) => Promise<T>;
  openFile: (options: OpenDialogOptions) => Promise<OpenDialogResult>;
  saveFile: (options: SaveDialogOptions) => Promise<SaveDialogResult>;
  getAppInfo: () => Promise<AppInfo>;
  platform: string;
}

declare global {
  interface Window {
    electronAPI: ElectronAPI;
  }
}

export {};
