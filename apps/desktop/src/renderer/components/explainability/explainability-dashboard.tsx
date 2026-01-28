/**
 * Explainability Dashboard - 4-Layer View System
 * 
 * Provides four different views of pipeline execution:
 * 1. Client View - Plain language summary for clients
 * 2. Operator View - Shot breakdown and status
 * 3. Technical View - Logs, metrics, and parameters
 * 4. Audit View - Immutable snapshots and change history
 */

import React, { useState, useEffect, useCallback } from 'react';

// Types
type ViewType = 'client' | 'operator' | 'technical' | 'audit';

interface ActionLog {
    id: string;
    agent_type: string;
    agent_name: string;
    action_name: string;
    status: string;
    confidence: number;
    cost_usd: number;
    started_at: string;
    completed_at?: string;
}

interface Snapshot {
    id: string;
    label: string;
    created_at: string;
    scene_count: number;
    character_count: number;
    shot_count: number;
}

interface DeltaReport {
    from_label: string;
    to_label: string;
    total_changes: number;
    additions: number;
    removals: number;
    modifications: number;
    changes: Array<{
        entity_type: string;
        entity_id: string;
        change_type: string;
        field_name?: string;
    }>;
}

interface ExplainabilityDashboardProps {
    projectId: string;
    pipelineStatus?: {
        status: string;
        current_phase: string;
        progress_percent: number;
        total_cost_usd: number;
    };
}

// View tabs configuration
const VIEW_TABS: Array<{ id: ViewType; label: string; icon: string }> = [
    { id: 'client', label: 'Client', icon: '👤' },
    { id: 'operator', label: 'Operator', icon: '🎬' },
    { id: 'technical', label: 'Technical', icon: '⚙️' },
    { id: 'audit', label: 'Audit', icon: '📋' },
];

// Phase descriptions for client view
const PHASE_DESCRIPTIONS: Record<string, string> = {
    parse: 'Reading and understanding your screenplay',
    characters: 'Setting up the look and voice of each character',
    shots: 'Planning how each scene will be filmed',
    generate: 'Creating the video clips',
    review: 'Checking quality of generated content',
    assemble: 'Putting all the clips together',
    export: 'Finalizing your movie',
};

