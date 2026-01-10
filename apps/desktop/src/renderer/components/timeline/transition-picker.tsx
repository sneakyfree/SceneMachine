/**
 * Transition Picker Component
 *
 * Allows users to select transition types between clips.
 * Supports Cut (instant), Fade, and Crossfade transitions.
 */

import { useState, useRef, useEffect } from 'react';
import { Scissors, Blend, Sparkles, ChevronDown, Check } from 'lucide-react';
import { cn } from '../../lib/utils';

export type TransitionType = 'cut' | 'fade' | 'crossfade';

export interface TransitionConfig {
  type: TransitionType;
  duration: number; // in seconds
}

interface TransitionPickerProps {
  currentTransition: TransitionConfig;
  onChange: (transition: TransitionConfig) => void;
  className?: string;
}

const TRANSITION_OPTIONS: {
  type: TransitionType;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  durations: number[];
}[] = [
  {
    type: 'cut',
    label: 'Cut',
    icon: Scissors,
    durations: [0] // Instant cut has no duration
  },
  {
    type: 'fade',
    label: 'Fade',
    icon: Sparkles,
    durations: [0.5, 1, 2]
  },
  {
    type: 'crossfade',
    label: 'Crossfade',
    icon: Blend,
    durations: [0.5, 1, 2]
  },
];

function formatDuration(seconds: number): string {
  if (seconds === 0) return 'Instant';
  if (seconds < 1) return `${seconds * 1000}ms`;
  return `${seconds}s`;
}

export function TransitionPicker({ currentTransition, onChange, className }: TransitionPickerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedType, setSelectedType] = useState<TransitionType>(currentTransition.type);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen]);

  // Close on Escape key
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [isOpen]);

  const currentOption = TRANSITION_OPTIONS.find(opt => opt.type === currentTransition.type);
  const CurrentIcon = currentOption?.icon || Scissors;

  const handleTypeSelect = (type: TransitionType) => {
    setSelectedType(type);
    const option = TRANSITION_OPTIONS.find(opt => opt.type === type);
    if (option) {
      if (type === 'cut') {
        onChange({ type, duration: 0 });
        setIsOpen(false);
      } else if (option.durations.length === 1) {
        onChange({ type, duration: option.durations[0] });
        setIsOpen(false);
      }
      // If multiple durations, keep dropdown open for duration selection
    }
  };

  const handleDurationSelect = (duration: number) => {
    onChange({ type: selectedType, duration });
    setIsOpen(false);
  };

  return (
    <div className={cn("relative", className)} ref={dropdownRef}>
      {/* Trigger button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "flex items-center gap-1 px-2 py-1 rounded text-xs",
          "bg-surface-700 hover:bg-surface-600 transition-colors",
          "focus:outline-none focus:ring-2 focus:ring-primary-500/50",
          isOpen && "ring-2 ring-primary-500/50"
        )}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        title={`Transition: ${currentOption?.label} ${currentTransition.duration > 0 ? formatDuration(currentTransition.duration) : ''}`}
      >
        <CurrentIcon className="w-3 h-3 text-surface-300" />
        <span className="text-surface-200">{currentOption?.label}</span>
        {currentTransition.duration > 0 && (
          <span className="text-surface-400">{formatDuration(currentTransition.duration)}</span>
        )}
        <ChevronDown className={cn(
          "w-3 h-3 text-surface-400 transition-transform",
          isOpen && "rotate-180"
        )} />
      </button>

      {/* Dropdown menu */}
      {isOpen && (
        <div
          className={cn(
            "absolute z-50 mt-1 w-48 rounded-lg shadow-lg",
            "bg-surface-800 border border-surface-600",
            "py-1 animate-in fade-in-0 zoom-in-95 duration-100"
          )}
          role="listbox"
        >
          {TRANSITION_OPTIONS.map((option) => {
            const Icon = option.icon;
            const isSelected = selectedType === option.type;

            return (
              <div key={option.type}>
                {/* Type header */}
                <button
                  type="button"
                  onClick={() => handleTypeSelect(option.type)}
                  className={cn(
                    "w-full flex items-center gap-2 px-3 py-2 text-sm",
                    "hover:bg-surface-700 transition-colors",
                    isSelected && "bg-surface-700"
                  )}
                  role="option"
                  aria-selected={currentTransition.type === option.type}
                >
                  <Icon className="w-4 h-4 text-surface-300" />
                  <span className="flex-1 text-left text-surface-100">{option.label}</span>
                  {currentTransition.type === option.type && option.type === 'cut' && (
                    <Check className="w-4 h-4 text-primary-400" />
                  )}
                </button>

                {/* Duration options (if applicable and type is selected) */}
                {isSelected && option.durations.length > 1 && (
                  <div className="pl-9 pb-1">
                    {option.durations.map((duration) => (
                      <button
                        key={duration}
                        type="button"
                        onClick={() => handleDurationSelect(duration)}
                        className={cn(
                          "w-full flex items-center justify-between px-3 py-1.5 text-xs",
                          "hover:bg-surface-700 transition-colors rounded",
                          currentTransition.type === option.type &&
                          currentTransition.duration === duration &&
                          "bg-primary-500/20 text-primary-300"
                        )}
                      >
                        <span className="text-surface-200">{formatDuration(duration)}</span>
                        {currentTransition.type === option.type &&
                         currentTransition.duration === duration && (
                          <Check className="w-3 h-3 text-primary-400" />
                        )}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/**
 * Inline transition zone component
 * Displayed between clips to indicate and edit transitions
 */
interface TransitionZoneProps {
  transition: TransitionConfig;
  onChange: (transition: TransitionConfig) => void;
  className?: string;
}

export function TransitionZone({ transition, onChange, className }: TransitionZoneProps) {
  const [showPicker, setShowPicker] = useState(false);

  const Icon = TRANSITION_OPTIONS.find(opt => opt.type === transition.type)?.icon || Scissors;

  return (
    <div
      className={cn(
        "relative flex items-center justify-center w-6 h-full",
        "cursor-pointer group",
        className
      )}
      onClick={() => setShowPicker(!showPicker)}
      title={`Transition: ${transition.type} ${transition.duration > 0 ? formatDuration(transition.duration) : ''}`}
    >
      {/* Visual indicator */}
      <div className={cn(
        "w-1 h-8 rounded-full transition-all",
        transition.type === 'cut'
          ? "bg-surface-600 group-hover:bg-surface-500"
          : "bg-primary-500/50 group-hover:bg-primary-400/60"
      )} />

      {/* Hover icon */}
      <div className={cn(
        "absolute inset-0 flex items-center justify-center",
        "opacity-0 group-hover:opacity-100 transition-opacity",
        "bg-surface-800/80 rounded"
      )}>
        <Icon className="w-3 h-3 text-surface-200" />
      </div>

      {/* Transition picker dropdown */}
      {showPicker && (
        <div className="absolute top-full left-1/2 -translate-x-1/2 mt-1 z-50">
          <TransitionPicker
            currentTransition={transition}
            onChange={(newTransition) => {
              onChange(newTransition);
              setShowPicker(false);
            }}
          />
        </div>
      )}
    </div>
  );
}

export default TransitionPicker;
