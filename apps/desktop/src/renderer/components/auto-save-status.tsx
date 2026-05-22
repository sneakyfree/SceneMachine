/**
 * Auto-Save Status Indicator Component
 *
 * Shows real-time auto-save status with visual feedback,
 * version history access, and recovery options.
 */

import { memo, useState, useEffect, useCallback } from 'react';
import {
  Cloud,
  CloudOff,
  Check,
  AlertCircle,
  Clock,
  History,
  RefreshCw,
  ChevronDown,
  Save,
  Loader2,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { getAutoSaveManager, AutoSaveState, RecoveryInfo } from '../lib/auto-save';

// =============================================================================
// Types
// =============================================================================

export type SaveStatus = 'idle' | 'saving' | 'saved' | 'error' | 'offline';

interface AutoSaveStatusProps {
  /**
   * Current project ID
   */
  projectId?: string;

  /**
   * Display mode
   */
  mode?: 'icon' | 'badge' | 'full';

  /**
   * Show version history dropdown
   */
  showHistory?: boolean;

  /**
   * Called when a version is selected for recovery
   */
  onRecoverVersion?: (data: unknown) => void;

  /**
   * Called when manual save is triggered
   */
  onManualSave?: () => void;

  /**
   * Additional CSS classes
   */
  className?: string;
}

// =============================================================================
// Helper Functions
// =============================================================================

function formatRelativeTime(timestamp: number): string {
  const now = Date.now();
  const diff = now - timestamp;

  if (diff < 1000) return 'just now';
  if (diff < 60000) return `${Math.floor(diff / 1000)}s ago`;
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  return new Date(timestamp).toLocaleDateString();
}

function formatTime(timestamp: number): string {
  return new Date(timestamp).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  });
}

// =============================================================================
// Status Icon Component
// =============================================================================

const StatusIcon = memo(function StatusIcon({
  status,
  className,
}: {
  status: SaveStatus;
  className?: string;
}) {
  switch (status) {
    case 'saving':
      return <Loader2 className={cn('animate-spin', className)} />;
    case 'saved':
      return <Cloud className={className} />;
    case 'error':
      return <CloudOff className={className} />;
    case 'offline':
      return <CloudOff className={className} />;
    default:
      return <Cloud className={className} />;
  }
});

// =============================================================================
// Main Component
// =============================================================================

