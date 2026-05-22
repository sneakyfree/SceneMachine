/**
 * Auto-save and crash recovery system.
 * Provides automatic background saving and recovery from crashes.
 */

// Storage keys
const AUTOSAVE_PREFIX = 'scenemachine:autosave:';
const RECOVERY_KEY = 'scenemachine:recovery';
const SESSION_KEY = 'scenemachine:session';

// Types
export interface AutoSaveState {
  projectId: string;
  timestamp: number;
  data: any;
  version: number;
}

export interface RecoveryInfo {
  projectId: string;
  projectName: string;
  timestamp: number;
  reason: 'crash' | 'unclean_exit' | 'manual';
}

export interface AutoSaveConfig {
  enabled: boolean;
  intervalMs: number;
  maxVersions: number;
  debounceMs: number;
}

// Default configuration
const DEFAULT_CONFIG: AutoSaveConfig = {
  enabled: true,
  intervalMs: 30000, // Auto-save every 30 seconds
  maxVersions: 5, // Keep last 5 versions
  debounceMs: 2000, // Debounce rapid changes
};

/**
 * AutoSaveManager handles automatic saving and recovery
 */
export class AutoSaveManager {
  private config: AutoSaveConfig;
  private intervalId: ReturnType<typeof setInterval> | null = null;
  private currentProjectId: string | null = null;
  private isDirty: boolean = false;
  private saveVersion: number = 0;
  private getData: (() => any) | null = null;
  private onRecover: ((data: any) => void) | null = null;

  constructor(config: Partial<AutoSaveConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.initSession();
  }

  /**
   * Initialize session tracking for crash detection
   */
  private initSession(): void {
    const existingSession = sessionStorage.getItem(SESSION_KEY);

    if (existingSession) {
      // Previous session exists - check for unclean exit
      const session = JSON.parse(existingSession);
      if (session.active) {
        // Previous session didn't close cleanly
        this.markForRecovery(session.projectId, 'unclean_exit');
      }
    }

    // Mark current session as active
    this.updateSession(true);

    // Set up beforeunload to mark clean exit
    window.addEventListener('beforeunload', this.handleBeforeUnload);

    // Set up visibility change for background saves
    document.addEventListener('visibilitychange', this.handleVisibilityChange);
  }

  private handleBeforeUnload = (): void => {
    // Mark session as cleanly closed
    this.updateSession(false);

    // Final save on exit
    if (this.isDirty && this.currentProjectId && this.getData) {
      this.saveNow();
    }
  };

  private handleVisibilityChange = (): void => {
    // Save when tab goes to background
    if (document.hidden && this.isDirty && this.currentProjectId) {
      this.saveNow();
    }
  };

  private updateSession(active: boolean): void {
    sessionStorage.setItem(
      SESSION_KEY,
      JSON.stringify({
        projectId: this.currentProjectId,
        active,
        timestamp: Date.now(),
      })
    );
  }

  /**
   * Mark a project for recovery
   */
  private markForRecovery(projectId: string, reason: RecoveryInfo['reason']): void {
    const savedState = this.getAutoSave(projectId);
    if (!savedState) return;

    const recoveryInfo: RecoveryInfo = {
      projectId,
      projectName: savedState.data?.name || 'Unknown Project',
      timestamp: savedState.timestamp,
      reason,
    };

    localStorage.setItem(RECOVERY_KEY, JSON.stringify(recoveryInfo));
  }

  /**
   * Start auto-save for a project
   */
  start(projectId: string, getData: () => any, onRecover?: (data: any) => void): void {
    this.stop();

    this.currentProjectId = projectId;
    this.getData = getData;
    this.onRecover = onRecover || null;
    this.isDirty = false;
    this.saveVersion = 0;

    this.updateSession(true);

    // Check for recovery
    const recovery = this.checkRecovery(projectId);
    if (recovery && onRecover) {
      // Will be handled by caller
    }

    if (this.config.enabled) {
      // Start interval-based auto-save
      this.intervalId = setInterval(() => {
        if (this.isDirty) {
          this.saveNow();
        }
      }, this.config.intervalMs);
    }
  }

  /**
   * Stop auto-save
   */
  stop(): void {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }

    // Final save before stopping
    if (this.isDirty && this.currentProjectId && this.getData) {
      this.saveNow();
    }

