/**
 * Provider Preferences Component
 *
 * Allows users to configure video generation provider routing,
 * set budget limits, and prioritize speed vs cost.
 */

import { useState, useCallback } from 'react';
import {
  GripVertical,
  Zap,
  DollarSign,
  AlertTriangle,
  Check,
  Cloud,
  Cpu,
  Power,
  PowerOff,
  Info,
} from 'lucide-react';
import { cn } from '../../lib/utils';

// Provider configuration
interface Provider {
  id: string;
  name: string;
  logo: string;
  description: string;
  costPerSecond: number;
  avgGenerationTime: number; // seconds
  isLocal: boolean;
  status: 'online' | 'offline' | 'degraded';
}

// Default providers
const DEFAULT_PROVIDERS: Provider[] = [
  {
    id: 'replicate',
    name: 'Replicate',
    logo: '🔁',
    description: 'MiniMax, Luma, Kling, SVD models',
    costPerSecond: 0.05,
    avgGenerationTime: 45,
    isLocal: false,
    status: 'online',
  },
  {
    id: 'fal',
    name: 'Fal.ai',
    logo: '⚡',
    description: 'CogVideoX, Hunyuan, LTX, AnimateDiff',
    costPerSecond: 0.04,
    avgGenerationTime: 35,
    isLocal: false,
    status: 'online',
  },
  {
    id: 'runpod',
    name: 'RunPod',
    logo: '🚀',
    description: 'Serverless GPU compute',
    costPerSecond: 0.03,
    avgGenerationTime: 60,
    isLocal: false,
    status: 'online',
  },
  {
    id: 'comfyui',
    name: 'ComfyUI (Local)',
    logo: '🖥️',
    description: 'Local GPU workflows',
    costPerSecond: 0,
    avgGenerationTime: 30,
    isLocal: true,
    status: 'offline',
  },
];

interface ProviderPreferencesProps {
  /**
   * Initial provider order
   */
  initialOrder?: string[];

  /**
   * Initial enabled providers
   */
  initialEnabled?: Record<string, boolean>;

  /**
   * Initial optimization preference (0 = cheapest, 1 = fastest)
   */
  initialOptimization?: number;

  /**
   * Initial monthly budget limit
   */
  initialBudgetLimit?: number;

  /**
   * Current month's spending
   */
  currentSpending?: number;

  /**
   * Called when preferences change
   */
  onChange?: (preferences: ProviderPreferences) => void;

  /**
   * CSS class name
   */
  className?: string;
}

export interface ProviderPreferences {
  providerOrder: string[];
  enabledProviders: Record<string, boolean>;
  optimization: number;
  budgetLimit: number;
}

