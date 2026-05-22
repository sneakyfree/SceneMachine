/**
 * Export Presets Component
 *
 * Quick-select presets for common export configurations.
 * Presets auto-fill all export settings for one-click export.
 */

import { memo, useCallback } from 'react';
import {
  Globe,
  Smartphone,
  Film,
  Settings,
  Youtube,
  Tv,
  Sparkles,
  MonitorPlay,
  CheckCircle,
} from 'lucide-react';
import { cn } from '../../lib/utils';

export interface ExportPreset {
  /**
   * Unique preset ID
   */
  id: string;

  /**
   * Display name
   */
  name: string;

  /**
   * Short description
   */
  description: string;

  /**
   * Icon name
   */
  icon: 'web' | 'social' | 'cinema' | 'custom' | 'youtube' | 'tv' | 'mobile' | 'broadcast';

  /**
   * Export format (e.g., 'mp4_h264', 'prores')
   */
  format: string;

  /**
   * Quality preset (e.g., 'high', 'master')
   */
  quality: string;

  /**
   * Resolution (e.g., '1920x1080')
   */
  resolution: string;

  /**
   * Frame rate
   */
  frameRate: number;

  /**
   * Video bitrate in kbps (informational)
   */
  videoBitrate?: number;

  /**
   * Audio bitrate in kbps (informational)
   */
  audioBitrate?: number;

  /**
   * Whether this is the recommended default
   */
  recommended?: boolean;

  /**
   * File extension
   */
  extension: string;
}

// Predefined export presets
export const DEFAULT_PRESETS: ExportPreset[] = [
  {
    id: 'web',
    name: 'Web',
    description: '720p H.264 for web streaming',
    icon: 'web',
    format: 'mp4_h264',
    quality: 'standard',
    resolution: '1280x720',
    frameRate: 30,
    videoBitrate: 5000,
    audioBitrate: 192,
    extension: 'mp4',
  },
  {
    id: 'social',
    name: 'Social',
    description: '1080p optimized for social media',
    icon: 'social',
    format: 'mp4_h264',
    quality: 'high',
    resolution: '1920x1080',
    frameRate: 30,
    videoBitrate: 8000,
    audioBitrate: 256,
    recommended: true,
    extension: 'mp4',
  },
  {
    id: 'youtube',
    name: 'YouTube',
    description: '1080p60 for YouTube uploads',
    icon: 'youtube',
    format: 'mp4_h264',
    quality: 'high',
    resolution: '1920x1080',
    frameRate: 60,
    videoBitrate: 12000,
    audioBitrate: 320,
    extension: 'mp4',
  },
  {
    id: 'cinema',
    name: 'Cinema',
    description: '4K ProRes for professional editing',
    icon: 'cinema',
    format: 'prores_422',
    quality: 'master',
    resolution: '3840x2160',
    frameRate: 24,
    videoBitrate: 150000,
    audioBitrate: 320,
    extension: 'mov',
  },
  {
    id: 'broadcast',
    name: 'Broadcast',
    description: '1080i for TV broadcast',
    icon: 'broadcast',
    format: 'mp4_h264',
    quality: 'high',
    resolution: '1920x1080',
    frameRate: 30,
    videoBitrate: 25000,
    audioBitrate: 320,
    extension: 'mp4',
  },
  {
    id: 'mobile',
    name: 'Mobile',
    description: '720p H.265 for smaller file size',
    icon: 'mobile',
    format: 'mp4_h265',
    quality: 'standard',
    resolution: '1280x720',
    frameRate: 30,
    videoBitrate: 3000,
    audioBitrate: 128,
    extension: 'mp4',
  },
];

function getPresetIcon(icon: ExportPreset['icon']) {
  switch (icon) {
    case 'web':
      return Globe;
    case 'social':
      return MonitorPlay;
    case 'cinema':
      return Film;
    case 'youtube':
      return Youtube;
    case 'tv':
      return Tv;
    case 'broadcast':
      return Tv;
    case 'mobile':
      return Smartphone;
    case 'custom':
    default:
      return Settings;
  }
}

interface ExportPresetsProps {
  /**
   * Currently selected preset ID
   */
  selectedPresetId?: string;

  /**
   * Called when a preset is selected
   */
  onSelectPreset: (preset: ExportPreset) => void;

  /**
   * Available presets (uses defaults if not provided)
   */
  presets?: ExportPreset[];

  /**
   * Layout mode
   */
  layout?: 'grid' | 'list';

  /**
   * Size variant
   */
  size?: 'sm' | 'md' | 'lg';

  /**
   * Show custom option
   */
  showCustom?: boolean;

  /**
   * Additional CSS classes
   */
  className?: string;
}

/**
 * Export Presets Selector
 */
