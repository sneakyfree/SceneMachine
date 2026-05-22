/**
 * Quality Radar Chart component.
 *
 * Renders an 8-axis spider/radar chart showing per-dimension
 * quality scores from the Video Quality Reviewer service.
 */

import { useState } from 'react';
import { Shield, CheckCircle, AlertTriangle, XCircle, Loader2 } from 'lucide-react';

// Quality dimension score from API
interface QualityDimensionScore {
  dimension: string;
  score: number;
  confidence: number;
  weight: number;
  issues: string[];
  notes: string;
}

interface QualityReviewResult {
  job_id: string;
  overall_score: number;
  passed: boolean;
  dimensions: QualityDimensionScore[];
  requires_escalation: boolean;
  escalation_reason?: string;
  recommendations: string[];
  reviewed_at?: string;
}

// Human-readable labels for quality dimensions
const DIMENSION_LABELS: Record<string, string> = {
  visual_fidelity: 'Visual Fidelity',
  motion_coherence: 'Motion',
  character_consistency: 'Character',
  prompt_adherence: 'Prompt Match',
  temporal_stability: 'Stability',
  physics_plausibility: 'Physics',
  lighting_consistency: 'Lighting',
  audio_sync: 'Audio Sync',
};

interface QualityRadarChartProps {
  review: QualityReviewResult | null;
  loading?: boolean;
  compact?: boolean;
}

function polarToCartesian(
  cx: number,
  cy: number,
  radius: number,
  angleRad: number
): { x: number; y: number } {
  return {
    x: cx + radius * Math.cos(angleRad - Math.PI / 2),
    y: cy + radius * Math.sin(angleRad - Math.PI / 2),
  };
}

