/**
 * Blockers Panel - Shows the "Why Not + What To Do Next" pattern.
 *
 * Displays production blockers with severity levels, categorization,
 * and actionable fix suggestions (unlockers).
 */

import { useState, useMemo, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  AlertCircle,
  AlertTriangle,
  Info,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Zap,
  Target,
  Loader2,
  Sparkles,
  ExternalLink,
  X,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { useTranslation } from '../i18n/use-translation';

// Severity levels matching backend
type BlockerSeverity = 'critical' | 'high' | 'medium' | 'low';

// Blocker categories
type BlockerCategory =
  | 'character_missing'
  | 'character_incomplete'
  | 'voice_missing'
  | 'reference_missing'
  | 'scene_vague'
  | 'quality_risk'
  | 'resource_insufficient'
  | 'approval_required'
  | 'budget_exceeded';

// Priority for fixes
type UnlockerPriority = 'quick_win' | 'thirty_days' | 'ninety_days';

interface Blocker {
  id: string;
  severity: BlockerSeverity;
  category: BlockerCategory;
  title: string;
  description: string;
  impact: string;
  affectedItems: string[];
  suggestedFixes: Unlocker[];
  createdAt: string;
  resolved: boolean;
}

interface Unlocker {
  id: string;
  title: string;
  description: string;
  priority: UnlockerPriority;
  estimatedEffort: string;
  impact: string;
  autoApplicable: boolean;
  actionUrl?: string;
}

interface BlockersPanelProps {
  projectId: string;
  onBlockerClick?: (blocker: Blocker) => void;
  onFixClick?: (blocker: Blocker, fix: Unlocker) => void;
  compact?: boolean;
  className?: string;
}

// Severity configuration
const SEVERITY_CONFIG: Record<
  BlockerSeverity,
  {
    icon: typeof AlertCircle;
    bgColor: string;
    textColor: string;
    borderColor: string;
    labelKey: string;
    labelEn: string;
  }
> = {
  critical: {
    icon: AlertCircle,
    bgColor: 'bg-red-500/10',
    textColor: 'text-red-400',
    borderColor: 'border-red-500/30',
    labelKey: 'blockers.severityCritical',
    labelEn: 'Critical',
  },
  high: {
    icon: AlertTriangle,
    bgColor: 'bg-orange-500/10',
    textColor: 'text-orange-400',
    borderColor: 'border-orange-500/30',
    labelKey: 'blockers.severityHigh',
    labelEn: 'High',
  },
  medium: {
    icon: Info,
    bgColor: 'bg-yellow-500/10',
    textColor: 'text-yellow-400',
    borderColor: 'border-yellow-500/30',
    labelKey: 'blockers.severityMedium',
    labelEn: 'Medium',
  },
  low: {
    icon: Info,
    bgColor: 'bg-blue-500/10',
    textColor: 'text-blue-400',
    borderColor: 'border-blue-500/30',
    labelKey: 'blockers.severityLow',
    labelEn: 'Low',
  },
};

// Priority configuration
const PRIORITY_CONFIG: Record<
  UnlockerPriority,
  {
    icon: typeof Zap;
    color: string;
    labelKey: string;
    labelEn: string;
  }
> = {
  quick_win: {
    icon: Zap,
    color: 'text-green-400',
    labelKey: 'blockers.priorityQuickWin',
    labelEn: 'Quick Win',
  },
  thirty_days: {
    icon: Clock,
    color: 'text-yellow-400',
    labelKey: 'blockers.priorityThirtyDays',
    labelEn: '30 Days',
  },
  ninety_days: {
    icon: Target,
    color: 'text-blue-400',
    labelKey: 'blockers.priorityNinetyDays',
    labelEn: '90 Days',
  },
};

// Category labels
const CATEGORY_LABELS: Record<BlockerCategory, { key: string; en: string }> = {
  character_missing: { key: 'blockers.categoryCharacterMissing', en: 'Missing Character' },
  character_incomplete: {
    key: 'blockers.categoryCharacterIncomplete',
    en: 'Incomplete Character',
  },
  voice_missing: { key: 'blockers.categoryVoiceMissing', en: 'Missing Voice' },
  reference_missing: { key: 'blockers.categoryReferenceMissing', en: 'Missing Reference' },
  scene_vague: { key: 'blockers.categorySceneVague', en: 'Vague Scene Description' },
  quality_risk: { key: 'blockers.categoryQualityRisk', en: 'Quality Risk' },
  resource_insufficient: {
    key: 'blockers.categoryResourceInsufficient',
    en: 'Insufficient Resources',
  },
  approval_required: { key: 'blockers.categoryApprovalRequired', en: 'Approval Required' },
  budget_exceeded: { key: 'blockers.categoryBudgetExceeded', en: 'Budget Exceeded' },
};

// Blocker item component
function BlockerItem({
  blocker,
  isExpanded,
  onToggle,
  onFixClick,
  isApplyingFix,
}: {
  blocker: Blocker;
  isExpanded: boolean;
  onToggle: () => void;
  onFixClick: (fix: Unlocker) => void;
  isApplyingFix: string | null;
}) {
  const { t } = useTranslation();
  const config = SEVERITY_CONFIG[blocker.severity];
  const Icon = config.icon;

  return (
    <div
      className={cn(
        'rounded-lg border transition-all',
        config.bgColor,
        config.borderColor,
        isExpanded && 'ring-1 ring-white/10'
      )}
    >
      {/* Header */}
      <button
        onClick={onToggle}
        className="w-full flex items-start gap-3 p-3 text-left hover:bg-white/5 transition-colors"
      >
        <Icon className={cn('w-5 h-5 mt-0.5 flex-shrink-0', config.textColor)} />

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span
              className={cn(
                'text-xs font-medium px-2 py-0.5 rounded',
                config.bgColor,
                config.textColor
              )}
            >
              {t(config.labelKey, config.labelEn)}
            </span>
            <span className="text-xs text-surface-400">
              {t(CATEGORY_LABELS[blocker.category].key, CATEGORY_LABELS[blocker.category].en)}
            </span>
          </div>
          <h4 className="font-medium text-sm text-white truncate">{blocker.title}</h4>
          <p className="text-xs text-surface-400 mt-1 line-clamp-2">{blocker.description}</p>
        </div>

        <div className="flex items-center gap-2">
          {blocker.suggestedFixes.length > 0 && (
            <span className="text-xs text-surface-400 bg-surface-700 px-2 py-1 rounded">
              {blocker.suggestedFixes.length} {t('blockers.fixesCountSuffix', 'fixes')}
            </span>
          )}
          {isExpanded ? (
            <ChevronDown className="w-4 h-4 text-surface-400" />
          ) : (
            <ChevronRight className="w-4 h-4 text-surface-400" />
          )}
        </div>
      </button>

      {/* Expanded content */}
      {isExpanded && (
        <div className="px-3 pb-3 space-y-3">
          {/* Impact */}
          {blocker.impact && (
            <div className="text-xs text-surface-300 bg-surface-800/50 p-2 rounded">
              <span className="font-medium text-surface-200">{t('blockers.impactLabel', 'Impact:')} </span>
              {blocker.impact}
            </div>
          )}

          {/* Affected items */}
          {blocker.affectedItems.length > 0 && (
            <div className="text-xs">
              <span className="text-surface-400">{t('blockers.affectsLabel', 'Affects:')} </span>
              <span className="text-surface-300">
                {blocker.affectedItems.slice(0, 3).join(', ')}
                {blocker.affectedItems.length > 3 &&
                  ` +${blocker.affectedItems.length - 3} ${t('blockers.moreSuffix', 'more')}`}
              </span>
            </div>
          )}

          {/* Suggested fixes */}
          {blocker.suggestedFixes.length > 0 && (
            <div className="space-y-2">
              <h5 className="text-xs font-medium text-surface-300 flex items-center gap-1">
                <Sparkles className="w-3 h-3" />
                {t('blockers.suggestedFixes', 'Suggested Fixes')}
              </h5>
              <div className="space-y-1.5">
                {blocker.suggestedFixes.map((fix) => {
                  const priorityConfig = PRIORITY_CONFIG[fix.priority];
                  const PriorityIcon = priorityConfig.icon;

                  return (
                    <div
                      key={fix.id}
                      className="flex items-center gap-2 bg-surface-800 rounded p-2"
                    >
                      <PriorityIcon className={cn('w-4 h-4 flex-shrink-0', priorityConfig.color)} />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium text-white truncate">{fix.title}</p>
                        <p className="text-xs text-surface-400 truncate">{fix.description}</p>
                      </div>
                      <button
                        onClick={() => onFixClick(fix)}
                        disabled={isApplyingFix === fix.id}
                        className={cn(
                          'flex items-center gap-1 px-2 py-1 rounded text-xs font-medium transition-colors',
                          fix.autoApplicable
                            ? 'bg-brand-500 hover:bg-brand-600 text-white'
                            : 'bg-surface-700 hover:bg-surface-600 text-surface-200'
                        )}
                      >
                        {isApplyingFix === fix.id ? (
                          <Loader2 className="w-3 h-3 animate-spin" />
                        ) : fix.autoApplicable ? (
                          <>
                            <Zap className="w-3 h-3" />
                            {t('blockers.applyFix', 'Apply')}
                          </>
                        ) : (
                          <>
                            <ExternalLink className="w-3 h-3" />
                            {t('blockers.viewFix', 'View')}
                          </>
                        )}
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function BlockersPanel({
  projectId,
  onBlockerClick,
  onFixClick,
  compact = false,
  className,
}: BlockersPanelProps) {
  const { t } = useTranslation();
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [filter, setFilter] = useState<BlockerSeverity | 'all'>('all');
  const [isApplyingFix, setIsApplyingFix] = useState<string | null>(null);
  const queryClient = useQueryClient();

  // Fetch blockers
  const {
    data: blockers,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['blockers', projectId],
    queryFn: async () => {
      const result = await window.electronAPI.backendRequest<{ blockers: Blocker[] }>(
        'blockers.analyze',
        { project_id: projectId }
      );
      return result.blockers || [];
    },
    enabled: !!projectId,
  });

  // Apply fix mutation
  const applyFixMutation = useMutation({
    mutationFn: async ({ blockerId, fixId }: { blockerId: string; fixId: string }) => {
      return await window.electronAPI.backendRequest('blockers.apply_fix', {
        blocker_id: blockerId,
        fix_id: fixId,
      });
    },
    onMutate: ({ fixId }) => {
      setIsApplyingFix(fixId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['blockers', projectId] });
    },
    onSettled: () => {
      setIsApplyingFix(null);
    },
  });

  // Filtered and sorted blockers
  const filteredBlockers = useMemo(() => {
    if (!blockers) return [];

    let result = [...blockers];

    if (filter !== 'all') {
      result = result.filter((b) => b.severity === filter);
    }

    // Sort by severity (critical first)
    const severityOrder: Record<BlockerSeverity, number> = {
      critical: 0,
      high: 1,
      medium: 2,
      low: 3,
    };

    return result.sort((a, b) => severityOrder[a.severity] - severityOrder[b.severity]);
  }, [blockers, filter]);

  // Summary counts
  const summaryCounts = useMemo(() => {
    if (!blockers) return { critical: 0, high: 0, medium: 0, low: 0, total: 0 };

    return blockers.reduce(
      (acc, b) => {
        acc[b.severity]++;
        acc.total++;
        return acc;
      },
      { critical: 0, high: 0, medium: 0, low: 0, total: 0 }
    );
  }, [blockers]);

  const handleToggle = useCallback((id: string) => {
    setExpandedId((prev) => (prev === id ? null : id));
  }, []);

  const handleFixClick = useCallback(
    (blocker: Blocker, fix: Unlocker) => {
      if (onFixClick) {
        onFixClick(blocker, fix);
      }

      if (fix.autoApplicable) {
        applyFixMutation.mutate({ blockerId: blocker.id, fixId: fix.id });
      } else if (fix.actionUrl) {
        // Navigate to action URL
        window.open(fix.actionUrl);
      }
    },
    [onFixClick, applyFixMutation]
  );

  if (isLoading) {
    return (
      <div className={cn('flex items-center justify-center p-8', className)}>
        <Loader2 className="w-6 h-6 animate-spin text-brand-400" />
      </div>
    );
  }

  if (error) {
    return (
      <div className={cn('p-4 text-red-400 text-sm', className)}>
        {t('blockers.loadError', 'Failed to load blockers')}
      </div>
    );
  }

  if (!blockers || blockers.length === 0) {
    return (
      <div className={cn('p-6 text-center', className)}>
        <CheckCircle2 className="w-12 h-12 mx-auto mb-3 text-green-400" />
        <h3 className="text-lg font-medium text-white mb-1">{t('blockers.allClearTitle', 'All Clear!')}</h3>
        <p className="text-sm text-surface-400">
          {t('blockers.allClearMessage', 'No blockers detected. Ready to generate.')}
        </p>
      </div>
    );
  }

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-surface-700">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-yellow-400" />
          <h2 className="font-semibold text-white">{t('blockers.panelTitle', 'Blockers')}</h2>
          <span className="text-xs bg-surface-700 px-2 py-0.5 rounded-full text-surface-300">
            {summaryCounts.total}
          </span>
        </div>

        {/* Summary badges */}
        <div className="flex items-center gap-1">
          {summaryCounts.critical > 0 && (
            <span className="px-2 py-0.5 text-xs font-medium bg-red-500/20 text-red-400 rounded">
              {summaryCounts.critical} {t('blockers.severityCritical', 'Critical')}
            </span>
          )}
          {summaryCounts.high > 0 && (
            <span className="px-2 py-0.5 text-xs font-medium bg-orange-500/20 text-orange-400 rounded">
              {summaryCounts.high} {t('blockers.severityHigh', 'High')}
            </span>
          )}
        </div>
      </div>

      {/* Filters */}
      {!compact && (
        <div className="flex items-center gap-1 p-2 border-b border-surface-700">
          {(['all', 'critical', 'high', 'medium', 'low'] as const).map((severity) => (
            <button
              key={severity}
              onClick={() => setFilter(severity)}
              className={cn(
                'px-3 py-1 text-xs rounded transition-colors',
                filter === severity
                  ? 'bg-brand-500 text-white'
                  : 'text-surface-400 hover:bg-surface-700'
              )}
            >
              {severity === 'all'
                ? t('blockers.filterAll', 'All')
                : t(SEVERITY_CONFIG[severity].labelKey, SEVERITY_CONFIG[severity].labelEn)}
            </button>
          ))}
        </div>
      )}

      {/* Blockers list */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {filteredBlockers.map((blocker) => (
          <BlockerItem
            key={blocker.id}
            blocker={blocker}
            isExpanded={expandedId === blocker.id}
            onToggle={() => handleToggle(blocker.id)}
            onFixClick={(fix) => handleFixClick(blocker, fix)}
            isApplyingFix={isApplyingFix}
          />
        ))}
      </div>
    </div>
  );
}

export default BlockersPanel;
