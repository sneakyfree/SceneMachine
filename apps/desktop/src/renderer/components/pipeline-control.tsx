/**
 * Pipeline Control Panel — "Generate Movie" button + progress display.
 *
 * Shows:
 * - Start / Pause / Resume / Cancel buttons
 * - Current pipeline stage and progress bar
 * - Cost tracking
 * - Agent crew status dots
 */

import { useCallback, useEffect } from 'react';
import { useCrewStore, AGENT_COLORS } from '../stores/crew-store';

const PHASES = [
    { key: 'parsing', label: 'Parsing', icon: '📝' },
    { key: 'character_setup', label: 'Characters', icon: '👤' },
    { key: 'generation', label: 'Generating', icon: '🎥' },
    { key: 'audio', label: 'Audio/TTS', icon: '🔊' },
    { key: 'lipsync', label: 'Lip Sync', icon: '👄' },
    { key: 'assembly', label: 'Assembly', icon: '🔧' },
    { key: 'review', label: 'Review', icon: '🔍' },
    { key: 'export', label: 'Export', icon: '📦' },
];

export function PipelineControl({ projectId }: { projectId: string }) {
    const {
        pipelineStatus,
        isPipelineRunning,
        agents,
        totalCost,
        fetchPipelineStatus,
        startPipeline,
        pausePipeline,
        resumePipeline,
        cancelPipeline,
        fetchAgents,
        fetchTotalCost,
    } = useCrewStore();

    const screenplayPath = '';

    useEffect(() => {
        fetchAgents();
        fetchTotalCost();
    }, [fetchAgents, fetchTotalCost]);

    // Poll pipeline status while running
    useEffect(() => {
        if (!isPipelineRunning) return;
        const interval = setInterval(() => {
            fetchPipelineStatus(projectId);
            fetchTotalCost();
        }, 2000);
        return () => clearInterval(interval);
    }, [isPipelineRunning, projectId, fetchPipelineStatus, fetchTotalCost]);

    const handleStart = useCallback(async () => {
        await startPipeline(projectId, screenplayPath || undefined);
        fetchPipelineStatus(projectId);
    }, [startPipeline, projectId, screenplayPath, fetchPipelineStatus]);

    const progress = pipelineStatus?.progress_percent ?? 0;
    const currentPhase = pipelineStatus?.current_phase ?? '';
    const status = pipelineStatus?.status ?? 'idle';
    const errors = pipelineStatus?.errors ?? [];

    return (
        <div style={{
            background: 'var(--bg-secondary, #1e1e2e)',
            borderRadius: 12,
            padding: '20px 24px',
            border: '1px solid var(--border, #2e2e3e)',
        }}>
            {/* Header */}
            <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: 16,
            }}>
                <h2 style={{
                    margin: 0,
                    fontSize: 18,
                    fontWeight: 700,
                    color: 'var(--text-primary, #fafafa)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                }}>
                    🎬 Generate Movie
                </h2>

                {/* Agent crew dots */}
                <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                    {agents.map((agent) => (
                        <span
                            key={agent.type}
                            title={agent.name}
                            style={{
                                width: 10,
                                height: 10,
                                borderRadius: '50%',
                                background: AGENT_COLORS[agent.type] ?? '#6b7280',
                                display: 'inline-block',
                                transition: 'transform 0.2s',
                            }}
                        />
                    ))}
                </div>
            </div>

            {/* Status line */}
            {isPipelineRunning && (
                <>
                    {/* Phase progress dots */}
                    <div style={{
                        display: 'flex',
                        gap: 4,
                        alignItems: 'center',
                        marginBottom: 12,
                    }}>
                        {PHASES.map((phase) => {
                            const isActive = phase.key === currentPhase;
                            const phaseIndex = PHASES.findIndex((p) => p.key === phase.key);
                            const currentIndex = PHASES.findIndex((p) => p.key === currentPhase);
                            const isDone = currentIndex > phaseIndex;

                            return (
                                <div
                                    key={phase.key}
                                    title={phase.label}
                                    style={{
                                        flex: 1,
                                        height: 4,
                                        borderRadius: 2,
                                        background: isDone ? '#22c55e' : isActive ? '#6366f1' : 'var(--bg-tertiary, #27272a)',
                                        transition: 'background 0.3s',
                                        position: 'relative',
                                    }}
                                >
                                    {isActive && (
                                        <div style={{
                                            position: 'absolute',
                                            top: -20,
                                            left: '50%',
                                            transform: 'translateX(-50%)',
                                            fontSize: 14,
                                        }}>
                                            {phase.icon}
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>

                    {/* Progress bar */}
                    <div style={{
                        height: 6,
                        borderRadius: 3,
                        background: 'var(--bg-tertiary, #27272a)',
                        marginBottom: 12,
                        overflow: 'hidden',
                    }}>
                        <div style={{
                            height: '100%',
                            width: `${progress}%`,
                            borderRadius: 3,
                            background: 'linear-gradient(90deg, #6366f1, #a855f7)',
                            transition: 'width 0.5s ease',
                        }} />
                    </div>

                    {/* Status text */}
                    <div style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginBottom: 12,
                        fontSize: 12,
                        color: 'var(--text-secondary, #a1a1aa)',
                    }}>
                        <span>
                            {currentPhase ? `${currentPhase.charAt(0).toUpperCase()}${currentPhase.slice(1)}` : status} — {Math.round(progress)}%
                        </span>
                        <span style={{ color: '#22c55e', fontWeight: 600 }}>
                            ${totalCost.toFixed(4)}
                        </span>
                    </div>
                </>
            )}

            {/* Errors */}
            {errors.length > 0 && (
                <div style={{
                    background: '#fee2e2',
                    borderRadius: 6,
                    padding: '8px 12px',
                    marginBottom: 12,
                }}>
                    {errors.map((err, i) => (
                        <div key={i} style={{ fontSize: 12, color: '#b91c1c' }}>
                            ⚠ {err}
                        </div>
                    ))}
                </div>
            )}

            {/* Controls */}
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                {!isPipelineRunning ? (
                    <>
                        <button
                            onClick={handleStart}
                            style={{
                                flex: 1,
                                padding: '12px 20px',
                                borderRadius: 8,
                                border: 'none',
                                background: 'linear-gradient(135deg, #6366f1, #a855f7)',
                                color: '#fff',
                                fontSize: 14,
                                fontWeight: 700,
                                cursor: 'pointer',
                                transition: 'transform 0.15s, box-shadow 0.15s',
                                boxShadow: '0 4px 14px rgba(99, 102, 241, 0.4)',
                            }}
                        >
                            🎬 Generate Movie
                        </button>
                    </>
                ) : (
                    <>
                        {status === 'paused' ? (
                            <button
                                onClick={() => resumePipeline(projectId)}
                                style={{
                                    flex: 1,
                                    padding: '10px 16px',
                                    borderRadius: 8,
                                    border: 'none',
                                    background: '#22c55e',
                                    color: '#fff',
                                    fontSize: 13,
                                    fontWeight: 600,
                                    cursor: 'pointer',
                                }}
                            >
                                ▶ Resume
                            </button>
                        ) : (
                            <button
                                onClick={() => pausePipeline(projectId)}
                                style={{
                                    flex: 1,
                                    padding: '10px 16px',
                                    borderRadius: 8,
                                    border: '1px solid #fbbf24',
                                    background: 'transparent',
                                    color: '#fbbf24',
                                    fontSize: 13,
                                    fontWeight: 600,
                                    cursor: 'pointer',
                                }}
                            >
                                ⏸ Pause
                            </button>
                        )}
                        <button
                            onClick={() => cancelPipeline(projectId)}
                            style={{
                                padding: '10px 16px',
                                borderRadius: 8,
                                border: '1px solid #ef4444',
                                background: 'transparent',
                                color: '#ef4444',
                                fontSize: 13,
                                fontWeight: 600,
                                cursor: 'pointer',
                            }}
                        >
                            ✕ Cancel
                        </button>
                    </>
                )}
            </div>
        </div>
    );
}

export default PipelineControl;
