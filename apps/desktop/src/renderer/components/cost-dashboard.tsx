/**
 * Cost tracking dashboard component.
 * Displays cost breakdown by provider, project, and time period.
 */

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  DollarSign,
  TrendingUp,
  TrendingDown,
  PieChart,
  Calendar,
  RefreshCw,
  Loader2,
  AlertTriangle,
  BarChart3,
  Layers,
  Film,
  Settings,
  Shield,
} from 'lucide-react';
import { cn } from '../lib/utils';

// Cost stats interfaces
interface CostStats {
  total_cost_usd: number;
  cost_by_provider: Record<string, number>;
  cost_by_project: Record<string, number>;
  avg_cost_per_shot: number;
}

interface DailyStats {
  date: string;
  total_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  success_rate: number;
  total_cost_usd: number;
}

interface ProviderUsage {
  provider: string;
  total_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  success_rate: number;
  total_cost_usd: number;
}

// Format currency
function formatCurrency(amount: number): string {
  if (amount < 0.01) return '$0.00';
  return `$${amount.toFixed(2)}`;
}

// Cost stat card
function CostStatCard({
  icon: Icon,
  label,
  value,
  subValue,
  trend,
  color = 'brand',
}: {
  icon: typeof DollarSign;
  label: string;
  value: string;
  subValue?: string;
  trend?: { direction: 'up' | 'down'; percent: number };
  color?: 'brand' | 'green' | 'red' | 'yellow' | 'blue';
}) {
  const colorClasses = {
    brand: 'bg-brand-500/20 text-brand-400',
    green: 'bg-green-500/20 text-green-400',
    red: 'bg-red-500/20 text-red-400',
    yellow: 'bg-yellow-500/20 text-yellow-400',
    blue: 'bg-blue-500/20 text-blue-400',
  };

  return (
    <div className="p-4 bg-surface-800 rounded-lg">
      <div className="flex items-start justify-between mb-2">
        <div className={cn('p-2 rounded-lg', colorClasses[color])}>
          <Icon className="w-5 h-5" />
        </div>
        {trend && (
          <div
            className={cn(
              'flex items-center gap-1 text-xs',
              trend.direction === 'up' ? 'text-green-400' : 'text-red-400'
            )}
          >
            {trend.direction === 'up' ? (
              <TrendingUp className="w-3 h-3" />
            ) : (
              <TrendingDown className="w-3 h-3" />
            )}
            {trend.percent.toFixed(1)}%
          </div>
        )}
      </div>
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-sm text-surface-400">{label}</div>
      {subValue && <div className="text-xs text-surface-500 mt-1">{subValue}</div>}
    </div>
  );
}