export const ExportPresets = memo(function ExportPresets({
  selectedPresetId,
  onSelectPreset,
  presets = DEFAULT_PRESETS,
  layout = 'grid',
  size = 'md',
  showCustom = true,
  className,
}: ExportPresetsProps) {
  const handleSelect = useCallback(
    (preset: ExportPreset) => {
      onSelectPreset(preset);
    },
    [onSelectPreset]
  );

  const sizeClasses = {
    sm: {
      card: 'p-2',
      icon: 'w-4 h-4',
      title: 'text-sm',
      desc: 'text-xs',
    },
    md: {
      card: 'p-3',
      icon: 'w-5 h-5',
      title: 'text-base',
      desc: 'text-sm',
    },
    lg: {
      card: 'p-4',
      icon: 'w-6 h-6',
      title: 'text-lg',
      desc: 'text-base',
    },
  };

  const sizes = sizeClasses[size];

  // Custom preset for manual configuration
  const customPreset: ExportPreset = {
    id: 'custom',
    name: 'Custom',
    description: 'Configure all settings manually',
    icon: 'custom',
    format: '',
    quality: '',
    resolution: '',
    frameRate: 0,
    extension: '',
  };

  const allPresets = showCustom ? [...presets, customPreset] : presets;

  if (layout === 'list') {
    return (
      <div className={cn('space-y-2', className)}>
        {allPresets.map((preset) => {
          const Icon = getPresetIcon(preset.icon);
          const isSelected = selectedPresetId === preset.id;

          return (
            <button
              key={preset.id}
              onClick={() => handleSelect(preset)}
              className={cn(
                'w-full flex items-center gap-3 rounded-lg transition-all',
                sizes.card,
                isSelected
                  ? 'bg-primary-500/20 border-2 border-primary-500'
                  : 'bg-surface-800 border-2 border-transparent hover:border-surface-600'
              )}
            >
              <div
                className={cn(
                  'p-2 rounded-lg',
                  isSelected ? 'bg-primary-500/30' : 'bg-surface-700'
                )}
              >
                <Icon
                  className={cn(sizes.icon, isSelected ? 'text-primary-400' : 'text-surface-300')}
                />
              </div>
              <div className="flex-1 text-left">
                <div className="flex items-center gap-2">
                  <span className={cn('font-medium text-surface-100', sizes.title)}>
                    {preset.name}
                  </span>
                  {preset.recommended && (
                    <span className="px-1.5 py-0.5 rounded bg-green-500/20 text-green-400 text-xs">
                      Recommended
                    </span>
                  )}
                </div>
                <p className={cn('text-surface-400', sizes.desc)}>{preset.description}</p>
              </div>
              {isSelected && <CheckCircle className="w-5 h-5 text-primary-400" />}
            </button>
          );
        })}
      </div>
    );
  }

  // Grid layout
  return (
    <div
      className={cn(
        'grid gap-3',
        size === 'sm' ? 'grid-cols-3' : size === 'md' ? 'grid-cols-3' : 'grid-cols-2',
        className
      )}
    >
      {allPresets.map((preset) => {
        const Icon = getPresetIcon(preset.icon);
        const isSelected = selectedPresetId === preset.id;

        return (
          <button
            key={preset.id}
            onClick={() => handleSelect(preset)}
            className={cn(
              'flex flex-col items-center text-center rounded-lg transition-all',
              sizes.card,
              isSelected
                ? 'bg-primary-500/20 border-2 border-primary-500'
                : 'bg-surface-800 border-2 border-transparent hover:border-surface-600'
            )}
          >
            {/* Recommended badge */}
            {preset.recommended && (
              <div className="absolute -top-1 -right-1">
                <Sparkles className="w-4 h-4 text-yellow-400" />
              </div>
            )}

            <div
              className={cn(
                'p-3 rounded-lg mb-2',
                isSelected ? 'bg-primary-500/30' : 'bg-surface-700'
              )}
            >
              <Icon
                className={cn(sizes.icon, isSelected ? 'text-primary-400' : 'text-surface-300')}
              />
            </div>

            <span className={cn('font-medium text-surface-100', sizes.title)}>{preset.name}</span>

            <p className={cn('text-surface-400 mt-0.5', sizes.desc)}>{preset.description}</p>

            {/* Preset details */}
            {preset.id !== 'custom' && (
              <div className="flex items-center gap-2 mt-2 text-xs text-surface-500">
                <span>{preset.resolution.split('x')[1]}p</span>
                <span>•</span>
                <span>{preset.frameRate}fps</span>
                <span>•</span>
                <span>.{preset.extension}</span>
              </div>
            )}
          </button>
        );
      })}
    </div>
  );
});

/**
 * Compact preset button row
 */
export const PresetButtonRow = memo(function PresetButtonRow({
  selectedPresetId,
  onSelectPreset,
  presets = DEFAULT_PRESETS,
  className,
}: Omit<ExportPresetsProps, 'layout' | 'size' | 'showCustom'>) {
  return (
    <div className={cn('flex flex-wrap gap-2', className)}>
      {presets.map((preset) => {
        const Icon = getPresetIcon(preset.icon);
        const isSelected = selectedPresetId === preset.id;

        return (
          <button
            key={preset.id}
            onClick={() => onSelectPreset(preset)}
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all',
              isSelected
                ? 'bg-primary-500 text-white'
                : 'bg-surface-700 text-surface-300 hover:bg-surface-600'
            )}
          >
            <Icon className="w-4 h-4" />
            <span>{preset.name}</span>
            {preset.recommended && !isSelected && (
              <span className="ml-1 text-xs text-green-400">★</span>
            )}
          </button>
        );
      })}
    </div>
  );
});

/**
 * Get preset by ID
 */
export function getPresetById(
  presetId: string,
  presets: ExportPreset[] = DEFAULT_PRESETS
): ExportPreset | undefined {
  return presets.find((p) => p.id === presetId);
}

/**
 * Apply preset to export settings
 */
export function applyPresetToSettings<
  T extends {
    format: string;
    quality: string;
    resolution: string;
    frameRate: number;
  },
>(settings: T, preset: ExportPreset): T {
  if (preset.id === 'custom') {
    return settings;
  }

  return {
    ...settings,
    format: preset.format,
    quality: preset.quality,
    resolution: preset.resolution,
    frameRate: preset.frameRate,
  };
}

export default ExportPresets;
