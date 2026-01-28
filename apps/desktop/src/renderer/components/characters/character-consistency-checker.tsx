/**
 * Character Consistency Checker
 * 
 * Validates character consistency across shots by:
 * - Comparing face embeddings
 * - Checking physical description adherence
 * - Flagging inconsistencies for review
 */

import React, { useState, useCallback, useEffect } from 'react';

interface Shot {
    id: string;
    thumbnailPath: string;
    sceneName: string;
    consistencyScore: number;
}

interface ConsistencyIssue {
    shotId: string;
    issueType: 'face' | 'clothing' | 'props' | 'other';
    severity: 'low' | 'medium' | 'high';
    description: string;
}

interface CharacterConsistencyCheckerProps {
    characterId: string;
    characterName: string;
    referenceImagePath?: string;
    shots: Shot[];
    onRegenerateShot?: (shotId: string) => void;
    onIgnoreIssue?: (shotId: string, issueType: string) => void;
}

export const CharacterConsistencyChecker: React.FC<CharacterConsistencyCheckerProps> = ({
    characterId,
    characterName,
    referenceImagePath,
    shots,
    onRegenerateShot,
    onIgnoreIssue,
}) => {
    const [isChecking, setIsChecking] = useState(false);
    const [issues, setIssues] = useState<ConsistencyIssue[]>([]);
    const [selectedShot, setSelectedShot] = useState<string | null>(null);
    const [overallScore, setOverallScore] = useState<number | null>(null);

    const runConsistencyCheck = useCallback(async () => {
        setIsChecking(true);
        setIssues([]);

        try {
            const response = await fetch(`/api/v1/characters/${characterId}/consistency-check`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ shot_ids: shots.map(s => s.id) }),
            });

            if (response.ok) {
                const data = await response.json();
                setIssues(data.issues || []);
                setOverallScore(data.overall_score);
            }
        } catch (error) {
            console.error('Consistency check failed:', error);
        } finally {
            setIsChecking(false);
        }
    }, [characterId, shots]);

    const getSeverityColor = (severity: string) => {
        switch (severity) {
            case 'high': return '#ef4444';
            case 'medium': return '#f59e0b';
            case 'low': return '#22c55e';
            default: return '#888';
        }
    };

    const getScoreColor = (score: number) => {
        if (score >= 0.9) return '#22c55e';
        if (score >= 0.7) return '#f59e0b';
        return '#ef4444';
    };

    return (
        <div className="consistency-checker">
            <div className="checker-header">
                <h3>
                    <span className="icon">🔍</span>
                    Consistency Checker
                </h3>
                <button
                    className="check-btn"
                    onClick={runConsistencyCheck}
                    disabled={isChecking || shots.length === 0}
                >
                    {isChecking ? 'Checking...' : 'Run Check'}
                </button>
            </div>

            {/* Reference Image */}
            {referenceImagePath && (
                <div className="reference-section">
                    <span className="label">Reference:</span>
                    <img src={referenceImagePath} alt="Reference" className="reference-thumb" />
                </div>
            )}

            {/* Overall Score */}
            {overallScore !== null && (
                <div className="overall-score">
                    <div
                        className="score-circle"
                        style={{ borderColor: getScoreColor(overallScore) }}
                    >
                        <span className="score-value">{Math.round(overallScore * 100)}%</span>
                        <span className="score-label">Consistency</span>
                    </div>
                </div>
            )}

            {/* Shot Grid */}
            <div className="shot-grid">
                {shots.map((shot) => {
                    const shotIssues = issues.filter(i => i.shotId === shot.id);
                    const hasIssues = shotIssues.length > 0;
                    const worstSeverity = shotIssues.reduce((worst, issue) => {
                        const severityOrder = { high: 3, medium: 2, low: 1 };
                        return severityOrder[issue.severity] > severityOrder[worst]
                            ? issue.severity
                            : worst;
                    }, 'low' as 'low' | 'medium' | 'high');

                    return (
                        <div
                            key={shot.id}
                            className={`shot-item ${hasIssues ? 'has-issues' : ''} ${selectedShot === shot.id ? 'selected' : ''}`}
                            onClick={() => setSelectedShot(shot.id === selectedShot ? null : shot.id)}
                        >
                            <img src={shot.thumbnailPath} alt={shot.sceneName} className="shot-thumb" />
                            <div className="shot-info">
                                <span className="scene-name">{shot.sceneName}</span>
                                <span
                                    className="score"
                                    style={{ color: getScoreColor(shot.consistencyScore) }}
                                >
                                    {Math.round(shot.consistencyScore * 100)}%
                                </span>
                            </div>
                            {hasIssues && (
                                <div
                                    className="issue-indicator"
                                    style={{ background: getSeverityColor(worstSeverity) }}
                                >
                                    {shotIssues.length}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>

            {/* Issue Details */}
            {selectedShot && (
                <div className="issue-details">
                    <h4>Issues for Selected Shot</h4>
                    {issues.filter(i => i.shotId === selectedShot).length === 0 ? (
                        <div className="no-issues">✓ No issues detected</div>
                    ) : (
                        <ul className="issue-list">
                            {issues
                                .filter(i => i.shotId === selectedShot)
                                .map((issue, idx) => (
                                    <li key={idx} className="issue-item">
                                        <div
                                            className="severity-dot"
                                            style={{ background: getSeverityColor(issue.severity) }}
                                        />
                                        <div className="issue-content">
                                            <span className="issue-type">{issue.issueType}</span>
                                            <span className="issue-desc">{issue.description}</span>
                                        </div>
                                        <div className="issue-actions">
                                            <button
                                                className="action-btn"
                                                onClick={() => onRegenerateShot?.(selectedShot)}
                                            >
                                                Regenerate
                                            </button>
                                            <button
                                                className="action-btn secondary"
                                                onClick={() => onIgnoreIssue?.(selectedShot, issue.issueType)}
                                            >
                                                Ignore
                                            </button>
                                        </div>
                                    </li>
                                ))}
                        </ul>
                    )}
                </div>
            )}

            {shots.length === 0 && (
                <div className="empty-state">
                    No shots to check. Generate some shots first.
                </div>
            )}

            <style>{`
        .consistency-checker {
          background: var(--bg-secondary, #1a1a2e);
          border-radius: 12px;
          padding: 20px;
        }

        .checker-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
        }

        .checker-header h3 {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 16px;
          margin: 0;
        }

        .icon {
          font-size: 20px;
        }

        .check-btn {
          padding: 8px 16px;
          background: var(--accent-color, #6366f1);
          border: none;
          border-radius: 6px;
          color: white;
          cursor: pointer;
          font-weight: 500;
        }

        .check-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .reference-section {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 16px;
          padding: 12px;
          background: var(--bg-tertiary, #252540);
          border-radius: 8px;
        }

        .reference-thumb {
          width: 48px;
          height: 48px;
          object-fit: cover;
          border-radius: 8px;
        }

        .overall-score {
          display: flex;
          justify-content: center;
          margin-bottom: 20px;
        }

        .score-circle {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          width: 100px;
          height: 100px;
          border: 4px solid;
          border-radius: 50%;
        }

        .score-value {
          font-size: 24px;
          font-weight: 600;
        }

        .score-label {
          font-size: 11px;
          color: var(--text-secondary, #888);
          text-transform: uppercase;
        }

        .shot-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
          gap: 12px;
          margin-bottom: 16px;
        }

        .shot-item {
          position: relative;
          border-radius: 8px;
          overflow: hidden;
          cursor: pointer;
          transition: transform 0.2s;
        }

        .shot-item:hover {
          transform: scale(1.02);
        }

        .shot-item.selected {
          ring: 2px solid var(--accent-color, #6366f1);
          box-shadow: 0 0 0 2px var(--accent-color, #6366f1);
        }

        .shot-item.has-issues {
          border: 2px solid rgba(239, 68, 68, 0.5);
        }

        .shot-thumb {
          width: 100%;
          aspect-ratio: 16/9;
          object-fit: cover;
        }

        .shot-info {
          display: flex;
          justify-content: space-between;
          padding: 8px;
          background: var(--bg-tertiary, #252540);
          font-size: 11px;
        }

        .scene-name {
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .issue-indicator {
          position: absolute;
          top: 8px;
          right: 8px;
          width: 20px;
          height: 20px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 11px;
          font-weight: 600;
          color: white;
        }

        .issue-details {
          background: var(--bg-tertiary, #252540);
          border-radius: 8px;
          padding: 16px;
        }

        .issue-details h4 {
          margin: 0 0 12px;
          font-size: 14px;
        }

        .no-issues {
          color: #22c55e;
          text-align: center;
          padding: 20px;
        }

        .issue-list {
          list-style: none;
          padding: 0;
          margin: 0;
        }

        .issue-item {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px 0;
          border-bottom: 1px solid var(--border-color, #333);
        }

        .severity-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          flex-shrink: 0;
        }

        .issue-content {
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .issue-type {
          font-size: 12px;
          font-weight: 500;
          text-transform: capitalize;
        }

        .issue-desc {
          font-size: 13px;
          color: var(--text-secondary, #888);
        }

        .issue-actions {
          display: flex;
          gap: 8px;
        }

        .action-btn {
          padding: 4px 12px;
          font-size: 12px;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          background: var(--accent-color, #6366f1);
          color: white;
        }

        .action-btn.secondary {
          background: transparent;
          border: 1px solid var(--border-color, #444);
          color: var(--text-secondary, #888);
        }

        .empty-state {
          text-align: center;
          padding: 40px;
          color: var(--text-secondary, #888);
        }
      `}</style>
        </div>
    );
};

export default CharacterConsistencyChecker;
