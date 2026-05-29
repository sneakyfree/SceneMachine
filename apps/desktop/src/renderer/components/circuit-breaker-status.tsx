/**
 * Circuit breaker status display components.
 * Shows the state and health of provider circuit breakers.
 */

import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock,
  RefreshCw,
  RotateCcw,
  Shield,
  ShieldAlert,
  ShieldCheck,
  XCircle,
  Loader2,
  Zap,
  TrendingUp,
} from 'lucide-react';
import { api, type CircuitBreakerStatus as CBStatus } from '../api/client';
import { cn } from '../lib/utils';
import { useToast } from '../stores/toast-store';
import { useTranslation } from '../i18n/use-translation';

// State colors and icons. User-facing label/description strings are stored as
// i18n key + English fallback pairs and resolved with `t` inside components.
const stateConfig = {
  closed: {
    color: 'bg-green-500/20 text-green-400 border-green-500/30',
    icon: ShieldCheck,
    labelKey: 'circuitBreaker.stateHealthy',
    labelEn: 'Healthy',
    descriptionKey: 'circuitBreaker.descClosed',
    descriptionEn: 'Normal operation, requests flowing through',
  },
  open: {
    color: 'bg-red-500/20 text-red-400 border-red-500/30',
    icon: ShieldAlert,
    labelKey: 'circuitBreaker.stateOpen',
    labelEn: 'Open',
    descriptionKey: 'circuitBreaker.descOpen',
    descriptionEn: 'Failing, requests are being rejected',
  },
  half_open: {
    color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    icon: Shield,
    labelKey: 'circuitBreaker.stateTesting',
    labelEn: 'Testing',
    descriptionKey: 'circuitBreaker.descHalfOpen',
    descriptionEn: 'Testing if service has recovered',
  },
};

/**
 * Format a timestamp to relative time.
 */