export function QualityRadarChart({
  review,
  loading = false,
  compact = false,
}: QualityRadarChartProps) {
  const [hoveredDim, setHoveredDim] = useState<string | null>(null);

  if (loading) {
    return (
      <div
        className="quality-radar-loading"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: compact ? '12px' : '24px',
          gap: '8px',
          color: 'var(--text-secondary, #999)',
        }}
      >
        <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} />
        <span style={{ fontSize: '13px' }}>Analyzing quality…</span>
      </div>
    );
  }

  if (!review) return null;

  const dims = review.dimensions;
  if (dims.length === 0) return null;

  const size = compact ? 160 : 220;
  const cx = size / 2;
  const cy = size / 2;
  const maxRadius = size / 2 - (compact ? 30 : 40);
  const n = dims.length;

  // Build polygon points for scores
  const scorePoints = dims.map((d, i) => {
    const angle = (2 * Math.PI * i) / n;
    const r = d.score * maxRadius;
    return polarToCartesian(cx, cy, r, angle);
  });

  const scorePolygon = scorePoints.map((p) => `${p.x},${p.y}`).join(' ');

  // Threshold ring (0.7)
  const thresholdPoints = Array.from({ length: n }, (_, i) => {
    const angle = (2 * Math.PI * i) / n;
    return polarToCartesian(cx, cy, 0.7 * maxRadius, angle);
  });
  const thresholdPolygon = thresholdPoints.map((p) => `${p.x},${p.y}`).join(' ');

  // Grid rings
  const rings = [0.25, 0.5, 0.75, 1.0];

  const OverallIcon = review.passed
    ? review.overall_score >= 0.85
      ? CheckCircle
      : Shield
    : review.requires_escalation
      ? XCircle
      : AlertTriangle;

  const overallColor = review.passed
    ? review.overall_score >= 0.85
      ? '#22c55e'
      : '#3b82f6'
    : review.requires_escalation
      ? '#ef4444'
      : '#f59e0b';

  const hoveredData = hoveredDim ? dims.find((d) => d.dimension === hoveredDim) : null;

  return (
    <div
      className="quality-radar-chart"
      style={{
        background: 'var(--bg-secondary, #1a1a2e)',
        borderRadius: '12px',
        border: '1px solid var(--border-primary, #2a2a4a)',
        padding: compact ? '12px' : '16px',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: compact ? '8px' : '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <OverallIcon size={16} color={overallColor} />
          <span
            style={{
              fontSize: '13px',
              fontWeight: 600,
              color: 'var(--text-primary, #e0e0e0)',
            }}
          >
            Quality Score
          </span>
        </div>
        <div
          style={{
            fontSize: '18px',
            fontWeight: 700,
            color: overallColor,
          }}
        >
          {Math.round(review.overall_score * 100)}%
        </div>
      </div>

      {/* SVG Radar */}
      <div style={{ display: 'flex', justifyContent: 'center' }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
          {/* Grid rings */}
          {rings.map((r) => {
            const pts = Array.from({ length: n }, (_, i) => {
              const angle = (2 * Math.PI * i) / n;
              return polarToCartesian(cx, cy, r * maxRadius, angle);
            });
            return (
              <polygon
                key={r}
                points={pts.map((p) => `${p.x},${p.y}`).join(' ')}
                fill="none"
                stroke="var(--border-secondary, #333)"
                strokeWidth="0.5"
                opacity={0.4}
              />
            );
          })}

          {/* Axis lines */}
          {dims.map((_, i) => {
            const angle = (2 * Math.PI * i) / n;
            const end = polarToCartesian(cx, cy, maxRadius, angle);
            return (
              <line
                key={i}
                x1={cx}
                y1={cy}
                x2={end.x}
                y2={end.y}
                stroke="var(--border-secondary, #333)"
                strokeWidth="0.5"
                opacity={0.3}
              />
            );
          })}

          {/* Threshold ring */}
          <polygon
            points={thresholdPolygon}
            fill="none"
            stroke="#f59e0b"
            strokeWidth="1"
            strokeDasharray="4 2"
            opacity={0.4}
          />

          {/* Score polygon */}
          <polygon
            points={scorePolygon}
            fill={review.passed ? 'rgba(59,130,246,0.15)' : 'rgba(245,158,11,0.15)'}
            stroke={review.passed ? '#3b82f6' : '#f59e0b'}
            strokeWidth="2"
          />

          {/* Score dots + labels */}
          {dims.map((d, i) => {
            const angle = (2 * Math.PI * i) / n;
            const dotPos = polarToCartesian(cx, cy, d.score * maxRadius, angle);
            const labelPos = polarToCartesian(cx, cy, maxRadius + (compact ? 18 : 24), angle);
            const isHovered = hoveredDim === d.dimension;
            const label = DIMENSION_LABELS[d.dimension] || d.dimension;

            return (
              <g
                key={d.dimension}
                onMouseEnter={() => setHoveredDim(d.dimension)}
                onMouseLeave={() => setHoveredDim(null)}
                style={{ cursor: 'pointer' }}
              >
                <circle
                  cx={dotPos.x}
                  cy={dotPos.y}
                  r={isHovered ? 5 : 3}
                  fill={d.score >= 0.7 ? '#3b82f6' : '#f59e0b'}
                  stroke="white"
                  strokeWidth="1"
                />
                <text
                  x={labelPos.x}
                  y={labelPos.y}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize={compact ? '8' : '9'}
                  fill={isHovered ? '#fff' : 'var(--text-secondary, #999)'}
                  fontWeight={isHovered ? 600 : 400}
                >
                  {label}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Hover tooltip */}
      {hoveredData && (
        <div
          style={{
            marginTop: '8px',
            padding: '8px 12px',
            background: 'var(--bg-tertiary, #222244)',
            borderRadius: '8px',
            fontSize: '12px',
            color: 'var(--text-secondary, #ccc)',
          }}
        >
          <div style={{ fontWeight: 600, color: 'var(--text-primary, #fff)', marginBottom: '4px' }}>
            {DIMENSION_LABELS[hoveredData.dimension] || hoveredData.dimension} —{' '}
            {Math.round(hoveredData.score * 100)}%
          </div>
          {hoveredData.issues.length > 0 && (
            <div style={{ color: '#f59e0b' }}>Issues: {hoveredData.issues.join(', ')}</div>
          )}
          {hoveredData.notes && (
            <div style={{ opacity: 0.7, marginTop: '2px' }}>{hoveredData.notes}</div>
          )}
        </div>
      )}

      {/* Recommendations */}
      {!compact && review.recommendations.length > 0 && (
        <div style={{ marginTop: '12px' }}>
          <div
            style={{
              fontSize: '11px',
              fontWeight: 600,
              textTransform: 'uppercase' as const,
              color: 'var(--text-secondary, #999)',
              marginBottom: '6px',
              letterSpacing: '0.5px',
            }}
          >
            Recommendations
          </div>
          {review.recommendations.map((rec, i) => (
            <div
              key={i}
              style={{
                fontSize: '12px',
                color: 'var(--text-secondary, #ccc)',
                padding: '4px 0',
                borderBottom: '1px solid var(--border-secondary, #333)',
              }}
            >
              • {rec}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export type { QualityReviewResult, QualityDimensionScore };
export default QualityRadarChart;