export const AutoSaveStatus = memo(function AutoSaveStatus({
  projectId,
  mode = 'badge',
  showHistory = true,
  onRecoverVersion,
  onManualSave,
  className,
}: AutoSaveStatusProps) {
  const [status, setStatus] = useState<SaveStatus>('idle');
  const [lastSaved, setLastSaved] = useState<number | null>(null);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [versionHistory, setVersionHistory] = useState<AutoSaveState[]>([]);
  const [pendingRecovery, setPendingRecovery] = useState<RecoveryInfo | null>(null);

  // Listen for auto-save events
  useEffect(() => {
    const handleSaved = (event: CustomEvent<{ projectId: string; timestamp: number }>) => {
      if (event.detail.projectId === projectId) {
        setStatus('saved');
        setLastSaved(event.detail.timestamp);

        // Reset to idle after showing saved
        setTimeout(() => setStatus('idle'), 2000);
      }
    };

    const handleError = () => {
      setStatus('error');
      setTimeout(() => setStatus('idle'), 5000);
    };

    const handleSaving = () => {
      setStatus('saving');
    };

    window.addEventListener('autosave:saved', handleSaved as EventListener);
    window.addEventListener('autosave:error', handleError);
    window.addEventListener('autosave:saving', handleSaving);

    return () => {
      window.removeEventListener('autosave:saved', handleSaved as EventListener);
      window.removeEventListener('autosave:error', handleError);
      window.removeEventListener('autosave:saving', handleSaving);
    };
  }, [projectId]);

  // Check for offline status
  useEffect(() => {
    const handleOnline = () => {
      if (status === 'offline') {
        setStatus('idle');
      }
    };

    const handleOffline = () => {
      setStatus('offline');
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Initial check
    if (!navigator.onLine) {
      setStatus('offline');
    }

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [status]);

  // Load version history and check for recovery
  useEffect(() => {
    if (!projectId) return;

    const manager = getAutoSaveManager();

    // Load version history
    const history = manager.getVersionHistory(projectId);
    setVersionHistory(history);

    // Check for pending recovery
    const recovery = manager.checkRecovery(projectId);
    setPendingRecovery(recovery);

    // Load last saved timestamp
    const autoSave = manager.getAutoSave(projectId);
    if (autoSave) {
      setLastSaved(autoSave.timestamp);
    }
  }, [projectId]);

  const handleManualSave = useCallback(() => {
    setStatus('saving');
    onManualSave?.();
  }, [onManualSave]);

  const handleRecoverVersion = useCallback(
    (version: AutoSaveState) => {
      onRecoverVersion?.(version.data);
      setIsDropdownOpen(false);
    },
    [onRecoverVersion]
  );

  const handleDismissRecovery = useCallback(() => {
    const manager = getAutoSaveManager();
    manager.dismissRecovery();
    setPendingRecovery(null);
  }, []);

  const getStatusConfig = () => {
    switch (status) {
      case 'saving':
        return {
          color: 'text-blue-400',
          bg: 'bg-blue-500/10',
          label: 'Saving...',
        };
      case 'saved':
        return {
          color: 'text-green-400',
          bg: 'bg-green-500/10',
          label: 'Saved',
        };
      case 'error':
        return {
          color: 'text-red-400',
          bg: 'bg-red-500/10',
          label: 'Save failed',
        };
      case 'offline':
        return {
          color: 'text-yellow-400',
          bg: 'bg-yellow-500/10',
          label: 'Offline',
        };
      default:
        return {
          color: 'text-surface-400',
          bg: 'bg-surface-700',
          label: lastSaved ? formatRelativeTime(lastSaved) : 'Not saved',
        };
    }
  };

  const config = getStatusConfig();

  // Icon-only mode
  if (mode === 'icon') {
    return (
      <div
        className={cn('relative', className)}
        title={`${config.label}${lastSaved ? ` - Last saved ${formatRelativeTime(lastSaved)}` : ''}`}
      >
        <StatusIcon status={status} className={cn('w-4 h-4', config.color)} />
        {status === 'saved' && (
          <Check className="w-2 h-2 text-green-400 absolute -bottom-0.5 -right-0.5" />
        )}
      </div>
    );
  }

  // Badge mode
  if (mode === 'badge') {
    return (
      <div className={cn('relative', className)}>
        <button
          onClick={() => showHistory && setIsDropdownOpen(!isDropdownOpen)}
          className={cn(
            'flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs',
            'transition-colors',
            config.bg,
            config.color,
            showHistory && 'hover:opacity-80 cursor-pointer'
          )}
        >
          <StatusIcon status={status} className="w-3.5 h-3.5" />
          <span>{config.label}</span>
          {showHistory && <ChevronDown className="w-3 h-3" />}
        </button>

        {/* Dropdown */}
        {isDropdownOpen && (
          <VersionHistoryDropdown
            history={versionHistory}
            onSelect={handleRecoverVersion}
            onClose={() => setIsDropdownOpen(false)}
          />
        )}
      </div>
    );
  }

  // Full mode
  return (
    <div className={cn('space-y-2', className)}>
      {/* Recovery alert */}
      {pendingRecovery && (
        <div className="p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm font-medium text-yellow-400">Unsaved changes detected</p>
              <p className="text-xs text-surface-400 mt-1">
                Found auto-saved content from {formatRelativeTime(pendingRecovery.timestamp)}. Would
                you like to recover it?
              </p>
              <div className="flex gap-2 mt-3">
                <button
                  onClick={() => {
                    const manager = getAutoSaveManager();
                    const data = manager.recover(pendingRecovery.projectId);
                    if (data) {
                      onRecoverVersion?.(data);
                    }
                    setPendingRecovery(null);
                  }}
                  className="px-3 py-1.5 bg-yellow-500 text-black text-xs font-medium rounded hover:bg-yellow-400 transition-colors"
                >
                  Recover
                </button>
                <button
                  onClick={handleDismissRecovery}
                  className="px-3 py-1.5 bg-surface-700 text-surface-300 text-xs rounded hover:bg-surface-600 transition-colors"
                >
                  Dismiss
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Status bar */}
      <div className="flex items-center justify-between p-3 bg-surface-800 rounded-lg">
        <div className="flex items-center gap-3">
          <div className={cn('p-2 rounded-lg', config.bg)}>
            <StatusIcon status={status} className={cn('w-4 h-4', config.color)} />
          </div>
          <div>
            <p className={cn('text-sm font-medium', config.color)}>{config.label}</p>
            {lastSaved && status !== 'saving' && (
              <p className="text-xs text-surface-500">Last saved {formatRelativeTime(lastSaved)}</p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {onManualSave && (
            <button
              onClick={handleManualSave}
              disabled={status === 'saving'}
              className={cn(
                'p-2 rounded-lg transition-colors',
                'bg-surface-700 hover:bg-surface-600',
                status === 'saving' && 'opacity-50 cursor-not-allowed'
              )}
              title="Save now"
            >
              <Save className="w-4 h-4 text-surface-300" />
            </button>
          )}

          {showHistory && versionHistory.length > 0 && (
            <button
              onClick={() => setIsDropdownOpen(!isDropdownOpen)}
              className="p-2 rounded-lg bg-surface-700 hover:bg-surface-600 transition-colors"
              title="Version history"
            >
              <History className="w-4 h-4 text-surface-300" />
            </button>
          )}
        </div>
      </div>

      {/* Version history dropdown */}
      {isDropdownOpen && (
        <VersionHistoryDropdown
          history={versionHistory}
          onSelect={handleRecoverVersion}
          onClose={() => setIsDropdownOpen(false)}
        />
      )}
    </div>
  );
});

// =============================================================================
// Version History Dropdown
// =============================================================================

interface VersionHistoryDropdownProps {
  history: AutoSaveState[];
  onSelect: (version: AutoSaveState) => void;
  onClose: () => void;
}

const VersionHistoryDropdown = memo(function VersionHistoryDropdown({
  history,
  onSelect,
  onClose,
}: VersionHistoryDropdownProps) {
  // Close on escape
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [onClose]);

  // Close on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target.closest('.version-history-dropdown')) {
        onClose();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [onClose]);

  if (history.length === 0) {
    return (
      <div className="version-history-dropdown absolute top-full left-0 mt-1 w-64 bg-surface-800 border border-surface-700 rounded-lg shadow-xl z-50 p-3">
        <p className="text-sm text-surface-400 text-center">No version history</p>
      </div>
    );
  }

  return (
    <div className="version-history-dropdown absolute top-full left-0 mt-1 w-72 bg-surface-800 border border-surface-700 rounded-lg shadow-xl z-50 overflow-hidden">
      <div className="px-3 py-2 border-b border-surface-700">
        <h4 className="text-sm font-medium text-surface-200 flex items-center gap-2">
          <History className="w-4 h-4" />
          Version History
        </h4>
      </div>

      <div className="max-h-64 overflow-y-auto">
        {history.map((version, index) => (
          <button
            key={version.version}
            onClick={() => onSelect(version)}
            className={cn(
              'w-full flex items-center gap-3 px-3 py-2 text-left',
              'hover:bg-surface-700 transition-colors',
              index === 0 && 'bg-surface-700/50'
            )}
          >
            <Clock className="w-4 h-4 text-surface-500 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm text-surface-200">
                {index === 0 ? 'Current' : `Version ${version.version}`}
              </p>
              <p className="text-xs text-surface-500">
                {formatTime(version.timestamp)} • {formatRelativeTime(version.timestamp)}
              </p>
            </div>
            <RefreshCw className="w-4 h-4 text-surface-500 opacity-0 group-hover:opacity-100" />
          </button>
        ))}
      </div>

      <div className="px-3 py-2 border-t border-surface-700 bg-surface-900/50">
        <p className="text-xs text-surface-500">Click a version to restore it</p>
      </div>
    </div>
  );
});

// =============================================================================
// Hook for Auto-Save Status
// =============================================================================

export function useAutoSaveStatus(projectId: string | undefined) {
  const [status, setStatus] = useState<SaveStatus>('idle');
  const [lastSaved, setLastSaved] = useState<number | null>(null);

  useEffect(() => {
    if (!projectId) return;

    const handleSaved = (event: CustomEvent<{ projectId: string; timestamp: number }>) => {
      if (event.detail.projectId === projectId) {
        setStatus('saved');
        setLastSaved(event.detail.timestamp);
        setTimeout(() => setStatus('idle'), 2000);
      }
    };

    const handleError = () => {
      setStatus('error');
      setTimeout(() => setStatus('idle'), 5000);
    };

    window.addEventListener('autosave:saved', handleSaved as EventListener);
    window.addEventListener('autosave:error', handleError);

    // Load initial state
    const manager = getAutoSaveManager();
    const autoSave = manager.getAutoSave(projectId);
    if (autoSave) {
      setLastSaved(autoSave.timestamp);
    }

    return () => {
      window.removeEventListener('autosave:saved', handleSaved as EventListener);
      window.removeEventListener('autosave:error', handleError);
    };
  }, [projectId]);

  return { status, lastSaved };
}

export default AutoSaveStatus;
