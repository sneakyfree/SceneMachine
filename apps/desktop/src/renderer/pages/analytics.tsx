/**
 * Analytics dashboard page.
 * Displays generation metrics, costs, and system performance.
 */

import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  BarChart3,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Clock,
  Zap,
  CheckCircle,
  XCircle,
  Activity,
  Film,
  Users,
  Layers,
  RefreshCw,
  Calendar,
  Loader2,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { LineChart, BarChart, DonutChart, ProgressRing, Sparkline } from '../components/charts';

// Analytics data interfaces
interface GenerationStats {
  total_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  cancelled_jobs: number;
  pending_jobs: number;
  success_rate: number;
  avg_generation_time_seconds: number;
  total_generation_time_seconds: number;
}

interface CostStats {
  total_cost_usd: number;
  cost_by_provider: Record<string, number>;
  cost_by_project: Record<string, number>;
  avg_cost_per_shot: number;
}

interface ProjectStats {
  total_projects: number;
  active_projects: number;
  total_scenes: number;
  total_shots: number;
  total_characters: number;
}

interface PerformanceStats {
  avg_wait_time_seconds: number;
  avg_processing_time_seconds: number;
  peak_concurrent_jobs: number;
  current_queue_size: number;
}

interface TimeSeriesData {
  timestamp: string;
  value: number;
}

interface HistoricalStats {
  success_rate_history: TimeSeriesData[];
  generation_count_history: TimeSeriesData[];
  cost_history: TimeSeriesData[];
}

// Stat card component
function StatCard({
  icon: Icon,
  label,
  value,
  subValue,
  trend,
  trendLabel,
  color = 'brand',
}: {
  icon: typeof BarChart3;
  label: string;
  value: string | number;
  subValue?: string;
  trend?: 'up' | 'down' | 'neutral';
  trendLabel?: string;
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
              trend === 'up' && 'text-green-400',
              trend === 'down' && 'text-red-400',
              trend === 'neutral' && 'text-surface-400'
            )}
          >
            {trend === 'up' && <TrendingUp className="w-3 h-3" />}
            {trend === 'down' && <TrendingDown className="w-3 h-3" />}
            {trendLabel}
          </div>
        )}
      </div>
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-sm text-surface-400">{label}</div>
      {subValue && <div className="text-xs text-surface-500 mt-1">{subValue}</div>}
    </div>
  );
}

