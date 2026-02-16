/**
 * Crew state store using Zustand.
 *
 * Manages agentic crew pipeline execution, agent status,
 * action logs, and HITL approval queue state.
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';

// ---- Types ----

export interface AgentInfo {
    type: string;
    name: string;
    capabilities: string[];
    requires_approval: string[];
}

export interface ActionLog {
    id: string;
    agent_type: string;
    agent_name: string;
    action_name: string;
    status: 'pending' | 'running' | 'completed' | 'failed' | 'escalated' | 'cancelled';
    confidence: number;
    cost_usd: number;
    started_at: string;
    completed_at: string | null;
}

export interface PipelineStatus {
    project_id: string;
    status: string;
    current_phase: string;
    progress_percent: number;
    total_cost_usd: number;
    errors: string[];
}

export interface ApprovalItem {
    id: string;
    agent_type: string;
    action_type: string;
    description: string;
    request_data: Record<string, unknown>;
    status: 'pending' | 'approved' | 'rejected';
    created_at: string;
    resolved_at: string | null;
}

// ---- Agent color mapping for UI ----
export const AGENT_COLORS: Record<string, string> = {
    orchestrator: '#6366f1', // indigo
    parser: '#3b82f6',      // blue
    character: '#22c55e',   // green
    generator: '#a855f7',   // purple
    assembler: '#f97316',   // orange
    reviewer: '#ef4444',    // red
    export: '#eab308',      // yellow
};

export const AGENT_ICONS: Record<string, string> = {
    orchestrator: '🎬',
    parser: '📝',
    character: '👤',
    generator: '🎥',
    assembler: '🔧',
    reviewer: '🔍',
    export: '📦',
};

// ---- Store ----

interface CrewStoreState {
    // Agents
    agents: AgentInfo[];
    isLoadingAgents: boolean;

    // Pipeline
    pipelineStatus: PipelineStatus | null;
    isPipelineRunning: boolean;

    // Action logs
    actionLogs: ActionLog[];
    isLoadingLogs: boolean;
    logFilter: string | null; // filter by agent_type

    // Approvals (HITL)
    approvals: ApprovalItem[];
    pendingApprovalCount: number;
    isLoadingApprovals: boolean;

    // Total cost
    totalCost: number;

    // Actions
    fetchAgents: () => Promise<void>;
    fetchActionLogs: (agentType?: string, limit?: number) => Promise<void>;
    fetchPipelineStatus: (projectId: string) => Promise<void>;
    fetchTotalCost: () => Promise<void>;

    startPipeline: (projectId: string, screenplayPath?: string, dryRun?: boolean) => Promise<boolean>;
    pausePipeline: (projectId: string) => Promise<boolean>;
    resumePipeline: (projectId: string) => Promise<boolean>;
    cancelPipeline: (projectId: string) => Promise<boolean>;

    setLogFilter: (agentType: string | null) => void;

    // HITL
    approveItem: (id: string) => Promise<boolean>;
    rejectItem: (id: string, reason?: string) => Promise<boolean>;

    // Live feed (for WebSocket push)
    addActionLog: (log: ActionLog) => void;
    updatePipelineStatus: (status: PipelineStatus) => void;
    addApproval: (item: ApprovalItem) => void;
}

const API_BASE = '/api/crew';

async function crewFetch<T>(path: string, opts?: RequestInit): Promise<T> {
    const res = await fetch(`${API_BASE}${path}`, {
        headers: { 'Content-Type': 'application/json' },
        ...opts,
    });
    if (!res.ok) throw new Error(`Crew API error: ${res.status}`);
    return res.json();
}

export const useCrewStore = create<CrewStoreState>()(
    devtools(
        immer((set, get) => ({
            // Initial state
            agents: [],
            isLoadingAgents: false,
            pipelineStatus: null,
            isPipelineRunning: false,
            actionLogs: [],
            isLoadingLogs: false,
            logFilter: null,
            approvals: [],
            pendingApprovalCount: 0,
            isLoadingApprovals: false,
            totalCost: 0,

            // ---- Agent Fetching ----
            fetchAgents: async () => {
                set((s) => { s.isLoadingAgents = true; });
                try {
                    const agents = await crewFetch<AgentInfo[]>('/agents');
                    set((s) => { s.agents = agents; s.isLoadingAgents = false; });
                } catch (e) {
                    console.error('Failed to fetch agents:', e);
                    set((s) => { s.isLoadingAgents = false; });
                }
            },

            // ---- Action Logs ----
            fetchActionLogs: async (agentType, limit = 50) => {
                set((s) => { s.isLoadingLogs = true; });
                try {
                    const params = new URLSearchParams();
                    if (agentType) params.set('agent_type', agentType);
                    params.set('limit', String(limit));
                    const logs = await crewFetch<ActionLog[]>(`/logs?${params}`);
                    set((s) => { s.actionLogs = logs; s.isLoadingLogs = false; });
                } catch (e) {
                    console.error('Failed to fetch action logs:', e);
                    set((s) => { s.isLoadingLogs = false; });
                }
            },

            setLogFilter: (agentType) => {
                set((s) => { s.logFilter = agentType; });
                get().fetchActionLogs(agentType ?? undefined);
            },

            // ---- Pipeline ----
            fetchPipelineStatus: async (projectId) => {
                try {
                    const status = await crewFetch<PipelineStatus>(`/pipeline/status/${projectId}`);
                    set((s) => {
                        s.pipelineStatus = status;
                        s.isPipelineRunning = !['completed', 'failed', 'idle'].includes(status.status);
                    });
                } catch (e) {
                    console.error('Failed to fetch pipeline status:', e);
                }
            },

            startPipeline: async (projectId, screenplayPath, dryRun = false) => {
                try {
                    const result = await crewFetch<{ success: boolean }>('/pipeline/start', {
                        method: 'POST',
                        body: JSON.stringify({
                            project_id: projectId,
                            screenplay_path: screenplayPath ?? null,
                            dry_run: dryRun,
                        }),
                    });
                    if (result.success) {
                        set((s) => { s.isPipelineRunning = true; });
                    }
                    return result.success;
                } catch (e) {
                    console.error('Failed to start pipeline:', e);
                    return false;
                }
            },

            pausePipeline: async (projectId) => {
                try {
                    await crewFetch(`/pipeline/pause/${projectId}`, { method: 'POST' });
                    set((s) => {
                        if (s.pipelineStatus) s.pipelineStatus.status = 'paused';
                    });
                    return true;
                } catch (e) {
                    console.error('Failed to pause pipeline:', e);
                    return false;
                }
            },

            resumePipeline: async (projectId) => {
                try {
                    await crewFetch(`/pipeline/resume/${projectId}`, { method: 'POST' });
                    set((s) => {
                        if (s.pipelineStatus) s.pipelineStatus.status = 'running';
                        s.isPipelineRunning = true;
                    });
                    return true;
                } catch (e) {
                    console.error('Failed to resume pipeline:', e);
                    return false;
                }
            },

            cancelPipeline: async (projectId) => {
                try {
                    await crewFetch(`/pipeline/cancel/${projectId}`, { method: 'POST' });
                    set((s) => {
                        if (s.pipelineStatus) s.pipelineStatus.status = 'cancelled';
                        s.isPipelineRunning = false;
                    });
                    return true;
                } catch (e) {
                    console.error('Failed to cancel pipeline:', e);
                    return false;
                }
            },

            // ---- Cost ----
            fetchTotalCost: async () => {
                try {
                    const { total_cost_usd } = await crewFetch<{ total_cost_usd: number }>('/logs/cost');
                    set((s) => { s.totalCost = total_cost_usd; });
                } catch (e) {
                    console.error('Failed to fetch total cost:', e);
                }
            },

            // ---- Live feed (WebSocket push) ----
            addActionLog: (log) => {
                set((s) => {
                    s.actionLogs.unshift(log);
                    if (s.actionLogs.length > 200) s.actionLogs.pop();
                });
            },

            updatePipelineStatus: (status) => {
                set((s) => {
                    s.pipelineStatus = status;
                    s.isPipelineRunning = !['completed', 'failed', 'idle'].includes(status.status);
                });
            },

            // ---- HITL Approvals ----
            addApproval: (item) => {
                set((s) => {
                    s.approvals.unshift(item);
                    s.pendingApprovalCount = s.approvals.filter((a) => a.status === 'pending').length;
                });
            },

            approveItem: async (id) => {
                try {
                    // POST to approve endpoint (to be wired)
                    set((s) => {
                        const item = s.approvals.find((a) => a.id === id);
                        if (item) {
                            item.status = 'approved';
                            item.resolved_at = new Date().toISOString();
                        }
                        s.pendingApprovalCount = s.approvals.filter((a) => a.status === 'pending').length;
                    });
                    return true;
                } catch (e) {
                    console.error('Failed to approve:', e);
                    return false;
                }
            },

            rejectItem: async (id, _reason) => {
                try {
                    set((s) => {
                        const item = s.approvals.find((a) => a.id === id);
                        if (item) {
                            item.status = 'rejected';
                            item.resolved_at = new Date().toISOString();
                        }
                        s.pendingApprovalCount = s.approvals.filter((a) => a.status === 'pending').length;
                    });
                    return true;
                } catch (e) {
                    console.error('Failed to reject:', e);
                    return false;
                }
            },
        })),
        { name: 'CrewStore' }
    )
);

/**
 * Hook to get the count of pending approvals (for badge display).
 */
export function usePendingApprovalCount(): number {
    return useCrewStore((s) => s.pendingApprovalCount);
}

/**
 * Hook to check if the pipeline is currently running.
 */
export function useIsPipelineRunning(): boolean {
    return useCrewStore((s) => s.isPipelineRunning);
}