export const ExplainabilityDashboard: React.FC<ExplainabilityDashboardProps> = ({
    projectId,
    pipelineStatus,
}) => {
    const [activeView, setActiveView] = useState<ViewType>('client');
    const [actionLogs, setActionLogs] = useState<ActionLog[]>([]);
    const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
    const [deltaReport, setDeltaReport] = useState<DeltaReport | null>(null);
    const [selectedSnapshots, setSelectedSnapshots] = useState<[string, string]>(['', '']);
    const [loading, setLoading] = useState(false);

    // Fetch action logs for technical view
    const fetchLogs = useCallback(async () => {
        try {
            const response = await fetch('/api/v1/crew/logs?limit=50');
            if (response.ok) {
                const data = await response.json();
                setActionLogs(data);
            }
        } catch (error) {
            console.error('Failed to fetch logs:', error);
        }
    }, []);

    // Fetch snapshots for audit view
    const fetchSnapshots = useCallback(async () => {
        try {
            const response = await fetch(`/api/v1/snapshots/${projectId}`);
            if (response.ok) {
                const data = await response.json();
                setSnapshots(data);
            }
        } catch (error) {
            console.error('Failed to fetch snapshots:', error);
        }
    }, [projectId]);

    // Compare snapshots
    const compareSnapshots = useCallback(async () => {
        if (!selectedSnapshots[0] || !selectedSnapshots[1]) return;

        setLoading(true);
        try {
            const response = await fetch(
                `/api/v1/snapshots/${projectId}/compare?from=${selectedSnapshots[0]}&to=${selectedSnapshots[1]}`
            );
            if (response.ok) {
                const data = await response.json();
                setDeltaReport(data);
            }
        } catch (error) {
            console.error('Failed to compare snapshots:', error);
        } finally {
            setLoading(false);
        }
    }, [projectId, selectedSnapshots]);

    useEffect(() => {
        if (activeView === 'technical') {
            fetchLogs();
        } else if (activeView === 'audit') {
            fetchSnapshots();
        }
    }, [activeView, fetchLogs, fetchSnapshots]);

    return (
        <div className="explainability-dashboard">
            {/* View Switcher */}
            <div className="view-switcher">
                {VIEW_TABS.map((tab) => (
                    <button
                        key={tab.id}
                        className={`view-tab ${activeView === tab.id ? 'active' : ''}`}
                        onClick={() => setActiveView(tab.id)}
                    >
                        <span className="tab-icon">{tab.icon}</span>
                        <span className="tab-label">{tab.label}</span>
                    </button>
                ))}
            </div>

            {/* View Content */}
            <div className="view-content">
                {activeView === 'client' && (
                    <ClientView pipelineStatus={pipelineStatus} />
                )}
                {activeView === 'operator' && (
                    <OperatorView pipelineStatus={pipelineStatus} />
                )}
                {activeView === 'technical' && (
                    <TechnicalView logs={actionLogs} onRefresh={fetchLogs} />
                )}
                {activeView === 'audit' && (
                    <AuditView
                        snapshots={snapshots}
                        deltaReport={deltaReport}
                        selectedSnapshots={selectedSnapshots}
                        onSelectSnapshots={setSelectedSnapshots}
                        onCompare={compareSnapshots}
                        loading={loading}
                    />
                )}
            </div>

            <style>{`
        .explainability-dashboard {
          background: var(--bg-secondary, #1a1a2e);
          border-radius: 12px;
          overflow: hidden;
        }

        .view-switcher {
          display: flex;
          border-bottom: 1px solid var(--border-color, #333);
          background: var(--bg-primary, #0f0f1a);
        }

        .view-tab {
          flex: 1;
          padding: 12px 16px;
          background: transparent;
          border: none;
          color: var(--text-secondary, #888);
          cursor: pointer;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 4px;
          transition: all 0.2s;
        }

        .view-tab:hover {
          background: rgba(255, 255, 255, 0.05);
        }

        .view-tab.active {
          color: var(--accent-color, #6366f1);
          background: rgba(99, 102, 241, 0.1);
          border-bottom: 2px solid var(--accent-color, #6366f1);
        }

        .tab-icon {
          font-size: 20px;
        }

        .tab-label {
          font-size: 12px;
          font-weight: 500;
        }

        .view-content {
          padding: 20px;
          min-height: 400px;
        }

        .view-section {
          margin-bottom: 24px;
        }

        .view-section h3 {
          font-size: 14px;
          color: var(--text-secondary, #888);
          margin-bottom: 12px;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .status-card {
          background: var(--bg-tertiary, #252540);
          border-radius: 8px;
          padding: 16px;
        }

        .plain-text {
          font-size: 16px;
          line-height: 1.6;
          color: var(--text-primary, #fff);
        }

        .progress-bar {
          height: 8px;
          background: var(--bg-tertiary, #252540);
          border-radius: 4px;
          overflow: hidden;
          margin-top: 12px;
        }

        .progress-fill {
          height: 100%;
          background: linear-gradient(90deg, #6366f1, #8b5cf6);
          transition: width 0.3s ease;
        }

        .log-table {
          width: 100%;
          border-collapse: collapse;
        }

        .log-table th,
        .log-table td {
          padding: 8px 12px;
          text-align: left;
          border-bottom: 1px solid var(--border-color, #333);
          font-size: 13px;
        }

        .log-table th {
          color: var(--text-secondary, #888);
          font-weight: 500;
        }

        .status-badge {
          padding: 2px 8px;
          border-radius: 4px;
          font-size: 11px;
          font-weight: 500;
        }

        .status-badge.completed {
          background: rgba(34, 197, 94, 0.2);
          color: #22c55e;
        }

        .status-badge.running {
          background: rgba(59, 130, 246, 0.2);
          color: #3b82f6;
        }

        .status-badge.failed {
          background: rgba(239, 68, 68, 0.2);
          color: #ef4444;
        }

        .snapshot-list {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .snapshot-item {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px;
          background: var(--bg-tertiary, #252540);
          border-radius: 8px;
        }

        .delta-summary {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 12px;
          margin-bottom: 16px;
        }

        .delta-stat {
          text-align: center;
          padding: 12px;
          background: var(--bg-tertiary, #252540);
          border-radius: 8px;
        }

        .delta-stat-value {
          font-size: 24px;
          font-weight: 600;
        }

        .delta-stat-label {
          font-size: 12px;
          color: var(--text-secondary, #888);
        }

        .delta-stat.additions .delta-stat-value { color: #22c55e; }
        .delta-stat.removals .delta-stat-value { color: #ef4444; }
        .delta-stat.modifications .delta-stat-value { color: #f59e0b; }
      `}</style>
        </div>
    );
};

