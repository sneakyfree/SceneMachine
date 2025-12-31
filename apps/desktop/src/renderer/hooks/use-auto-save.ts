/**
 * React hook for auto-save functionality.
 */

import { useEffect, useCallback, useState, useRef } from 'react';
import {
  AutoSaveManager,
  AutoSaveConfig,
  AutoSaveState,
  RecoveryInfo,
  getAutoSaveManager,
} from '../lib/auto-save';

export type { AutoSaveConfig, AutoSaveState, RecoveryInfo };

interface UseAutoSaveOptions<T> {
  projectId: string;
  getData: () => T;
  onRecover?: (data: T) => void;
  enabled?: boolean;
}

interface UseAutoSaveReturn {
  isDirty: boolean;
  lastSaved: number | null;
  markDirty: () => void;
  saveNow: () => void;
  recovery: RecoveryInfo | null;
  recover: () => void;
  dismissRecovery: () => void;
  versionHistory: AutoSaveState[];
  recoverVersion: (version: number) => void;
}

/**
 * Hook for project auto-save
 */
export function useAutoSave<T>({
  projectId,
  getData,
  onRecover,
  enabled = true,
}: UseAutoSaveOptions<T>): UseAutoSaveReturn {
  const [isDirty, setIsDirty] = useState(false);
  const [lastSaved, setLastSaved] = useState<number | null>(null);
  const [recovery, setRecovery] = useState<RecoveryInfo | null>(null);
  const [versionHistory, setVersionHistory] = useState<AutoSaveState[]>([]);

  const managerRef = useRef<AutoSaveManager | null>(null);
  const getDataRef = useRef(getData);
  getDataRef.current = getData;

  // Initialize manager
  useEffect(() => {
    if (!enabled) return;

    const manager = getAutoSaveManager();
    managerRef.current = manager;

    // Check for recovery
    const pendingRecovery = manager.checkRecovery(projectId);
    if (pendingRecovery) {
      setRecovery(pendingRecovery);
    }

    // Load version history
    setVersionHistory(manager.getVersionHistory(projectId));

    // Load last saved time
    const autoSave = manager.getAutoSave(projectId);
    if (autoSave) {
      setLastSaved(autoSave.timestamp);
    }

    // Start auto-save
    manager.start(projectId, () => getDataRef.current(), (data) => {
      if (onRecover) {
        onRecover(data as T);
      }
    });

    return () => {
      manager.stop();
    };
  }, [projectId, enabled]);

  // Listen for save events
  useEffect(() => {
    const handleSaved = (event: CustomEvent<{ projectId: string; timestamp: number }>) => {
      if (event.detail.projectId === projectId) {
        setLastSaved(event.detail.timestamp);
        setIsDirty(false);

        // Update version history
        const manager = managerRef.current;
        if (manager) {
          setVersionHistory(manager.getVersionHistory(projectId));
        }
      }
    };

    window.addEventListener('autosave:saved', handleSaved as EventListener);
    return () => {
      window.removeEventListener('autosave:saved', handleSaved as EventListener);
    };
  }, [projectId]);

  // Mark dirty
  const markDirty = useCallback(() => {
    setIsDirty(true);
    managerRef.current?.markDirty();
  }, []);

  // Save now
  const saveNow = useCallback(() => {
    managerRef.current?.saveNow();
  }, []);

  // Recover from auto-save
  const recover = useCallback(() => {
    const manager = managerRef.current;
    if (manager && onRecover) {
      const data = manager.recover(projectId);
      if (data) {
        onRecover(data as T);
        setRecovery(null);
      }
    }
  }, [projectId, onRecover]);

  // Dismiss recovery
  const dismissRecovery = useCallback(() => {
    managerRef.current?.dismissRecovery();
    setRecovery(null);
  }, []);

  // Recover specific version
  const recoverVersion = useCallback(
    (version: number) => {
      const manager = managerRef.current;
      if (manager && onRecover) {
        const data = manager.recoverVersion(projectId, version);
        if (data) {
          onRecover(data as T);
        }
      }
    },
    [projectId, onRecover]
  );

  return {
    isDirty,
    lastSaved,
    markDirty,
    saveNow,
    recovery,
    recover,
    dismissRecovery,
    versionHistory,
    recoverVersion,
  };
}

/**
 * Hook for checking pending recovery on app startup
 */
export function usePendingRecovery(): {
  recovery: RecoveryInfo | null;
  dismiss: () => void;
} {
  const [recovery, setRecovery] = useState<RecoveryInfo | null>(() => {
    return getAutoSaveManager().getPendingRecovery();
  });

  const dismiss = useCallback(() => {
    getAutoSaveManager().dismissRecovery();
    setRecovery(null);
  }, []);

  return { recovery, dismiss };
}

/**
 * Hook for auto-save settings management
 */
export function useAutoSaveSettings(): {
  config: AutoSaveConfig;
  updateConfig: (config: Partial<AutoSaveConfig>) => void;
  stats: { projectCount: number; totalSize: number; lastSave: number | null };
  clearAll: () => void;
} {
  const manager = getAutoSaveManager();
  const [config, setConfig] = useState<AutoSaveConfig>(() => manager.getConfig());
  const [stats, setStats] = useState(() => manager.getStats());

  const updateConfig = useCallback((newConfig: Partial<AutoSaveConfig>) => {
    manager.updateConfig(newConfig);
    setConfig(manager.getConfig());
  }, []);

  const clearAll = useCallback(() => {
    manager.clearAll();
    setStats(manager.getStats());
  }, []);

  // Refresh stats periodically
  useEffect(() => {
    const interval = setInterval(() => {
      setStats(manager.getStats());
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  return { config, updateConfig, stats, clearAll };
}

/**
 * Simple hook for marking state changes as dirty
 */
export function useDirtyState<T>(
  value: T,
  markDirty: () => void,
  deps: any[] = []
): void {
  const prevRef = useRef<T>(value);
  const isFirstRender = useRef(true);

  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }

    // Check if value changed
    if (JSON.stringify(prevRef.current) !== JSON.stringify(value)) {
      markDirty();
      prevRef.current = value;
    }
  }, [value, markDirty, ...deps]);
}
