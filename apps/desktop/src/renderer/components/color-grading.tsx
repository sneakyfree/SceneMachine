/**
 * Color grading panel with presets, LUT support, and manual adjustments.
 * Professional color correction tools for video clips.
 */

import { useState, useMemo } from 'react';
import {
  Palette,
  Sun,
  Contrast,
  Droplets,
  Thermometer,
  SlidersHorizontal,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Copy,
  Download,
  Upload,
  Star,
  Check,
  Eye,
  EyeOff,
} from 'lucide-react';
import { cn } from '../lib/utils';

export interface ColorGrade {
  // Basic adjustments
  exposure: number; // -2 to 2
  contrast: number; // -100 to 100
  highlights: number; // -100 to 100
  shadows: number; // -100 to 100
  whites: number; // -100 to 100
  blacks: number; // -100 to 100

  // Color adjustments
  temperature: number; // -100 (cool) to 100 (warm)
  tint: number; // -100 (green) to 100 (magenta)
  saturation: number; // -100 to 100
  vibrance: number; // -100 to 100

  // HSL adjustments
  hue: number; // -180 to 180

  // Split toning
  highlightTint: string;
  shadowTint: string;
  splitBalance: number; // -100 to 100

  // Vignette
  vignetteAmount: number; // 0 to 100
  vignetteMidpoint: number; // 0 to 100
  vignetteFeather: number; // 0 to 100

  // Grain
  grainAmount: number; // 0 to 100
  grainSize: number; // 0 to 100

  // LUT
  lutId?: string;
  lutIntensity: number; // 0 to 100
}

export interface ColorPreset {
  id: string;
  name: string;
  category: 'cinematic' | 'vintage' | 'modern' | 'dramatic' | 'natural' | 'custom';
  thumbnail?: string;
  grade: Partial<ColorGrade>;
  isFavorite: boolean;
  isBuiltIn: boolean;
}

export interface LUT {
  id: string;
  name: string;
  category: string;
  thumbnail?: string;
  filePath?: string;
}

const DEFAULT_GRADE: ColorGrade = {
  exposure: 0,
  contrast: 0,
  highlights: 0,
  shadows: 0,
  whites: 0,
  blacks: 0,
  temperature: 0,
  tint: 0,
  saturation: 0,
  vibrance: 0,
  hue: 0,
  highlightTint: '#FFE4C4',
  shadowTint: '#4169E1',
  splitBalance: 0,
  vignetteAmount: 0,
  vignetteMidpoint: 50,
  vignetteFeather: 50,
  grainAmount: 0,
  grainSize: 50,
  lutIntensity: 100,
};