// Client View - Plain language summary
const ClientView: React.FC<{ pipelineStatus?: ExplainabilityDashboardProps['pipelineStatus'] }> = ({
    pipelineStatus,
}) => {
    const currentPhase = pipelineStatus?.current_phase || 'idle';
    const progress = pipelineStatus?.progress_percent || 0;
    const status = pipelineStatus?.status || 'idle';

    const getStatusMessage = () => {
        if (status === 'idle') return "Your movie project is ready to start.";
        if (status === 'completed') return "🎉 Your movie is complete and ready for download!";
        if (status === 'failed') return "❌ Something went wrong. Our team will help resolve this.";
        if (status === 'paused') return "⏸️ Production is paused. Resume when you're ready.";

        const phaseDesc = PHASE_DESCRIPTIONS[currentPhase] || 'Working on your movie';
        return `${phaseDesc}... (${Math.round(progress)}% complete)`;
    };

    return (
        <div className="client-view">
            <div className="view-section">
                <h3>Current Status</h3>
                <div className="status-card">
                    <p className="plain-text">{getStatusMessage()}</p>
                    {status === 'running' && (
                        <div className="progress-bar">
                            <div className="progress-fill" style={{ width: `${progress}%` }} />
                        </div>
                    )}
                </div>
            </div>

            <div className="view-section">
                <h3>What's Happening</h3>
                <div className="status-card">
                    <ul className="plain-text" style={{ marginLeft: 20 }}>
                        <li>✅ Your screenplay has been analyzed</li>
                        <li>✅ Characters are set up with their looks and voices</li>
                        {progress >= 30 && <li>✅ Scenes are planned and ready</li>}
                        {progress >= 50 && <li>🎬 Video clips are being generated</li>}
                        {progress >= 80 && <li>🔍 Quality is being reviewed</li>}
                        {progress >= 95 && <li>📦 Final movie is being prepared</li>}
                    </ul>
                </div>
            </div>

            <div className="view-section">
                <h3>Estimated Cost</h3>
                <div className="status-card">
                    <p className="plain-text">
                        Current spend: <strong>${(pipelineStatus?.total_cost_usd || 0).toFixed(2)}</strong>
                    </p>
                </div>
            </div>
        </div>
    );
};

// Operator View - Shot breakdown
const OperatorView: React.FC<{ pipelineStatus?: ExplainabilityDashboardProps['pipelineStatus'] }> = ({
    pipelineStatus,
}) => {
    // In a real implementation, this would show shot-by-shot status
    const phases = ['parse', 'characters', 'shots', 'generate', 'review', 'assemble', 'export'];
    const currentPhaseIndex = phases.indexOf(pipelineStatus?.current_phase || 'parse');

    return (
        <div className="operator-view">
            <div className="view-section">
                <h3>Pipeline Phases</h3>
                <div className="phase-timeline">
                    {phases.map((phase, index) => (
                        <div
                            key={phase}
                            className={`phase-item ${index < currentPhaseIndex ? 'complete' : ''} ${index === currentPhaseIndex ? 'active' : ''
                                }`}
                        >
                            <div className="phase-marker">
                                {index < currentPhaseIndex ? '✓' : index === currentPhaseIndex ? '●' : '○'}
                            </div>
                            <div className="phase-label">{phase}</div>
                        </div>
                    ))}
                </div>
            </div>

            <div className="view-section">
                <h3>Current Activity</h3>
                <div className="status-card">
                    <p className="plain-text">
                        Phase: <strong>{pipelineStatus?.current_phase || 'idle'}</strong>
                    </p>
                    <p className="plain-text">
                        Status: <strong>{pipelineStatus?.status || 'idle'}</strong>
                    </p>
                </div>
            </div>

            <style>{`
        .phase-timeline {
          display: flex;
          justify-content: space-between;
          padding: 20px 0;
        }

        .phase-item {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 8px;
          opacity: 0.4;
        }

        .phase-item.complete,
        .phase-item.active {
          opacity: 1;
        }

        .phase-marker {
          width: 32px;
          height: 32px;
          border-radius: 50%;
          background: var(--bg-tertiary, #252540);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 14px;
        }

        .phase-item.complete .phase-marker {
          background: #22c55e;
          color: white;
        }

        .phase-item.active .phase-marker {
          background: #6366f1;
          color: white;
          animation: pulse 2s infinite;
        }

        @keyframes pulse {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.1); }
        }

        .phase-label {
          font-size: 11px;
          text-transform: uppercase;
        }
      `}</style>
        </div>
    );
};