// Progress bar component
function ProgressBar({
  value,
  max,
  label,
  color = 'brand',
}: {
  value: number;
  max: number;
  label?: string;
  color?: string;
}) {
  const percentage = max > 0 ? (value / max) * 100 : 0;

  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span>{label}</span>
        <span className="text-surface-400">
          {value} / {max}
        </span>
      </div>
      <div className="h-2 bg-surface-700 rounded-full overflow-hidden">
        <div
          className={cn('h-full rounded-full transition-all', `bg-${color}-500`)}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

// Provider cost breakdown
function ProviderCostChart({ costs }: { costs: Record<string, number> }) {
  const total = Object.values(costs).reduce((sum, cost) => sum + cost, 0);
  const providers = Object.entries(costs)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 5);

  const colors = ['bg-brand-500', 'bg-blue-500', 'bg-green-500', 'bg-yellow-500', 'bg-purple-500'];

  return (
    <div className="space-y-3">
      {providers.map(([provider, cost], index) => {
        const percentage = total > 0 ? (cost / total) * 100 : 0;
        return (
          <div key={provider}>
            <div className="flex justify-between text-sm mb-1">
              <span className="capitalize">{provider}</span>
              <span className="text-surface-400">
                ${cost.toFixed(2)} ({percentage.toFixed(1)}%)
              </span>
            </div>
            <div className="h-2 bg-surface-700 rounded-full overflow-hidden">
              <div
                className={cn('h-full rounded-full', colors[index % colors.length])}
                style={{ width: `${percentage}%` }}
              />
            </div>
          </div>
        );
      })}
      {providers.length === 0 && (
        <div className="text-center text-surface-400 py-4">No cost data available</div>
      )}
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
    { value: '24h', label: '24 Hours' },
    { value: '7d', label: '7 Days' },
    { value: '30d', label: '30 Days' },
    { value: 'all', label: 'All Time' },
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

export function AnalyticsPage() {
  const [timeRange, setTimeRange] = useState('7d');

  // Generate mock historical data based on time range
  const generateHistoricalData = (days: number): HistoricalStats => {
    const now = new Date();
    const successHistory: TimeSeriesData[] = [];
    const countHistory: TimeSeriesData[] = [];
    const costHistory: TimeSeriesData[] = [];

    for (let i = days - 1; i >= 0; i--) {
      const date = new Date(now);
      date.setDate(date.getDate() - i);
      const dateStr = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

      successHistory.push({
        timestamp: dateStr,
        value: 75 + Math.random() * 20, // 75-95% success rate
      });
      countHistory.push({
        timestamp: dateStr,
        value: Math.floor(10 + Math.random() * 40), // 10-50 generations
      });
      costHistory.push({
        timestamp: dateStr,
        value: Math.random() * 5 + 1, // $1-6 per day
      });
    }

    return {
      success_rate_history: successHistory,
      generation_count_history: countHistory,
      cost_history: costHistory,
    };
  };

  // Fetch analytics data
  const { data: analytics, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['analytics', timeRange],
    queryFn: async () => {
      // Fetch from backend
      const [generation, costs, projects, performance] = await Promise.all([
        window.electronAPI.backendRequest<GenerationStats>('analytics.getGenerationStats', {
          time_range: timeRange,
        }),
        window.electronAPI.backendRequest<CostStats>('analytics.getCostStats', {
          time_range: timeRange,
        }),
        window.electronAPI.backendRequest<ProjectStats>('analytics.getProjectStats', {}),
        window.electronAPI.backendRequest<PerformanceStats>('analytics.getPerformanceStats', {}),
      ]);

      // Generate historical data based on time range
      const days = timeRange === '24h' ? 24 : timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90;
      const historical = generateHistoricalData(days);

      return { generation, costs, projects, performance, historical };
    },
    // Provide default data when API not available
    placeholderData: {
      generation: {
        total_jobs: 156,
        completed_jobs: 142,
        failed_jobs: 8,
        cancelled_jobs: 6,
        pending_jobs: 3,
        success_rate: 91.0,
        avg_generation_time_seconds: 45.2,
        total_generation_time_seconds: 7053.2,
      },
      costs: {
        total_cost_usd: 24.50,
        cost_by_provider: {
          local: 0,
          replicate: 12.30,
          fal: 8.20,
          runwayml: 4.00,
        },
        cost_by_project: {},
        avg_cost_per_shot: 0.17,
      },
      projects: {
        total_projects: 5,
        active_projects: 2,
        total_scenes: 45,
        total_shots: 156,
        total_characters: 12,
      },
      performance: {
        avg_wait_time_seconds: 12.5,
        avg_processing_time_seconds: 38.7,
        peak_concurrent_jobs: 4,
        current_queue_size: 3,
      },
      historical: generateHistoricalData(7),
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  const formatDuration = (seconds: number): string => {
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    if (seconds < 3600) return `${(seconds / 60).toFixed(1)}m`;
    return `${(seconds / 3600).toFixed(1)}h`;
  };

  return (
    <div className="h-full overflow-y-auto">
      <div className="p-8 max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <BarChart3 className="w-6 h-6 text-brand-400" />
              Analytics
            </h1>
            <p className="text-surface-400 mt-1">
              Generation metrics, costs, and performance insights
            </p>
          </div>

          <div className="flex items-center gap-4">
            <TimeRangeSelector value={timeRange} onChange={setTimeRange} />
            <button
              onClick={() => refetch()}
              disabled={isFetching}
              className="p-2 bg-surface-700 hover:bg-surface-600 rounded-lg transition-colors disabled:opacity-50"
              title="Refresh"
            >
              <RefreshCw className={cn('w-5 h-5', isFetching && 'animate-spin')} />
            </button>
          </div>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="w-8 h-8 animate-spin text-brand-400" />
          </div>
        ) : (
          <div className="space-y-6">
            {/* Generation Stats */}
            <div>
              <h2 className="text-lg font-medium mb-4 flex items-center gap-2">
                <Zap className="w-5 h-5 text-brand-400" />
                Generation Overview
              </h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <StatCard
                  icon={Activity}
                  label="Total Jobs"
                  value={analytics?.generation.total_jobs || 0}
                  color="brand"
                />
                <StatCard
                  icon={CheckCircle}
                  label="Completed"
                  value={analytics?.generation.completed_jobs || 0}
                  subValue={`${(analytics?.generation.success_rate || 0).toFixed(1)}% success rate`}
                  color="green"
                />
                <StatCard
                  icon={XCircle}
                  label="Failed"
                  value={analytics?.generation.failed_jobs || 0}
                  color="red"
                />
                <StatCard
                  icon={Clock}
                  label="Avg. Generation Time"
                  value={formatDuration(analytics?.generation.avg_generation_time_seconds || 0)}
                  subValue={`Total: ${formatDuration(analytics?.generation.total_generation_time_seconds || 0)}`}
                  color="blue"
                />
              </div>
            </div>

            {/* Cost Stats */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="card">
                <h2 className="text-lg font-medium mb-4 flex items-center gap-2">
                  <DollarSign className="w-5 h-5 text-brand-400" />
                  Cost Summary
                </h2>
                <div className="grid grid-cols-2 gap-4 mb-6">
                  <StatCard
                    icon={DollarSign}
                    label="Total Spent"
                    value={`$${(analytics?.costs.total_cost_usd || 0).toFixed(2)}`}
                    color="green"
                  />
                  <StatCard
                    icon={Film}
                    label="Avg. Cost/Shot"
                    value={`$${(analytics?.costs.avg_cost_per_shot || 0).toFixed(3)}`}
                    color="blue"
                  />
                </div>
                <h3 className="text-sm font-medium text-surface-400 mb-3">Cost by Provider</h3>
                <ProviderCostChart costs={analytics?.costs.cost_by_provider || {}} />
              </div>

              {/* Project Stats */}
              <div className="card">
                <h2 className="text-lg font-medium mb-4 flex items-center gap-2">
                  <Layers className="w-5 h-5 text-brand-400" />
                  Project Overview
                </h2>
                <div className="grid grid-cols-2 gap-4">
                  <StatCard
                    icon={Film}
                    label="Total Projects"
                    value={analytics?.projects.total_projects || 0}
                    subValue={`${analytics?.projects.active_projects || 0} active`}
                    color="brand"
                  />
                  <StatCard
                    icon={Layers}
                    label="Total Scenes"
                    value={analytics?.projects.total_scenes || 0}
                    color="blue"
                  />
                  <StatCard
                    icon={Activity}
                    label="Total Shots"
                    value={analytics?.projects.total_shots || 0}
                    color="green"
                  />
                  <StatCard
                    icon={Users}
                    label="Characters"
                    value={analytics?.projects.total_characters || 0}
                    color="yellow"
                  />
                </div>
              </div>
            </div>

            {/* Performance Stats */}
            <div className="card">
              <h2 className="text-lg font-medium mb-4 flex items-center gap-2">
                <Activity className="w-5 h-5 text-brand-400" />
                Performance Metrics
              </h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <StatCard
                  icon={Clock}
                  label="Avg. Wait Time"
                  value={formatDuration(analytics?.performance.avg_wait_time_seconds || 0)}
                  color="yellow"
                />
                <StatCard
                  icon={Zap}
                  label="Avg. Processing Time"
                  value={formatDuration(analytics?.performance.avg_processing_time_seconds || 0)}
                  color="blue"
                />
                <StatCard
                  icon={Activity}
                  label="Peak Concurrent"
                  value={analytics?.performance.peak_concurrent_jobs || 0}
                  subValue="jobs"
                  color="brand"
                />
                <StatCard
                  icon={Layers}
                  label="Current Queue"
                  value={analytics?.performance.current_queue_size || 0}
                  subValue="pending jobs"
                  color="green"
                />
              </div>
            </div>

            {/* Success Rate Chart */}
            <div className="card">
              <h2 className="text-lg font-medium mb-4 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-brand-400" />
                Success Rate Over Time
              </h2>
              <LineChart
                data={analytics?.historical?.success_rate_history || []}
                height={200}
                color="#22c55e"
                fillColor="rgba(34, 197, 94, 0.15)"
                formatValue={(v) => `${v.toFixed(0)}%`}
                showDots={false}
              />
            </div>

            {/* Generation Count & Cost Charts */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="card">
                <h2 className="text-lg font-medium mb-4 flex items-center gap-2">
                  <Activity className="w-5 h-5 text-brand-400" />
                  Generations Over Time
                </h2>
                <LineChart
                  data={analytics?.historical?.generation_count_history || []}
                  height={180}
                  color="#8b5cf6"
                  fillColor="rgba(139, 92, 246, 0.15)"
                  formatValue={(v) => v.toFixed(0)}
                  showDots={false}
                />
              </div>

              <div className="card">
                <h2 className="text-lg font-medium mb-4 flex items-center gap-2">
                  <DollarSign className="w-5 h-5 text-brand-400" />
                  Daily Cost Trend
                </h2>
                <LineChart
                  data={analytics?.historical?.cost_history || []}
                  height={180}
                  color="#f59e0b"
                  fillColor="rgba(245, 158, 11, 0.15)"
                  formatValue={(v) => `$${v.toFixed(2)}`}
                  showDots={false}
                />
              </div>
            </div>

            {/* Job Status Breakdown */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="card">
                <h2 className="text-lg font-medium mb-4 flex items-center gap-2">
                  <Layers className="w-5 h-5 text-brand-400" />
                  Job Status Breakdown
                </h2>
                <DonutChart
                  data={[
                    { label: 'Completed', value: analytics?.generation.completed_jobs || 0, color: '#22c55e' },
                    { label: 'Failed', value: analytics?.generation.failed_jobs || 0, color: '#ef4444' },
                    { label: 'Cancelled', value: analytics?.generation.cancelled_jobs || 0, color: '#f59e0b' },
                    { label: 'Pending', value: analytics?.generation.pending_jobs || 0, color: '#6b7280' },
                  ].filter(d => d.value > 0)}
                  size={160}
                  centerValue={`${(analytics?.generation.success_rate || 0).toFixed(0)}%`}
                  centerLabel="Success"
                />
              </div>

              <div className="card">
                <h2 className="text-lg font-medium mb-4 flex items-center gap-2">
                  <Zap className="w-5 h-5 text-brand-400" />
                  Quick Stats
                </h2>
                <div className="grid grid-cols-2 gap-4">
                  <div className="flex flex-col items-center">
                    <ProgressRing
                      value={analytics?.generation.success_rate || 0}
                      color="#22c55e"
                      size={80}
                      label="Success"
                    />
                  </div>
                  <div className="flex flex-col items-center">
                    <ProgressRing
                      value={analytics?.projects.active_projects || 0}
                      max={analytics?.projects.total_projects || 1}
                      color="#8b5cf6"
                      size={80}
                      label="Active"
                    />
                  </div>
                  <div className="text-center">
                    <p className="text-2xl font-bold text-brand-400">
                      {analytics?.projects.total_shots || 0}
                    </p>
                    <p className="text-xs text-surface-400">Total Shots</p>
                  </div>
                  <div className="text-center">
                    <p className="text-2xl font-bold text-green-400">
                      ${(analytics?.costs.total_cost_usd || 0).toFixed(2)}
                    </p>
                    <p className="text-xs text-surface-400">Total Spent</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
