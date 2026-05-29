/**
 * Cost Estimate component.
 *
 * Displays estimated costs for video generation before queueing.
 * Shows cost per shot and total cost with confidence indicator.
 */

import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { DollarSign, AlertTriangle, Loader2, Info, TrendingUp } from 'lucide-react';
import { cn } from '../lib/utils';
import { api } from '../api/client';
import { useGenerationStore } from '../stores/generation-store';
import { useExperienceStore } from '../stores/experience-store';
import { useTranslation } from '../i18n/use-translation';

interface CostEstimateProps {
  /** Duration in seconds for a single shot */
  durationSeconds?: number;
  /** Number of shots to generate */
  shotCount?: number;
  /** Show detailed breakdown */
  showBreakdown?: boolean;
  /** Compact display mode */
  compact?: boolean;
  /** Custom provider override (defaults to store) */
  provider?: string;
  /** Custom model override (defaults to store) */
  modelId?: string;
  /** Warning threshold in USD */
  warningThreshold?: number;
  /** Danger threshold in USD */
  dangerThreshold?: number;
}

export function CostEstimate({
  durationSeconds = 3.0,
  shotCount = 1,
  showBreakdown = false,
  compact = false,
  provider: providerOverride,
  modelId: modelIdOverride,
  warningThreshold = 1.0,
  dangerThreshold = 5.0,
}: CostEstimateProps) {
  const { selectedProvider, selectedModel } = useGenerationStore();
  const { getTerm } = useExperienceStore();
  const { t } = useTranslation();

  const provider = providerOverride ?? selectedProvider;
  const modelId = modelIdOverride ?? selectedModel;

  const {
    data: estimate,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['cost-estimate', provider, modelId, durationSeconds, shotCount],
    queryFn: () =>
      api.estimateCost({
        provider,
        model_id: modelId ?? undefined,
        duration_seconds: durationSeconds,
        shot_count: shotCount,
      }),
    enabled: !!provider,
    staleTime: 60 * 1000, // 1 minute
  });

  const costLevel = useMemo(() => {
    if (!estimate) return 'unknown';
    if (estimate.total_cost >= dangerThreshold) return 'danger';
    if (estimate.total_cost >= warningThreshold) return 'warning';
    return 'normal';
  }, [estimate, warningThreshold, dangerThreshold]);

  if (isLoading) {
    return (
      <div
        className={cn('flex items-center gap-2 text-surface-500', compact ? 'text-xs' : 'text-sm')}
      >
        <Loader2 className="w-3 h-3 animate-spin" />
        <span>{t('costEst.estimatingCost', 'Estimating cost...')}</span>
      </div>
    );
  }

  if (error || !estimate) {
    return (
      <div
        className={cn('flex items-center gap-2 text-surface-500', compact ? 'text-xs' : 'text-sm')}
      >
        <Info className="w-3 h-3" />
        <span>{t('costEst.costUnavailable', 'Cost unavailable')}</span>
      </div>
    );
  }

  if (compact) {
    return (
      <CostBadge amount={estimate.total_cost} currency={estimate.currency} level={costLevel} />
    );
  }

  return (
    <div className="space-y-2">
      {/* Main cost display */}
      <div
        className={cn(
          'flex items-center gap-3 px-3 py-2 rounded-lg',
          costLevel === 'normal' && 'bg-surface-800',
          costLevel === 'warning' && 'bg-yellow-500/10 border border-yellow-500/30',
          costLevel === 'danger' && 'bg-red-500/10 border border-red-500/30'
        )}
      >
        <div
          className={cn(
            'p-2 rounded-lg',
            costLevel === 'normal' && 'bg-brand-500/20 text-brand-400',
            costLevel === 'warning' && 'bg-yellow-500/20 text-yellow-400',
            costLevel === 'danger' && 'bg-red-500/20 text-red-400'
          )}
        >
          <DollarSign className="w-5 h-5" />
        </div>

        <div className="flex-1">
          <div className="flex items-baseline gap-2">
            <span
              className={cn(
                'text-xl font-bold',
                costLevel === 'normal' && 'text-surface-100',
                costLevel === 'warning' && 'text-yellow-300',
                costLevel === 'danger' && 'text-red-300'
              )}
            >
              ${estimate.total_cost.toFixed(2)}
            </span>
            <span className="text-sm text-surface-500">{estimate.currency}</span>
          </div>
          <div className="text-sm text-surface-400">
            {shotCount > 1
              ? `${shotCount} shots × $${estimate.cost_per_shot.toFixed(3)}/shot`
              : `${durationSeconds}s video`}
          </div>
        </div>

        {costLevel !== 'normal' && (
          <AlertTriangle
            className={cn(
              'w-5 h-5',
              costLevel === 'warning' && 'text-yellow-400',
              costLevel === 'danger' && 'text-red-400'
            )}
          />
        )}
      </div>

      {/* Breakdown */}
      {showBreakdown && (
        <div className="px-3 py-2 bg-surface-800/50 rounded-lg text-sm space-y-1">
          <div className="flex justify-between text-surface-400">
            <span>{t('costEst.provider', 'Provider')}</span>
            <span className="text-surface-200">{getTerm(estimate.provider, 'generation')}</span>
          </div>
          <div className="flex justify-between text-surface-400">
            <span>{t('costEst.model', 'Model')}</span>
            <span className="text-surface-200">{estimate.model_name}</span>
          </div>
          <div className="flex justify-between text-surface-400">
            <span>{t('costEst.duration', 'Duration')}</span>
            <span className="text-surface-200">{estimate.duration_seconds}s</span>
          </div>
          <div className="flex justify-between text-surface-400">
            <span>{t('costEst.costPerShot', 'Cost per shot')}</span>
            <span className="text-surface-200">${estimate.cost_per_shot.toFixed(4)}</span>
          </div>
          {shotCount > 1 && (
            <div className="flex justify-between text-surface-400 pt-1 border-t border-surface-700">
              <span>{t('costEst.shots', 'Shots')}</span>
              <span className="text-surface-200">×{shotCount}</span>
            </div>
          )}
        </div>
      )}

      {/* Warning message */}
      {costLevel === 'danger' && (
        <div className="flex items-start gap-2 px-3 py-2 bg-red-500/10 border border-red-500/30 rounded-lg text-sm text-red-300">
          <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
          <span>
            {t(
              'costEst.highCostWarning',
              'This is a high-cost operation. Consider reducing shot count or duration.'
            )}
          </span>
        </div>
      )}
    </div>
  );
}

