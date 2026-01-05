/**
 * Electron main process entry point.
 */

import { app, BrowserWindow, dialog, ipcMain, OpenDialogOptions, SaveDialogOptions } from 'electron';
import * as path from 'path';
import { PythonBackend } from './python-backend';
import { IPCClient } from './ipc-client';

class Application {
  private pythonBackend: PythonBackend | null = null;
  private ipcClient: IPCClient | null = null;
  private mainWindow: BrowserWindow | null = null;
  private isQuitting = false;

  /**
   * Start the application.
   */
  async start(): Promise<void> {
    // Ensure single instance
    const gotLock = app.requestSingleInstanceLock();
    if (!gotLock) {
      app.quit();
      return;
    }

    app.on('second-instance', () => {
      this.focusMainWindow();
    });

    await app.whenReady();

    try {
      await this.initialize();
    } catch (error) {
      console.error('Startup error:', error);
      dialog.showErrorBox('Startup Error', `Failed to start SceneMachine: ${error}`);
      app.quit();
    }
  }

  /**
   * Initialize the application.
   */
  private async initialize(): Promise<void> {
    console.log('Starting SceneMachine...');

    // Start Python backend
    this.pythonBackend = new PythonBackend();
    await this.pythonBackend.start();
    console.log('Python backend started');

    // Connect IPC client
    this.ipcClient = new IPCClient(this.pythonBackend.socketPath);
    await this.ipcClient.connect();
    console.log('IPC client connected');

    // Set up IPC handlers
    this.setupIPCHandlers();

    // Create main window
    await this.createMainWindow();

    // Set up app event handlers
    this.setupAppEvents();

    console.log('SceneMachine started successfully');
  }

  /**
   * Create the main application window.
   */
  private async createMainWindow(): Promise<void> {
    this.mainWindow = new BrowserWindow({
      width: 1400,
      height: 900,
      minWidth: 1024,
      minHeight: 768,
      title: 'SceneMachine',
      backgroundColor: '#09090b', // surface-950
      webPreferences: {
        preload: path.join(__dirname, '../preload/index.js'),
        contextIsolation: true,
        nodeIntegration: false,
        sandbox: true,
      },
      show: false, // Show when ready
    });

    // Show window when ready
    this.mainWindow.once('ready-to-show', () => {
      this.mainWindow?.show();
    });

    // Handle window close
    this.mainWindow.on('close', (event) => {
      if (!this.isQuitting) {
        event.preventDefault();
        this.mainWindow?.hide();
      }
    });

    this.mainWindow.on('closed', () => {
      this.mainWindow = null;
    });

    // Load the app
    if (process.env.NODE_ENV === 'development') {
      // Development: load from Vite dev server
      await this.mainWindow.loadURL('http://localhost:5173');
      this.mainWindow.webContents.openDevTools();
    } else {
      // Production: load from built files
      await this.mainWindow.loadFile(path.join(__dirname, '../renderer/index.html'));
    }
  }

  /**
   * Set up IPC handlers for renderer communication.
   */
  private setupIPCHandlers(): void {
    // Backend request handler
    ipcMain.handle('backend:request', async (_event, method: string, params?: unknown) => {
      if (!this.ipcClient) {
        throw new Error('Backend not connected');
      }
      return this.ipcClient.request(method, params as Record<string, unknown>);
    });

    // File dialog handlers
    ipcMain.handle('dialog:openFile', async (_event, options: OpenDialogOptions) => {
      return dialog.showOpenDialog(options);
    });

    ipcMain.handle('dialog:saveFile', async (_event, options: SaveDialogOptions) => {
      return dialog.showSaveDialog(options);
    });

    // App info
    ipcMain.handle('app:info', () => {
      return {
        platform: process.platform,
        versions: {
          node: process.versions.node,
          electron: process.versions.electron,
          chrome: process.versions.chrome,
        },
      };
    });
  }

  /**
   * Set up application event handlers.
   */
  private setupAppEvents(): void {
    app.on('window-all-closed', () => {
      if (process.platform !== 'darwin') {
        this.quit();
      }
    });

    app.on('activate', () => {
      if (BrowserWindow.getAllWindows().length === 0) {
        this.createMainWindow();
      } else {
        this.focusMainWindow();
      }
    });

    app.on('before-quit', (event) => {
      if (!this.isQuitting) {
        event.preventDefault();
        this.quit();
      }
    });
  }

  /**
   * Focus the main window.
   */
  private focusMainWindow(): void {
    if (this.mainWindow) {
      if (this.mainWindow.isMinimized()) {
        this.mainWindow.restore();
      }
      this.mainWindow.show();
      this.mainWindow.focus();
    }
  }

  /**
   * Quit the application gracefully.
   */
  private async quit(): Promise<void> {
    this.isQuitting = true;
    console.log('Shutting down...');

    // Disconnect IPC
    this.ipcClient?.disconnect();

    // Stop Python backend
    await this.pythonBackend?.stop();

    console.log('Shutdown complete');
    app.quit();
  }
}

// Start the application
const application = new Application();
application.start();
