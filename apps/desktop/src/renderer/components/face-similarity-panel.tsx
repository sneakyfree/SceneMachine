/**
 * Face Similarity Panel component.
 *
 * Displays per-shot face similarity scores for a character,
 * using the FaceEmbeddingService's cosine similarity comparison.
 * Shows an average similarity badge and horizontal bar chart.
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  ScanFace,
  BarChart3,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Loader2,
  RefreshCw,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { useTranslation } from '../i18n/use-translation';

interface FaceSimilarityComparison {
  shot_id: string;
  similarity_score: number;
  is_same_person: boolean;
  thumbnail_url?: string;
}

interface FaceSimilarityResult {
  character_id: string;
  character_name: string;
  comparisons: FaceSimilarityComparison[];
  average_similarity: number;
}

interface FaceSimilarityPanelProps {
  characterId: string;
  characterName: string;
  isLocked: boolean;
  className?: string;
}

function getScoreColor(score: number): string {
  if (score >= 0.85) return '#22c55e';
  if (score >= 0.7) return '#f59e0b';
  return '#ef4444';
}

function getScoreLabel(score: number): { key: string; en: string } {
  if (score >= 0.85) return { key: 'faceSim.scoreExcellent', en: 'Excellent' };
  if (score >= 0.7) return { key: 'faceSim.scoreGood', en: 'Good' };
  if (score >= 0.5) return { key: 'faceSim.scoreFair', en: 'Fair' };
  return { key: 'faceSim.scoreLow', en: 'Low' };
}

function getScoreIcon(score: number) {
  if (score >= 0.85) return CheckCircle;
  if (score >= 0.7) return AlertTriangle;
  return XCircle;
}

export function FaceSimilarityPanel({
  characterId,
  characterName,
  isLocked,
  className,
}: FaceSimilarityPanelProps) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);

  const {
    data: result,
    isLoading,
    refetch,
    isFetching,
  } = useQuery<FaceSimilarityResult>({
    queryKey: ['face-similarity', characterId],
    queryFn: async () => {
      const response = await fetch(`/api/characters/${characterId}/face-similarity`, {
        method: 'POST',
      });
      if (!response.ok) {
        return {
          character_id: characterId,
          character_name: characterName,
          comparisons: [],
          average_similarity: 0,
        };
      }
      return response.json();
    },
    enabled: isLocked, // Only fetch for locked characters
    staleTime: 60_000,
  });

  if (!isLocked) {
    return (
      <div
        className={cn('face-similarity-panel', className)}
        style={{
          padding: '12px 16px',
          background: 'var(--bg-tertiary, #222244)',
          borderRadius: '10px',
          fontSize: '12px',
          color: 'var(--text-secondary, #999)',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
        }}
      >
        <ScanFace size={14} />
        {t('faceSim.lockToEnable', 'Lock character to enable face similarity analysis')}
      </div>
    );
  }

  if (isLoading) {
    return (
      <div
        style={{
          padding: '16px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          color: 'var(--text-secondary, #999)',
        }}
      >
        <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} />
        <span style={{ fontSize: '12px' }}>{t('faceSim.analyzing', 'Analyzing face similarity…')}</span>
      </div>
    );
  }

  if (!result || result.comparisons.length === 0) {
    return (
      <div
        className={cn('face-similarity-panel', className)}
        style={{
          padding: '12px 16px',
          background: 'var(--bg-tertiary, #222244)',
          borderRadius: '10px',
          fontSize: '12px',
          color: 'var(--text-secondary, #999)',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
        }}
      >
        <ScanFace size={14} />
        {t('faceSim.noShots', 'No generated shots to compare yet')}
      </div>
    );
  }

  const avgScore = result.average_similarity;
  const avgColor = getScoreColor(avgScore);
  const ScoreIcon = getScoreIcon(avgScore);
  const sorted = [...result.comparisons].sort((a, b) => b.similarity_score - a.similarity_score);

  return (
    <div
      className={cn('face-similarity-panel', className)}
      style={{
        background: 'var(--bg-secondary, #1a1a2e)',
        borderRadius: '12px',
        border: '1px solid var(--border-primary, #2a2a4a)',
        padding: '16px',
      }}
    >
      {/* Header with average score */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <ScanFace size={16} color="var(--accent-primary, #6366f1)" />
          <span
            style={{
              fontSize: '13px',
              fontWeight: 600,
              color: 'var(--text-primary, #e0e0e0)',
            }}
          >
            {t('faceSim.faceConsistency', 'Face Consistency')}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: 'var(--text-secondary, #999)',
              padding: '4px',
              display: 'flex',
              alignItems: 'center',
            }}
            title={t('faceSim.refresh', 'Refresh similarity scores')}
          >
            <RefreshCw
              size={14}
              style={isFetching ? { animation: 'spin 1s linear infinite' } : {}}
            />
          </button>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              padding: '4px 10px',
              background: `${avgColor}15`,
              border: `1px solid ${avgColor}40`,
              borderRadius: '20px',
            }}
          >
            <ScoreIcon size={14} color={avgColor} />
            <span style={{ fontSize: '14px', fontWeight: 700, color: avgColor }}>
              {Math.round(avgScore * 100)}%
            </span>
          </div>
        </div>
      </div>

      {/* Score label */}
      <div
        style={{
          fontSize: '11px',
          color: 'var(--text-secondary, #999)',
          marginBottom: '12px',
        }}
      >
        {(() => {
          const label = getScoreLabel(avgScore);
          return t(label.key, label.en);
        })()}{' '}
        {t('faceSim.consistencyAcross', 'consistency across')} {result.comparisons.length}{' '}
        {result.comparisons.length !== 1
          ? t('faceSim.shotsPlural', 'shots')
          : t('faceSim.shotSingular', 'shot')}
      </div>

      {/* Expandable bar chart */}
      <button
        onClick={() => setExpanded(!expanded)}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '6px 0',
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          color: 'var(--accent-primary, #6366f1)',
          fontSize: '11px',
          fontWeight: 600,
        }}
      >
        <BarChart3 size={12} />
        {expanded ? t('faceSim.hide', 'Hide') : t('faceSim.show', 'Show')}{' '}
        {t('faceSim.perShotBreakdown', 'per-shot breakdown')} ({sorted.length})
      </button>

      {expanded && (
        <div style={{ marginTop: '8px' }}>
          {sorted.map((comp) => {
            const barColor = getScoreColor(comp.similarity_score);
            return (
              <div
                key={comp.shot_id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  marginBottom: '6px',
                }}
              >
                {/* Shot ID */}
                <div
                  style={{
                    fontSize: '10px',
                    color: 'var(--text-secondary, #999)',
                    width: '60px',
                    flexShrink: 0,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {comp.shot_id.substring(0, 8)}
                </div>

                {/* Bar */}
                <div
                  style={{
                    flex: 1,
                    height: '8px',
                    background: 'var(--bg-tertiary, #333)',
                    borderRadius: '4px',
                    overflow: 'hidden',
                  }}
                >
                  <div
                    style={{
                      width: `${comp.similarity_score * 100}%`,
                      height: '100%',
                      background: barColor,
                      borderRadius: '4px',
                      transition: 'width 0.3s ease',
                    }}
                  />
                </div>

                {/* Score */}
                <div
                  style={{
                    fontSize: '11px',
                    fontWeight: 600,
                    color: barColor,
                    width: '36px',
                    textAlign: 'right',
                  }}
                >
                  {Math.round(comp.similarity_score * 100)}%
                </div>

                {/* Status icon */}
                {comp.is_same_person ? (
                  <CheckCircle size={12} color="#22c55e" />
                ) : (
                  <AlertTriangle size={12} color="#f59e0b" />
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export type { FaceSimilarityResult, FaceSimilarityComparison };
export default FaceSimilarityPanel;
