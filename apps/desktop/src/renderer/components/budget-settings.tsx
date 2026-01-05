/**
 * Budget Settings component.
 * Allows users to configure spending limits and alert thresholds.
 */

import { useState, useEffect } from 'react';
import {
  DollarSign,
  AlertTriangle,
  Check,
  Info,
  Loader2,
} from 'lucide-react';
import { cn } from '../lib/utils';

interface BudgetSettingsProps {
  currentBudgetLimit: number | null;
  currentPeriodDays: number;
  currentSpent: number;
  onSave: (limit: number | null, periodDays: number) => Promise<void>;
  isSaving?: boolean;
}

// Period options
const periodOptions = [
  { value: 7, label: '7 days' },
  { value: 14, label: '14 days' },
  { value: 30, label: '30 days' },
  { value: 90, label: '90 days' },
];

export function BudgetSettings({
  currentBudgetLimit,
  currentPeriodDays,
  currentSpent,
  onSave,
  isSaving = false,
}: BudgetSettingsProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [budgetLimit, setBudgetLimit] = useState<string>(
    currentBudgetLimit?.toString() || ''
  );
  const [periodDays, setPeriodDays] = useState<number>(currentPeriodDays);
  const [hasChanges, setHasChanges] = useState(false);

  // Update local state when props change
  useEffect(() => {
    setBudgetLimit(currentBudgetLimit?.toString() || '');
    setPeriodDays(currentPeriodDays);
  }, [currentBudgetLimit, currentPeriodDays]);

  // Calculate budget usage
  const budgetUsagePercent = currentBudgetLimit
    ? Math.min((currentSpent / currentBudgetLimit) * 100, 100)
    : 0;

  const isNearBudget = budgetUsagePercent >= 80;
  const isOverBudget = budgetUsagePercent >= 100;

  const handleLimitChange = (value: string) => {
    // Allow empty or valid numbers
    if (value === '' || /^\d*\.?\d*$/.test(value)) {
      setBudgetLimit(value);
      setHasChanges(true);
    }
  };

  const handlePeriodChange = (value: number) => {
    setPeriodDays(value);
    setHasChanges(true);
  };

  const handleSave = async () => {
    const limit = budgetLimit ? parseFloat(budgetLimit) : null;
    await onSave(limit, periodDays);
    setHasChanges(false);
    setIsEditing(false);
  };

  const handleCancel = () => {
    setBudgetLimit(currentBudgetLimit?.toString() || '');
    setPeriodDays(currentPeriodDays);
    setHasChanges(false);
    setIsEditing(false);
  };

  const handleRemoveBudget = async () => {
    await onSave(null, periodDays);
    setBudgetLimit('');
    setHasChanges(false);
    setIsEditing(false);
  };

  return (
    <div className="space-y-4">
      {/* Current Budget Status */}
      {currentBudgetLimit ? (
        <div
          className={cn(
            'p-4 rounded-lg border',
            isOverBudget
              ? 'bg-red-500/10 border-red-500/30'
              : isNearBudget
              ? 'bg-yellow-500/10 border-yellow-500/30'
              : 'bg-green-500/10 border-green-500/30'
          )}
        >
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <DollarSign
                className={cn(
                  'w-5 h-5',
                  isOverBudget
                    ? 'text-red-400'
                    : isNearBudget
                    ? 'text-yellow-400'
                    : 'text-green-400'
                )}
              />
              <span className="font-medium">Budget Status</span>
            </div>
            <div className="flex items-center gap-2">
              {isOverBudget && (
                <span className="flex items-center gap-1 text-xs text-red-400">
                  <AlertTriangle className="w-3 h-3" />
                  Over Budget
                </span>
              )}
              {isNearBudget && !isOverBudget && (
                <span className="flex items-center gap-1 text-xs text-yellow-400">
                  <AlertTriangle className="w-3 h-3" />
                  Near Limit
                </span>
              )}
              {!isNearBudget && (
                <span className="flex items-center gap-1 text-xs text-green-400">
                  <Check className="w-3 h-3" />
                  On Track
                </span>
              )}
            </div>
          </div>

          {/* Progress Bar */}
          <div className="mb-2">
            <div className="h-2 bg-surface-700 rounded-full overflow-hidden">
              <div
                className={cn(
                  'h-full rounded-full transition-all',
                  isOverBudget
                    ? 'bg-red-500'
                    : isNearBudget
                    ? 'bg-yellow-500'
                    : 'bg-green-500'
                )}
                style={{ width: `${budgetUsagePercent}%` }}
              />
            </div>
          </div>

          <div className="flex items-center justify-between text-sm">
            <span className="text-surface-400">
              ${currentSpent.toFixed(2)} / ${currentBudgetLimit.toFixed(2)}
            </span>
            <span
              className={cn(
                'font-medium',
                isOverBudget
                  ? 'text-red-400'
                  : isNearBudget
                  ? 'text-yellow-400'
                  : 'text-green-400'
              )}
            >
              {budgetUsagePercent.toFixed(0)}%
            </span>
          </div>

          <div className="text-xs text-surface-500 mt-2">
            Period: {currentPeriodDays} days
          </div>
        </div>
      ) : (
        <div className="p-4 bg-surface-800/50 rounded-lg border border-surface-700">
          <div className="flex items-center gap-2 text-surface-400">
            <Info className="w-5 h-5" />
            <span>No budget limit set. Set one below to receive alerts.</span>
          </div>
        </div>
      )}

      {/* Edit Controls */}
      {isEditing ? (
        <div className="space-y-4 p-4 bg-surface-800/50 rounded-lg">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-surface-400 mb-2">
                Budget Limit (USD)
              </label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-surface-400">
                  $
                </span>
                <input
                  type="text"
                  value={budgetLimit}
                  onChange={(e) => handleLimitChange(e.target.value)}
                  placeholder="e.g., 50.00"
                  className="w-full bg-surface-800 border border-surface-700 rounded-lg pl-7 pr-3 py-2 focus:outline-none focus:border-brand-500"
                />
              </div>
              <p className="text-xs text-surface-500 mt-1">
                Leave empty for no limit
              </p>
            </div>

            <div>
              <label className="block text-sm text-surface-400 mb-2">
                Budget Period
              </label>
              <select
                value={periodDays}
                onChange={(e) => handlePeriodChange(parseInt(e.target.value))}
                className="w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2 focus:outline-none focus:border-brand-500"
              >
                {periodOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex items-center gap-2 text-sm text-surface-400">
            <Info className="w-4 h-4" />
            <span>
              You'll receive alerts at 80% and 100% of your budget.
            </span>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            {currentBudgetLimit && (
              <button
                onClick={handleRemoveBudget}
                disabled={isSaving}
                className="px-3 py-1.5 text-sm text-red-400 hover:bg-red-500/10 rounded-lg transition-colors disabled:opacity-50"
              >
                Remove Limit
              </button>
            )}
            <button
              onClick={handleCancel}
              disabled={isSaving}
              className="px-3 py-1.5 text-sm bg-surface-700 hover:bg-surface-600 rounded-lg transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={isSaving || !hasChanges}
              className="px-3 py-1.5 text-sm bg-brand-500 hover:bg-brand-600 rounded-lg transition-colors disabled:opacity-50 flex items-center gap-1.5"
            >
              {isSaving ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Check className="w-4 h-4" />
              )}
              Save
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setIsEditing(true)}
          className="w-full px-4 py-2 bg-surface-700 hover:bg-surface-600 rounded-lg text-sm transition-colors text-left flex items-center justify-between"
        >
          <span>
            {currentBudgetLimit ? 'Change Budget Settings' : 'Set Budget Limit'}
          </span>
          <DollarSign className="w-4 h-4 text-surface-400" />
        </button>
      )}
    </div>
  );
}