function formatRelativeTime(
  timestamp: number | null,
  t: (key: string, fallback?: string) => string
): string {
  if (!timestamp) return t('circuitBreaker.timeNever', 'Never');

  const now = Date.now() / 1000;
  const diff = now - timestamp;

  if (diff < 60) return t('circuitBreaker.timeJustNow', 'Just now');
  if (diff < 3600) return `${Math.floor(diff / 60)}${t('circuitBreaker.timeMinutesAgo', 'm ago')}`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}${t('circuitBreaker.timeHoursAgo', 'h ago')}`;
  return `${Math.floor(diff / 86400)}${t('circuitBreaker.timeDaysAgo', 'd ago')}`;
}

/**
 * Extract provider name from circuit name.
 */
function getProviderDisplayName(
  name: string,
  t: (key: string, fallback?: string) => string
): { category: string; provider: string } {
  if (name.startsWith('provider:')) {
    const provider = name.replace('provider:', '');
    return {
      category: t('circuitBreaker.categoryVideoProvider', 'Video Provider'),
      provider: provider.charAt(0).toUpperCase() + provider.slice(1),
    };
  }
  if (name.startsWith('llm:')) {
    const provider = name.replace('llm:', '');
    return {
      category: t('circuitBreaker.categoryLlmProvider', 'LLM Provider'),
      provider: provider.charAt(0).toUpperCase() + provider.slice(1),
    };
  }
  return { category: t('circuitBreaker.categoryService', 'Service'), provider: name };
}

/**
 * Single circuit breaker status badge.
 */
export function CircuitBreakerBadge({ circuit }: { circuit: CBStatus }) {
  const { t } = useTranslation();
  const config = stateConfig[circuit.state];
  const Icon = config.icon;

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border',
        config.color
      )}
      title={t(config.descriptionKey, config.descriptionEn)}
    >
      <Icon className="w-3 h-3" />
      {t(config.labelKey, config.labelEn)}
    </span>
  );
}

/**
 * Detailed circuit breaker card.
 */
export function CircuitBreakerCard({
  circuit,
  onReset,
  isResetting,
}: {
  circuit: CBStatus;
  onReset?: () => void;
  isResetting?: boolean;
}) {
  const { t } = useTranslation();
  const config = stateConfig[circuit.state];
  const Icon = config.icon;
  const { category, provider } = getProviderDisplayName(circuit.name, t);

  return (
    <div
      className={cn(
        'rounded-lg border p-4 transition-colors',
        config.color.replace('text-', 'hover:border-').replace('/30', '/50'),
        circuit.state === 'closed' ? 'bg-surface-800/30' : ''
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="text-xs text-surface-400 mb-0.5">{category}</div>
          <h3 className="font-medium text-surface-100">{provider}</h3>
        </div>
        <CircuitBreakerBadge circuit={circuit} />
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-3 mb-3">
        <div className="bg-surface-900/50 rounded-lg p-2">
          <div className="flex items-center gap-1.5 text-xs text-surface-400 mb-1">
            <Activity className="w-3 h-3" />
            {t('circuitBreaker.totalCalls', 'Total Calls')}
          </div>
          <div className="text-lg font-semibold">{circuit.totalCalls.toLocaleString()}</div>
        </div>
        <div className="bg-surface-900/50 rounded-lg p-2">
          <div className="flex items-center gap-1.5 text-xs text-surface-400 mb-1">
            <TrendingUp className="w-3 h-3" />
            {t('circuitBreaker.successRate', 'Success Rate')}
          </div>
          <div
            className={cn(
              'text-lg font-semibold',
              circuit.successRate >= 95
                ? 'text-green-400'
                : circuit.successRate >= 80
                  ? 'text-yellow-400'
                  : 'text-red-400'
            )}
          >
            {circuit.successRate}%
          </div>
        </div>
      </div>

      {/* Call Statistics */}
      <div className="flex items-center gap-4 text-xs text-surface-400 mb-3">
        <span className="flex items-center gap-1">
          <CheckCircle2 className="w-3 h-3 text-green-400" />
          {circuit.successfulCalls} {t('circuitBreaker.success', 'success')}
        </span>
        <span className="flex items-center gap-1">
          <XCircle className="w-3 h-3 text-red-400" />
          {circuit.failedCalls} {t('circuitBreaker.failed', 'failed')}
        </span>
        {circuit.rejectedCalls > 0 && (
          <span className="flex items-center gap-1">
            <AlertTriangle className="w-3 h-3 text-yellow-400" />
            {circuit.rejectedCalls} {t('circuitBreaker.rejected', 'rejected')}
          </span>
        )}
      </div>

      {/* Circuit State Details */}
      {circuit.state !== 'closed' && (
        <div className="space-y-2 pt-3 border-t border-surface-700">
          <div className="flex items-center justify-between text-xs">
            <span className="text-surface-400">
              {t('circuitBreaker.consecutiveFailures', 'Consecutive Failures')}
            </span>
            <span className="text-red-400 font-medium">
              {circuit.consecutiveFailures} / {circuit.failureThreshold}
            </span>
          </div>

          {circuit.state === 'open' && circuit.remainingTimeout > 0 && (
            <div className="flex items-center justify-between text-xs">
              <span className="text-surface-400 flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {t('circuitBreaker.recoveryIn', 'Recovery in')}
              </span>
              <span className="text-yellow-400 font-medium">
                {Math.ceil(circuit.remainingTimeout)}s
              </span>
            </div>
          )}

          {circuit.state === 'half_open' && (
            <div className="flex items-center justify-between text-xs">
              <span className="text-surface-400">
                {t('circuitBreaker.recoveryProgress', 'Recovery Progress')}
              </span>
              <span className="text-yellow-400 font-medium">
                {circuit.consecutiveSuccesses} / {Math.max(2, circuit.failureThreshold - 2)}{' '}
                {t('circuitBreaker.successesNeeded', 'successes needed')}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Last Activity */}
      <div className="flex items-center justify-between text-xs text-surface-500 mt-3 pt-3 border-t border-surface-700">
        <span>
          {t('circuitBreaker.lastSuccess', 'Last success:')}{' '}
          {formatRelativeTime(circuit.lastSuccessTime, t)}
        </span>
        <span>
          {t('circuitBreaker.lastFailure', 'Last failure:')}{' '}
          {formatRelativeTime(circuit.lastFailureTime, t)}
        </span>
      </div>

      {/* Reset Button (only for open circuits) */}
      {circuit.state === 'open' && onReset && (
        <button
          onClick={onReset}
          disabled={isResetting}
          className="mt-3 w-full px-3 py-2 bg-surface-700 hover:bg-surface-600 rounded-lg text-sm flex items-center justify-center gap-2 disabled:opacity-50 transition-colors"
        >
          {isResetting ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <RotateCcw className="w-4 h-4" />
          )}
          {t('circuitBreaker.forceReset', 'Force Reset')}
        </button>
      )}
    </div>
  );
}

/**
 * Summary badge showing overall circuit breaker health.
 */
export function CircuitBreakerSummary() {
  const { t } = useTranslation();
  const { data, isLoading, error } = useQuery({
    queryKey: ['circuit-breakers'],
    queryFn: () => api.getCircuitBreakers(),
    refetchInterval: 10000, // Refresh every 10 seconds
  });

  if (isLoading) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs bg-surface-700 text-surface-400">
        <Loader2 className="w-3 h-3 animate-spin" />
        {t('circuitBreaker.loading', 'Loading...')}
      </span>
    );
  }

  if (error || !data) {
    return null;
  }

  if (data.openCount > 0) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-red-500/20 text-red-400 border border-red-500/30">
        <ShieldAlert className="w-3 h-3" />
        {data.openCount}{' '}
        {data.openCount > 1
          ? t('circuitBreaker.circuitsPlural', 'Circuits')
          : t('circuitBreaker.circuitSingular', 'Circuit')}{' '}
        {t('circuitBreaker.stateOpen', 'Open')}
      </span>
    );
  }

  if (data.halfOpenCount > 0) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-yellow-500/20 text-yellow-400 border border-yellow-500/30">
        <Shield className="w-3 h-3" />
        {data.halfOpenCount} {t('circuitBreaker.recovering', 'Recovering')}
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-green-500/20 text-green-400 border border-green-500/30">
      <ShieldCheck className="w-3 h-3" />
      {t('circuitBreaker.allCircuitsHealthy', 'All Circuits Healthy')}
    </span>
  );
}

/**
 * Full circuit breaker panel for settings/admin page.
 */
export function CircuitBreakerPanel() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['circuit-breakers'],
    queryFn: () => api.getCircuitBreakers(),
    refetchInterval: 10000,
  });

  const resetMutation = useMutation({
    mutationFn: (name: string) => api.resetCircuitBreaker(name),
    onSuccess: (result, name) => {
      if (result.success) {
        toast.success(
          t('circuitBreaker.toastResetTitle', 'Circuit Reset'),
          `${t('circuitBreaker.toastResetMessagePrefix', 'Circuit')} "${name}" ${t('circuitBreaker.toastResetMessageSuffix', 'has been reset to closed state')}`
        );
        queryClient.invalidateQueries({ queryKey: ['circuit-breakers'] });
      } else {
        toast.error(
          t('circuitBreaker.toastResetFailedTitle', 'Reset Failed'),
          result.error || t('circuitBreaker.unknownError', 'Unknown error')
        );
      }
    },
    onError: (error) => {
      toast.error(t('circuitBreaker.toastResetFailedTitle', 'Reset Failed'), String(error));
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-6 h-6 text-brand-400 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <AlertTriangle className="w-8 h-8 text-yellow-400 mx-auto mb-2" />
        <p className="text-surface-400">
          {t('circuitBreaker.loadError', 'Failed to load circuit breaker status')}
        </p>
        <button
          onClick={() => refetch()}
          className="mt-2 text-sm text-brand-400 hover:text-brand-300"
        >
          {t('circuitBreaker.retry', 'Retry')}
        </button>
      </div>
    );
  }

  // `data` may be truthy but `data.circuits` undefined if the handler returns
  // partial state (e.g., new install with no breakers registered, or backend
  // shape drift). Guarding the inner property too prevents a renderer crash
  // that takes down the whole Settings page. Found by /qa_screenshot_tour.
  if (!data || !Array.isArray(data.circuits) || data.circuits.length === 0) {
    return (
      <div className="text-center py-8 text-surface-400">
        <Shield className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p>{t('circuitBreaker.noneRegistered', 'No circuit breakers registered yet.')}</p>
        <p className="text-sm mt-1">
          {t(
            'circuitBreaker.noneRegisteredHint',
            'Circuit breakers will appear after providers are used.'
          )}
        </p>
      </div>
    );
  }

  // Group circuits by category
  const providerCircuits = data.circuits.filter((c) => c.name.startsWith('provider:'));
  const llmCircuits = data.circuits.filter((c) => c.name.startsWith('llm:'));
  const otherCircuits = data.circuits.filter(
    (c) => !c.name.startsWith('provider:') && !c.name.startsWith('llm:')
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-medium flex items-center gap-2">
            <Zap className="w-5 h-5 text-brand-400" />
            {t('circuitBreaker.heading', 'Circuit Breakers')}
          </h3>
          <CircuitBreakerSummary />
        </div>
        <button
          onClick={() => refetch()}
          disabled={isLoading}
          className="text-sm text-brand-400 hover:text-brand-300 flex items-center gap-1"
        >
          <RefreshCw className={cn('w-4 h-4', isLoading && 'animate-spin')} />
          {t('circuitBreaker.refresh', 'Refresh')}
        </button>
      </div>

      {/* Overview Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-surface-800/50 rounded-lg p-3 text-center">
          <div className="text-2xl font-bold">{data.totalCount}</div>
          <div className="text-xs text-surface-400">
            {t('circuitBreaker.totalCircuits', 'Total Circuits')}
          </div>
        </div>
        <div className="bg-green-500/10 rounded-lg p-3 text-center">
          <div className="text-2xl font-bold text-green-400">
            {data.totalCount - data.openCount - data.halfOpenCount}
          </div>
          <div className="text-xs text-surface-400">
            {t('circuitBreaker.stateHealthy', 'Healthy')}
          </div>
        </div>
        <div className="bg-yellow-500/10 rounded-lg p-3 text-center">
          <div className="text-2xl font-bold text-yellow-400">{data.halfOpenCount}</div>
          <div className="text-xs text-surface-400">
            {t('circuitBreaker.recovering', 'Recovering')}
          </div>
        </div>
        <div className="bg-red-500/10 rounded-lg p-3 text-center">
          <div className="text-2xl font-bold text-red-400">{data.openCount}</div>
          <div className="text-xs text-surface-400">{t('circuitBreaker.stateOpen', 'Open')}</div>
        </div>
      </div>

      {/* Video Providers */}
      {providerCircuits.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-surface-400 mb-3">
            {t('circuitBreaker.sectionVideoProviders', 'Video Providers')}
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {providerCircuits.map((circuit) => (
              <CircuitBreakerCard
                key={circuit.name}
                circuit={circuit}
                onReset={() => resetMutation.mutate(circuit.name)}
                isResetting={resetMutation.isPending && resetMutation.variables === circuit.name}
              />
            ))}
          </div>
        </div>
      )}

      {/* LLM Providers */}
      {llmCircuits.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-surface-400 mb-3">
            {t('circuitBreaker.sectionLlmProviders', 'LLM Providers')}
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {llmCircuits.map((circuit) => (
              <CircuitBreakerCard
                key={circuit.name}
                circuit={circuit}
                onReset={() => resetMutation.mutate(circuit.name)}
                isResetting={resetMutation.isPending && resetMutation.variables === circuit.name}
              />
            ))}
          </div>
        </div>
      )}

      {/* Other Services */}
      {otherCircuits.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-surface-400 mb-3">
            {t('circuitBreaker.sectionOtherServices', 'Other Services')}
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {otherCircuits.map((circuit) => (
              <CircuitBreakerCard
                key={circuit.name}
                circuit={circuit}
                onReset={() => resetMutation.mutate(circuit.name)}
                isResetting={resetMutation.isPending && resetMutation.variables === circuit.name}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