// Provider cost breakdown
function ProviderCostBreakdown({ costs }: { costs: Record<string, number> }) {
  const total = Object.values(costs).reduce((sum, cost) => sum + cost, 0);
  const providers = Object.entries(costs)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 6);

  const colors = [
    'bg-brand-500',
    'bg-blue-500',
    'bg-green-500',
    'bg-yellow-500',
    'bg-purple-500',
    'bg-pink-500',
  ];

  if (providers.length === 0) {
    return (
      <div className="text-center py-8 text-surface-400">
        <PieChart className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p>No cost data available</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Visual bar chart */}
      <div className="h-4 rounded-full overflow-hidden flex bg-surface-700">
        {providers.map(([provider, cost], index) => {
          const percentage = total > 0 ? (cost / total) * 100 : 0;
          if (percentage < 1) return null;
          return (
            <div
              key={provider}
              className={cn('h-full', colors[index % colors.length])}
              style={{ width: `${percentage}%` }}
              title={`${provider}: ${formatCurrency(cost)} (${percentage.toFixed(1)}%)`}
            />
          );
        })}
      </div>

      {/* Legend */}
      <div className="space-y-2">
        {providers.map(([provider, cost], index) => {
          const percentage = total > 0 ? (cost / total) * 100 : 0;
          return (
            <div key={provider} className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className={cn('w-3 h-3 rounded', colors[index % colors.length])} />
                <span className="text-sm capitalize">{provider}</span>
              </div>
              <div className="text-sm">
                <span className="font-medium">{formatCurrency(cost)}</span>
                <span className="text-surface-400 ml-2">({percentage.toFixed(1)}%)</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Total */}
      <div className="pt-2 border-t border-surface-700 flex justify-between">
        <span className="text-sm font-medium">Total</span>
        <span className="font-bold">{formatCurrency(total)}</span>
      </div>
    </div>
  );
}

// Project cost breakdown
function ProjectCostBreakdown({ costs }: { costs: Record<string, number> }) {
  const projects = Object.entries(costs)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 5);

  if (projects.length === 0) {
    return (
      <div className="text-center py-8 text-surface-400">
        <Layers className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p>No project costs yet</p>
      </div>
    );
  }

  const maxCost = Math.max(...projects.map(([, cost]) => cost));

  return (
    <div className="space-y-3">
      {projects.map(([project, cost]) => {
        const percentage = maxCost > 0 ? (cost / maxCost) * 100 : 0;
        return (
          <div key={project}>
            <div className="flex justify-between text-sm mb-1">
              <span className="truncate mr-2">{project}</span>
              <span className="font-medium shrink-0">{formatCurrency(cost)}</span>
            </div>
            <div className="h-2 bg-surface-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-brand-500 rounded-full transition-all"
                style={{ width: `${percentage}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

// Daily cost chart
function DailyCostChart({ data }: { data: DailyStats[] }) {
  if (data.length === 0) {
    return (
      <div className="text-center py-8 text-surface-400">
        <BarChart3 className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p>No daily data available</p>
      </div>
    );
  }

  const maxCost = Math.max(...data.map((d) => d.total_cost_usd), 0.01);

  return (
    <div className="space-y-4">
      {/* Bar chart */}
      <div className="flex items-end gap-1 h-32">
        {data.map((day, index) => {
          const height = maxCost > 0 ? (day.total_cost_usd / maxCost) * 100 : 0;
          return (
            <div
              key={day.date}
              className="flex-1 flex flex-col items-center group"
              title={`${day.date}: ${formatCurrency(day.total_cost_usd)}`}
            >
              <div
                className="w-full bg-brand-500 rounded-t transition-all hover:bg-brand-400"
                style={{ height: `${Math.max(height, 2)}%` }}
              />
            </div>
          );
        })}
      </div>

      {/* X-axis labels */}
      <div className="flex justify-between text-xs text-surface-400">
        {data.length > 0 && (
          <>
            <span>{new Date(data[0].date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
            <span>{new Date(data[data.length - 1].date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
          </>
        )}
      </div>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-4 pt-2 border-t border-surface-700 text-sm">
        <div>
          <span className="text-surface-400">Total</span>
          <p className="font-medium">{formatCurrency(data.reduce((sum, d) => sum + d.total_cost_usd, 0))}</p>
        </div>
        <div>
          <span className="text-surface-400">Jobs</span>
          <p className="font-medium">{data.reduce((sum, d) => sum + d.total_jobs, 0)}</p>
        </div>
        <div>
          <span className="text-surface-400">Avg/Day</span>
          <p className="font-medium">
            {formatCurrency(data.reduce((sum, d) => sum + d.total_cost_usd, 0) / Math.max(data.length, 1))}
          </p>
        </div>
      </div>
    </div>
  );
}

// Provider usage table
function ProviderUsageTable({ data }: { data: ProviderUsage[] }) {
  if (data.length === 0) {
    return (
      <div className="text-center py-8 text-surface-400">
        <Film className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p>No provider usage data</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-surface-400 border-b border-surface-700">
            <th className="pb-2 font-medium">Provider</th>
            <th className="pb-2 font-medium text-right">Jobs</th>
            <th className="pb-2 font-medium text-right">Success</th>
            <th className="pb-2 font-medium text-right">Cost</th>
          </tr>
        </thead>
        <tbody>
          {data.map((provider) => (
            <tr key={provider.provider} className="border-b border-surface-800">
              <td className="py-2 capitalize">{provider.provider}</td>
              <td className="py-2 text-right">{provider.total_jobs}</td>
              <td className="py-2 text-right">
                <span
                  className={cn(
                    provider.success_rate >= 90
                      ? 'text-green-400'
                      : provider.success_rate >= 70
                        ? 'text-yellow-400'
                        : 'text-red-400'
                  )}
                >
                  {provider.success_rate.toFixed(1)}%
                </span>
              </td>
              <td className="py-2 text-right font-medium">{formatCurrency(provider.total_cost_usd)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Time range selector
function TimeRangeSelector({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  const ranges = [
    { value: '24h', label: '24H' },
    { value: '7d', label: '7D' },
    { value: '30d', label: '30D' },
    { value: 'all', label: 'All' },
  ];

  return (
    <div className="flex gap-1 bg-surface-800 rounded-lg p-1">
      {ranges.map((range) => (
        <button
          key={range.value}
          onClick={() => onChange(range.value)}
          className={cn(
            'px-3 py-1.5 text-sm rounded-md transition-colors',
            value === range.value
              ? 'bg-brand-500 text-white'
              : 'text-surface-400 hover:text-surface-200'
          )}
        >
          {range.label}
        </button>
      ))}
    </div>
  );
}

interface CostDashboardProps {
  projectId?: string;
}

export function CostDashboard({ projectId }: CostDashboardProps) {
  const queryClient = useQueryClient();
  const [timeRange, setTimeRange] = useState('7d');
  const [showBudgetForm, setShowBudgetForm] = useState(false);
  const [budgetInput, setBudgetInput] = useState('100');

  // Fetch cost stats
  const { data: costStats, isLoading: costLoading, refetch: refetchCost } = useQuery({
    queryKey: ['cost-stats', timeRange, projectId],
    queryFn: async () => {
      return window.electronAPI.backendRequest<CostStats>('analytics.getCostStats', {
        time_range: timeRange,
        project_id: projectId,
      });
    },
  });

  // Fetch daily stats
  const { data: dailyStats, isLoading: dailyLoading } = useQuery({
    queryKey: ['daily-stats', timeRange, projectId],
    queryFn: async () => {
      const days = timeRange === '24h' ? 1 : timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90;
      return window.electronAPI.backendRequest<DailyStats[]>('analytics.getDailyStats', {
        days,
        project_id: projectId,
      });
    },
  });

  // Fetch provider usage
  const { data: providerUsage, isLoading: providerLoading } = useQuery({
    queryKey: ['provider-usage', timeRange],
    queryFn: async () => {
      return window.electronAPI.backendRequest<ProviderUsage[]>('analytics.getProviderUsage', {
        time_range: timeRange,
      });
    },
  });

  // Fetch budget status
  const { data: budgetStatus } = useQuery({
    queryKey: ['budget-status'],
    queryFn: async () => {
      return window.electronAPI.backendRequest<{
        budget: {
          has_budget: boolean;
          limit_usd?: number;
          remaining_usd?: number;
          percent_used?: number;
          status?: string;
        };
        currentSpend: number;
        totalJobs: number;
        budgetAlert: {
          alert_type?: string;
          current_spend_usd?: number;
          budget_limit_usd?: number;
          percent_used?: number;
        } | null;
      }>('analytics.getBudget', {});
    },
  });

  // Set budget mutation
  const setBudgetMutation = useMutation({
    mutationFn: async (limitUsd: number) => {
      return window.electronAPI.backendRequest('analytics.setBudget', {
        limit_usd: limitUsd,
        period_days: 30,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budget-status'] });
      setShowBudgetForm(false);
    },
  });

  const isLoading = costLoading || dailyLoading || providerLoading;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-medium flex items-center gap-2">
            <DollarSign className="w-5 h-5 text-brand-400" />
            Cost Tracking
          </h2>
          <p className="text-sm text-surface-400 mt-1">
            Monitor generation costs and usage across providers
          </p>
        </div>

        <div className="flex items-center gap-4">
          <TimeRangeSelector value={timeRange} onChange={setTimeRange} />
          <button
            onClick={() => refetchCost()}
            disabled={isLoading}
            className="p-2 hover:bg-surface-700 rounded-lg"
            title="Refresh"
          >
            <RefreshCw className={cn('w-4 h-4', isLoading && 'animate-spin')} />
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-brand-400" />
        </div>
      ) : (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <CostStatCard
              icon={DollarSign}
              label="Total Spent"
              value={formatCurrency(costStats?.total_cost_usd || 0)}
              color="green"
            />
            <CostStatCard
              icon={Film}
              label="Avg Cost/Shot"
              value={formatCurrency(costStats?.avg_cost_per_shot || 0)}
              color="blue"
            />
            <CostStatCard
              icon={Layers}
              label="Active Providers"
              value={String(Object.keys(costStats?.cost_by_provider || {}).length)}
              color="brand"
            />
            <CostStatCard
              icon={Calendar}
              label="Active Projects"
              value={String(Object.keys(costStats?.cost_by_project || {}).length)}
              color="yellow"
            />
          </div>

          {/* Charts grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Provider breakdown */}
            <div className="card">
              <h3 className="text-sm font-medium text-surface-400 mb-4 flex items-center gap-2">
                <PieChart className="w-4 h-4" />
                Cost by Provider
              </h3>
              <ProviderCostBreakdown costs={costStats?.cost_by_provider || {}} />
            </div>

            {/* Project breakdown */}
            <div className="card">
              <h3 className="text-sm font-medium text-surface-400 mb-4 flex items-center gap-2">
                <Layers className="w-4 h-4" />
                Cost by Project
              </h3>
              <ProjectCostBreakdown costs={costStats?.cost_by_project || {}} />
            </div>
          </div>

          {/* Daily chart */}
          <div className="card">
            <h3 className="text-sm font-medium text-surface-400 mb-4 flex items-center gap-2">
              <BarChart3 className="w-4 h-4" />
              Daily Costs
            </h3>
            <DailyCostChart data={dailyStats || []} />
          </div>

          {/* Provider usage table */}
          <div className="card">
            <h3 className="text-sm font-medium text-surface-400 mb-4 flex items-center gap-2">
              <Film className="w-4 h-4" />
              Provider Performance
            </h3>
            <ProviderUsageTable data={providerUsage || []} />
          </div>

          {/* Budget Management */}
          <div className="card">
            <h3 className="text-sm font-medium text-surface-400 mb-4 flex items-center gap-2">
              <Shield className="w-4 h-4" />
              Budget Management
              <button
                onClick={() => setShowBudgetForm(!showBudgetForm)}
                className="ml-auto p-1 hover:bg-surface-700 rounded transition-colors"
                title="Configure budget"
              >
                <Settings className="w-3.5 h-3.5 text-surface-400" />
              </button>
            </h3>

            {budgetStatus?.budget?.has_budget ? (
              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-surface-400">Spent / Limit</span>
                  <span className="font-medium">
                    {formatCurrency(budgetStatus.currentSpend)} / {formatCurrency(budgetStatus.budget.limit_usd ?? 0)}
                  </span>
                </div>
                <div className="h-2.5 bg-surface-700 rounded-full overflow-hidden">
                  <div
                    className={cn(
                      'h-full rounded-full transition-all',
                      (budgetStatus.budget.percent_used ?? 0) >= 100
                        ? 'bg-red-500'
                        : (budgetStatus.budget.percent_used ?? 0) >= 80
                          ? 'bg-yellow-500'
                          : 'bg-green-500'
                    )}
                    style={{ width: `${Math.min(100, budgetStatus.budget.percent_used ?? 0)}%` }}
                  />
                </div>
                <div className="flex justify-between text-xs text-surface-500">
                  <span>{Math.round(budgetStatus.budget.percent_used ?? 0)}% used</span>
                  <span>{formatCurrency(budgetStatus.budget.remaining_usd ?? 0)} remaining</span>
                </div>

                {budgetStatus.budgetAlert && (
                  <div className={cn(
                    'p-3 rounded-lg flex items-start gap-2 text-sm mt-2',
                    budgetStatus.budgetAlert.alert_type === 'budget_exceeded'
                      ? 'bg-red-500/10 border border-red-500/30 text-red-400'
                      : 'bg-yellow-500/10 border border-yellow-500/30 text-yellow-400'
                  )}>
                    <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                    <span>
                      {budgetStatus.budgetAlert.alert_type === 'budget_exceeded'
                        ? 'Budget exceeded! Generation will be blocked until limit is raised.'
                        : `Warning: ${Math.round(budgetStatus.budgetAlert.percent_used ?? 0)}% of budget used.`}
                    </span>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-4 text-surface-400 text-sm">
                <Shield className="w-6 h-6 mx-auto mb-2 opacity-50" />
                No budget limit configured
              </div>
            )}

            {showBudgetForm && (
              <div className="mt-4 pt-4 border-t border-surface-700">
                <label className="text-xs text-surface-400 mb-1 block">30-day budget limit (USD)</label>
                <div className="flex gap-2">
                  <input
                    type="number"
                    value={budgetInput}
                    onChange={(e) => setBudgetInput(e.target.value)}
                    placeholder="$ limit"
                    className="flex-1 px-3 py-1.5 bg-surface-700 border border-surface-600 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-brand-500"
                    min="1"
                  />
                  <button
                    onClick={() => setBudgetMutation.mutate(parseFloat(budgetInput))}
                    disabled={setBudgetMutation.isPending || !budgetInput}
                    className="btn-primary text-xs px-4"
                  >
                    {setBudgetMutation.isPending ? (
                      <Loader2 className="w-3 h-3 animate-spin" />
                    ) : (
                      'Set Budget'
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

export default CostDashboard;