// Technical View - Logs and metrics
const TechnicalView: React.FC<{ logs: ActionLog[]; onRefresh: () => void }> = ({
    logs,
    onRefresh,
}) => {
    return (
        <div className="technical-view">
            <div className="view-section">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h3>Action Logs</h3>
                    <button onClick={onRefresh} style={{ padding: '4px 12px', borderRadius: 4 }}>
                        Refresh
                    </button>
                </div>
                <table className="log-table">
                    <thead>
                        <tr>
                            <th>Agent</th>
                            <th>Action</th>
                            <th>Status</th>
                            <th>Confidence</th>
                            <th>Cost</th>
                            <th>Time</th>
                        </tr>
                    </thead>
                    <tbody>
                        {logs.map((log) => (
                            <tr key={log.id}>
                                <td>{log.agent_name}</td>
                                <td>{log.action_name}</td>
                                <td>
                                    <span className={`status-badge ${log.status}`}>{log.status}</span>
                                </td>
                                <td>{(log.confidence * 100).toFixed(0)}%</td>
                                <td>${log.cost_usd.toFixed(4)}</td>
                                <td>{new Date(log.started_at).toLocaleTimeString()}</td>
                            </tr>
                        ))}
                        {logs.length === 0 && (
                            <tr>
                                <td colSpan={6} style={{ textAlign: 'center', padding: 20 }}>
                                    No logs yet. Start a pipeline to see agent activity.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

// Audit View - Snapshots and deltas
const AuditView: React.FC<{
    snapshots: Snapshot[];
    deltaReport: DeltaReport | null;
    selectedSnapshots: [string, string];
    onSelectSnapshots: (snapshots: [string, string]) => void;
    onCompare: () => void;
    loading: boolean;
}> = ({ snapshots, deltaReport, selectedSnapshots, onSelectSnapshots, onCompare, loading }) => {
    return (
        <div className="audit-view">
            <div className="view-section">
                <h3>Project Snapshots</h3>
                <div className="snapshot-list">
                    {snapshots.map((snapshot) => (
                        <div key={snapshot.id} className="snapshot-item">
                            <input
                                type="checkbox"
                                checked={selectedSnapshots.includes(snapshot.id)}
                                onChange={(e) => {
                                    if (e.target.checked) {
                                        if (!selectedSnapshots[0]) {
                                            onSelectSnapshots([snapshot.id, selectedSnapshots[1]]);
                                        } else if (!selectedSnapshots[1]) {
                                            onSelectSnapshots([selectedSnapshots[0], snapshot.id]);
                                        }
                                    } else {
                                        onSelectSnapshots([
                                            selectedSnapshots[0] === snapshot.id ? '' : selectedSnapshots[0],
                                            selectedSnapshots[1] === snapshot.id ? '' : selectedSnapshots[1],
                                        ]);
                                    }
                                }}
                            />
                            <div style={{ flex: 1 }}>
                                <div style={{ fontWeight: 500 }}>{snapshot.label}</div>
                                <div style={{ fontSize: 12, color: '#888' }}>
                                    {new Date(snapshot.created_at).toLocaleString()} • {snapshot.shot_count} shots
                                </div>
                            </div>
                        </div>
                    ))}
                    {snapshots.length === 0 && (
                        <div style={{ textAlign: 'center', padding: 20, color: '#888' }}>
                            No snapshots yet. Snapshots are created automatically during pipeline execution.
                        </div>
                    )}
                </div>

                {selectedSnapshots[0] && selectedSnapshots[1] && (
                    <button
                        onClick={onCompare}
                        disabled={loading}
                        style={{
                            marginTop: 12,
                            padding: '8px 16px',
                            background: '#6366f1',
                            border: 'none',
                            borderRadius: 6,
                            color: 'white',
                            cursor: loading ? 'wait' : 'pointer',
                        }}
                    >
                        {loading ? 'Comparing...' : 'Compare Selected'}
                    </button>
                )}
            </div>

            {deltaReport && (
                <div className="view-section">
                    <h3>Delta Report: {deltaReport.from_label} → {deltaReport.to_label}</h3>
                    <div className="delta-summary">
                        <div className="delta-stat additions">
                            <div className="delta-stat-value">+{deltaReport.additions}</div>
                            <div className="delta-stat-label">Added</div>
                        </div>
                        <div className="delta-stat removals">
                            <div className="delta-stat-value">-{deltaReport.removals}</div>
                            <div className="delta-stat-label">Removed</div>
                        </div>
                        <div className="delta-stat modifications">
                            <div className="delta-stat-value">~{deltaReport.modifications}</div>
                            <div className="delta-stat-label">Modified</div>
                        </div>
                    </div>

                    <table className="log-table">
                        <thead>
                            <tr>
                                <th>Type</th>
                                <th>Entity</th>
                                <th>Change</th>
                                <th>Field</th>
                            </tr>
                        </thead>
                        <tbody>
                            {deltaReport.changes.slice(0, 20).map((change, i) => (
                                <tr key={i}>
                                    <td>{change.entity_type}</td>
                                    <td>{change.entity_id.slice(0, 8)}...</td>
                                    <td>
                                        <span className={`status-badge ${change.change_type === 'added' ? 'completed' : change.change_type === 'removed' ? 'failed' : 'running'}`}>
                                            {change.change_type}
                                        </span>
                                    </td>
                                    <td>{change.field_name || '-'}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
};

export default ExplainabilityDashboard;