// Compact budget alert banner for use in other pages
export function BudgetAlertBanner({
  budgetLimit,
  spent,
  periodDays,
  onDismiss,
}: {
  budgetLimit: number;
  spent: number;
  periodDays: number;
  onDismiss?: () => void;
}) {
  const usagePercent = (spent / budgetLimit) * 100;
  const isOver = usagePercent >= 100;
  const isNear = usagePercent >= 80;

  if (!isNear) return null;

  return (
    <div
      className={cn(
        'px-4 py-3 rounded-lg flex items-center justify-between',
        isOver ? 'bg-red-500/20 text-red-400' : 'bg-yellow-500/20 text-yellow-400'
      )}
    >
      <div className="flex items-center gap-3">
        <AlertTriangle className="w-5 h-5" />
        <div>
          <span className="font-medium">
            {isOver ? 'Budget Exceeded' : 'Approaching Budget Limit'}
          </span>
          <span className="text-sm opacity-80 ml-2">
            ${spent.toFixed(2)} / ${budgetLimit.toFixed(2)} ({usagePercent.toFixed(0)}%) in last{' '}
            {periodDays} days
          </span>
        </div>
      </div>
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="icon-btn p-2 hover:bg-white/10 rounded transition-colors"
          aria-label="Dismiss budget warning"
        >
          <span className="sr-only">Dismiss</span>
          &times;
        </button>
      )}
    </div>
  );
}
