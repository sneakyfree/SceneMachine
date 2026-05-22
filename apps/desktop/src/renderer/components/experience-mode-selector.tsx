/**
 * Experience Mode Selector Component
 *
 * Allows users to switch between Story, Creator, and Pro modes
 * both globally and per-feature.
 */

import { useState } from 'react';
import { Wand2, Palette, Settings2, ChevronDown, Check, RotateCcw, Info } from 'lucide-react';
import { cn } from '../lib/utils';
import {
  useExperienceStore,
  ExperienceMode,
  FeatureArea,
  MODE_INFO,
} from '../stores/experience-store';

// Icon mapping
const MODE_ICONS: Record<ExperienceMode, typeof Wand2> = {
  story: Wand2,
  creator: Palette,
  pro: Settings2,
};

interface ExperienceModeSelectorProps {
  // If feature is provided, this is a per-feature selector
  feature?: FeatureArea;
  // Compact mode for inline use
  compact?: boolean;
  // Show description
  showDescription?: boolean;
  // Callback when mode changes
  onChange?: (mode: ExperienceMode) => void;
}

export function ExperienceModeSelector({
  feature,
  compact = false,
  showDescription = true,
  onChange,
}: ExperienceModeSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);

  const {
    globalMode,
    featureOverrides,
    setGlobalMode,
    setFeatureMode,
    getEffectiveMode,
    resetFeatureOverrides,
  } = useExperienceStore();

  const currentMode = getEffectiveMode(feature);
  const hasOverride = feature && featureOverrides[feature];
  const CurrentIcon = MODE_ICONS[currentMode];

  const handleModeSelect = (mode: ExperienceMode) => {
    if (feature) {
      setFeatureMode(feature, mode);
    } else {
      setGlobalMode(mode);
    }
    onChange?.(mode);
    setIsOpen(false);
  };

  const handleResetOverride = () => {
    if (feature) {
      setFeatureMode(feature, null);
    }
    setIsOpen(false);
  };

  if (compact) {
    return (
      <div className="relative">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className={cn(
            'flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors',
            'bg-surface-800 hover:bg-surface-700 border border-surface-700'
          )}
        >
          <CurrentIcon className="w-4 h-4" />
          <span>{MODE_INFO[currentMode].shortName}</span>
          <ChevronDown className={cn('w-3 h-3 transition-transform', isOpen && 'rotate-180')} />
        </button>

        {isOpen && (
          <>
            <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />
            <div className="absolute right-0 mt-2 w-48 bg-surface-900 rounded-lg shadow-xl border border-surface-800 py-1 z-50">
              {(Object.keys(MODE_INFO) as ExperienceMode[]).map((mode) => {
                const Icon = MODE_ICONS[mode];
                const isSelected = mode === currentMode;

                return (
                  <button
                    key={mode}
                    onClick={() => handleModeSelect(mode)}
                    className={cn(
                      'w-full flex items-center gap-3 px-4 py-2 text-left hover:bg-surface-800 transition-colors',
                      isSelected && 'bg-surface-800'
                    )}
                  >
                    <Icon className={cn('w-4 h-4', isSelected && 'text-brand-400')} />
                    <span className={cn(isSelected && 'text-brand-400')}>
                      {MODE_INFO[mode].shortName}
                    </span>
                    {isSelected && <Check className="w-4 h-4 text-brand-400 ml-auto" />}
                  </button>
                );
              })}

              {hasOverride && (
                <>
                  <div className="border-t border-surface-800 my-1" />
                  <button
                    onClick={handleResetOverride}
                    className="w-full flex items-center gap-3 px-4 py-2 text-left text-surface-400 hover:bg-surface-800 transition-colors"
                  >
                    <RotateCcw className="w-4 h-4" />
                    <span>Reset to global</span>
                  </button>
                </>
              )}
            </div>
          </>
        )}
      </div>
    );
  }

  // Full selector (for settings page)
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-medium">Experience Level</h3>
          {showDescription && (
            <p className="text-sm text-surface-400 mt-1">
              {feature
                ? 'Override the experience level for this feature'
                : 'Choose how much control and technical detail you want to see'}
            </p>
          )}
        </div>
        {hasOverride && (
          <button
            onClick={handleResetOverride}
            className="flex items-center gap-1 text-sm text-surface-400 hover:text-surface-200"
          >
            <RotateCcw className="w-3 h-3" />
            Reset
          </button>
        )}
      </div>

      <div className="grid grid-cols-3 gap-3">
        {(Object.keys(MODE_INFO) as ExperienceMode[]).map((mode) => {
          const info = MODE_INFO[mode];
          const Icon = MODE_ICONS[mode];
          const isSelected = mode === currentMode;

          const colorClasses = {
            story: 'border-green-500 bg-green-500/10',
            creator: 'border-blue-500 bg-blue-500/10',
            pro: 'border-purple-500 bg-purple-500/10',
          };

          return (
            <button
              key={mode}
              onClick={() => handleModeSelect(mode)}
              className={cn(
                'p-4 rounded-xl border-2 transition-all text-left',
                isSelected
                  ? colorClasses[mode]
                  : 'border-surface-700 bg-surface-800/50 hover:border-surface-600'
              )}
            >
              <div className="flex items-center gap-2 mb-2">
                <Icon
                  className={cn(
                    'w-5 h-5',
                    isSelected &&
                      (mode === 'story'
                        ? 'text-green-400'
                        : mode === 'creator'
                          ? 'text-blue-400'
                          : 'text-purple-400')
                  )}
                />
                <span className="font-medium">{info.name}</span>
                {isSelected && (
                  <Check
                    className={cn(
                      'w-4 h-4 ml-auto',
                      mode === 'story'
                        ? 'text-green-400'
                        : mode === 'creator'
                          ? 'text-blue-400'
                          : 'text-purple-400'
                    )}
                  />
                )}
              </div>
              <p className="text-xs text-surface-400">{info.description}</p>
            </button>
          );
        })}
      </div>

      {feature && !hasOverride && (
        <p className="text-xs text-surface-500 flex items-center gap-1">
          <Info className="w-3 h-3" />
          Using global setting: {MODE_INFO[globalMode].name}
        </p>
      )}
    </div>
  );
}

