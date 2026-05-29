/**
 * Cache Status Components
 *
 * Visual indicators for cached data and sync status.
 */

import { memo } from 'react';
import { Database, RefreshCw, Cloud, CloudOff, Check, AlertCircle } from 'lucide-react';
import { cn } from '../lib/utils';
import { useTranslation } from '../i18n/use-translation';
import { useOfflineCache } from '../hooks/use-offline-cache';
import { useOnlineStatus } from '../hooks/use-online-status';

/**
 * Badge showing if an item is cached
 */
export const CachedBadge = memo(function CachedBadge({
  isCached,
  className,
}: {
  isCached: boolean;
  className?: string;
}) {
  const { t } = useTranslation();
  if (!isCached) return null;

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs',
        'bg-surface-700/50 text-surface-300',
        className
      )}
      title={t('cacheStatus.availableOffline', 'Available offline')}
    >
      <Database className="w-3 h-3" />
      <span>{t('cacheStatus.cached', 'Cached')}</span>
    </span>
  );
});

/**
 * Indicator showing pending sync items
 */
export const SyncIndicator = memo(function SyncIndicator({ className }: { className?: string }) {
  const { t } = useTranslation();
  const { pendingSync, isSyncing } = useOfflineCache();
  const { isOnline } = useOnlineStatus();

  if (pendingSync.length === 0 && !isSyncing) {
    return null;
  }

  return (
    <div
      className={cn(
        'inline-flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs',
        isOnline
          ? isSyncing
            ? 'bg-blue-500/20 text-blue-300'
            : 'bg-yellow-500/20 text-yellow-300'
          : 'bg-surface-700 text-surface-400',
        className
      )}
      title={
        isSyncing
          ? t('cacheStatus.syncingChanges', 'Syncing changes...')
          : isOnline
            ? `${pendingSync.length} ${t('cacheStatus.changesPendingSync', 'changes pending sync')}`
            : `${pendingSync.length} ${t('cacheStatus.changesWillSyncWhenOnline', 'changes will sync when online')}`
      }
    >
      {isSyncing ? (
        <>
          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
          <span>{t('cacheStatus.syncing', 'Syncing...')}</span>
        </>
      ) : isOnline ? (
        <>
          <Cloud className="w-3.5 h-3.5" />
          <span>{pendingSync.length} {t('cacheStatus.pending', 'pending')}</span>
        </>
      ) : (
        <>
          <CloudOff className="w-3.5 h-3.5" />
          <span>{pendingSync.length} {t('cacheStatus.queued', 'queued')}</span>
        </>
      )}
    </div>
  );
});

/**
 * Full sync status display with details
 */
export const SyncStatusPanel = memo(function SyncStatusPanel({
  className,
  onSync,
}: {
  className?: string;
  onSync?: () => void;
}) {
  const { t } = useTranslation();
  const { stats, pendingSync, isSyncing } = useOfflineCache();
  const { isOnline, isChecking } = useOnlineStatus();

  return (
    <div className={cn('rounded-lg border border-surface-700 bg-surface-800 p-4', className)}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-surface-200">{t('cacheStatus.offlineCache', 'Offline Cache')}</h3>
        <div
          className={cn(
            'flex items-center gap-1.5 px-2 py-0.5 rounded text-xs',
            isOnline ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'
          )}
        >
          {isChecking ? (
            <RefreshCw className="w-3 h-3 animate-spin" />
          ) : isOnline ? (
            <Check className="w-3 h-3" />
          ) : (
            <AlertCircle className="w-3 h-3" />
          )}
          <span>{isOnline ? t('cacheStatus.online', 'Online') : t('cacheStatus.offline', 'Offline')}</span>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 gap-3 mb-4">
          <div className="p-2 rounded bg-surface-900">
            <div className="text-xs text-surface-400">{t('cacheStatus.projectsCached', 'Projects Cached')}</div>
            <div className="text-lg font-medium text-surface-100">{stats.projectCount}</div>
          </div>
          <div className="p-2 rounded bg-surface-900">
            <div className="text-xs text-surface-400">{t('cacheStatus.videosCached', 'Videos Cached')}</div>
            <div className="text-lg font-medium text-surface-100">{stats.videoCount}</div>
          </div>
          <div className="p-2 rounded bg-surface-900">
            <div className="text-xs text-surface-400">{t('cacheStatus.cacheSize', 'Cache Size')}</div>
            <div className="text-lg font-medium text-surface-100">
              {stats.totalVideoSizeMB.toFixed(1)} MB
            </div>
          </div>
          <div className="p-2 rounded bg-surface-900">
            <div className="text-xs text-surface-400">{t('cacheStatus.pendingSync', 'Pending Sync')}</div>
            <div className="text-lg font-medium text-surface-100">{stats.syncQueueCount}</div>
          </div>
        </div>
      )}

      {/* Pending sync items */}
      {pendingSync.length > 0 && (
        <div className="border-t border-surface-700 pt-3 mt-3">
          <div className="text-xs text-surface-400 mb-2">{t('cacheStatus.pendingChanges', 'Pending Changes')}</div>
          <div className="space-y-1 max-h-32 overflow-y-auto">
            {pendingSync.slice(0, 5).map((item) => (
              <div
                key={item.id}
                className="flex items-center justify-between text-xs p-1.5 rounded bg-surface-900"
              >
                <span className="text-surface-300">
                  {item.type} {item.entity}
                </span>
                {item.retryCount > 0 && (
                  <span className="text-yellow-400">{t('cacheStatus.retry', 'Retry')} {item.retryCount}</span>
                )}
              </div>
            ))}
            {pendingSync.length > 5 && (
              <div className="text-xs text-surface-500 pl-1">+{pendingSync.length - 5} {t('cacheStatus.more', 'more...')}</div>
            )}
          </div>

          {/* Sync button */}
          {isOnline && onSync && (
            <button
              onClick={onSync}
              disabled={isSyncing}
              className={cn(
                'w-full mt-3 px-3 py-2 rounded-lg text-sm font-medium',
                'bg-primary-500 text-white',
                'hover:bg-primary-600 transition-colors',
                'disabled:opacity-50 disabled:cursor-not-allowed',
                'flex items-center justify-center gap-2'
              )}
            >
              {isSyncing ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  {t('cacheStatus.syncing', 'Syncing...')}
                </>
              ) : (
                <>
                  <Cloud className="w-4 h-4" />
                  {t('cacheStatus.syncNow', 'Sync Now')}
                </>
              )}
            </button>
          )}
        </div>
      )}
    </div>
  );
});

export default CachedBadge;
