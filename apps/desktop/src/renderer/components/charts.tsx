/**
 * Chart components for analytics visualization.
 * Uses SVG for crisp rendering without external dependencies.
 */

import { useMemo } from 'react';
import { cn } from '../lib/utils';

// Common interfaces
interface DataPoint {
  label: string;
  value: number;
  color?: string;
}

interface TimeSeriesPoint {
  timestamp: string;
  value: number;
}

// Line chart component
interface LineChartProps {
  data: TimeSeriesPoint[];
  height?: number;
  color?: string;
  fillColor?: string;
  showArea?: boolean;
  showDots?: boolean;
  showGrid?: boolean;
  formatValue?: (value: number) => string;
  formatLabel?: (timestamp: string) => string;
  className?: string;
}

export function LineChart({
  data,
  height = 200,
  color = '#8b5cf6',
  fillColor = 'rgba(139, 92, 246, 0.2)',
  showArea = true,
  showDots = true,
  showGrid = true,
  formatValue = (v) => v.toFixed(0),
  formatLabel = (t) => t,
  className,
}: LineChartProps) {
  const chartData = useMemo(() => {
    if (data.length === 0) return { path: '', areaPath: '', points: [], yLabels: [], xLabels: [] };

    const padding = { top: 20, right: 20, bottom: 30, left: 50 };
    const width = 600;
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;

    const values = data.map((d) => d.value);
    const minValue = Math.min(...values);
    const maxValue = Math.max(...values);
    const range = maxValue - minValue || 1;

    // Calculate points
    const points = data.map((d, i) => ({
      x: padding.left + (i / (data.length - 1 || 1)) * chartWidth,
      y: padding.top + (1 - (d.value - minValue) / range) * chartHeight,
      value: d.value,
      label: d.timestamp,
    }));

    // Build path
    const pathCommands = points.map((p, i) => (i === 0 ? `M ${p.x} ${p.y}` : `L ${p.x} ${p.y}`));
    const path = pathCommands.join(' ');

    // Build area path
    const areaPath = [
      `M ${padding.left} ${padding.top + chartHeight}`,
      ...points.map((p) => `L ${p.x} ${p.y}`),
      `L ${padding.left + chartWidth} ${padding.top + chartHeight}`,
      'Z',
    ].join(' ');

    // Y-axis labels
    const yLabelCount = 5;
    const yLabels = Array.from({ length: yLabelCount }, (_, i) => {
      const value = minValue + (range * i) / (yLabelCount - 1);
      const y = padding.top + (1 - i / (yLabelCount - 1)) * chartHeight;
      return { value, y, label: formatValue(value) };
    });

    // X-axis labels (show subset)
    const xLabelCount = Math.min(data.length, 6);
    const step = Math.floor(data.length / xLabelCount);
    const xLabels = Array.from({ length: xLabelCount }, (_, i) => {
      const index = Math.min(i * step, data.length - 1);
      return {
        x: points[index]?.x || 0,
        label: formatLabel(data[index]?.timestamp || ''),
      };
    });

    return { path, areaPath, points, yLabels, xLabels, padding, chartHeight, chartWidth, width };
  }, [data, height, formatValue, formatLabel]);

  if (data.length === 0) {
    return (
      <div
        className={cn('flex items-center justify-center bg-surface-800/50 rounded-lg', className)}
        style={{ height }}
      >
        <p className="text-surface-500">No data available</p>
      </div>
    );
  }

  return (
    <svg
      viewBox={`0 0 ${chartData.width} ${height}`}
      className={cn('w-full', className)}
      style={{ height }}
    >
      {/* Grid lines */}
      {showGrid && (
        <g className="grid-lines">
          {chartData.yLabels.map((label, i) => (
            <line
              key={i}
              x1={chartData.padding.left}
              y1={label.y}
              x2={chartData.padding.left + chartData.chartWidth}
              y2={label.y}
              stroke="#374151"
              strokeDasharray="4,4"
            />
          ))}
        </g>
      )}

      {/* Area fill */}
      {showArea && <path d={chartData.areaPath} fill={fillColor} />}

      {/* Line */}
      <path
        d={chartData.path}
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Dots */}
      {showDots &&
        chartData.points.map((point, i) => (
          <circle
            key={i}
            cx={point.x}
            cy={point.y}
            r="4"
            fill={color}
            stroke="#1f2937"
            strokeWidth="2"
          />
        ))}

      {/* Y-axis labels */}
      {chartData.yLabels.map((label, i) => (
        <text
          key={i}
          x={chartData.padding.left - 10}
          y={label.y + 4}
          textAnchor="end"
          fill="#9ca3af"
          fontSize="12"
        >
          {label.label}
        </text>
      ))}

      {/* X-axis labels */}
      {chartData.xLabels.map((label, i) => (
        <text key={i} x={label.x} y={height - 10} textAnchor="middle" fill="#9ca3af" fontSize="11">
          {label.label}
        </text>
      ))}
    </svg>
  );
}