// Slider version for quick switching
export function ExperienceModeSlider({
  feature,
  onChange,
}: {
  feature?: FeatureArea;
  onChange?: (mode: ExperienceMode) => void;
}) {
  const { getEffectiveMode, setGlobalMode, setFeatureMode } = useExperienceStore();
  const currentMode = getEffectiveMode(feature);

  const modes: ExperienceMode[] = ['story', 'creator', 'pro'];
  const currentIndex = modes.indexOf(currentMode);

  const handleChange = (index: number) => {
    const newMode = modes[index];
    if (feature) {
      setFeatureMode(feature, newMode);
    } else {
      setGlobalMode(newMode);
    }
    onChange?.(newMode);
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="text-surface-400">Simplest</span>
        <span className="font-medium">{MODE_INFO[currentMode].shortName}</span>
        <span className="text-surface-400">Most Control</span>
      </div>

      <div className="relative h-2 bg-surface-800 rounded-full">
        {/* Track gradient */}
        <div className="absolute inset-0 rounded-full bg-gradient-to-r from-green-500 via-blue-500 to-purple-500 opacity-20" />

        {/* Thumb */}
        <div
          className={cn(
            'absolute top-1/2 -translate-y-1/2 w-6 h-6 rounded-full shadow-lg transition-all cursor-pointer',
            currentMode === 'story' && 'bg-green-500 left-0',
            currentMode === 'creator' && 'bg-blue-500 left-1/2 -translate-x-1/2',
            currentMode === 'pro' && 'bg-purple-500 right-0'
          )}
        />

        {/* Clickable areas */}
        <div className="absolute inset-0 flex">
          {modes.map((mode, index) => (
            <button
              key={mode}
              onClick={() => handleChange(index)}
              className="flex-1 h-full"
              aria-label={MODE_INFO[mode].name}
            />
          ))}
        </div>
      </div>

      <p className="text-xs text-center text-surface-500">{MODE_INFO[currentMode].description}</p>
    </div>
  );
}

// Inline badge showing current mode
export function ExperienceModeBadge({ feature }: { feature?: FeatureArea }) {
  const { getEffectiveMode, featureOverrides } = useExperienceStore();
  const mode = getEffectiveMode(feature);
  const hasOverride = feature && featureOverrides[feature];
  const Icon = MODE_ICONS[mode];

  const colorClasses = {
    story: 'bg-green-500/20 text-green-400 border-green-500/30',
    creator: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    pro: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs border',
        colorClasses[mode]
      )}
    >
      <Icon className="w-3 h-3" />
      {MODE_INFO[mode].shortName}
      {hasOverride && <span className="opacity-50">*</span>}
    </span>
  );
}
