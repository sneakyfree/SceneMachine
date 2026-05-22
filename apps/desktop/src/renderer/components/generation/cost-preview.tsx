/**
 * Cost Preview Component
 *
 * Displays estimated generation cost before starting a job.
 * Shows provider, cost breakdown, and estimated time.
 */

import { useState } from 'react';
import {
  DollarSign,
  Clock,
  Cloud,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  Info,
  Zap,
} from 'lucide-react';
import { cn } from '../../lib/utils';

export interface CostEstimate {
  provider: string;
  providerLogo?: string;
  costPerSecond: number;
  estimatedDuration: number; // seconds
  totalCost: number;
  estimatedTime: number; // seconds to generate
  confidence: 'high' | 'medium' | 'low';
}

export interface CostBreakdownItem {
  label: string;
  value: number;
  unit: string;
  description?: string;
}

interface CostPreviewProps {
  /**
   * Single cost estimate for one job
   */
  estimate?: CostEstimate;

  /**
   * Multiple estimates for batch operations
   */
  batchEstimates?: CostEstimate[];

  /**
   * Cost breakdown details
   */
  breakdown?: CostBreakdownItem[];

  /**
   * Current budget remaining
   */
  budgetRemaining?: number;

  /**
   * Whether to require confirmation
   */
  requireConfirmation?: boolean;

  /**
   * Called when user confirms cost
   */
  onConfirm?: () => void;

  /**
   * Called when user cancels
   */
  onCancel?: () => void;

  /**
   * Loading state
   */
  isLoading?: boolean;

  /**
   * CSS class name
   */
  className?: string;
}

function formatCost(cost: number): string {
  if (cost < 0.01) return `$${cost.toFixed(4)}`;
  if (cost < 1) return `$${cost.toFixed(3)}`;
  return `$${cost.toFixed(2)}`;
}

