/**
 * Model Selector component.
 *
 * Allows users to select a specific AI model from a provider
 * for video generation. Shows model info, cost, and capabilities.
 */

import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  ChevronDown,
  Info,
  Zap,
  Clock,
  DollarSign,
  Film,
  Image,
  Loader2,
  AlertCircle,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { api, type ProviderModel } from '../api/client';

interface ModelSelectorProps {
  providerId: string;
  selectedModel: string | null;
  onModelSelect: (modelId: string) => void;
  disabled?: boolean;
  compact?: boolean;
  showCost?: boolean;
}

export function ModelSelector({
  providerId,
  selectedModel,
  onModelSelect,
  disabled = false,
  compact = false,
  showCost = true,
}: ModelSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);

  // Fetch models for the provider
  const {
    data: models,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['provider-models', providerId],
    queryFn: () => api.getProviderModels(providerId),
    enabled: !!providerId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Find the currently selected model
  const currentModel = models?.find((m) => m.id === selectedModel);

  // Auto-select first model if none selected
  useEffect(() => {
    if (models && models.length > 0 && !selectedModel) {
      onModelSelect(models[0].id);
    }
  }, [models, selectedModel, onModelSelect]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = () => setIsOpen(false);
    if (isOpen) {
      document.addEventListener('click', handleClickOutside);
      return () => document.removeEventListener('click', handleClickOutside);
    }
  }, [isOpen]);

  if (isLoading) {
    return (
      <div
        className={cn(
          'flex items-center gap-2 px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg',
          compact && 'px-2 py-1.5 text-sm'
        )}
      >
        <Loader2 className="w-4 h-4 animate-spin text-surface-500" />
        <span className="text-surface-500">Loading models...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className={cn(
          'flex items-center gap-2 px-3 py-2 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400',
          compact && 'px-2 py-1.5 text-sm'
        )}
      >
        <AlertCircle className="w-4 h-4" />
        <span>Failed to load models</span>
      </div>
    );
  }

  if (!models || models.length === 0) {
    return (
      <div
        className={cn(
          'flex items-center gap-2 px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg text-surface-500',
          compact && 'px-2 py-1.5 text-sm'
        )}
      >
        <Info className="w-4 h-4" />
        <span>No models available</span>
      </div>
    );
  }

  return (
    <div className="relative">
      {/* Selected Model Button */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          if (!disabled) setIsOpen(!isOpen);
        }}
        disabled={disabled}
        className={cn(
          'w-full flex items-center justify-between gap-2 px-3 py-2',
          'bg-surface-800 border border-surface-700 rounded-lg',
          'hover:border-surface-600 transition-colors',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          compact && 'px-2 py-1.5'
        )}
      >
        <div className="flex items-center gap-2 min-w-0">
          <Zap
            className={cn('w-4 h-4 shrink-0', currentModel ? 'text-brand-400' : 'text-surface-500')}
          />
          <div className="text-left min-w-0">
            <div className={cn('font-medium truncate', compact ? 'text-sm' : 'text-base')}>
              {currentModel?.name || 'Select model'}
            </div>
            {showCost && currentModel && !compact && (
              <div className="text-xs text-surface-500">
                ${currentModel.cost_per_second.toFixed(4)}/sec
              </div>
            )}
          </div>
        </div>
        <ChevronDown
          className={cn(
            'w-4 h-4 shrink-0 text-surface-500 transition-transform',
            isOpen && 'rotate-180'
          )}
        />
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute z-50 w-full mt-1 bg-surface-900 border border-surface-700 rounded-lg shadow-xl overflow-hidden">
          <div className="max-h-64 overflow-y-auto">
            {models.map((model) => (
              <ModelOption
                key={model.id}
                model={model}
                isSelected={model.id === selectedModel}
                onClick={() => {
                  onModelSelect(model.id);
                  setIsOpen(false);
                }}
                showCost={showCost}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

interface ModelOptionProps {
  model: ProviderModel;
  isSelected: boolean;
  onClick: () => void;
  showCost: boolean;
}

function ModelOption({ model, isSelected, onClick, showCost }: ModelOptionProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full flex items-start gap-3 px-3 py-2.5 text-left transition-colors',
        isSelected ? 'bg-brand-500/20 text-brand-300' : 'hover:bg-surface-800'
      )}
    >
      <Zap
        className={cn(
          'w-4 h-4 mt-0.5 shrink-0',
          isSelected ? 'text-brand-400' : 'text-surface-500'
        )}
      />
      <div className="flex-1 min-w-0">
        <div className="font-medium">{model.name}</div>
        <div className="flex flex-wrap gap-x-3 gap-y-1 mt-1 text-xs text-surface-400">
          {showCost && (
            <span className="flex items-center gap-1">
              <DollarSign className="w-3 h-3" />${model.cost_per_second.toFixed(4)}/sec
            </span>
          )}
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            Max {model.max_duration}s
          </span>
          {model.supports_text_to_video && (
            <span className="flex items-center gap-1 text-green-400">
              <Film className="w-3 h-3" />
              Text→Video
            </span>
          )}
          {model.supports_image_to_video && (
            <span className="flex items-center gap-1 text-blue-400">
              <Image className="w-3 h-3" />
              Img→Video
            </span>
          )}
        </div>
      </div>
    </button>
  );
}

/**
 * Compact model badge for displaying selected model info.
 */
export function ModelBadge({
  model,
  showCost = true,
}: {
  model?: ProviderModel | null;
  showCost?: boolean;
}) {
  if (!model) return null;

  return (
    <div className="inline-flex items-center gap-1.5 px-2 py-1 bg-surface-800 rounded text-xs">
      <Zap className="w-3 h-3 text-brand-400" />
      <span className="text-surface-200">{model.name}</span>
      {showCost && <span className="text-surface-500">${model.cost_per_second.toFixed(3)}/s</span>}
    </div>
  );
}
