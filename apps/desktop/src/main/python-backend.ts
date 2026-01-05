/**
 * Python backend process management.
 */

import { spawn, ChildProcess } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';
import * as os from 'os';
import { app } from 'electron';

/**
 * Manages the Python backend subprocess.
 */
export class PythonBackend {
  private process: ChildProcess | null = null;
  private _socketPath: string;
  private _isRunning = false;

  constructor() {
    // Generate unique socket path
    const tempDir = os.tmpdir();
    this._socketPath = path.join(tempDir, `scenemachine-${process.pid}.sock`);
  }

  /**
   * Get the socket path for IPC communication.
   */
  get socketPath(): string {
    return this._socketPath;
  }

  /**
   * Check if backend is running.
   */
  get isRunning(): boolean {
    return this._isRunning;
  }

  /**
   * Start the Python backend.
   */
  async start(): Promise<void> {
    const pythonPath = this.findPython();
    const scriptPath = this.findBackendScript();
    const backendDir = this.findBackendDir();

    console.log(`Starting Python backend: ${pythonPath} ${scriptPath}`);
    console.log(`Socket path: ${this._socketPath}`);
    console.log(`Backend dir (PYTHONPATH): ${backendDir}`);

    return new Promise((resolve, reject) => {
      this.process = spawn(pythonPath, [scriptPath], {
        env: {
          ...process.env,
          SCENEMACHINE_SOCKET_PATH: this._socketPath,
          SCENEMACHINE_DEBUG: process.env.NODE_ENV === 'development' ? '1' : '0',
          PYTHONUNBUFFERED: '1',
          PYTHONPATH: backendDir,
        },
        cwd: backendDir,
        stdio: ['pipe', 'pipe', 'pipe'],
      });

      let startupTimeout: NodeJS.Timeout | null = null;

      this.process.stdout?.on('data', (data) => {
        const output = data.toString().trim();
        console.log(`[Python] ${output}`);

        // Check for startup signal
        if (output.includes('IPC server started')) {
          this._isRunning = true;
          if (startupTimeout) {
            clearTimeout(startupTimeout);
          }
          resolve();
        }
      });

      this.process.stderr?.on('data', (data) => {
        console.error(`[Python Error] ${data.toString().trim()}`);
      });

      this.process.on('exit', (code, signal) => {
        this._isRunning = false;
        if (code !== 0 && code !== null) {
          console.error(`Python backend exited with code ${code}, signal ${signal}`);
        }
      });

      this.process.on('error', (error) => {
        this._isRunning = false;
        reject(new Error(`Failed to start Python backend: ${error.message}`));
      });

      // Startup timeout
      startupTimeout = setTimeout(() => {
        if (!this._isRunning) {
          this.process?.kill();
          reject(new Error('Python backend startup timeout'));
        }
      }, 30000);
    });
  }

  /**
   * Stop the Python backend.
   */
  async stop(): Promise<void> {
    if (!this.process) {
      return;
    }

    console.log('Stopping Python backend...');

    // Send SIGTERM first
    this.process.kill('SIGTERM');

    // Wait for graceful shutdown
    await new Promise<void>((resolve) => {
      const timeout = setTimeout(() => {
        console.log('Force killing Python backend...');
        this.process?.kill('SIGKILL');
        resolve();
      }, 5000);

      this.process?.on('exit', () => {
        clearTimeout(timeout);
        resolve();
      });
    });

    this.process = null;

    // Clean up socket file
    if (fs.existsSync(this._socketPath)) {
      fs.unlinkSync(this._socketPath);
    }

    console.log('Python backend stopped');
  }

  /**
   * Find Python executable.
   */
  private findPython(): string {
    // Check for custom Python path first
    const customPath = process.env.PYTHON_PATH;
    if (customPath && fs.existsSync(customPath)) {
      return customPath;
    }

    // Determine if running in development mode
    const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;

    // In development or when not packaged, use system Python
    if (isDev) {
      // Try common Python paths including miniconda/anaconda
      const homeDir = os.homedir();
      const candidates = [
        'python3',
        'python',
        path.join(homeDir, 'miniconda3/bin/python3'),
        path.join(homeDir, 'miniconda3/bin/python'),
        path.join(homeDir, 'anaconda3/bin/python3'),
        path.join(homeDir, 'anaconda3/bin/python'),
        '/usr/bin/python3',
        '/usr/local/bin/python3',
      ];

      for (const candidate of candidates) {
        try {
          if (candidate.startsWith('/') || candidate.includes(homeDir)) {
            // Absolute path - check if exists
            if (fs.existsSync(candidate)) {
              return candidate;
            }
          } else {
            // Command name - try to execute
            require('child_process').execSync(`${candidate} --version`, { stdio: 'ignore' });
            return candidate;
          }
        } catch {
          continue;
        }
      }
    }

    // In production, use bundled Python
    const resourcesPath = process.resourcesPath || app.getAppPath();

    // Platform-specific paths
    const pythonPaths = [
      path.join(resourcesPath, 'python', 'bin', 'python3'), // Linux/macOS
      path.join(resourcesPath, 'python', 'python.exe'), // Windows
    ];

    for (const pythonPath of pythonPaths) {
      if (fs.existsSync(pythonPath)) {
        return pythonPath;
      }
    }

    throw new Error('Python not found. Please install Python 3.11 or later.');
  }

  /**
   * Find the backend directory (for PYTHONPATH).
   */
  private findBackendDir(): string {
    const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;

    if (isDev) {
      const possiblePaths = [
        path.join(__dirname, '..', '..', '..', '..', 'packages', 'core'),
        path.resolve(process.cwd(), 'packages/core'),
        path.resolve(process.cwd(), '../../packages/core'),
        '/home/user1-gpu/Desktop/SceneMachine/packages/core',
      ];

      for (const devPath of possiblePaths) {
        if (fs.existsSync(path.join(devPath, 'scenemachine'))) {
          return devPath;
        }
      }
    }

    // In production, use bundled backend
    const resourcesPath = process.resourcesPath || app.getAppPath();
    return path.join(resourcesPath, 'backend');
  }

  /**
   * Find the backend script.
   */
  private findBackendScript(): string {
    // Determine if running in development mode
    const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;

    // In development or when not packaged, use source directory
    if (isDev) {
      // Try various paths relative to the app location
      const possiblePaths = [
        // From dist/main relative to packages
        path.join(__dirname, '..', '..', '..', '..', 'packages', 'core', 'scenemachine', 'main.py'),
        // From current working directory
        path.resolve(process.cwd(), 'packages/core/scenemachine/main.py'),
        // From apps/desktop relative path
        path.resolve(process.cwd(), '../../packages/core/scenemachine/main.py'),
        // Absolute path from monorepo root
        '/home/user1-gpu/Desktop/SceneMachine/packages/core/scenemachine/main.py',
      ];

      for (const devPath of possiblePaths) {
        if (fs.existsSync(devPath)) {
          return devPath;
        }
      }
    }

    // In production, use bundled backend
    const resourcesPath = process.resourcesPath || app.getAppPath();
    const prodPath = path.join(resourcesPath, 'backend', 'scenemachine', 'main.py');

    if (fs.existsSync(prodPath)) {
      return prodPath;
    }

    throw new Error('Backend script not found');
  }
}