function formatTime(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`;
  }
  const hours = Math.floor(seconds / 3600);
  const mins = Math.round((seconds % 3600) / 60);
  return `${hours}h ${mins}m`;
}

export function CostPreview({
  estimate,
  batchEstimates,
  breakdown,
  budgetRemaining,
  requireConfirmation = true,
  onConfirm,
  onCancel,
  isLoading = false,
  className,
}: CostPreviewProps) {
  const [showBreakdown, setShowBreakdown] = useState(false);

  // Calculate totals for batch
  const estimates = batchEstimates || (estimate ? [estimate] : []);
  const totalCost = estimates.reduce((sum, e) => sum + e.totalCost, 0);
  const totalTime = estimates.reduce((sum, e) => sum + e.estimatedTime, 0);
  const isBatch = estimates.length > 1;

  // Check if over budget
  const isOverBudget = budgetRemaining !== undefined && totalCost > budgetRemaining;

  // Get primary provider
  const primaryProvider = estimates[0]?.provider || 'Unknown';
  const primaryLogo = estimates[0]?.providerLogo;

  if (estimates.length === 0) {
    return null;
  }

  return (
    <div
      className={cn(
        'rounded-lg border bg-surface-800/50 backdrop-blur-sm',
        isOverBudget ? 'border-red-500/50' : 'border-surface-700',
        className
      )}
    >
      {/* Header */}
      <div className="px-4 py-3 border-b border-surface-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <DollarSign className="w-4 h-4 text-primary-400" />
            <span className="font-medium text-white">
              {isBatch ? 'Batch Cost Estimate' : 'Cost Estimate'}
            </span>
          </div>
          {isBatch && (
            <span className="text-xs px-2 py-0.5 rounded bg-surface-700 text-surface-300">
              {estimates.length} jobs
            </span>
          )}
        </div>
      </div>

      {/* Main estimate */}
      <div className="p-4 space-y-4">
        {/* Cost and time summary */}
        <div className="grid grid-cols-2 gap-4">
          {/* Total cost */}
          <div className="space-y-1">
            <div className="text-xs text-surface-400 uppercase tracking-wide">Estimated Cost</div>
            <div className="flex items-baseline gap-1">
              <span
                className={cn('text-2xl font-bold', isOverBudget ? 'text-red-400' : 'text-white')}
              >
                {formatCost(totalCost)}
              </span>
              {isBatch && (
                <span className="text-xs text-surface-500">
                  ({formatCost(totalCost / estimates.length)} avg)
                </span>
              )}
            </div>
          </div>

          {/* Estimated time */}
          <div className="space-y-1">
            <div className="text-xs text-surface-400 uppercase tracking-wide">Est. Time</div>
            <div className="flex items-baseline gap-1">
              <Clock className="w-4 h-4 text-surface-400" />
              <span className="text-2xl font-bold text-white">{formatTime(totalTime)}</span>
            </div>
          </div>
        </div>

        {/* Provider info */}
        <div className="flex items-center gap-3 p-3 rounded-lg bg-surface-900/50">
          {primaryLogo ? (
            <span className="text-xl">{primaryLogo}</span>
          ) : (
            <Cloud className="w-5 h-5 text-surface-400" />
          )}
          <div className="flex-1">
            <div className="text-sm font-medium text-white">{primaryProvider}</div>
            <div className="text-xs text-surface-400">
              {formatCost(estimates[0]?.costPerSecond || 0)}/sec
            </div>
          </div>
          {estimates[0]?.confidence && (
            <span
              className={cn(
                'text-xs px-2 py-0.5 rounded',
                estimates[0].confidence === 'high' && 'bg-green-500/20 text-green-400',
                estimates[0].confidence === 'medium' && 'bg-yellow-500/20 text-yellow-400',
                estimates[0].confidence === 'low' && 'bg-red-500/20 text-red-400'
              )}
            >
              {estimates[0].confidence} confidence
            </span>
          )}
        </div>

        {/* Budget warning */}
        {isOverBudget && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/30">
            <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
            <div className="text-sm text-red-300">
              This exceeds your remaining budget of {formatCost(budgetRemaining!)}. Generation will
              be blocked.
            </div>
          </div>
        )}

        {/* Breakdown toggle */}
        {breakdown && breakdown.length > 0 && (
          <button
            onClick={() => setShowBreakdown(!showBreakdown)}
            className={cn(
              'w-full flex items-center justify-between px-3 py-2 rounded-lg',
              'bg-surface-700/50 hover:bg-surface-700 transition-colors',
              'text-sm text-surface-300'
            )}
          >
            <span className="flex items-center gap-2">
              <Info className="w-4 h-4" />
              Cost Breakdown
            </span>
            {showBreakdown ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </button>
        )}

        {/* Breakdown details */}
        {showBreakdown && breakdown && (
          <div className="space-y-2 animate-in slide-in-from-top-2 duration-200">
            {breakdown.map((item, index) => (
              <div
                key={index}
                className="flex items-center justify-between text-sm px-3 py-2 rounded bg-surface-900/30"
              >
                <div>
                  <span className="text-surface-300">{item.label}</span>
                  {item.description && (
                    <p className="text-xs text-surface-500">{item.description}</p>
                  )}
                </div>
                <span className="text-white font-mono">
                  {item.value.toFixed(2)} {item.unit}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Batch job list */}
        {isBatch && estimates.length <= 5 && (
          <div className="space-y-2">
            <div className="text-xs text-surface-400 uppercase tracking-wide">Individual Jobs</div>
            {estimates.map((est, index) => (
              <div
                key={index}
                className="flex items-center justify-between text-sm px-3 py-2 rounded bg-surface-900/30"
              >
                <span className="text-surface-300">Job {index + 1}</span>
                <div className="flex items-center gap-4 text-surface-400">
                  <span>{formatCost(est.totalCost)}</span>
                  <span>{formatTime(est.estimatedTime)}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Confirmation footer */}
      {requireConfirmation && (
        <div className="px-4 py-3 border-t border-surface-700 flex items-center justify-end gap-3">
          <button
            onClick={onCancel}
            className={cn(
              'px-4 py-2 rounded-lg text-sm font-medium',
              'bg-surface-700 text-surface-200',
              'hover:bg-surface-600 transition-colors'
            )}
            disabled={isLoading}
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isLoading || isOverBudget}
            className={cn(
              'px-4 py-2 rounded-lg text-sm font-medium',
              'bg-primary-500 text-white',
              'hover:bg-primary-600 transition-colors',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              'flex items-center gap-2'
            )}
          >
            {isLoading ? (
              <>
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Starting...
              </>
            ) : (
              <>
                <Zap className="w-4 h-4" />
                Confirm & Generate
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
}

export default CostPreview;
