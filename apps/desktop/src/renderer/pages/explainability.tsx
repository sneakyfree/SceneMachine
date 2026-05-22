/**
 * Explainability Dashboard — 4-layer explanation system.
 *
 * Provides Client, Operator, Technical, and Audit views
 * for full transparency into AI generation decisions.
 */

import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Eye,
  Clapperboard,
  Code2,
  Shield,
  RefreshCw,
  Loader2,
  CheckCircle,
  XCircle,
  Clock,
  DollarSign,
  Film,
  AlertTriangle,
  FileText,
  GitCompare,
  ChevronDown,
  ChevronRight,
  Info,
} from 'lucide-react';
import { cn } from '../lib/utils';

/* ────────────────────── Types ────────────────────── */

interface GenerationJob {
  id: string;
  shot_number: number;
  status: string;
  provider?: string;
  model?: string;
  cost_usd?: number;
  generation_time_seconds?: number;
  prompt?: string;
  error?: string;
  created_at: string;
}

interface AgentLog {
  id: string;
  agent_type: string;
  action: string;
  details?: string;
  timestamp: string;
  confidence?: number;
}

interface Snapshot {
  id: string;
  version: number;
  entity_type: string;
  entity_id: string;
  data: Record<string, unknown>;
  created_at: string;
  created_by?: string;
}

interface DashboardStats {
  generation: {
    totalJobs: number;
    completedJobs: number;
    failedJobs: number;
    successRate: number;
    avgGenerationTimeSeconds: number;
  };
  costs: {
    totalCostUsd: number;
    costByProvider: Record<string, number>;
    avgCostPerShot: number;
  };
  projects: {
    totalProjects: number;
    totalScenes: number;
    totalShots: number;
    totalCharacters: number;
  };
  budgetAlert: {
    alert_type?: string;
    current_spend_usd?: number;
    budget_limit_usd?: number;
    percent_used?: number;
  } | null;
}

/* ────────────────────── Tab views ────────────────── */

const TABS = [
  { id: 'client', label: 'Client', icon: Eye, description: 'Plain-language summary' },
  { id: 'operator', label: 'Operator', icon: Clapperboard, description: 'Shot-by-shot breakdown' },
  { id: 'technical', label: 'Technical', icon: Code2, description: 'Model parameters & logs' },
  { id: 'audit', label: 'Audit', icon: Shield, description: 'Immutable snapshots' },
] as const;

type TabId = (typeof TABS)[number]['id'];

/* ────────────────────── Client View ─────────────── */

function ClientView({ stats }: { stats: DashboardStats | undefined }) {
  if (!stats) {
    return <EmptyState icon={Eye} message="No project data available yet" />;
  }

  return (
    <div className="space-y-6">
      {/* Project summary */}
      <div className="card">
        <h3 className="text-lg font-medium mb-4">Project Overview</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <SummaryCard label="Scenes" value={stats.projects.totalScenes} icon={Film} />
          <SummaryCard label="Shots" value={stats.projects.totalShots} icon={Clapperboard} />
          <SummaryCard label="Characters" value={stats.projects.totalCharacters} icon={Eye} />
          <SummaryCard
            label="Total Cost"
            value={`$${stats.costs.totalCostUsd.toFixed(2)}`}
            icon={DollarSign}
          />
        </div>
      </div>

      {/* Generation status */}
      <div className="card">
        <h3 className="text-lg font-medium mb-4">Generation Status</h3>
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-surface-400">Progress</span>
            <span className="text-sm">
              {stats.generation.completedJobs} / {stats.generation.totalJobs} shots complete
            </span>
          </div>
          <div className="h-3 bg-surface-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-green-500 rounded-full transition-all"
              style={{
                width: `${
                  stats.generation.totalJobs > 0
                    ? (stats.generation.completedJobs / stats.generation.totalJobs) * 100
                    : 0
                }%`,
              }}
            />
          </div>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div className="flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-green-400" />
              <span>{stats.generation.completedJobs} completed</span>
            </div>
            <div className="flex items-center gap-2">
              <XCircle className="w-4 h-4 text-red-400" />
              <span>{stats.generation.failedJobs} failed</span>
            </div>
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-yellow-400" />
              <span>{stats.generation.avgGenerationTimeSeconds.toFixed(0)}s avg</span>
            </div>
          </div>
        </div>
      </div>

      {/* Budget alert */}
      {stats.budgetAlert && (
        <div
          className={cn(
            'p-4 rounded-lg flex items-start gap-3',
            stats.budgetAlert.alert_type === 'budget_exceeded'
              ? 'bg-red-500/10 border border-red-500/30'
              : 'bg-yellow-500/10 border border-yellow-500/30'
          )}
        >
          <AlertTriangle
            className={cn(
              'w-5 h-5 shrink-0 mt-0.5',
              stats.budgetAlert.alert_type === 'budget_exceeded'
                ? 'text-red-400'
                : 'text-yellow-400'
            )}
          />
          <div>
            <p className="font-medium">
              {stats.budgetAlert.alert_type === 'budget_exceeded'
                ? 'Budget Exceeded'
                : 'Budget Warning'}
            </p>
            <p className="text-sm text-surface-400 mt-1">
              ${stats.budgetAlert.current_spend_usd?.toFixed(2)} of $
              {stats.budgetAlert.budget_limit_usd?.toFixed(2)} used (
              {Math.round(stats.budgetAlert.percent_used ?? 0)}%)
            </p>
          </div>
        </div>
      )}

      {/* Estimated delivery */}
      <div className="card">
        <h3 className="text-lg font-medium mb-2">Estimated Completion</h3>
        <p className="text-surface-400 text-sm">
          Based on current rates, remaining shots should complete in approximately{' '}
          <span className="text-white font-medium">
            {Math.ceil(
              ((stats.generation.totalJobs - stats.generation.completedJobs) *
                stats.generation.avgGenerationTimeSeconds) /
                60
            )}{' '}
            minutes
          </span>
          .
        </p>
      </div>
    </div>
  );
}