// Bar chart component
interface BarChartProps {
  data: DataPoint[];
  height?: number;
  barColor?: string;
  showValues?: boolean;
  horizontal?: boolean;
  className?: string;
}

export function BarChart({
  data,
  height = 200,
  barColor = '#8b5cf6',
  showValues = true,
  horizontal = false,
  className,
}: BarChartProps) {
  const chartData = useMemo(() => {
    if (data.length === 0) return { bars: [], maxValue: 0 };

    const maxValue = Math.max(...data.map((d) => d.value));
    const bars = data.map((d, i) => ({
      ...d,
      percentage: maxValue > 0 ? (d.value / maxValue) * 100 : 0,
      index: i,
    }));

    return { bars, maxValue };
  }, [data]);

  if (data.length === 0) {
    return (
      <div
        className={cn('flex items-center justify-center bg-surface-800/50 rounded-lg', className)}
        style={{ height }}
      >
        <p className="text-surface-500">No data available</p>
      </div>
    );
  }

  if (horizontal) {
    return (
      <div className={cn('space-y-3', className)}>
        {chartData.bars.map((bar) => (
          <div key={bar.index}>
            <div className="flex justify-between text-sm mb-1">
              <span className="text-surface-300">{bar.label}</span>
              {showValues && <span className="text-surface-400">{bar.value}</span>}
            </div>
            <div className="h-6 bg-surface-800 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${bar.percentage}%`,
                  backgroundColor: bar.color || barColor,
                }}
              />
            </div>
          </div>
        ))}
      </div>
    );
  }

  const padding = { top: 20, right: 20, bottom: 40, left: 20 };
  const width = 600;
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;
  const barWidth = chartWidth / data.length - 10;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className={cn('w-full', className)} style={{ height }}>
      {chartData.bars.map((bar) => {
        const barHeight = (bar.percentage / 100) * chartHeight;
        const x = padding.left + bar.index * (barWidth + 10) + 5;
        const y = padding.top + chartHeight - barHeight;

        return (
          <g key={bar.index}>
            {/* Bar */}
            <rect
              x={x}
              y={y}
              width={barWidth}
              height={barHeight}
              fill={bar.color || barColor}
              rx="4"
            />
            {/* Value label */}
            {showValues && (
              <text x={x + barWidth / 2} y={y - 8} textAnchor="middle" fill="#9ca3af" fontSize="12">
                {bar.value}
              </text>
            )}
            {/* X-axis label */}
            <text
              x={x + barWidth / 2}
              y={height - 10}
              textAnchor="middle"
              fill="#9ca3af"
              fontSize="11"
            >
              {bar.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

// Donut/Pie chart component
interface DonutChartProps {
  data: DataPoint[];
  size?: number;
  strokeWidth?: number;
  showLegend?: boolean;
  centerLabel?: string;
  centerValue?: string;
  className?: string;
}

export function DonutChart({
  data,
  size = 200,
  strokeWidth = 24,
  showLegend = true,
  centerLabel,
  centerValue,
  className,
}: DonutChartProps) {
  const chartData = useMemo(() => {
    const total = data.reduce((sum, d) => sum + d.value, 0);
    if (total === 0) return { segments: [], total: 0 };

    const radius = (size - strokeWidth) / 2;
    const circumference = 2 * Math.PI * radius;
    const center = size / 2;

    let currentAngle = -90; // Start at top
    const segments = data.map((d, i) => {
      const percentage = d.value / total;
      const angle = percentage * 360;
      const startAngle = currentAngle;
      currentAngle += angle;

      // Calculate dash array for this segment
      const dashLength = percentage * circumference;
      const dashOffset = circumference - dashLength + (i > 0 ? 0 : circumference * 0.25);

      // Calculate rotation to position segment correctly
      const rotation =
        i === 0 ? 0 : data.slice(0, i).reduce((sum, d) => sum + (d.value / total) * 360, 0);

      return {
        ...d,
        percentage: percentage * 100,
        dashArray: `${dashLength} ${circumference - dashLength}`,
        rotation,
        color: d.color || getDefaultColor(i),
      };
    });

    return { segments, total, radius, circumference, center };
  }, [data, size, strokeWidth]);

  if (data.length === 0) {
    return (
      <div
        className={cn('flex items-center justify-center bg-surface-800/50 rounded-lg', className)}
        style={{ height: size }}
      >
        <p className="text-surface-500">No data available</p>
      </div>
    );
  }

  return (
    <div className={cn('flex items-center gap-6', className)}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {/* Background circle */}
        <circle
          cx={chartData.center}
          cy={chartData.center}
          r={chartData.radius}
          fill="none"
          stroke="#374151"
          strokeWidth={strokeWidth}
        />

        {/* Segments */}
        {chartData.segments.map((segment, i) => (
          <circle
            key={i}
            cx={chartData.center}
            cy={chartData.center}
            r={chartData.radius}
            fill="none"
            stroke={segment.color}
            strokeWidth={strokeWidth}
            strokeDasharray={segment.dashArray}
            strokeLinecap="round"
            transform={`rotate(${segment.rotation - 90} ${chartData.center} ${chartData.center})`}
            className="transition-all duration-500"
          />
        ))}

        {/* Center text */}
        {(centerLabel || centerValue) && (
          <g>
            {centerValue && (
              <text
                x={chartData.center}
                y={chartData.center - (centerLabel ? 8 : 0)}
                textAnchor="middle"
                fill="white"
                fontSize="24"
                fontWeight="bold"
              >
                {centerValue}
              </text>
            )}
            {centerLabel && (
              <text
                x={chartData.center}
                y={chartData.center + 16}
                textAnchor="middle"
                fill="#9ca3af"
                fontSize="12"
              >
                {centerLabel}
              </text>
            )}
          </g>
        )}
      </svg>

      {/* Legend */}
      {showLegend && (
        <div className="space-y-2">
          {chartData.segments.map((segment, i) => (
            <div key={i} className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: segment.color }} />
              <span className="text-sm text-surface-300">{segment.label}</span>
              <span className="text-sm text-surface-500">({segment.percentage.toFixed(1)}%)</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Sparkline component (mini line chart)
interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
  showDot?: boolean;
  className?: string;
}

export function Sparkline({
  data,
  width = 100,
  height = 30,
  color = '#8b5cf6',
  showDot = true,
  className,
}: SparklineProps) {
  const path = useMemo(() => {
    if (data.length < 2) return '';

    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;
    const padding = 2;

    const points = data.map((value, i) => ({
      x: padding + (i / (data.length - 1)) * (width - 2 * padding),
      y: padding + (1 - (value - min) / range) * (height - 2 * padding),
    }));

    return points.map((p, i) => (i === 0 ? `M ${p.x} ${p.y}` : `L ${p.x} ${p.y}`)).join(' ');
  }, [data, width, height]);

  const lastPoint = useMemo(() => {
    if (data.length < 2) return null;
    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;
    const padding = 2;
    const value = data[data.length - 1];
    return {
      x: width - padding,
      y: padding + (1 - (value - min) / range) * (height - 2 * padding),
    };
  }, [data, width, height]);

  if (data.length < 2) return null;

  return (
    <svg width={width} height={height} className={className}>
      <path
        d={path}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {showDot && lastPoint && <circle cx={lastPoint.x} cy={lastPoint.y} r="3" fill={color} />}
    </svg>
  );
}

// Progress ring component
interface ProgressRingProps {
  value: number;
  max?: number;
  size?: number;
  strokeWidth?: number;
  color?: string;
  backgroundColor?: string;
  showValue?: boolean;
  label?: string;
  className?: string;
}

export function ProgressRing({
  value,
  max = 100,
  size = 80,
  strokeWidth = 8,
  color = '#8b5cf6',
  backgroundColor = '#374151',
  showValue = true,
  label,
  className,
}: ProgressRingProps) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const percentage = Math.min(100, (value / max) * 100);
  const dashOffset = circumference - (percentage / 100) * circumference;
  const center = size / 2;

  return (
    <svg width={size} height={size} className={className}>
      {/* Background circle */}
      <circle
        cx={center}
        cy={center}
        r={radius}
        fill="none"
        stroke={backgroundColor}
        strokeWidth={strokeWidth}
      />
      {/* Progress circle */}
      <circle
        cx={center}
        cy={center}
        r={radius}
        fill="none"
        stroke={color}
        strokeWidth={strokeWidth}
        strokeDasharray={circumference}
        strokeDashoffset={dashOffset}
        strokeLinecap="round"
        transform={`rotate(-90 ${center} ${center})`}
        className="transition-all duration-500"
      />
      {/* Center text */}
      {showValue && (
        <text
          x={center}
          y={center + (label ? -4 : 4)}
          textAnchor="middle"
          fill="white"
          fontSize={size / 5}
          fontWeight="bold"
        >
          {percentage.toFixed(0)}%
        </text>
      )}
      {label && (
        <text x={center} y={center + 12} textAnchor="middle" fill="#9ca3af" fontSize={size / 8}>
          {label}
        </text>
      )}
    </svg>
  );
}

// Helper function for default colors
function getDefaultColor(index: number): string {
  const colors = [
    '#8b5cf6', // purple
    '#3b82f6', // blue
    '#22c55e', // green
    '#f59e0b', // amber
    '#ef4444', // red
    '#ec4899', // pink
    '#06b6d4', // cyan
    '#f97316', // orange
  ];
  return colors[index % colors.length];
}
