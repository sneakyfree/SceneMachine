/**
 * Timeline transitions component.
 * Provides transition effects between clips.
 */

import { useState } from 'react';
import {
  ArrowRight,
  Sparkles,
  Square,
  Circle,
  ChevronRight,
  ChevronDown,
  Clock,
  Sliders,
  X,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { useTranslation } from '../i18n/use-translation';

export type TransitionType =
  | 'none'
  | 'fade'
  | 'dissolve'
  | 'wipe_left'
  | 'wipe_right'
  | 'wipe_up'
  | 'wipe_down'
  | 'slide_left'
  | 'slide_right'
  | 'zoom_in'
  | 'zoom_out'
  | 'blur'
  | 'flash';

export interface Transition {
  id: string;
  type: TransitionType;
  duration: number; // milliseconds
  easing: 'linear' | 'ease-in' | 'ease-out' | 'ease-in-out';
  params?: Record<string, any>;
}

interface TransitionOption {
  type: TransitionType;
  nameKey: string;
  nameEn: string;
  icon: React.ReactNode;
  descKey: string;
  descEn: string;
  category: 'basic' | 'directional' | 'effects';
  defaultDuration: number;
}

const TRANSITIONS: TransitionOption[] = [
  // Basic
  {
    type: 'none',
    nameKey: 'tlTransitions.none',
    nameEn: 'None',
    icon: <Square className="w-4 h-4" />,
    descKey: 'tlTransitions.noTransition',
    descEn: 'No transition',
    category: 'basic',
    defaultDuration: 0,
  },
  {
    type: 'fade',
    nameKey: 'tlTransitions.fade',
    nameEn: 'Fade',
    icon: <Circle className="w-4 h-4 opacity-50" />,
    descKey: 'tlTransitions.fadeDesc',
    descEn: 'Fade to black and back',
    category: 'basic',
    defaultDuration: 500,
  },
  {
    type: 'dissolve',
    nameKey: 'tlTransitions.dissolve',
    nameEn: 'Dissolve',
    icon: <Sparkles className="w-4 h-4" />,
    descKey: 'tlTransitions.dissolveDesc',
    descEn: 'Cross dissolve between clips',
    category: 'basic',
    defaultDuration: 750,
  },

  // Directional
  {
    type: 'wipe_left',
    nameKey: 'tlTransitions.wipeLeft',
    nameEn: 'Wipe Left',
    icon: <ArrowRight className="w-4 h-4 rotate-180" />,
    descKey: 'tlTransitions.wipeLeftDesc',
    descEn: 'Wipe from right to left',
    category: 'directional',
    defaultDuration: 500,
  },
  {
    type: 'wipe_right',
    nameKey: 'tlTransitions.wipeRight',
    nameEn: 'Wipe Right',
    icon: <ArrowRight className="w-4 h-4" />,
    descKey: 'tlTransitions.wipeRightDesc',
    descEn: 'Wipe from left to right',
    category: 'directional',
    defaultDuration: 500,
  },
  {
    type: 'wipe_up',
    nameKey: 'tlTransitions.wipeUp',
    nameEn: 'Wipe Up',
    icon: <ArrowRight className="w-4 h-4 -rotate-90" />,
    descKey: 'tlTransitions.wipeUpDesc',
    descEn: 'Wipe from bottom to top',
    category: 'directional',
    defaultDuration: 500,
  },
  {
    type: 'wipe_down',
    nameKey: 'tlTransitions.wipeDown',
    nameEn: 'Wipe Down',
    icon: <ArrowRight className="w-4 h-4 rotate-90" />,
    descKey: 'tlTransitions.wipeDownDesc',
    descEn: 'Wipe from top to bottom',
    category: 'directional',
    defaultDuration: 500,
  },
  {
    type: 'slide_left',
    nameKey: 'tlTransitions.slideLeft',
    nameEn: 'Slide Left',
    icon: <ChevronRight className="w-4 h-4 rotate-180" />,
    descKey: 'tlTransitions.slideLeftDesc',
    descEn: 'Slide next clip from right',
    category: 'directional',
    defaultDuration: 400,
  },
  {
    type: 'slide_right',
    nameKey: 'tlTransitions.slideRight',
    nameEn: 'Slide Right',
    icon: <ChevronRight className="w-4 h-4" />,
    descKey: 'tlTransitions.slideRightDesc',
    descEn: 'Slide next clip from left',
    category: 'directional',
    defaultDuration: 400,
  },

  // Effects
  {
    type: 'zoom_in',
    nameKey: 'tlTransitions.zoomIn',
    nameEn: 'Zoom In',
    icon: <Circle className="w-3 h-3" />,
    descKey: 'tlTransitions.zoomInDesc',
    descEn: 'Zoom into next clip',
    category: 'effects',
    defaultDuration: 600,
  },
  {
    type: 'zoom_out',
    nameKey: 'tlTransitions.zoomOut',
    nameEn: 'Zoom Out',
    icon: <Circle className="w-5 h-5" />,
    descKey: 'tlTransitions.zoomOutDesc',
    descEn: 'Zoom out to next clip',
    category: 'effects',
    defaultDuration: 600,
  },
  {
    type: 'blur',
    nameKey: 'tlTransitions.blur',
    nameEn: 'Blur',
    icon: <Circle className="w-4 h-4 opacity-30" />,
    descKey: 'tlTransitions.blurDesc',
    descEn: 'Blur transition',
    category: 'effects',
    defaultDuration: 500,
  },
  {
    type: 'flash',
    nameKey: 'tlTransitions.flash',
    nameEn: 'Flash',
    icon: <Sparkles className="w-4 h-4 text-yellow-400" />,
    descKey: 'tlTransitions.flashDesc',
    descEn: 'White flash transition',
    category: 'effects',
    defaultDuration: 300,
  },
];

const EASING_OPTIONS = [
  { value: 'linear', labelKey: 'tlTransitions.easingLinear', labelEn: 'Linear' },
  { value: 'ease-in', labelKey: 'tlTransitions.easingEaseIn', labelEn: 'Ease In' },
  { value: 'ease-out', labelKey: 'tlTransitions.easingEaseOut', labelEn: 'Ease Out' },
  { value: 'ease-in-out', labelKey: 'tlTransitions.easingEaseInOut', labelEn: 'Ease In/Out' },
] as const;

interface TransitionPickerProps {
  selectedType: TransitionType;
  duration: number;
  easing: 'linear' | 'ease-in' | 'ease-out' | 'ease-in-out';
  onSelect: (type: TransitionType, duration: number, easing: string) => void;
  compact?: boolean;
}

export function TransitionPicker({
  selectedType,
  duration,
  easing,
  onSelect,
  compact = false,
}: TransitionPickerProps) {
  const { t } = useTranslation();
  const [expandedCategory, setExpandedCategory] = useState<string | null>('basic');
  const [showSettings, setShowSettings] = useState(false);

  const selectedTransition = TRANSITIONS.find((tr) => tr.type === selectedType);
  const categories = ['basic', 'directional', 'effects'] as const;

  const categoryNames = {
    basic: t('tlTransitions.categoryBasic', 'Basic'),
    directional: t('tlTransitions.categoryDirectional', 'Directional'),
    effects: t('tlTransitions.categoryEffects', 'Effects'),
  };

  if (compact) {
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2 flex-wrap">
          {TRANSITIONS.slice(0, 5).map((transition) => (
            <button
              key={transition.type}
              onClick={() => onSelect(transition.type, transition.defaultDuration, easing)}
              className={cn(
                'flex items-center gap-1 px-2 py-1 rounded text-xs transition-colors',
                selectedType === transition.type
                  ? 'bg-brand-500/20 text-brand-400 border border-brand-500/50'
                  : 'bg-surface-700 text-surface-300 hover:bg-surface-600'
              )}
            >
              {transition.icon}
              <span>{t(transition.nameKey, transition.nameEn)}</span>
            </button>
          ))}
        </div>
        {selectedType !== 'none' && (
          <div className="flex items-center gap-2 text-xs">
            <Clock className="w-3 h-3 text-surface-400" />
            <input
              type="range"
              min="100"
              max="2000"
              step="100"
              value={duration}
              onChange={(e) => onSelect(selectedType, parseInt(e.target.value), easing)}
              className="w-24 accent-brand-500"
            />
            <span className="text-surface-400">{duration}ms</span>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="bg-surface-900 border border-surface-800 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-surface-800">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-brand-400" />
          <span className="font-medium">{t('tlTransitions.transition', 'Transition')}</span>
        </div>
        {selectedTransition && selectedType !== 'none' && (
          <button
            onClick={() => setShowSettings(!showSettings)}
            className={cn(
              'p-1.5 rounded transition-colors',
              showSettings
                ? 'bg-brand-500/20 text-brand-400'
                : 'text-surface-400 hover:text-surface-200'
            )}
          >
            <Sliders className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Settings panel */}
      {showSettings && selectedType !== 'none' && (
        <div className="p-4 border-b border-surface-800 bg-surface-800/50 space-y-4">
          {/* Duration */}
          <div>
            <label className="text-sm text-surface-400 mb-2 block">
              {t('tlTransitions.duration', 'Duration')}: {duration}ms
            </label>
            <input
              type="range"
              min="100"
              max="2000"
              step="50"
              value={duration}
              onChange={(e) => onSelect(selectedType, parseInt(e.target.value), easing)}
              className="w-full accent-brand-500"
            />
            <div className="flex justify-between text-xs text-surface-500 mt-1">
              <span>100ms</span>
              <span>2000ms</span>
            </div>
          </div>

          {/* Easing */}
          <div>
            <label className="text-sm text-surface-400 mb-2 block">{t('tlTransitions.easing', 'Easing')}</label>
            <div className="flex gap-2">
              {EASING_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  onClick={() => onSelect(selectedType, duration, option.value)}
                  className={cn(
                    'flex-1 px-2 py-1.5 rounded text-xs transition-colors',
                    easing === option.value
                      ? 'bg-brand-500/20 text-brand-400'
                      : 'bg-surface-700 text-surface-300 hover:bg-surface-600'
                  )}
                >
                  {t(option.labelKey, option.labelEn)}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Categories */}
      <div className="p-2">
        {categories.map((category) => (
          <div key={category} className="mb-2">
            <button
              onClick={() => setExpandedCategory(expandedCategory === category ? null : category)}
              className="w-full flex items-center gap-2 px-2 py-1.5 text-sm text-surface-400 hover:text-surface-200"
            >
              {expandedCategory === category ? (
                <ChevronDown className="w-4 h-4" />
              ) : (
                <ChevronRight className="w-4 h-4" />
              )}
              {categoryNames[category]}
            </button>

            {expandedCategory === category && (
              <div className="grid grid-cols-3 gap-2 mt-2 px-2">
                {TRANSITIONS.filter((tr) => tr.category === category).map((transition) => (
                  <button
                    key={transition.type}
                    onClick={() => onSelect(transition.type, transition.defaultDuration, easing)}
                    className={cn(
                      'flex flex-col items-center gap-1 p-3 rounded-lg transition-colors',
                      selectedType === transition.type
                        ? 'bg-brand-500/20 border border-brand-500/50'
                        : 'bg-surface-800 hover:bg-surface-700 border border-transparent'
                    )}
                  >
                    <div
                      className={cn(
                        'w-8 h-8 rounded-lg flex items-center justify-center',
                        selectedType === transition.type
                          ? 'bg-brand-500/20 text-brand-400'
                          : 'bg-surface-700'
                      )}
                    >
                      {transition.icon}
                    </div>
                    <span className="text-xs">{t(transition.nameKey, transition.nameEn)}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Preview */}
      {selectedTransition && selectedType !== 'none' && (
        <div className="p-4 border-t border-surface-800">
          <div className="text-sm text-surface-400 mb-2">{t('tlTransitions.preview', 'Preview')}</div>
          <TransitionPreview type={selectedType} duration={duration} />
        </div>
      )}
    </div>
  );
}

/**
 * Visual preview of a transition effect.
 */
function TransitionPreview({ type, duration }: { type: TransitionType; duration: number }) {
  const { t } = useTranslation();
  const [isAnimating, setIsAnimating] = useState(false);

  const triggerAnimation = () => {
    setIsAnimating(true);
    setTimeout(() => setIsAnimating(false), duration);
  };

  const getAnimationStyle = (): React.CSSProperties => {
    if (!isAnimating) return {};

    switch (type) {
      case 'fade':
        return { animation: `fadeTransition ${duration}ms ease-in-out` };
      case 'dissolve':
        return { animation: `dissolveTransition ${duration}ms ease-in-out` };
      case 'wipe_left':
        return { animation: `wipeLeft ${duration}ms ease-in-out` };
      case 'wipe_right':
        return { animation: `wipeRight ${duration}ms ease-in-out` };
      case 'slide_left':
        return { animation: `slideLeft ${duration}ms ease-in-out` };
      case 'slide_right':
        return { animation: `slideRight ${duration}ms ease-in-out` };
      case 'zoom_in':
        return { animation: `zoomIn ${duration}ms ease-in-out` };
      case 'zoom_out':
        return { animation: `zoomOut ${duration}ms ease-in-out` };
      default:
        return {};
    }
  };

  return (
    <div
      className="relative w-full h-16 bg-surface-800 rounded-lg overflow-hidden cursor-pointer"
      onClick={triggerAnimation}
    >
      {/* Clip A */}
      <div
        className="absolute inset-0 bg-gradient-to-r from-blue-500 to-blue-600 flex items-center justify-center"
        style={isAnimating ? { opacity: 0 } : {}}
      >
        <span className="text-white text-sm font-medium">{t('tlTransitions.clipA', 'Clip A')}</span>
      </div>

      {/* Clip B */}
      <div
        className="absolute inset-0 bg-gradient-to-r from-purple-500 to-purple-600 flex items-center justify-center"
        style={getAnimationStyle()}
      >
        <span className="text-white text-sm font-medium">{t('tlTransitions.clipB', 'Clip B')}</span>
      </div>

      {/* Click hint */}
      <div className="absolute bottom-1 right-2 text-xs text-white/50">
        {t('tlTransitions.clickToPreview', 'Click to preview')}
      </div>

      <style>{`
        @keyframes fadeTransition {
          0% { opacity: 0; }
          100% { opacity: 1; }
        }
        @keyframes dissolveTransition {
          0% { opacity: 0; filter: blur(4px); }
          100% { opacity: 1; filter: blur(0); }
        }
        @keyframes wipeLeft {
          0% { clip-path: inset(0 0 0 100%); }
          100% { clip-path: inset(0 0 0 0); }
        }
        @keyframes wipeRight {
          0% { clip-path: inset(0 100% 0 0); }
          100% { clip-path: inset(0 0 0 0); }
        }
        @keyframes slideLeft {
          0% { transform: translateX(100%); }
          100% { transform: translateX(0); }
        }
        @keyframes slideRight {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(0); }
        }
        @keyframes zoomIn {
          0% { transform: scale(1.5); opacity: 0; }
          100% { transform: scale(1); opacity: 1; }
        }
        @keyframes zoomOut {
          0% { transform: scale(0.5); opacity: 0; }
          100% { transform: scale(1); opacity: 1; }
        }
      `}</style>
    </div>
  );
}

/**
 * Inline transition indicator between timeline clips.
 */
export function TransitionIndicator({
  transition,
  onClick,
  onRemove,
}: {
  transition: Transition | null;
  onClick: () => void;
  onRemove: () => void;
}) {
  const { t } = useTranslation();
  if (!transition || transition.type === 'none') {
    return (
      <button
        onClick={onClick}
        className="w-6 h-full flex items-center justify-center text-surface-500 hover:text-brand-400 hover:bg-brand-500/10 transition-colors"
        title={t('tlTransitions.addTransition', 'Add transition')}
      >
        <Sparkles className="w-3 h-3" />
      </button>
    );
  }

  const transitionInfo = TRANSITIONS.find((tr) => tr.type === transition.type);

  return (
    <div
      className="relative w-8 h-full flex items-center justify-center bg-brand-500/20 border-x border-brand-500/50 group cursor-pointer"
      onClick={onClick}
      title={`${transitionInfo ? t(transitionInfo.nameKey, transitionInfo.nameEn) : ''} (${transition.duration}ms)`}
    >
      <div className="text-brand-400">{transitionInfo?.icon}</div>
      <button
        onClick={(e) => {
          e.stopPropagation();
          onRemove();
        }}
        className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full items-center justify-center hidden group-hover:flex"
      >
        <X className="w-3 h-3 text-white" />
      </button>
    </div>
  );
}