export function ProviderPreferencesPanel({
  initialOrder = DEFAULT_PROVIDERS.map((p) => p.id),
  initialEnabled = Object.fromEntries(DEFAULT_PROVIDERS.map((p) => [p.id, !p.isLocal])),
  initialOptimization = 0.5,
  initialBudgetLimit = 100,
  currentSpending = 0,
  onChange,
  className,
}: ProviderPreferencesProps) {
  const [providerOrder, setProviderOrder] = useState<string[]>(initialOrder);
  const [enabledProviders, setEnabledProviders] = useState<Record<string, boolean>>(initialEnabled);
  const [optimization, setOptimization] = useState(initialOptimization);
  const [budgetLimit, setBudgetLimit] = useState(initialBudgetLimit);
  const [draggedProvider, setDraggedProvider] = useState<string | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);

  // Notify parent of changes
  const notifyChange = useCallback(
    (updates: Partial<ProviderPreferences>) => {
      onChange?.({
        providerOrder,
        enabledProviders,
        optimization,
        budgetLimit,
        ...updates,
      });
    },
    [providerOrder, enabledProviders, optimization, budgetLimit, onChange]
  );

  // Handle drag start
  const handleDragStart = (providerId: string) => {
    setDraggedProvider(providerId);
  };

  // Handle drag over
  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    setDragOverIndex(index);
  };

  // Handle drop
  const handleDrop = (dropIndex: number) => {
    if (!draggedProvider) return;

    const dragIndex = providerOrder.indexOf(draggedProvider);
    if (dragIndex === dropIndex) {
      setDraggedProvider(null);
      setDragOverIndex(null);
      return;
    }

    const newOrder = [...providerOrder];
    newOrder.splice(dragIndex, 1);
    newOrder.splice(dropIndex, 0, draggedProvider);

    setProviderOrder(newOrder);
    setDraggedProvider(null);
    setDragOverIndex(null);
    notifyChange({ providerOrder: newOrder });
  };

  // Toggle provider enabled state
  const toggleProvider = (providerId: string) => {
    const newEnabled = {
      ...enabledProviders,
      [providerId]: !enabledProviders[providerId],
    };
    setEnabledProviders(newEnabled);
    notifyChange({ enabledProviders: newEnabled });
  };

  // Handle optimization slider change
  const handleOptimizationChange = (value: number) => {
    setOptimization(value);
    notifyChange({ optimization: value });
  };

  // Handle budget limit change
  const handleBudgetChange = (value: number) => {
    setBudgetLimit(value);
    notifyChange({ budgetLimit: value });
  };

  // Calculate budget percentage
  const budgetPercentage = budgetLimit > 0 ? (currentSpending / budgetLimit) * 100 : 0;
  const isNearBudget = budgetPercentage >= 80;
  const isOverBudget = budgetPercentage >= 100;

  // Get provider by ID
  const getProvider = (id: string) => DEFAULT_PROVIDERS.find((p) => p.id === id);

  return (
    <div className={cn("space-y-6", className)}>
      {/* Section Header */}
      <div>
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <Cloud className="w-5 h-5 text-primary-400" />
          Provider Preferences
        </h3>
        <p className="text-sm text-surface-400 mt-1">
          Configure how video generation jobs are routed to providers.
        </p>
      </div>

      {/* Provider Priority List */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-surface-200 flex items-center gap-2">
          Provider Priority
          <span className="text-xs text-surface-500">(drag to reorder)</span>
        </label>

        <div className="space-y-2">
          {providerOrder.map((providerId, index) => {
            const provider = getProvider(providerId);
            if (!provider) return null;

            const isEnabled = enabledProviders[providerId] ?? false;
            const isDragging = draggedProvider === providerId;
            const isDropTarget = dragOverIndex === index;

            return (
              <div
                key={providerId}
                draggable
                onDragStart={() => handleDragStart(providerId)}
                onDragOver={(e) => handleDragOver(e, index)}
                onDrop={() => handleDrop(index)}
                onDragEnd={() => {
                  setDraggedProvider(null);
                  setDragOverIndex(null);
                }}
                className={cn(
                  "flex items-center gap-3 p-3 rounded-lg border transition-all",
                  "bg-surface-800 cursor-grab active:cursor-grabbing",
                  isDragging && "opacity-50 scale-95",
                  isDropTarget && "border-primary-500 bg-primary-500/10",
                  !isDropTarget && "border-surface-700 hover:border-surface-600"
                )}
              >
                {/* Drag handle */}
                <GripVertical className="w-4 h-4 text-surface-500 shrink-0" />

                {/* Priority number */}
                <span className="w-6 h-6 flex items-center justify-center rounded-full bg-surface-700 text-xs font-medium text-surface-300">
                  {index + 1}
                </span>

                {/* Provider logo */}
                <span className="text-xl">{provider.logo}</span>

                {/* Provider info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-white">{provider.name}</span>
                    {provider.isLocal && (
                      <span className="text-xs px-1.5 py-0.5 rounded bg-surface-700 text-surface-400">
                        <Cpu className="w-3 h-3 inline mr-1" />
                        Local
                      </span>
                    )}
                    {/* Status indicator */}
                    <span
                      className={cn(
                        "w-2 h-2 rounded-full",
                        provider.status === 'online' && "bg-green-400",
                        provider.status === 'degraded' && "bg-yellow-400",
                        provider.status === 'offline' && "bg-red-400"
                      )}
                      title={provider.status}
                    />
                  </div>
                  <div className="text-xs text-surface-400 truncate">
                    {provider.description}
                  </div>
                </div>

                {/* Cost and time info */}
                <div className="text-right text-xs text-surface-400 shrink-0">
                  <div>${provider.costPerSecond.toFixed(3)}/sec</div>
                  <div>~{provider.avgGenerationTime}s avg</div>
                </div>

                {/* Enable/Disable toggle */}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleProvider(providerId);
                  }}
                  className={cn(
                    "p-2 rounded-lg transition-colors",
                    isEnabled
                      ? "bg-green-500/20 text-green-400 hover:bg-green-500/30"
                      : "bg-surface-700 text-surface-500 hover:bg-surface-600"
                  )}
                  title={isEnabled ? 'Disable provider' : 'Enable provider'}
                >
                  {isEnabled ? (
                    <Power className="w-4 h-4" />
                  ) : (
                    <PowerOff className="w-4 h-4" />
                  )}
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* Optimization Preference */}
      <div className="space-y-3">
        <label className="text-sm font-medium text-surface-200 flex items-center gap-2">
          Optimization Preference
          <button
            type="button"
            className="p-1 hover:bg-surface-700 rounded"
            title="This affects how jobs are routed when multiple providers are available"
          >
            <Info className="w-3 h-3 text-surface-500" />
          </button>
        </label>

        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs text-surface-400">
            <span className="flex items-center gap-1">
              <DollarSign className="w-3 h-3" />
              Cheapest
            </span>
            <span className="flex items-center gap-1">
              <Zap className="w-3 h-3" />
              Fastest
            </span>
          </div>

          <input
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={optimization}
            onChange={(e) => handleOptimizationChange(parseFloat(e.target.value))}
            className={cn(
              "w-full h-2 rounded-full appearance-none cursor-pointer",
              "bg-gradient-to-r from-green-500 via-yellow-500 to-orange-500",
              "[&::-webkit-slider-thumb]:appearance-none",
              "[&::-webkit-slider-thumb]:w-4",
              "[&::-webkit-slider-thumb]:h-4",
              "[&::-webkit-slider-thumb]:rounded-full",
              "[&::-webkit-slider-thumb]:bg-white",
              "[&::-webkit-slider-thumb]:shadow-lg",
              "[&::-webkit-slider-thumb]:cursor-grab",
              "[&::-webkit-slider-thumb]:active:cursor-grabbing"
            )}
          />

          <div className="text-center text-sm text-surface-300">
            {optimization < 0.3
              ? 'Prioritizing lowest cost'
              : optimization > 0.7
              ? 'Prioritizing fastest speed'
              : 'Balanced approach'}
          </div>
        </div>
      </div>

      {/* Budget Limit */}
      <div className="space-y-3">
        <label className="text-sm font-medium text-surface-200">
          Monthly Budget Limit
        </label>

        <div className="flex items-center gap-3">
          <span className="text-surface-400">$</span>
          <input
            type="number"
            min="0"
            step="10"
            value={budgetLimit}
            onChange={(e) => handleBudgetChange(Math.max(0, parseFloat(e.target.value) || 0))}
            className={cn(
              "flex-1 px-3 py-2 rounded-lg",
              "bg-surface-800 border border-surface-700",
              "text-white placeholder-surface-500",
              "focus:outline-none focus:ring-2 focus:ring-primary-500/50"
            )}
            placeholder="100"
          />
          <span className="text-surface-400">/month</span>
        </div>

        {/* Budget usage bar */}
        <div className="space-y-1">
          <div className="flex items-center justify-between text-xs">
            <span className="text-surface-400">
              Current: ${currentSpending.toFixed(2)}
            </span>
            <span
              className={cn(
                isOverBudget && "text-red-400",
                isNearBudget && !isOverBudget && "text-yellow-400",
                !isNearBudget && "text-surface-400"
              )}
            >
              {budgetPercentage.toFixed(0)}% used
            </span>
          </div>

          <div className="h-2 bg-surface-700 rounded-full overflow-hidden">
            <div
              className={cn(
                "h-full rounded-full transition-all",
                isOverBudget && "bg-red-500",
                isNearBudget && !isOverBudget && "bg-yellow-500",
                !isNearBudget && "bg-primary-500"
              )}
              style={{ width: `${Math.min(100, budgetPercentage)}%` }}
            />
          </div>

          {/* Budget warnings */}
          {isOverBudget && (
            <div className="flex items-center gap-2 text-xs text-red-400 mt-2">
              <AlertTriangle className="w-3 h-3" />
              Budget exceeded! Generation disabled until next month.
            </div>
          )}
          {isNearBudget && !isOverBudget && (
            <div className="flex items-center gap-2 text-xs text-yellow-400 mt-2">
              <AlertTriangle className="w-3 h-3" />
              Approaching budget limit. Consider increasing or slowing down.
            </div>
          )}
        </div>
      </div>

      {/* Save indicator */}
      <div className="flex items-center gap-2 text-xs text-surface-500">
        <Check className="w-3 h-3" />
        Changes are saved automatically
      </div>
    </div>
  );
}

export default ProviderPreferencesPanel;