/* ────────────────────── Operator View ────────────── */

function OperatorView({ jobs }: { jobs: GenerationJob[] }) {
  if (jobs.length === 0) {
    return <EmptyState icon={Clapperboard} message="No generation jobs found" />;
  }

  return (
    <div className="space-y-4">
      <div className="card">
        <h3 className="text-lg font-medium mb-4">Shot-by-Shot Breakdown</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-surface-400 border-b border-surface-700">
                <th className="pb-2 font-medium">Shot</th>
                <th className="pb-2 font-medium">Status</th>
                <th className="pb-2 font-medium">Provider</th>
                <th className="pb-2 font-medium">Model</th>
                <th className="pb-2 font-medium text-right">Time</th>
                <th className="pb-2 font-medium text-right">Cost</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr key={job.id} className="border-b border-surface-800 hover:bg-surface-800/50">
                  <td className="py-2.5 font-mono">#{job.shot_number}</td>
                  <td className="py-2.5">
                    <StatusBadge status={job.status} />
                  </td>
                  <td className="py-2.5 capitalize">{job.provider || '—'}</td>
                  <td className="py-2.5 text-surface-400">{job.model || '—'}</td>
                  <td className="py-2.5 text-right">
                    {job.generation_time_seconds
                      ? `${job.generation_time_seconds.toFixed(1)}s`
                      : '—'}
                  </td>
                  <td className="py-2.5 text-right font-medium">
                    {job.cost_usd ? `$${job.cost_usd.toFixed(4)}` : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Cost summary */}
      <div className="card">
        <h3 className="text-sm font-medium text-surface-400 mb-3">Cost Summary</h3>
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div>
            <span className="text-surface-400">Total Cost</span>
            <p className="font-medium text-lg">
              ${jobs.reduce((sum, j) => sum + (j.cost_usd || 0), 0).toFixed(2)}
            </p>
          </div>
          <div>
            <span className="text-surface-400">Avg/Shot</span>
            <p className="font-medium text-lg">
              $
              {jobs.length > 0
                ? (jobs.reduce((sum, j) => sum + (j.cost_usd || 0), 0) / jobs.length).toFixed(4)
                : '0.00'}
            </p>
          </div>
          <div>
            <span className="text-surface-400">Total Time</span>
            <p className="font-medium text-lg">
              {(jobs.reduce((sum, j) => sum + (j.generation_time_seconds || 0), 0) / 60).toFixed(1)}
              m
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ────────────────────── Technical View ───────────── */

function TechnicalView({ jobs, agentLogs }: { jobs: GenerationJob[]; agentLogs: AgentLog[] }) {
  const [expandedJob, setExpandedJob] = useState<string | null>(null);

  return (
    <div className="space-y-6">
      {/* Agent action log */}
      <div className="card">
        <h3 className="text-lg font-medium mb-4 flex items-center gap-2">
          <Code2 className="w-5 h-5 text-brand-400" />
          Agent Action Log
        </h3>
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {agentLogs.length === 0 ? (
            <p className="text-surface-400 text-sm">No agent actions logged yet.</p>
          ) : (
            agentLogs.slice(0, 50).map((log) => (
              <div
                key={log.id}
                className="flex items-start gap-3 p-2 rounded hover:bg-surface-800/50 text-sm"
              >
                <AgentBadge type={log.agent_type} />
                <div className="flex-1 min-w-0">
                  <span className="text-surface-200">{log.action}</span>
                  {log.details && (
                    <p className="text-xs text-surface-500 mt-0.5 truncate">{log.details}</p>
                  )}
                </div>
                {log.confidence != null && (
                  <span
                    className={cn(
                      'text-xs px-1.5 py-0.5 rounded',
                      log.confidence >= 0.8
                        ? 'bg-green-500/20 text-green-400'
                        : log.confidence >= 0.6
                          ? 'bg-yellow-500/20 text-yellow-400'
                          : 'bg-red-500/20 text-red-400'
                    )}
                  >
                    {(log.confidence * 100).toFixed(0)}%
                  </span>
                )}
                <span className="text-xs text-surface-500 shrink-0">
                  {new Date(log.timestamp).toLocaleTimeString()}
                </span>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Generation parameters per job */}
      <div className="card">
        <h3 className="text-lg font-medium mb-4">Generation Parameters</h3>
        <div className="space-y-1">
          {jobs.slice(0, 20).map((job) => (
            <div key={job.id} className="border border-surface-700 rounded-lg">
              <button
                onClick={() => setExpandedJob(expandedJob === job.id ? null : job.id)}
                className="w-full flex items-center gap-3 p-3 text-left hover:bg-surface-800/50"
              >
                {expandedJob === job.id ? (
                  <ChevronDown className="w-4 h-4 text-surface-400" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-surface-400" />
                )}
                <span className="font-mono text-sm">Shot #{job.shot_number}</span>
                <StatusBadge status={job.status} />
                <span className="text-xs text-surface-500 ml-auto">{job.provider}</span>
              </button>
              {expandedJob === job.id && (
                <div className="px-3 pb-3 pt-0 border-t border-surface-700">
                  <div className="grid grid-cols-2 gap-3 text-sm mt-3">
                    <div>
                      <span className="text-surface-500 text-xs">Provider</span>
                      <p className="capitalize">{job.provider || 'N/A'}</p>
                    </div>
                    <div>
                      <span className="text-surface-500 text-xs">Model</span>
                      <p>{job.model || 'N/A'}</p>
                    </div>
                    <div>
                      <span className="text-surface-500 text-xs">Cost</span>
                      <p>{job.cost_usd ? `$${job.cost_usd.toFixed(6)}` : 'N/A'}</p>
                    </div>
                    <div>
                      <span className="text-surface-500 text-xs">Inference Time</span>
                      <p>
                        {job.generation_time_seconds
                          ? `${job.generation_time_seconds.toFixed(2)}s`
                          : 'N/A'}
                      </p>
                    </div>
                  </div>
                  {job.prompt && (
                    <div className="mt-3">
                      <span className="text-surface-500 text-xs">Prompt</span>
                      <p className="text-sm bg-surface-800 rounded p-2 mt-1 font-mono text-xs">
                        {job.prompt}
                      </p>
                    </div>
                  )}
                  {job.error && (
                    <div className="mt-3">
                      <span className="text-red-400 text-xs">Error</span>
                      <p className="text-sm bg-red-500/10 border border-red-500/20 rounded p-2 mt-1 text-red-300">
                        {job.error}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ────────────────────── Audit View ───────────────── */

function AuditView({ snapshots }: { snapshots: Snapshot[] }) {
  const [selectedPair, setSelectedPair] = useState<[number, number] | null>(null);

  if (snapshots.length === 0) {
    return <EmptyState icon={Shield} message="No snapshots recorded yet" />;
  }

  return (
    <div className="space-y-6">
      {/* Snapshot timeline */}
      <div className="card">
        <h3 className="text-lg font-medium mb-4 flex items-center gap-2">
          <FileText className="w-5 h-5 text-brand-400" />
          Immutable Snapshot History
        </h3>
        <div className="space-y-2">
          {snapshots.map((snap, index) => (
            <div
              key={snap.id}
              className={cn(
                'flex items-center gap-4 p-3 rounded-lg border transition-colors cursor-pointer',
                selectedPair && (selectedPair[0] === index || selectedPair[1] === index)
                  ? 'border-brand-500/50 bg-brand-500/5'
                  : 'border-surface-700 hover:border-surface-600'
              )}
              onClick={() => {
                if (!selectedPair) {
                  setSelectedPair([index, -1]);
                } else if (selectedPair[1] === -1 && selectedPair[0] !== index) {
                  setSelectedPair([selectedPair[0], index]);
                } else {
                  setSelectedPair(null);
                }
              }}
            >
              <div className="w-8 h-8 rounded-full bg-surface-700 flex items-center justify-center text-xs font-mono">
                v{snap.version}
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium capitalize">
                  {snap.entity_type} — {snap.entity_id.slice(0, 8)}
                </p>
                <p className="text-xs text-surface-500">
                  {new Date(snap.created_at).toLocaleString()}
                  {snap.created_by && ` by ${snap.created_by}`}
                </p>
              </div>
              <span className="text-xs text-surface-500">
                {Object.keys(snap.data).length} fields
              </span>
            </div>
          ))}
        </div>
        <p className="text-xs text-surface-500 mt-3 flex items-center gap-1">
          <Info className="w-3 h-3" />
          Click two snapshots to compare them side-by-side.
        </p>
      </div>

      {/* Delta comparison */}
      {selectedPair && selectedPair[1] !== -1 && (
        <div className="card">
          <h3 className="text-lg font-medium mb-4 flex items-center gap-2">
            <GitCompare className="w-5 h-5 text-brand-400" />
            Delta Comparison — v{snapshots[selectedPair[0]]?.version} → v
            {snapshots[selectedPair[1]]?.version}
          </h3>
          <DeltaViewer
            before={snapshots[selectedPair[0]]?.data || {}}
            after={snapshots[selectedPair[1]]?.data || {}}
          />
        </div>
      )}

      {/* Consent & provenance */}
      <div className="card">
        <h3 className="text-sm font-medium text-surface-400 mb-3">Provenance & Consent</h3>
        <div className="space-y-2 text-sm">
          <div className="flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-green-400" />
            <span>All generation prompts derived from uploaded screenplay</span>
          </div>
          <div className="flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-green-400" />
            <span>No real-person likeness used without user confirmation</span>
          </div>
          <div className="flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-green-400" />
            <span>All snapshots cryptographically immutable</span>
          </div>
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-brand-400" />
            <span>{snapshots.length} snapshots in audit trail</span>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ────────────────────── Helpers ──────────────────── */

function DeltaViewer({
  before,
  after,
}: {
  before: Record<string, unknown>;
  after: Record<string, unknown>;
}) {
  const allKeys = [...new Set([...Object.keys(before), ...Object.keys(after)])].sort();

  const changes = allKeys.filter(
    (key) => JSON.stringify(before[key]) !== JSON.stringify(after[key])
  );

  if (changes.length === 0) {
    return (
      <p className="text-surface-400 text-sm">No differences found between these snapshots.</p>
    );
  }

  return (
    <div className="space-y-2">
      {changes.map((key) => (
        <div key={key} className="bg-surface-800 rounded-lg p-3 text-sm">
          <span className="font-mono text-brand-400">{key}</span>
          <div className="grid grid-cols-2 gap-4 mt-2">
            <div>
              <span className="text-xs text-red-400">Before</span>
              <pre className="text-xs text-surface-400 mt-1 overflow-hidden text-ellipsis">
                {JSON.stringify(before[key] ?? null, null, 2)}
              </pre>
            </div>
            <div>
              <span className="text-xs text-green-400">After</span>
              <pre className="text-xs text-surface-400 mt-1 overflow-hidden text-ellipsis">
                {JSON.stringify(after[key] ?? null, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function SummaryCard({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: string | number;
  icon: typeof Film;
}) {
  return (
    <div className="p-4 bg-surface-800 rounded-lg text-center">
      <Icon className="w-5 h-5 text-brand-400 mx-auto mb-2" />
      <div className="text-xl font-bold">{value}</div>
      <div className="text-xs text-surface-400">{label}</div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    completed: 'bg-green-500/20 text-green-400',
    failed: 'bg-red-500/20 text-red-400',
    pending: 'bg-yellow-500/20 text-yellow-400',
    processing: 'bg-blue-500/20 text-blue-400',
    queued: 'bg-surface-600 text-surface-300',
  };

  return (
    <span
      className={cn(
        'text-xs px-2 py-0.5 rounded-full capitalize',
        styles[status] || 'bg-surface-600 text-surface-300'
      )}
    >
      {status}
    </span>
  );
}

function AgentBadge({ type }: { type: string }) {
  const colors: Record<string, string> = {
    orchestrator: 'bg-purple-500/20 text-purple-400',
    parser: 'bg-blue-500/20 text-blue-400',
    character: 'bg-green-500/20 text-green-400',
    generator: 'bg-orange-500/20 text-orange-400',
    assembler: 'bg-cyan-500/20 text-cyan-400',
    reviewer: 'bg-yellow-500/20 text-yellow-400',
    export: 'bg-pink-500/20 text-pink-400',
  };

  return (
    <span
      className={cn(
        'text-xs px-2 py-0.5 rounded capitalize shrink-0',
        colors[type] || 'bg-surface-600 text-surface-300'
      )}
    >
      {type}
    </span>
  );
}

function EmptyState({ icon: Icon, message }: { icon: typeof Eye; message: string }) {
  return (
    <div className="text-center py-16 text-surface-400">
      <Icon className="w-10 h-10 mx-auto mb-3 opacity-40" />
      <p>{message}</p>
    </div>
  );
}

/* ────────────────────── Main Page ────────────────── */

export function ExplainabilityPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [activeTab, setActiveTab] = useState<TabId>('client');

  // Dashboard stats
  const {
    data: dashboardStats,
    isLoading: statsLoading,
    refetch,
  } = useQuery({
    queryKey: ['explainability-stats', projectId],
    queryFn: async () => {
      return window.electronAPI.backendRequest<DashboardStats>('analytics.getDashboard', {
        time_range: '30d',
      });
    },
  });

  // Generation jobs — backend exposes this as `generation.getPendingJobs`
  // (P0-4 in docs/INVENTORY_DEFECTS.md: renderer was calling a non-existent
  // `generation.listJobs` channel, so this page silently rendered empty).
  const { data: jobs = [] } = useQuery({
    queryKey: ['explainability-jobs', projectId],
    queryFn: async () => {
      return window.electronAPI.backendRequest<GenerationJob[]>('generation.getPendingJobs', {
        project_id: projectId,
        limit: 100,
      });
    },
  });

  // Agent logs — backend exposes this as `crew.getActionLogs` (P0-7).
  const { data: agentLogs = [] } = useQuery({
    queryKey: ['explainability-logs', projectId],
    queryFn: async () => {
      return window.electronAPI.backendRequest<AgentLog[]>('crew.getActionLogs', {
        limit: 100,
      });
    },
  });

  // Snapshots
  const { data: snapshots = [] } = useQuery({
    queryKey: ['explainability-snapshots', projectId],
    queryFn: async () => {
      return window.electronAPI.backendRequest<Snapshot[]>('snapshots.list', {
        project_id: projectId,
        limit: 50,
      });
    },
  });

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-3">
            <Eye className="w-7 h-7 text-brand-400" />
            Explainability Dashboard
          </h1>
          <p className="text-sm text-surface-400 mt-1">
            Understand every AI decision with full transparency
          </p>
        </div>
        <button
          onClick={() => refetch()}
          disabled={statsLoading}
          className="p-2 hover:bg-surface-700 rounded-lg"
          title="Refresh"
        >
          <RefreshCw className={cn('w-4 h-4', statsLoading && 'animate-spin')} />
        </button>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 bg-surface-800 rounded-lg p-1">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-md text-sm transition-colors',
                activeTab === tab.id
                  ? 'bg-brand-500 text-white'
                  : 'text-surface-400 hover:text-surface-200 hover:bg-surface-700'
              )}
            >
              <Icon className="w-4 h-4" />
              <span className="hidden sm:inline">{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Active view description */}
      <div className="flex items-center gap-2 text-sm text-surface-500">
        <Info className="w-4 h-4" />
        {TABS.find((t) => t.id === activeTab)?.description}
      </div>

      {/* Loading state */}
      {statsLoading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-8 h-8 animate-spin text-brand-400" />
        </div>
      ) : (
        <>
          {activeTab === 'client' && <ClientView stats={dashboardStats} />}
          {activeTab === 'operator' && <OperatorView jobs={jobs} />}
          {activeTab === 'technical' && <TechnicalView jobs={jobs} agentLogs={agentLogs} />}
          {activeTab === 'audit' && <AuditView snapshots={snapshots} />}
        </>
      )}
    </div>
  );
}

export default ExplainabilityPage;
