/**
 * HITL Approval Queue — Human-in-the-Loop approval UI.
 *
 * Shows pending agent escalations that require human review:
 * - Quality review failures
 * - Budget exceeded alerts
 * - Sensitive content flags
 * - Approve / Reject with one click
 */

import {} from 'react';
import { useCrewStore, AGENT_COLORS, AGENT_ICONS, type ApprovalItem } from '../stores/crew-store';
import { useTranslation } from '../i18n/use-translation';

function ApprovalCard({
  item,
  onApprove,
  onReject,
}: {
  item: ApprovalItem;
  onApprove: () => void;
  onReject: () => void;
}) {
  const { t } = useTranslation();
  const agentColor = AGENT_COLORS[item.agent_type] ?? '#6b7280';
  const agentIcon = AGENT_ICONS[item.agent_type] ?? '🤖';
  const isPending = item.status === 'pending';

  return (
    <div
      style={{
        padding: '12px 14px',
        background: isPending ? 'var(--bg-secondary, #1e1e2e)' : 'var(--bg-tertiary, #161622)',
        borderRadius: 8,
        border: isPending
          ? '1px solid var(--border-accent, #fbbf24)'
          : '1px solid var(--border, #2e2e3e)',
        marginBottom: 8,
        opacity: isPending ? 1 : 0.6,
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <span style={{ fontSize: 18 }}>{agentIcon}</span>
        <span
          style={{
            fontWeight: 600,
            fontSize: 13,
            color: agentColor,
            textTransform: 'capitalize',
          }}
        >
          {item.agent_type}
        </span>
        <span
          style={{
            fontSize: 11,
            padding: '2px 8px',
            borderRadius: 12,
            fontWeight: 600,
            background:
              item.status === 'pending'
                ? '#fef3c7'
                : item.status === 'approved'
                  ? '#dcfce7'
                  : '#fee2e2',
            color:
              item.status === 'pending'
                ? '#92400e'
                : item.status === 'approved'
                  ? '#15803d'
                  : '#b91c1c',
          }}
        >
          {item.status.toUpperCase()}
        </span>
        <span
          style={{
            marginLeft: 'auto',
            fontSize: 11,
            color: 'var(--text-tertiary, #71717a)',
          }}
        >
          {new Date(item.created_at).toLocaleTimeString()}
        </span>
      </div>

      {/* Action type */}
      <div
        style={{
          fontSize: 13,
          fontWeight: 500,
          color: 'var(--text-primary, #fafafa)',
          marginBottom: 4,
        }}
      >
        {item.action_type}
      </div>

      {/* Description */}
      <div
        style={{
          fontSize: 12,
          color: 'var(--text-secondary, #a1a1aa)',
          marginBottom: 10,
          lineHeight: 1.5,
        }}
      >
        {item.description}
      </div>

      {/* Actions */}
      {isPending && (
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button
            onClick={onReject}
            style={{
              fontSize: 12,
              fontWeight: 600,
              padding: '6px 16px',
              borderRadius: 6,
              border: '1px solid #ef4444',
              background: 'transparent',
              color: '#ef4444',
              cursor: 'pointer',
              transition: 'all 0.15s',
            }}
          >
            ✗ {t('approvalQueue.reject', 'Reject')}
          </button>
          <button
            onClick={onApprove}
            style={{
              fontSize: 12,
              fontWeight: 600,
              padding: '6px 16px',
              borderRadius: 6,
              border: 'none',
              background: '#22c55e',
              color: '#fff',
              cursor: 'pointer',
              transition: 'all 0.15s',
            }}
          >
            ✓ {t('approvalQueue.approve', 'Approve')}
          </button>
        </div>
      )}

      {/* Resolved info */}
      {!isPending && item.resolved_at && (
        <div
          style={{
            fontSize: 11,
            color: 'var(--text-tertiary, #71717a)',
            textAlign: 'right',
          }}
        >
          {t('approvalQueue.resolvedPrefix', 'Resolved')}{' '}
          {new Date(item.resolved_at).toLocaleTimeString()}
        </div>
      )}
    </div>
  );
}

export function ApprovalQueue() {
  const { t } = useTranslation();
  const { approvals, pendingApprovalCount, approveItem, rejectItem } = useCrewStore();

  const pendingItems = approvals.filter((a) => a.status === 'pending');
  const resolvedItems = approvals.filter((a) => a.status !== 'pending');

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
          display: 'flex',
          alignItems: 'center',
          gap: 8,
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
          🔔 {t('approvalQueue.title', 'Approval Queue')}
        </h3>
        {pendingApprovalCount > 0 && (
          <span
            style={{
              fontSize: 11,
              fontWeight: 700,
              padding: '2px 8px',
              borderRadius: 12,
              background: '#ef4444',
              color: '#fff',
            }}
          >
            {pendingApprovalCount}
          </span>
        )}
      </div>

      {/* Content */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '8px 14px',
        }}
      >
        {approvals.length === 0 && (
          <div
            style={{
              textAlign: 'center',
              padding: 24,
              color: 'var(--text-tertiary, #71717a)',
              fontSize: 13,
            }}
          >
            <span style={{ fontSize: 24, display: 'block', marginBottom: 8 }}>✅</span>
            {t('approvalQueue.emptyTitle', 'No pending approvals.')}
            <br />
            {t('approvalQueue.emptySubtitle', 'The crew is operating autonomously.')}
          </div>
        )}

        {/* Pending first */}
        {pendingItems.map((item) => (
          <ApprovalCard
            key={item.id}
            item={item}
            onApprove={() => approveItem(item.id)}
            onReject={() => rejectItem(item.id)}
          />
        ))}

        {/* Resolved */}
        {resolvedItems.length > 0 && pendingItems.length > 0 && (
          <div
            style={{
              fontSize: 11,
              color: 'var(--text-tertiary, #71717a)',
              padding: '8px 0',
              textAlign: 'center',
              borderTop: '1px solid var(--border, #2e2e3e)',
              marginTop: 4,
            }}
          >
            {t('approvalQueue.previouslyResolved', 'Previously resolved')}
          </div>
        )}
        {resolvedItems.slice(0, 10).map((item) => (
          <ApprovalCard key={item.id} item={item} onApprove={() => {}} onReject={() => {}} />
        ))}
      </div>
    </div>
  );
}

export default ApprovalQueue;
