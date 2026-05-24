/**
 * Admin/Health Dashboard page.
 * Shows system health, storage stats, and provider monitoring.
 */

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Cpu,
  Database,
  HardDrive,
  Loader2,
  RefreshCw,
  Server,
  TrendingUp,
  Wifi,
  WifiOff,
  Zap,
} from 'lucide-react';
import { api, type WorkerStatus } from '../api/client';
import { cn } from '../lib/utils';
import { CircuitBreakerPanel } from '../components/circuit-breaker-status';
import { useSettingsStore } from '../stores/settings-store';
import { useGenerationStore } from '../stores/generation-store';

/**
 * Format bytes to human readable string.
 * Guards against undefined/NaN input — the storage stats handler can
 * return partial state on a new install, which used to render as
 * `NaN undefined` across all four Storage Usage cards (caught by
 * /qa_screenshot_tour iter 13).
 */
function formatBytes(bytes: number | undefined | null): string {
  if (bytes === undefined || bytes === null || Number.isNaN(bytes) || bytes === 0) {
    return '0 B';
  }
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

/**
 * Format duration in seconds to human readable string.
 * Guards undefined/NaN like formatBytes above.
 */
function formatDuration(seconds: number | undefined | null): string {
  if (seconds === undefined || seconds === null || Number.isNaN(seconds) || seconds <= 0) {
    return '0s';
  }
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
}

/**
 * System status indicator card.
 */
function StatusCard({
  title,
  icon: Icon,
  status,
  value,
  subtext,
  color,
}: {
  title: string;
  icon: React.ElementType;
  status: 'ok' | 'warning' | 'error' | 'loading';
  value: string;
  subtext?: string;
  color?: string;
}) {
  const statusColors = {
    ok: 'bg-green-500/10 border-green-500/30',
    warning: 'bg-yellow-500/10 border-yellow-500/30',
    error: 'bg-red-500/10 border-red-500/30',
    loading: 'bg-surface-800/50 border-surface-700',
  };

  const iconColors = {
    ok: 'text-green-400',
    warning: 'text-yellow-400',
    error: 'text-red-400',
    loading: 'text-surface-400',
  };

  return (
    <div className={cn('rounded-lg border p-4', statusColors[status])}>
      <div className="flex items-start justify-between mb-2">
        <Icon className={cn('w-5 h-5', color || iconColors[status])} />
        {status === 'loading' ? (
          <Loader2 className="w-4 h-4 animate-spin text-surface-400" />
        ) : status === 'ok' ? (
          <CheckCircle2 className="w-4 h-4 text-green-400" />
        ) : status === 'warning' ? (
          <AlertTriangle className="w-4 h-4 text-yellow-400" />
        ) : (
          <AlertTriangle className="w-4 h-4 text-red-400" />
        )}
      </div>
      <div className="text-2xl font-bold mb-1">{value}</div>
      <div className="text-sm text-surface-400">{title}</div>
      {subtext && <div className="text-xs text-surface-500 mt-1">{subtext}</div>}
    </div>
  );
}

/**
 * Storage usage gauge component.
 */
function StorageGauge({
  label,
  used,
  total,
  color,
}: {
  label: string;
  used: number;
  total: number;
  color: string;
}) {
  // Coerce undefined/NaN to 0 so the "X% of Y" subtext + width math don't
  // render "NaN undefined" / "0.0% of NaN undefined" on a new install with
  // no storage stats yet (caught by /qa_screenshot_tour iter 13).
  const safeUsed = Number.isFinite(used) ? used : 0;
  const safeTotal = Number.isFinite(total) ? total : 0;
  const percentage = safeTotal > 0 ? (safeUsed / safeTotal) * 100 : 0;
  const isHigh = percentage > 80;

  return (
    <div className="bg-surface-800/50 rounded-lg p-3">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-surface-300">{label}</span>
        <span className="text-sm font-medium">{formatBytes(safeUsed)}</span>
      </div>
      <div className="h-2 bg-surface-700 rounded-full overflow-hidden">
        <div
          className={cn('h-full rounded-full transition-all', isHigh ? 'bg-red-400' : color)}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>
      <div className="text-xs text-surface-500 mt-1">
        {percentage.toFixed(1)}% of {formatBytes(safeTotal)}
      </div>
    </div>
  );
}

/**
 * Queue worker status panel.
 */
function WorkerStatusPanel({ status }: { status: WorkerStatus | null }) {
  if (!status) {
    return (
      <div className="text-center py-4 text-surface-400">
        <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
        Loading worker status...
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Worker State */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {status.is_running ? (
            status.is_paused ? (
              <span className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-yellow-500/20 text-yellow-400 text-sm font-medium">
                <Clock className="w-4 h-4" />
                Paused
              </span>
            ) : (
              <span className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-green-500/20 text-green-400 text-sm font-medium">
                <Zap className="w-4 h-4" />
                Running
              </span>
            )
          ) : (
            <span className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-red-500/20 text-red-400 text-sm font-medium">
              <WifiOff className="w-4 h-4" />
              Stopped
            </span>
          )}
        </div>
        <div className="text-sm text-surface-400">
          Uptime: {formatDuration(status.uptime_seconds)}
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-4 gap-3">
        <div className="bg-surface-800/50 rounded-lg p-3 text-center">
          <div className="text-2xl font-bold">{status.jobs_processed}</div>
          <div className="text-xs text-surface-400">Processed</div>
        </div>
        <div className="bg-green-500/10 rounded-lg p-3 text-center">
          <div className="text-2xl font-bold text-green-400">{status.jobs_succeeded}</div>
          <div className="text-xs text-surface-400">Succeeded</div>
        </div>
        <div className="bg-red-500/10 rounded-lg p-3 text-center">
          <div className="text-2xl font-bold text-red-400">{status.jobs_failed}</div>
          <div className="text-xs text-surface-400">Failed</div>
        </div>
        <div className="bg-brand-500/10 rounded-lg p-3 text-center">
          <div className="text-2xl font-bold text-brand-400">
            {(status.success_rate ?? 0).toFixed(1)}%
          </div>
          <div className="text-xs text-surface-400">Success Rate</div>
        </div>
      </div>

      {/* Current Job */}
      {status.current_job_id && (
        <div className="bg-surface-800/50 rounded-lg p-3">
          <div className="text-xs text-surface-400 mb-1">Currently Processing</div>
          <div className="font-mono text-sm truncate">{status.current_job_id}</div>
        </div>
      )}
    </div>
  );
}

/**
 * Admin/Health Dashboard Page.
 */
export function AdminPage() {
  const { storageStats, fetchStorageStats } = useSettingsStore();
  const { workerStatus, fetchWorkerStatus } = useGenerationStore();

  // Fetch version info
  const { data: versionInfo, isLoading: versionLoading } = useQuery({
    queryKey: ['version'],
    queryFn: () => api.getVersion(),
    refetchInterval: 60000,
  });

  // Fetch provider health
  const {
    data: providersHealth,
    isLoading: providersLoading,
    refetch: refetchProviders,
  } = useQuery({
    queryKey: ['providers-health'],
    queryFn: () => api.getProvidersHealth(),
    refetchInterval: 30000,
  });

  // Fetch generation stats
  const { data: generationStats, isLoading: statsLoading } = useQuery({
    queryKey: ['generation-stats'],
    queryFn: () => api.getGenerationStats({ timeRange: '7d' }),
    refetchInterval: 60000,
  });

  // Fetch cost stats
  const { data: costStats } = useQuery({
    queryKey: ['cost-stats'],
    queryFn: () => api.getCostStats({ timeRange: '30d' }),
    refetchInterval: 60000,
  });

  // Refresh on mount
  React.useEffect(() => {
    fetchStorageStats();
    fetchWorkerStatus();
  }, []);

  // Count available providers. providersHealth can come back as undefined or
  // even an object when the backend returns partial state — guarding with
  // Array.isArray prevents "filter is not a function" which took down the
  // whole Admin page. Found by /qa_screenshot_tour.
  const providersList = Array.isArray(providersHealth) ? providersHealth : [];
  const availableProviders = providersList.filter((p) => p.available).length;
  const totalProviders = providersList.length;

  // Determine system status
  const hasProviderIssues = providersList.some((p) => p.configured && !p.available);

  return (
    <div className="h-full overflow-y-auto">
      <div className="p-8 max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Server className="w-6 h-6 text-brand-400" />
              System Health
            </h1>
            <p className="text-surface-400 mt-1">
              Monitor system status, providers, and resource usage
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-surface-400">
              v{versionInfo?.version || '...'} ({versionInfo?.environment || '...'})
            </span>
            <button
              onClick={() => {
                fetchStorageStats();
                fetchWorkerStatus();
                refetchProviders();
              }}
              className="px-3 py-1.5 bg-surface-700 hover:bg-surface-600 rounded-lg text-sm flex items-center gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh All
            </button>
          </div>
        </div>

        {/* System Overview */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          <StatusCard
            title="Backend Status"
            icon={Server}
            status={versionLoading ? 'loading' : versionInfo ? 'ok' : 'error'}
            value={versionInfo ? 'Connected' : 'Disconnected'}
            subtext={versionInfo ? `Python backend v${versionInfo.version}` : undefined}
          />
          <StatusCard
            title="Providers"
            icon={Wifi}
            status={
              providersLoading
                ? 'loading'
                : hasProviderIssues
                  ? 'warning'
                  : availableProviders > 0
                    ? 'ok'
                    : 'error'
            }
            value={`${availableProviders}/${totalProviders}`}
            subtext={
              hasProviderIssues ? 'Some providers unavailable' : 'All configured providers healthy'
            }
          />
          <StatusCard
            title="Generations (7d)"
            icon={Activity}
            status={statsLoading ? 'loading' : 'ok'}
            value={generationStats?.totalGenerations?.toString() || '0'}
            subtext={
              generationStats
                ? `${(generationStats.successRate ?? 0).toFixed(1)}% success rate`
                : undefined
            }
            color="text-brand-400"
          />
          <StatusCard
            title="Cost (30d)"
            icon={TrendingUp}
            status="ok"
            value={`$${costStats?.totalCostUsd?.toFixed(2) || '0.00'}`}
            subtext={
              costStats
                ? `$${costStats.averageCostPerGeneration?.toFixed(3) || '0'} avg/gen`
                : undefined
            }
            color="text-green-400"
          />
        </div>

        {/* Storage Section */}
        <div className="card mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-medium flex items-center gap-2">
              <HardDrive className="w-5 h-5 text-brand-400" />
              Storage Usage
            </h2>
            <button
              onClick={() => fetchStorageStats()}
              className="text-sm text-brand-400 hover:text-brand-300 flex items-center gap-1"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>
          </div>

          {storageStats ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <StorageGauge
                  label="Uploads"
                  used={storageStats.uploadSizeBytes}
                  total={storageStats.totalSizeBytes}
                  color="bg-blue-400"
                />
                <StorageGauge
                  label="Outputs"
                  used={storageStats.outputSizeBytes}
                  total={storageStats.totalSizeBytes}
                  color="bg-green-400"
                />
                <StorageGauge
                  label="Cache"
                  used={storageStats.cacheSizeBytes}
                  total={storageStats.totalSizeBytes}
                  color="bg-yellow-400"
                />
                <div className="bg-surface-800/50 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-surface-300">Total Used</span>
                    <span className="text-sm font-medium">
                      {formatBytes(storageStats.totalSizeBytes)}
                    </span>
                  </div>
                  <div className="text-xs text-surface-500">
                    {storageStats.tempFilesCount} temp files
                  </div>
                </div>
              </div>

              <div className="text-xs text-surface-500 space-y-1">
                <div className="flex justify-between">
                  <span>Data Directory</span>
                  <span className="font-mono">{storageStats.dataDir}</span>
                </div>
                <div className="flex justify-between">
                  <span>Cache Directory</span>
                  <span className="font-mono">{storageStats.cacheDir}</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-surface-400">
              <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
              Loading storage stats...
            </div>
          )}
        </div>

        {/* Queue Worker Section */}
        <div className="card mb-6">
          <h2 className="text-lg font-medium mb-4 flex items-center gap-2">
            <Cpu className="w-5 h-5 text-brand-400" />
            Queue Worker
          </h2>
          <WorkerStatusPanel status={workerStatus} />
        </div>

        {/* Circuit Breakers Section */}
        <div className="card mb-6">
          <CircuitBreakerPanel />
        </div>

        {/* Provider Details */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-medium flex items-center gap-2">
              <Database className="w-5 h-5 text-brand-400" />
              Provider Details
            </h2>
            <button
              onClick={() => refetchProviders()}
              disabled={providersLoading}
              className="text-sm text-brand-400 hover:text-brand-300 flex items-center gap-1"
            >
              {providersLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
              Refresh
            </button>
          </div>

          {providersLoading ? (
            <div className="text-center py-8 text-surface-400">
              <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
              Loading providers...
            </div>
          ) : providersHealth && providersHealth.length > 0 ? (
            <div className="space-y-3">
              {providersHealth.map((provider) => (
                <div
                  key={provider.provider}
                  className={cn(
                    'p-4 rounded-lg border',
                    provider.available
                      ? 'bg-green-500/5 border-green-500/30'
                      : provider.configured
                        ? 'bg-yellow-500/5 border-yellow-500/30'
                        : 'bg-surface-800/50 border-surface-700'
                  )}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <div
                          className={cn(
                            'w-2.5 h-2.5 rounded-full',
                            provider.available
                              ? 'bg-green-400'
                              : provider.configured
                                ? 'bg-yellow-400'
                                : 'bg-surface-500'
                          )}
                        />
                        <span className="font-medium">{provider.name}</span>
                        {provider.configured && (
                          <span className="text-xs px-1.5 py-0.5 bg-surface-700 rounded">
                            Configured
                          </span>
                        )}
                      </div>
                      <div className="text-sm text-surface-400 mt-1">
                        {provider.available
                          ? `${provider.models.length} models available`
                          : provider.error || 'Not configured'}
                      </div>
                    </div>
                    {provider.available && provider.default_model && (
                      <div className="text-right">
                        <div className="text-xs text-surface-400">Default Model</div>
                        <div className="text-sm font-medium">{provider.default_model}</div>
                      </div>
                    )}
                  </div>

                  {/* Model List (collapsed) */}
                  {provider.available && provider.models.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-surface-700">
                      <div className="text-xs text-surface-400 mb-2">Available Models</div>
                      <div className="flex flex-wrap gap-2">
                        {provider.models.map((model) => (
                          <span
                            key={model.id}
                            className="px-2 py-1 bg-surface-700 rounded text-xs"
                            title={`$${model.cost_per_second}/sec, max ${model.max_duration}s`}
                          >
                            {model.name}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-surface-400">
              No providers configured. Add API keys in Settings.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