    this.currentProjectId = null;
    this.getData = null;
    this.isDirty = false;
  }

  /**
   * Mark data as changed (dirty)
   */
  markDirty(): void {
    this.isDirty = true;
    this.debouncedSave();
  }

  /**
   * Debounced save function
   */
  private debouncedSave = debounce(() => {
    if (this.isDirty) {
      this.saveNow();
    }
  }, DEFAULT_CONFIG.debounceMs);

  /**
   * Save immediately
   */
  saveNow(): void {
    if (!this.currentProjectId || !this.getData) return;

    try {
      const data = this.getData();
      const state: AutoSaveState = {
        projectId: this.currentProjectId,
        timestamp: Date.now(),
        data,
        version: ++this.saveVersion,
      };

      // Save current version
      localStorage.setItem(`${AUTOSAVE_PREFIX}${this.currentProjectId}`, JSON.stringify(state));

      // Save to version history
      this.saveVersionHistory(state);

      this.isDirty = false;

      // Dispatch event for UI updates
      window.dispatchEvent(
        new CustomEvent('autosave:saved', {
          detail: { projectId: this.currentProjectId, timestamp: state.timestamp },
        })
      );
    } catch (error) {
      console.error('Auto-save failed:', error);
      window.dispatchEvent(new CustomEvent('autosave:error', { detail: { error } }));
    }
  }

  /**
   * Save to version history for recovery
   */
  private saveVersionHistory(state: AutoSaveState): void {
    const historyKey = `${AUTOSAVE_PREFIX}history:${state.projectId}`;
    let history: AutoSaveState[] = [];

    try {
      const stored = localStorage.getItem(historyKey);
      if (stored) {
        history = JSON.parse(stored);
      }
    } catch {
      history = [];
    }

    // Add new version
    history.unshift(state);

    // Trim to max versions
    if (history.length > this.config.maxVersions) {
      history = history.slice(0, this.config.maxVersions);
    }

    localStorage.setItem(historyKey, JSON.stringify(history));
  }

  /**
   * Get the latest auto-save for a project
   */
  getAutoSave(projectId: string): AutoSaveState | null {
    try {
      const stored = localStorage.getItem(`${AUTOSAVE_PREFIX}${projectId}`);
      if (stored) {
        return JSON.parse(stored);
      }
    } catch {
      // Ignore parse errors
    }
    return null;
  }

  /**
   * Get version history for a project
   */
  getVersionHistory(projectId: string): AutoSaveState[] {
    try {
      const stored = localStorage.getItem(`${AUTOSAVE_PREFIX}history:${projectId}`);
      if (stored) {
        return JSON.parse(stored);
      }
    } catch {
      // Ignore parse errors
    }
    return [];
  }

  /**
   * Check if there's a recovery available
   */
  checkRecovery(projectId: string): RecoveryInfo | null {
    try {
      const stored = localStorage.getItem(RECOVERY_KEY);
      if (stored) {
        const recovery: RecoveryInfo = JSON.parse(stored);
        if (recovery.projectId === projectId) {
          return recovery;
        }
      }
    } catch {
      // Ignore parse errors
    }
    return null;
  }

  /**
   * Get any pending recovery (for startup check)
   */
  getPendingRecovery(): RecoveryInfo | null {
    try {
      const stored = localStorage.getItem(RECOVERY_KEY);
      if (stored) {
        return JSON.parse(stored);
      }
    } catch {
      // Ignore parse errors
    }
    return null;
  }

  /**
   * Recover from auto-save
   */
  recover(projectId: string): any | null {
    const state = this.getAutoSave(projectId);
    if (state) {
      // Clear recovery marker
      localStorage.removeItem(RECOVERY_KEY);
      return state.data;
    }
    return null;
  }

  /**
   * Recover from a specific version
   */
  recoverVersion(projectId: string, version: number): any | null {
    const history = this.getVersionHistory(projectId);
    const state = history.find((s) => s.version === version);
    if (state) {
      return state.data;
    }
    return null;
  }

  /**
   * Dismiss recovery (user chose not to recover)
   */
  dismissRecovery(): void {
    localStorage.removeItem(RECOVERY_KEY);
  }

  /**
   * Clear auto-save data for a project
   */
  clearAutoSave(projectId: string): void {
    localStorage.removeItem(`${AUTOSAVE_PREFIX}${projectId}`);
    localStorage.removeItem(`${AUTOSAVE_PREFIX}history:${projectId}`);
  }

  /**
   * Clear all auto-save data
   */
  clearAll(): void {
    const keysToRemove: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key?.startsWith(AUTOSAVE_PREFIX)) {
        keysToRemove.push(key);
      }
    }
    keysToRemove.forEach((key) => localStorage.removeItem(key));
    localStorage.removeItem(RECOVERY_KEY);
  }

  /**
   * Get auto-save statistics
   */
  getStats(): {
    projectCount: number;
    totalSize: number;
    lastSave: number | null;
  } {
    let projectCount = 0;
    let totalSize = 0;
    let lastSave: number | null = null;

    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key?.startsWith(AUTOSAVE_PREFIX) && !key.includes('history:')) {
        projectCount++;
        const value = localStorage.getItem(key) || '';
        totalSize += value.length * 2; // UTF-16

        try {
          const state: AutoSaveState = JSON.parse(value);
          if (!lastSave || state.timestamp > lastSave) {
            lastSave = state.timestamp;
          }
        } catch {
          // Ignore
        }
      }
    }

    return { projectCount, totalSize, lastSave };
  }

  /**
   * Update configuration
   */
  updateConfig(config: Partial<AutoSaveConfig>): void {
    this.config = { ...this.config, ...config };

    // Restart interval if needed
    if (this.intervalId && this.currentProjectId) {
      clearInterval(this.intervalId);
      if (this.config.enabled) {
        this.intervalId = setInterval(() => {
          if (this.isDirty) {
            this.saveNow();
          }
        }, this.config.intervalMs);
      }
    }
  }

  /**
   * Get current configuration
   */
  getConfig(): AutoSaveConfig {
    return { ...this.config };
  }
}

// Singleton instance
let autoSaveManager: AutoSaveManager | null = null;

/**
 * Get the auto-save manager instance
 */
export function getAutoSaveManager(): AutoSaveManager {
  if (!autoSaveManager) {
    autoSaveManager = new AutoSaveManager();
  }
  return autoSaveManager;
}

/**
 * Simple debounce utility
 */
function debounce<T extends (...args: any[]) => void>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout> | null = null;

  return (...args: Parameters<T>) => {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
    timeoutId = setTimeout(() => {
      fn(...args);
      timeoutId = null;
    }, delay);
  };
}