const BUILT_IN_PRESETS: ColorPreset[] = [
  // Cinematic
  {
    id: 'teal-orange',
    name: 'Teal & Orange',
    category: 'cinematic',
    grade: {
      temperature: 15,
      tint: -5,
      contrast: 20,
      saturation: 10,
      shadows: -10,
      highlightTint: '#FF8C00',
      shadowTint: '#008B8B',
      splitBalance: -20,
    },
    isFavorite: false,
    isBuiltIn: true,
  },
  {
    id: 'blockbuster',
    name: 'Blockbuster',
    category: 'cinematic',
    grade: {
      contrast: 25,
      saturation: -10,
      blacks: -15,
      highlights: -10,
      temperature: 5,
      vignetteAmount: 20,
    },
    isFavorite: false,
    isBuiltIn: true,
  },
  {
    id: 'noir',
    name: 'Film Noir',
    category: 'cinematic',
    grade: {
      saturation: -100,
      contrast: 40,
      blacks: -20,
      whites: 10,
      vignetteAmount: 35,
      grainAmount: 15,
    },
    isFavorite: false,
    isBuiltIn: true,
  },

  // Vintage
  {
    id: 'vintage-film',
    name: 'Vintage Film',
    category: 'vintage',
    grade: {
      temperature: 20,
      contrast: -10,
      saturation: -15,
      blacks: 10,
      grainAmount: 25,
      shadowTint: '#2F4F4F',
      highlightTint: '#F5DEB3',
    },
    isFavorite: false,
    isBuiltIn: true,
  },
  {
    id: 'faded-memory',
    name: 'Faded Memory',
    category: 'vintage',
    grade: {
      exposure: 0.2,
      contrast: -20,
      saturation: -30,
      blacks: 20,
      highlights: -20,
      temperature: 10,
    },
    isFavorite: false,
    isBuiltIn: true,
  },
  {
    id: 'polaroid',
    name: 'Polaroid',
    category: 'vintage',
    grade: {
      temperature: 15,
      tint: 5,
      contrast: -15,
      saturation: -20,
      blacks: 15,
      vignetteAmount: 15,
    },
    isFavorite: false,
    isBuiltIn: true,
  },

  // Modern
  {
    id: 'crisp-clean',
    name: 'Crisp & Clean',
    category: 'modern',
    grade: {
      contrast: 15,
      saturation: 5,
      vibrance: 20,
      highlights: -5,
      shadows: 5,
    },
    isFavorite: false,
    isBuiltIn: true,
  },
  {
    id: 'muted-tones',
    name: 'Muted Tones',
    category: 'modern',
    grade: {
      saturation: -25,
      vibrance: -10,
      contrast: 10,
      temperature: -5,
    },
    isFavorite: false,
    isBuiltIn: true,
  },
  {
    id: 'high-fashion',
    name: 'High Fashion',
    category: 'modern',
    grade: {
      contrast: 30,
      saturation: -20,
      exposure: 0.1,
      highlights: 10,
      blacks: -10,
    },
    isFavorite: false,
    isBuiltIn: true,
  },

  // Dramatic
  {
    id: 'dark-moody',
    name: 'Dark & Moody',
    category: 'dramatic',
    grade: {
      exposure: -0.3,
      contrast: 20,
      shadows: -20,
      blacks: -30,
      saturation: -10,
      vignetteAmount: 40,
      shadowTint: '#191970',
    },
    isFavorite: false,
    isBuiltIn: true,
  },
  {
    id: 'apocalyptic',
    name: 'Apocalyptic',
    category: 'dramatic',
    grade: {
      temperature: -20,
      saturation: -40,
      contrast: 35,
      blacks: -25,
      grainAmount: 20,
      vignetteAmount: 30,
    },
    isFavorite: false,
    isBuiltIn: true,
  },
  {
    id: 'horror',
    name: 'Horror',
    category: 'dramatic',
    grade: {
      temperature: -30,
      saturation: -50,
      contrast: 25,
      shadows: -30,
      highlights: -20,
      vignetteAmount: 45,
      grainAmount: 10,
    },
    isFavorite: false,
    isBuiltIn: true,
  },

  // Natural
  {
    id: 'golden-hour',
    name: 'Golden Hour',
    category: 'natural',
    grade: {
      temperature: 35,
      tint: 10,
      exposure: 0.15,
      contrast: 5,
      vibrance: 15,
      highlightTint: '#FFD700',
    },
    isFavorite: false,
    isBuiltIn: true,
  },
  {
    id: 'overcast',
    name: 'Overcast Day',
    category: 'natural',
    grade: {
      temperature: -10,
      contrast: -5,
      saturation: -15,
      shadows: 5,
    },
    isFavorite: false,
    isBuiltIn: true,
  },
  {
    id: 'summer-vibes',
    name: 'Summer Vibes',
    category: 'natural',
    grade: {
      temperature: 20,
      saturation: 15,
      vibrance: 25,
      contrast: 10,
      exposure: 0.1,
    },
    isFavorite: false,
    isBuiltIn: true,
  },
];

const CATEGORY_NAMES: Record<string, string> = {
  cinematic: 'Cinematic',
  vintage: 'Vintage',
  modern: 'Modern',
  dramatic: 'Dramatic',
  natural: 'Natural',
  custom: 'Custom',
};

interface SliderControlProps {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  onChange: (value: number) => void;
  format?: (value: number) => string;
}

function SliderControl({
  label,
  value,
  min,
  max,
  step = 1,
  onChange,
  format,
}: SliderControlProps) {
  const displayValue = format ? format(value) : value.toString();

  return (
    <div>
      <div className="flex items-center justify-between text-xs mb-1">
        <span className="text-surface-400">{label}</span>
        <span className="text-surface-300 font-mono">{displayValue}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full accent-brand-500"
      />
    </div>
  );
}

interface PresetThumbnailProps {
  preset: ColorPreset;
  isSelected: boolean;
  onSelect: () => void;
  onToggleFavorite: () => void;
}

