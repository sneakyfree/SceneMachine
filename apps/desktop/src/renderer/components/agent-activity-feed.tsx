/**
 * Agent Activity Feed — Real-time display of agentic crew actions.
 *
 * Shows each agent's actions as cards in a live feed:
 * - Color-coded by agent type (Parser=blue, Character=green, etc.)
 * - Status indicators (running/completed/failed)
 * - Cost tracking per action
 * - Collapsible in sidebar
 */

import { useEffect, useMemo } from 'react';
import { useCrewStore, AGENT_COLORS, AGENT_ICONS, type ActionLog } from '../stores/crew-store';

// ---- Status badge ----
function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, { bg: string; text: string; label: string }> = {
    running: { bg: '#dbeafe', text: '#1d4ed8', label: 'Running' },
    completed: { bg: '#dcfce7', text: '#15803d', label: 'Done' },
    failed: { bg: '#fee2e2', text: '#b91c1c', label: 'Failed' },
    escalated: { bg: '#fef3c7', text: '#92400e', label: 'Escalated' },
    pending: { bg: '#f3f4f6', text: '#6b7280', label: 'Pending' },
    cancelled: { bg: '#f3f4f6', text: '#9ca3af', label: 'Cancelled' },
  };
  const c = colors[status] ?? colors.pending;
  return (
    <span
      style={{
        fontSize: 11,
        fontWeight: 600,
        padding: '2px 8px',
        borderRadius: 12,
        background: c.bg,
        color: c.text,
        whiteSpace: 'nowrap',
      }}
    >
      {status === 'running' && (
        <span
          className="pulse-dot"
          style={{
            display: 'inline-block',
            width: 6,
            height: 6,
            borderRadius: '50%',
            background: c.text,
            marginRight: 4,
            animation: 'pulse 1.5s ease-in-out infinite',
          }}
        />
      )}
      {c.label}
    </span>
  );
}

