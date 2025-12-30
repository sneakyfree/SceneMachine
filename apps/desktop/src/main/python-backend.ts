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

    console.log(`Starting Python backend: ${pythonPath} ${scriptPath}`);
    console.log(`Socket path: ${this._socketPath}`);

    return new Promise((resolve, reject) => {
      this.process = spawn(pythonPath, [scriptPath], {
        env: {
          ...process.env,
          SCENEMACHINE_SOCKET_PATH: this._socketPath,
          SCENEMACHINE_DEBUG: process.env.NODE_ENV === 'development' ? '1' : '0',
          PYTHONUNBUFFERED: '1',
        },
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
    // In development, use system Python
    if (process.env.NODE_ENV === 'development') {
      const customPath = process.env.PYTHON_PATH;
      if (customPath && fs.existsSync(customPath)) {
        return customPath;
      }

      // Try common Python paths
      const candidates = ['python3', 'python'];
      for (const candidate of candidates) {
        try {
          require('child_process').execSync(`${candidate} --version`, { stdio: 'ignore' });
          return candidate;
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
   * Find the backend script.
   */
  private findBackendScript(): string {
    // In development, use source directory
    if (process.env.NODE_ENV === 'development') {
      const devPath = path.join(
        __dirname,
        '..',
        '..',
        '..',
        '..',
        'packages',
        'core',
        'scenemachine',
        'main.py'
      );

      if (fs.existsSync(devPath)) {
        return devPath;
      }

      // Try alternative path
      const altPath = path.resolve(process.cwd(), 'packages/core/scenemachine/main.py');
      if (fs.existsSync(altPath)) {
        return altPath;
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