function PresetThumbnail({
  preset,
  isSelected,
  onSelect,
  onToggleFavorite,
}: PresetThumbnailProps) {
  // Generate a gradient preview based on the preset
  const previewStyle = useMemo(() => {
    const g = { ...DEFAULT_GRADE, ...preset.grade };
    const warmth = g.temperature > 0 ? `rgba(255,200,100,${g.temperature / 200})` : `rgba(100,150,255,${-g.temperature / 200})`;
    const satMod = 1 + g.saturation / 100;

    return {
      background: `linear-gradient(135deg,
        ${g.shadowTint || '#1a1a2e'} 0%,
        ${warmth} 50%,
        ${g.highlightTint || '#f0f0f0'} 100%)`,
      filter: `saturate(${satMod}) contrast(${1 + g.contrast / 100})`,
    };
  }, [preset.grade]);

  return (
    <button
      onClick={onSelect}
      className={cn(
        'relative w-full aspect-video rounded-lg overflow-hidden border-2 transition-all',
        isSelected
          ? 'border-brand-500 ring-2 ring-brand-500/50'
          : 'border-surface-700 hover:border-surface-600'
      )}
    >
      <div className="absolute inset-0" style={previewStyle} />
      <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
      <div className="absolute bottom-0 left-0 right-0 p-2">
        <span className="text-xs font-medium text-white">{preset.name}</span>
      </div>
      {isSelected && (
        <div className="absolute top-1 right-1 w-5 h-5 bg-brand-500 rounded-full flex items-center justify-center">
          <Check className="w-3 h-3 text-white" />
        </div>
      )}
      <button
        onClick={(e) => {
          e.stopPropagation();
          onToggleFavorite();
        }}
        className={cn(
          'absolute top-1 left-1 p-1 rounded transition-colors',
          preset.isFavorite
            ? 'text-yellow-400'
            : 'text-white/50 hover:text-white/80'
        )}
      >
        <Star className={cn('w-3 h-3', preset.isFavorite && 'fill-current')} />
      </button>
    </button>
  );
}

interface ColorGradingPanelProps {
  grade: ColorGrade;
  onChange: (grade: ColorGrade) => void;
  presets?: ColorPreset[];
  onPresetsChange?: (presets: ColorPreset[]) => void;
  onExportPreset?: (preset: ColorPreset) => void;
  onImportLUT?: () => void;
  isEnabled?: boolean;
  onToggleEnabled?: (enabled: boolean) => void;
}