/**
 * Compact cost badge for inline display.
 */
export function CostBadge({
  amount,
  currency = 'USD',
  level = 'normal',
}: {
  amount: number;
  currency?: string;
  level?: 'normal' | 'warning' | 'danger' | 'unknown';
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium',
        level === 'normal' && 'bg-surface-800 text-surface-300',
        level === 'warning' && 'bg-yellow-500/20 text-yellow-400',
        level === 'danger' && 'bg-red-500/20 text-red-400',
        level === 'unknown' && 'bg-surface-700 text-surface-400'
      )}
    >
      <DollarSign className="w-3 h-3" />
      {level === 'unknown' ? '—' : `${amount.toFixed(2)}`}
    </span>
  );
}

/**
 * Cost preview tooltip content for shot cards.
 */
export function CostTooltip({
  durationSeconds = 3.0,
  provider,
  modelId,
}: {
  durationSeconds?: number;
  provider?: string;
  modelId?: string;
}) {
  const { selectedProvider, selectedModel } = useGenerationStore();
  const { getTerm } = useExperienceStore();
  const { t } = useTranslation();

  const effectiveProvider = provider ?? selectedProvider;
  const effectiveModel = modelId ?? selectedModel;

  const { data: estimate, isLoading } = useQuery({
    queryKey: ['cost-tooltip', effectiveProvider, effectiveModel, durationSeconds],
    queryFn: () =>
      api.estimateCost({
        provider: effectiveProvider,
        model_id: effectiveModel ?? undefined,
        duration_seconds: durationSeconds,
        shot_count: 1,
      }),
    enabled: !!effectiveProvider,
    staleTime: 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="p-2 text-xs text-surface-400">
        {t('costEst.calculatingCost', 'Calculating cost...')}
      </div>
    );
  }

  if (!estimate) {
    return (
      <div className="p-2 text-xs text-surface-400">
        {t('costEst.costUnavailable', 'Cost unavailable')}
      </div>
    );
  }

  return (
    <div className="p-2 text-xs space-y-1">
      <div className="font-medium text-surface-200">
        {t('costEst.estimatedCostLabel', 'Estimated Cost:')} ${estimate.cost_per_shot.toFixed(4)}
      </div>
      <div className="text-surface-400">
        {estimate.model_name} ({getTerm(estimate.provider, 'generation')})
      </div>
      <div className="text-surface-400">
        ${(estimate.cost_per_shot / durationSeconds).toFixed(4)}/second
      </div>
    </div>
  );
}

/**
 * Cost summary for batch operations.
 */
export function BatchCostSummary({
  shots,
  showPerShot = true,
}: {
  shots: Array<{ id: string; duration?: number }>;
  showPerShot?: boolean;
}) {
  const { selectedProvider, selectedModel } = useGenerationStore();
  const { t } = useTranslation();

  const totalDuration = useMemo(() => {
    return shots.reduce((sum, shot) => sum + (shot.duration ?? 3.0), 0);
  }, [shots]);

  const avgDuration = shots.length > 0 ? totalDuration / shots.length : 3.0;

  const { data: estimate, isLoading } = useQuery({
    queryKey: ['batch-cost', selectedProvider, selectedModel, avgDuration, shots.length],
    queryFn: () =>
      api.estimateCost({
        provider: selectedProvider,
        model_id: selectedModel ?? undefined,
        duration_seconds: avgDuration,
        shot_count: shots.length,
      }),
    enabled: !!selectedProvider && shots.length > 0,
    staleTime: 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-surface-500">
        <Loader2 className="w-4 h-4 animate-spin" />
        <span>{t('costEst.calculatingTotalCost', 'Calculating total cost...')}</span>
      </div>
    );
  }

  if (!estimate) {
    return null;
  }

  return (
    <div className="flex items-center justify-between px-4 py-3 bg-surface-800 rounded-lg">
      <div>
        <div className="text-sm text-surface-400">
          {shots.length}{' '}
          {shots.length !== 1
            ? t('costEst.shotsToGenerate', 'shots to generate')
            : t('costEst.shotToGenerate', 'shot to generate')}
        </div>
        {showPerShot && (
          <div className="text-xs text-surface-500 mt-0.5">
            ~${estimate.cost_per_shot.toFixed(3)} {t('costEst.perShot', 'per shot')}
          </div>
        )}
      </div>
      <div className="text-right">
        <div className="flex items-center gap-1.5">
          <TrendingUp className="w-4 h-4 text-brand-400" />
          <span className="text-lg font-bold text-surface-100">
            ${estimate.total_cost.toFixed(2)}
          </span>
        </div>
        <div className="text-xs text-surface-500">{t('costEst.estimatedTotal', 'Estimated total')}</div>
      </div>
    </div>
  );
}