// ---- Single action card ----
function ActionCard({ log }: { log: ActionLog }) {
  const agentColor = AGENT_COLORS[log.agent_type] ?? '#6b7280';
  const agentIcon = AGENT_ICONS[log.agent_type] ?? '🤖';
  const timeAgo = useMemo(() => {
    const ms = Date.now() - new Date(log.started_at).getTime();
    if (ms < 60_000) return `${Math.round(ms / 1000)}s ago`;
    if (ms < 3600_000) return `${Math.round(ms / 60_000)}m ago`;
    return `${Math.round(ms / 3600_000)}h ago`;
  }, [log.started_at]);

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: 10,
        padding: '10px 12px',
        borderLeft: `3px solid ${agentColor}`,
        background: 'var(--bg-secondary, #1e1e2e)',
        borderRadius: 6,
        marginBottom: 6,
        transition: 'background 0.15s',
      }}
    >
      {/* Agent icon */}
      <span style={{ fontSize: 20, lineHeight: 1 }}>{agentIcon}</span>

      {/* Content */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
          <span
            style={{
              fontWeight: 600,
              fontSize: 13,
              color: agentColor,
              textTransform: 'capitalize',
            }}
          >
            {log.agent_name}
          </span>
          <StatusBadge status={log.status} />
        </div>
        <div
          style={{
            fontSize: 12,
            color: 'var(--text-secondary, #a1a1aa)',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {log.action_name}
        </div>
        <div
          style={{
            display: 'flex',
            gap: 12,
            marginTop: 4,
            fontSize: 11,
            color: 'var(--text-tertiary, #71717a)',
          }}
        >
          <span>{timeAgo}</span>
          {log.confidence < 1 && <span>Confidence: {Math.round(log.confidence * 100)}%</span>}
          {log.cost_usd > 0 && <span>${log.cost_usd.toFixed(4)}</span>}
        </div>
      </div>
    </div>
  );
}

// ---- Agent filter pills ----
function AgentFilterPills() {
  const { agents, logFilter, setLogFilter } = useCrewStore();

  return (
    <div
      style={{
        display: 'flex',
        gap: 4,
        flexWrap: 'wrap',
        marginBottom: 10,
      }}
    >
      <button
        onClick={() => setLogFilter(null)}
        style={{
          fontSize: 11,
          padding: '3px 10px',
          borderRadius: 12,
          border: 'none',
          cursor: 'pointer',
          background: !logFilter ? '#6366f1' : 'var(--bg-tertiary, #27272a)',
          color: !logFilter ? '#fff' : 'var(--text-secondary, #a1a1aa)',
          fontWeight: 500,
        }}
      >
        All
      </button>
      {agents.map((agent) => (
        <button
          key={agent.type}
          onClick={() => setLogFilter(agent.type)}
          style={{
            fontSize: 11,
            padding: '3px 10px',
            borderRadius: 12,
            border: 'none',
            cursor: 'pointer',
            background:
              logFilter === agent.type
                ? (AGENT_COLORS[agent.type] ?? '#6366f1')
                : 'var(--bg-tertiary, #27272a)',
            color: logFilter === agent.type ? '#fff' : 'var(--text-secondary, #a1a1aa)',
            fontWeight: 500,
            textTransform: 'capitalize',
          }}
        >
          {AGENT_ICONS[agent.type] ?? '🤖'} {agent.name}
        </button>
      ))}
    </div>
  );
}

// ---- Main component ----
export function AgentActivityFeed() {
  const {
    actionLogs,
    isLoadingLogs,
    fetchActionLogs,
    fetchAgents,
    agents,
    totalCost,
    fetchTotalCost,
  } = useCrewStore();

  useEffect(() => {
    fetchAgents();
    fetchActionLogs();
    fetchTotalCost();
    // Poll every 5 seconds when open
    const interval = setInterval(() => {
      fetchActionLogs();
      fetchTotalCost();
    }, 5000);
    return () => clearInterval(interval);
  }, [fetchActionLogs, fetchAgents, fetchTotalCost]);

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '12px 14px 8px',
          borderBottom: '1px solid var(--border, #2e2e3e)',
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: 8,
          }}
        >
          <h3
            style={{
              margin: 0,
              fontSize: 14,
              fontWeight: 700,
              color: 'var(--text-primary, #fafafa)',
            }}
          >
            🎬 Agent Crew
          </h3>
          {totalCost > 0 && (
            <span
              style={{
                fontSize: 11,
                color: '#22c55e',
                fontWeight: 600,
              }}
            >
              ${totalCost.toFixed(4)}
            </span>
          )}
        </div>

        {/* Agent status pills */}
        {agents.length > 0 && (
          <div style={{ display: 'flex', gap: 6, marginBottom: 8 }}>
            {agents.map((agent) => (
              <span
                key={agent.type}
                title={`${agent.name}: ${agent.capabilities.join(', ')}`}
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  background: AGENT_COLORS[agent.type] ?? '#6b7280',
                  display: 'inline-block',
                }}
              />
            ))}
          </div>
        )}

        <AgentFilterPills />
      </div>

      {/* Feed */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '8px 14px',
        }}
      >
        {isLoadingLogs && actionLogs.length === 0 && (
          <div
            style={{
              textAlign: 'center',
              padding: 20,
              color: 'var(--text-tertiary, #71717a)',
              fontSize: 13,
            }}
          >
            Loading agent actions...
          </div>
        )}

        {!isLoadingLogs && actionLogs.length === 0 && (
          <div
            style={{
              textAlign: 'center',
              padding: 20,
              color: 'var(--text-tertiary, #71717a)',
              fontSize: 13,
            }}
          >
            <span style={{ fontSize: 24, display: 'block', marginBottom: 8 }}>🤖</span>
            No agent activity yet.
            <br />
            Start a pipeline to see the crew in action.
          </div>
        )}

        {actionLogs.map((log) => (
          <ActionCard key={log.id} log={log} />
        ))}
      </div>
    </div>
  );
}

export default AgentActivityFeed;