export function ColorGradingPanel({
  grade,
  onChange,
  presets: customPresets = [],
  onPresetsChange,
  onExportPreset,
  onImportLUT,
  isEnabled = true,
  onToggleEnabled,
}: ColorGradingPanelProps) {
  const [activeTab, setActiveTab] = useState<'presets' | 'adjust' | 'effects'>('presets');
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(['basic', 'color'])
  );
  const [selectedPresetId, setSelectedPresetId] = useState<string | null>(null);
  const [presetFilter, setPresetFilter] = useState<string>('all');

  const allPresets = [...BUILT_IN_PRESETS, ...customPresets];

  const filteredPresets = useMemo(() => {
    if (presetFilter === 'all') return allPresets;
    if (presetFilter === 'favorites') return allPresets.filter((p) => p.isFavorite);
    return allPresets.filter((p) => p.category === presetFilter);
  }, [allPresets, presetFilter]);

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(section)) {
        next.delete(section);
      } else {
        next.add(section);
      }
      return next;
    });
  };

  const updateGrade = (updates: Partial<ColorGrade>) => {
    onChange({ ...grade, ...updates });
  };

  const applyPreset = (preset: ColorPreset) => {
    setSelectedPresetId(preset.id);
    onChange({ ...DEFAULT_GRADE, ...preset.grade });
  };

  const resetGrade = () => {
    setSelectedPresetId(null);
    onChange(DEFAULT_GRADE);
  };

  const togglePresetFavorite = (presetId: string) => {
    const preset = allPresets.find((p) => p.id === presetId);
    if (!preset) return;

    if (preset.isBuiltIn) {
      // For built-in presets, we'd need to track favorites separately
      // For now, just show a toast or do nothing
      return;
    }

    if (onPresetsChange) {
      onPresetsChange(
        customPresets.map((p) =>
          p.id === presetId ? { ...p, isFavorite: !p.isFavorite } : p
        )
      );
    }
  };

  const saveAsPreset = () => {
    const newPreset: ColorPreset = {
      id: `custom_${Date.now()}`,
      name: 'Custom Preset',
      category: 'custom',
      grade: { ...grade },
      isFavorite: false,
      isBuiltIn: false,
    };

    if (onPresetsChange) {
      onPresetsChange([...customPresets, newPreset]);
    }
  };

  return (
    <div className="bg-surface-900 border border-surface-800 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-surface-800">
        <div className="flex items-center gap-3">
          <Palette className="w-5 h-5 text-brand-400" />
          <span className="font-medium">Color Grading</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={resetGrade}
            className="icon-btn p-2 text-surface-400 hover:text-surface-200 transition-colors rounded"
            title="Reset"
            aria-label="Reset color grading"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={() => onToggleEnabled?.(!isEnabled)}
            className={cn(
              'icon-btn p-2 rounded transition-colors',
              isEnabled
                ? 'text-brand-400'
                : 'text-surface-500'
            )}
            aria-label={isEnabled ? 'Disable color grading' : 'Enable color grading'}
            title={isEnabled ? 'Disable' : 'Enable'}
          >
            {isEnabled ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-surface-800">
        {[
          { id: 'presets', label: 'Presets' },
          { id: 'adjust', label: 'Adjust' },
          { id: 'effects', label: 'Effects' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as typeof activeTab)}
            className={cn(
              'flex-1 px-4 py-2 text-sm transition-colors',
              activeTab === tab.id
                ? 'text-brand-400 border-b-2 border-brand-500'
                : 'text-surface-400 hover:text-surface-200'
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="p-4 max-h-[600px] overflow-y-auto">
        {/* Presets Tab */}
        {activeTab === 'presets' && (
          <div className="space-y-4">
            {/* Category filter */}
            <div className="flex items-center gap-2 flex-wrap">
              {['all', 'favorites', ...Object.keys(CATEGORY_NAMES)].map((cat) => (
                <button
                  key={cat}
                  onClick={() => setPresetFilter(cat)}
                  className={cn(
                    'px-3 py-1 rounded-full text-xs transition-colors',
                    presetFilter === cat
                      ? 'bg-brand-500/20 text-brand-400'
                      : 'bg-surface-800 text-surface-400 hover:bg-surface-700'
                  )}
                >
                  {cat === 'all'
                    ? 'All'
                    : cat === 'favorites'
                    ? 'Favorites'
                    : CATEGORY_NAMES[cat]}
                </button>
              ))}
            </div>

            {/* Preset grid */}
            <div className="grid grid-cols-3 gap-2">
              {filteredPresets.map((preset) => (
                <PresetThumbnail
                  key={preset.id}
                  preset={preset}
                  isSelected={selectedPresetId === preset.id}
                  onSelect={() => applyPreset(preset)}
                  onToggleFavorite={() => togglePresetFavorite(preset.id)}
                />
              ))}
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2 pt-2 border-t border-surface-800">
              <button
                onClick={saveAsPreset}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-surface-800 hover:bg-surface-700 rounded text-sm transition-colors"
              >
                <Copy className="w-3 h-3" />
                Save as Preset
              </button>
              {onImportLUT && (
                <button
                  onClick={onImportLUT}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-surface-800 hover:bg-surface-700 rounded text-sm transition-colors"
                >
                  <Upload className="w-3 h-3" />
                  Import LUT
                </button>
              )}
            </div>
          </div>
        )}

        {/* Adjust Tab */}
        {activeTab === 'adjust' && (
          <div className="space-y-4">
            {/* Basic adjustments */}
            <div>
              <button
                onClick={() => toggleSection('basic')}
                className="w-full flex items-center justify-between text-sm font-medium mb-3"
              >
                <div className="flex items-center gap-2">
                  <Sun className="w-4 h-4 text-surface-400" />
                  Basic
                </div>
                {expandedSections.has('basic') ? (
                  <ChevronUp className="w-4 h-4 text-surface-400" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-surface-400" />
                )}
              </button>
              {expandedSections.has('basic') && (
                <div className="space-y-3">
                  <SliderControl
                    label="Exposure"
                    value={grade.exposure}
                    min={-2}
                    max={2}
                    step={0.1}
                    onChange={(v) => updateGrade({ exposure: v })}
                    format={(v) => (v >= 0 ? `+${v.toFixed(1)}` : v.toFixed(1))}
                  />
                  <SliderControl
                    label="Contrast"
                    value={grade.contrast}
                    min={-100}
                    max={100}
                    onChange={(v) => updateGrade({ contrast: v })}
                  />
                  <SliderControl
                    label="Highlights"
                    value={grade.highlights}
                    min={-100}
                    max={100}
                    onChange={(v) => updateGrade({ highlights: v })}
                  />
                  <SliderControl
                    label="Shadows"
                    value={grade.shadows}
                    min={-100}
                    max={100}
                    onChange={(v) => updateGrade({ shadows: v })}
                  />
                  <SliderControl
                    label="Whites"
                    value={grade.whites}
                    min={-100}
                    max={100}
                    onChange={(v) => updateGrade({ whites: v })}
                  />
                  <SliderControl
                    label="Blacks"
                    value={grade.blacks}
                    min={-100}
                    max={100}
                    onChange={(v) => updateGrade({ blacks: v })}
                  />
                </div>
              )}
            </div>

            {/* Color adjustments */}
            <div>
              <button
                onClick={() => toggleSection('color')}
                className="w-full flex items-center justify-between text-sm font-medium mb-3"
              >
                <div className="flex items-center gap-2">
                  <Droplets className="w-4 h-4 text-surface-400" />
                  Color
                </div>
                {expandedSections.has('color') ? (
                  <ChevronUp className="w-4 h-4 text-surface-400" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-surface-400" />
                )}
              </button>
              {expandedSections.has('color') && (
                <div className="space-y-3">
                  <SliderControl
                    label="Temperature"
                    value={grade.temperature}
                    min={-100}
                    max={100}
                    onChange={(v) => updateGrade({ temperature: v })}
                    format={(v) => (v < 0 ? 'Cool' : v > 0 ? 'Warm' : 'Neutral')}
                  />
                  <SliderControl
                    label="Tint"
                    value={grade.tint}
                    min={-100}
                    max={100}
                    onChange={(v) => updateGrade({ tint: v })}
                    format={(v) => (v < 0 ? 'Green' : v > 0 ? 'Magenta' : 'Neutral')}
                  />
                  <SliderControl
                    label="Saturation"
                    value={grade.saturation}
                    min={-100}
                    max={100}
                    onChange={(v) => updateGrade({ saturation: v })}
                  />
                  <SliderControl
                    label="Vibrance"
                    value={grade.vibrance}
                    min={-100}
                    max={100}
                    onChange={(v) => updateGrade({ vibrance: v })}
                  />
                  <SliderControl
                    label="Hue"
                    value={grade.hue}
                    min={-180}
                    max={180}
                    onChange={(v) => updateGrade({ hue: v })}
                    format={(v) => `${v}°`}
                  />
                </div>
              )}
            </div>

            {/* Split toning */}
            <div>
              <button
                onClick={() => toggleSection('split')}
                className="w-full flex items-center justify-between text-sm font-medium mb-3"
              >
                <div className="flex items-center gap-2">
                  <Contrast className="w-4 h-4 text-surface-400" />
                  Split Toning
                </div>
                {expandedSections.has('split') ? (
                  <ChevronUp className="w-4 h-4 text-surface-400" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-surface-400" />
                )}
              </button>
              {expandedSections.has('split') && (
                <div className="space-y-3">
                  <div className="flex items-center gap-4">
                    <div>
                      <label className="text-xs text-surface-400 mb-1 block">
                        Highlights
                      </label>
                      <input
                        type="color"
                        value={grade.highlightTint}
                        onChange={(e) => updateGrade({ highlightTint: e.target.value })}
                        className="w-10 h-10 rounded border border-surface-700 cursor-pointer"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-surface-400 mb-1 block">
                        Shadows
                      </label>
                      <input
                        type="color"
                        value={grade.shadowTint}
                        onChange={(e) => updateGrade({ shadowTint: e.target.value })}
                        className="w-10 h-10 rounded border border-surface-700 cursor-pointer"
                      />
                    </div>
                  </div>
                  <SliderControl
                    label="Balance"
                    value={grade.splitBalance}
                    min={-100}
                    max={100}
                    onChange={(v) => updateGrade({ splitBalance: v })}
                    format={(v) =>
                      v < 0 ? 'Shadows' : v > 0 ? 'Highlights' : 'Balanced'
                    }
                  />
                </div>
              )}
            </div>
          </div>
        )}

        {/* Effects Tab */}
        {activeTab === 'effects' && (
          <div className="space-y-4">
            {/* Vignette */}
            <div>
              <button
                onClick={() => toggleSection('vignette')}
                className="w-full flex items-center justify-between text-sm font-medium mb-3"
              >
                <span>Vignette</span>
                {expandedSections.has('vignette') ? (
                  <ChevronUp className="w-4 h-4 text-surface-400" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-surface-400" />
                )}
              </button>
              {expandedSections.has('vignette') && (
                <div className="space-y-3">
                  <SliderControl
                    label="Amount"
                    value={grade.vignetteAmount}
                    min={0}
                    max={100}
                    onChange={(v) => updateGrade({ vignetteAmount: v })}
                  />
                  <SliderControl
                    label="Midpoint"
                    value={grade.vignetteMidpoint}
                    min={0}
                    max={100}
                    onChange={(v) => updateGrade({ vignetteMidpoint: v })}
                  />
                  <SliderControl
                    label="Feather"
                    value={grade.vignetteFeather}
                    min={0}
                    max={100}
                    onChange={(v) => updateGrade({ vignetteFeather: v })}
                  />
                </div>
              )}
            </div>

            {/* Grain */}
            <div>
              <button
                onClick={() => toggleSection('grain')}
                className="w-full flex items-center justify-between text-sm font-medium mb-3"
              >
                <span>Film Grain</span>
                {expandedSections.has('grain') ? (
                  <ChevronUp className="w-4 h-4 text-surface-400" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-surface-400" />
                )}
              </button>
              {expandedSections.has('grain') && (
                <div className="space-y-3">
                  <SliderControl
                    label="Amount"
                    value={grade.grainAmount}
                    min={0}
                    max={100}
                    onChange={(v) => updateGrade({ grainAmount: v })}
                  />
                  <SliderControl
                    label="Size"
                    value={grade.grainSize}
                    min={0}
                    max={100}
                    onChange={(v) => updateGrade({ grainSize: v })}
                  />
                </div>
              )}
            </div>

            {/* LUT */}
            <div>
              <button
                onClick={() => toggleSection('lut')}
                className="w-full flex items-center justify-between text-sm font-medium mb-3"
              >
                <span>LUT</span>
                {expandedSections.has('lut') ? (
                  <ChevronUp className="w-4 h-4 text-surface-400" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-surface-400" />
                )}
              </button>
              {expandedSections.has('lut') && (
                <div className="space-y-3">
                  {grade.lutId ? (
                    <>
                      <div className="flex items-center justify-between p-2 bg-surface-800 rounded">
                        <span className="text-sm">{grade.lutId}</span>
                        <button
                          onClick={() => updateGrade({ lutId: undefined })}
                          className="text-xs text-surface-400 hover:text-surface-200"
                        >
                          Remove
                        </button>
                      </div>
                      <SliderControl
                        label="Intensity"
                        value={grade.lutIntensity}
                        min={0}
                        max={100}
                        onChange={(v) => updateGrade({ lutIntensity: v })}
                        format={(v) => `${v}%`}
                      />
                    </>
                  ) : (
                    <button
                      onClick={onImportLUT}
                      className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-surface-800 hover:bg-surface-700 border border-dashed border-surface-600 rounded-lg text-sm transition-colors"
                    >
                      <Upload className="w-4 h-4" />
                      Import LUT File
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Compact color grading indicator.
 */
export function ColorGradeIndicator({
  hasGrade,
  onClick,
}: {
  hasGrade: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex items-center gap-1.5 px-2 py-1 rounded text-xs transition-colors',
        hasGrade
          ? 'bg-brand-500/20 text-brand-400'
          : 'bg-surface-700 text-surface-400 hover:bg-surface-600'
      )}
    >
      <Palette className="w-3 h-3" />
      <span>Color</span>
    </button>
  );
}

/**
 * Generate CSS filter string from color grade.
 */
export function gradeToFilter(grade: ColorGrade): string {
  const filters: string[] = [];

  if (grade.exposure !== 0) {
    filters.push(`brightness(${1 + grade.exposure})`);
  }
  if (grade.contrast !== 0) {
    filters.push(`contrast(${1 + grade.contrast / 100})`);
  }
  if (grade.saturation !== 0) {
    filters.push(`saturate(${1 + grade.saturation / 100})`);
  }
  if (grade.hue !== 0) {
    filters.push(`hue-rotate(${grade.hue}deg)`);
  }
  if (grade.temperature !== 0) {
    // Approximate with sepia and hue-rotate
    if (grade.temperature > 0) {
      filters.push(`sepia(${grade.temperature / 200})`);
    }
  }

  return filters.length > 0 ? filters.join(' ') : 'none';
}
