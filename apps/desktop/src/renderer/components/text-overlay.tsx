/**
 * Text overlay system for titles, lower thirds, and captions.
 * Supports styling, positioning, and animation of text on video.
 */

import { useState, useCallback } from 'react';
import {
  Type,
  AlignLeft,
  AlignCenter,
  AlignRight,
  Bold,
  Italic,
  Underline,
  Palette,
  Move,
  Clock,
  ChevronDown,
  ChevronUp,
  Plus,
  Trash2,
  Copy,
  Eye,
  EyeOff,
  Layers,
  Sparkles,
} from 'lucide-react';
import { cn } from '../lib/utils';

export type TextOverlayType = 'title' | 'subtitle' | 'lower_third' | 'caption' | 'custom';

export type TextAnimation =
  | 'none'
  | 'fade_in'
  | 'fade_out'
  | 'fade_in_out'
  | 'slide_up'
  | 'slide_down'
  | 'slide_left'
  | 'slide_right'
  | 'typewriter'
  | 'scale_in'
  | 'blur_in';

export type TextPosition =
  | 'top_left'
  | 'top_center'
  | 'top_right'
  | 'center_left'
  | 'center'
  | 'center_right'
  | 'bottom_left'
  | 'bottom_center'
  | 'bottom_right'
  | 'custom';

export interface TextStyle {
  fontFamily: string;
  fontSize: number;
  fontWeight: 'normal' | 'bold';
  fontStyle: 'normal' | 'italic';
  textDecoration: 'none' | 'underline';
  color: string;
  backgroundColor: string;
  backgroundOpacity: number;
  textAlign: 'left' | 'center' | 'right';
  letterSpacing: number;
  lineHeight: number;
  textShadow: boolean;
  textShadowColor: string;
  textShadowBlur: number;
}

export interface TextOverlay {
  id: string;
  type: TextOverlayType;
  text: string;
  position: TextPosition;
  customX?: number; // 0-100 percentage
  customY?: number; // 0-100 percentage
  style: TextStyle;
  animation: {
    in: TextAnimation;
    out: TextAnimation;
    inDuration: number; // ms
    outDuration: number; // ms
  };
  timing: {
    startTime: number; // ms from clip start
    duration: number; // ms
  };
  isVisible: boolean;
  zIndex: number;
}

const DEFAULT_STYLE: TextStyle = {
  fontFamily: 'Inter',
  fontSize: 48,
  fontWeight: 'bold',
  fontStyle: 'normal',
  textDecoration: 'none',
  color: '#FFFFFF',
  backgroundColor: '#000000',
  backgroundOpacity: 0,
  textAlign: 'center',
  letterSpacing: 0,
  lineHeight: 1.2,
  textShadow: true,
  textShadowColor: '#000000',
  textShadowBlur: 4,
};

const FONTS = [
  { value: 'Inter', label: 'Inter' },
  { value: 'Arial', label: 'Arial' },
  { value: 'Helvetica', label: 'Helvetica' },
  { value: 'Georgia', label: 'Georgia' },
  { value: 'Times New Roman', label: 'Times' },
  { value: 'Courier New', label: 'Courier' },
  { value: 'Verdana', label: 'Verdana' },
  { value: 'Impact', label: 'Impact' },
];

const ANIMATIONS: { value: TextAnimation; label: string }[] = [
  { value: 'none', label: 'None' },
  { value: 'fade_in', label: 'Fade In' },
  { value: 'fade_out', label: 'Fade Out' },
  { value: 'fade_in_out', label: 'Fade In/Out' },
  { value: 'slide_up', label: 'Slide Up' },
  { value: 'slide_down', label: 'Slide Down' },
  { value: 'slide_left', label: 'Slide Left' },
  { value: 'slide_right', label: 'Slide Right' },
  { value: 'typewriter', label: 'Typewriter' },
  { value: 'scale_in', label: 'Scale In' },
  { value: 'blur_in', label: 'Blur In' },
];

const POSITIONS: { value: TextPosition; label: string }[] = [
  { value: 'top_left', label: 'Top Left' },
  { value: 'top_center', label: 'Top Center' },
  { value: 'top_right', label: 'Top Right' },
  { value: 'center_left', label: 'Center Left' },
  { value: 'center', label: 'Center' },
  { value: 'center_right', label: 'Center Right' },
  { value: 'bottom_left', label: 'Bottom Left' },
  { value: 'bottom_center', label: 'Bottom Center' },
  { value: 'bottom_right', label: 'Bottom Right' },
  { value: 'custom', label: 'Custom' },
];

const PRESETS: { type: TextOverlayType; label: string; style: Partial<TextStyle> }[] = [
  {
    type: 'title',
    label: 'Title',
    style: {
      fontSize: 72,
      fontWeight: 'bold',
      textAlign: 'center',
    },
  },
  {
    type: 'subtitle',
    label: 'Subtitle',
    style: {
      fontSize: 36,
      fontWeight: 'normal',
      textAlign: 'center',
    },
  },
  {
    type: 'lower_third',
    label: 'Lower Third',
    style: {
      fontSize: 24,
      fontWeight: 'bold',
      textAlign: 'left',
      backgroundColor: '#000000',
      backgroundOpacity: 0.7,
    },
  },
  {
    type: 'caption',
    label: 'Caption',
    style: {
      fontSize: 20,
      fontWeight: 'normal',
      textAlign: 'center',
      backgroundColor: '#000000',
      backgroundOpacity: 0.5,
    },
  },
];

interface TextOverlayEditorProps {
  overlay: TextOverlay;
  onChange: (overlay: TextOverlay) => void;
  onDelete: () => void;
  onDuplicate: () => void;
}

function TextOverlayEditor({
  overlay,
  onChange,
  onDelete,
  onDuplicate,
}: TextOverlayEditorProps) {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(['text', 'style'])
  );

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

  const updateStyle = (updates: Partial<TextStyle>) => {
    onChange({
      ...overlay,
      style: { ...overlay.style, ...updates },
    });
  };

  const updateAnimation = (updates: Partial<TextOverlay['animation']>) => {
    onChange({
      ...overlay,
      animation: { ...overlay.animation, ...updates },
    });
  };

  const updateTiming = (updates: Partial<TextOverlay['timing']>) => {
    onChange({
      ...overlay,
      timing: { ...overlay.timing, ...updates },
    });
  };

  return (
    <div className="bg-surface-800/50 rounded-lg border border-surface-700 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 bg-surface-800">
        <div className="flex items-center gap-2">
          <Type className="w-4 h-4 text-brand-400" />
          <span className="text-sm font-medium truncate max-w-[120px]">
            {overlay.text || 'Untitled'}
          </span>
          <span className="text-xs text-surface-500 capitalize">
            {overlay.type.replace('_', ' ')}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => onChange({ ...overlay, isVisible: !overlay.isVisible })}
            className={cn(
              'p-1 rounded transition-colors',
              overlay.isVisible
                ? 'text-surface-400 hover:text-surface-200'
                : 'text-surface-600'
            )}
          >
            {overlay.isVisible ? (
              <Eye className="w-4 h-4" />
            ) : (
              <EyeOff className="w-4 h-4" />
            )}
          </button>
          <button
            onClick={onDuplicate}
            className="p-1 text-surface-400 hover:text-surface-200 rounded transition-colors"
          >
            <Copy className="w-4 h-4" />
          </button>
          <button
            onClick={onDelete}
            className="p-1 text-surface-400 hover:text-red-400 rounded transition-colors"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="p-3 space-y-3">
        {/* Text Content Section */}
        <div>
          <button
            onClick={() => toggleSection('text')}
            className="w-full flex items-center justify-between text-sm text-surface-300 mb-2"
          >
            <span>Text Content</span>
            {expandedSections.has('text') ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </button>
          {expandedSections.has('text') && (
            <textarea
              value={overlay.text}
              onChange={(e) => onChange({ ...overlay, text: e.target.value })}
              placeholder="Enter text..."
              rows={2}
              className="w-full px-3 py-2 bg-surface-900 border border-surface-700 rounded-lg text-sm resize-none"
            />
          )}
        </div>

        {/* Style Section */}
        <div>
          <button
            onClick={() => toggleSection('style')}
            className="w-full flex items-center justify-between text-sm text-surface-300 mb-2"
          >
            <span>Style</span>
            {expandedSections.has('style') ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </button>
          {expandedSections.has('style') && (
            <div className="space-y-3">
              {/* Font family */}
              <div>
                <label className="text-xs text-surface-500 mb-1 block">Font</label>
                <select
                  value={overlay.style.fontFamily}
                  onChange={(e) => updateStyle({ fontFamily: e.target.value })}
                  className="w-full px-2 py-1.5 bg-surface-900 border border-surface-700 rounded text-sm"
                >
                  {FONTS.map((font) => (
                    <option key={font.value} value={font.value}>
                      {font.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Font size */}
              <div>
                <label className="text-xs text-surface-500 mb-1 block">
                  Size: {overlay.style.fontSize}px
                </label>
                <input
                  type="range"
                  min="12"
                  max="200"
                  value={overlay.style.fontSize}
                  onChange={(e) => updateStyle({ fontSize: parseInt(e.target.value) })}
                  className="w-full accent-brand-500"
                />
              </div>

              {/* Font style buttons */}
              <div className="flex items-center gap-2">
                <button
                  onClick={() =>
                    updateStyle({
                      fontWeight: overlay.style.fontWeight === 'bold' ? 'normal' : 'bold',
                    })
                  }
                  className={cn(
                    'p-2 rounded transition-colors',
                    overlay.style.fontWeight === 'bold'
                      ? 'bg-brand-500/20 text-brand-400'
                      : 'bg-surface-700 hover:bg-surface-600'
                  )}
                >
                  <Bold className="w-4 h-4" />
                </button>
                <button
                  onClick={() =>
                    updateStyle({
                      fontStyle: overlay.style.fontStyle === 'italic' ? 'normal' : 'italic',
                    })
                  }
                  className={cn(
                    'p-2 rounded transition-colors',
                    overlay.style.fontStyle === 'italic'
                      ? 'bg-brand-500/20 text-brand-400'
                      : 'bg-surface-700 hover:bg-surface-600'
                  )}
                >
                  <Italic className="w-4 h-4" />
                </button>
                <button
                  onClick={() =>
                    updateStyle({
                      textDecoration:
                        overlay.style.textDecoration === 'underline' ? 'none' : 'underline',
                    })
                  }
                  className={cn(
                    'p-2 rounded transition-colors',
                    overlay.style.textDecoration === 'underline'
                      ? 'bg-brand-500/20 text-brand-400'
                      : 'bg-surface-700 hover:bg-surface-600'
                  )}
                >
                  <Underline className="w-4 h-4" />
                </button>
                <div className="w-px h-6 bg-surface-700" />
                <button
                  onClick={() => updateStyle({ textAlign: 'left' })}
                  className={cn(
                    'p-2 rounded transition-colors',
                    overlay.style.textAlign === 'left'
                      ? 'bg-brand-500/20 text-brand-400'
                      : 'bg-surface-700 hover:bg-surface-600'
                  )}
                >
                  <AlignLeft className="w-4 h-4" />
                </button>
                <button
                  onClick={() => updateStyle({ textAlign: 'center' })}
                  className={cn(
                    'p-2 rounded transition-colors',
                    overlay.style.textAlign === 'center'
                      ? 'bg-brand-500/20 text-brand-400'
                      : 'bg-surface-700 hover:bg-surface-600'
                  )}
                >
                  <AlignCenter className="w-4 h-4" />
                </button>
                <button
                  onClick={() => updateStyle({ textAlign: 'right' })}
                  className={cn(
                    'p-2 rounded transition-colors',
                    overlay.style.textAlign === 'right'
                      ? 'bg-brand-500/20 text-brand-400'
                      : 'bg-surface-700 hover:bg-surface-600'
                  )}
                >
                  <AlignRight className="w-4 h-4" />
                </button>
              </div>

              {/* Colors */}
              <div className="flex items-center gap-3">
                <div>
                  <label className="text-xs text-surface-500 mb-1 block">Text</label>
                  <input
                    type="color"
                    value={overlay.style.color}
                    onChange={(e) => updateStyle({ color: e.target.value })}
                    className="w-8 h-8 rounded border border-surface-700 cursor-pointer"
                  />
                </div>
                <div>
                  <label className="text-xs text-surface-500 mb-1 block">Background</label>
                  <input
                    type="color"
                    value={overlay.style.backgroundColor}
                    onChange={(e) => updateStyle({ backgroundColor: e.target.value })}
                    className="w-8 h-8 rounded border border-surface-700 cursor-pointer"
                  />
                </div>
                <div className="flex-1">
                  <label className="text-xs text-surface-500 mb-1 block">
                    Opacity: {Math.round(overlay.style.backgroundOpacity * 100)}%
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={overlay.style.backgroundOpacity}
                    onChange={(e) =>
                      updateStyle({ backgroundOpacity: parseFloat(e.target.value) })
                    }
                    className="w-full accent-brand-500"
                  />
                </div>
              </div>

              {/* Text shadow */}
              <div className="flex items-center gap-3">
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={overlay.style.textShadow}
                    onChange={(e) => updateStyle({ textShadow: e.target.checked })}
                    className="accent-brand-500"
                  />
                  Shadow
                </label>
                {overlay.style.textShadow && (
                  <>
                    <input
                      type="color"
                      value={overlay.style.textShadowColor}
                      onChange={(e) => updateStyle({ textShadowColor: e.target.value })}
                      className="w-6 h-6 rounded border border-surface-700 cursor-pointer"
                    />
                    <input
                      type="range"
                      min="0"
                      max="20"
                      value={overlay.style.textShadowBlur}
                      onChange={(e) =>
                        updateStyle({ textShadowBlur: parseInt(e.target.value) })
                      }
                      className="w-16 accent-brand-500"
                    />
                  </>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Position Section */}
        <div>
          <button
            onClick={() => toggleSection('position')}
            className="w-full flex items-center justify-between text-sm text-surface-300 mb-2"
          >
            <span>Position</span>
            {expandedSections.has('position') ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </button>
          {expandedSections.has('position') && (
            <div className="space-y-3">
              <select
                value={overlay.position}
                onChange={(e) =>
                  onChange({ ...overlay, position: e.target.value as TextPosition })
                }
                className="w-full px-2 py-1.5 bg-surface-900 border border-surface-700 rounded text-sm"
              >
                {POSITIONS.map((pos) => (
                  <option key={pos.value} value={pos.value}>
                    {pos.label}
                  </option>
                ))}
              </select>

              {overlay.position === 'custom' && (
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-surface-500 mb-1 block">
                      X: {overlay.customX ?? 50}%
                    </label>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={overlay.customX ?? 50}
                      onChange={(e) =>
                        onChange({ ...overlay, customX: parseInt(e.target.value) })
                      }
                      className="w-full accent-brand-500"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-surface-500 mb-1 block">
                      Y: {overlay.customY ?? 50}%
                    </label>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={overlay.customY ?? 50}
                      onChange={(e) =>
                        onChange({ ...overlay, customY: parseInt(e.target.value) })
                      }
                      className="w-full accent-brand-500"
                    />
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Animation Section */}
        <div>
          <button
            onClick={() => toggleSection('animation')}
            className="w-full flex items-center justify-between text-sm text-surface-300 mb-2"
          >
            <span>Animation</span>
            {expandedSections.has('animation') ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </button>
          {expandedSections.has('animation') && (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-surface-500 mb-1 block">In</label>
                  <select
                    value={overlay.animation.in}
                    onChange={(e) =>
                      updateAnimation({ in: e.target.value as TextAnimation })
                    }
                    className="w-full px-2 py-1.5 bg-surface-900 border border-surface-700 rounded text-sm"
                  >
                    {ANIMATIONS.map((anim) => (
                      <option key={anim.value} value={anim.value}>
                        {anim.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-surface-500 mb-1 block">Out</label>
                  <select
                    value={overlay.animation.out}
                    onChange={(e) =>
                      updateAnimation({ out: e.target.value as TextAnimation })
                    }
                    className="w-full px-2 py-1.5 bg-surface-900 border border-surface-700 rounded text-sm"
                  >
                    {ANIMATIONS.map((anim) => (
                      <option key={anim.value} value={anim.value}>
                        {anim.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-surface-500 mb-1 block">
                    In Duration: {overlay.animation.inDuration}ms
                  </label>
                  <input
                    type="range"
                    min="100"
                    max="2000"
                    step="100"
                    value={overlay.animation.inDuration}
                    onChange={(e) =>
                      updateAnimation({ inDuration: parseInt(e.target.value) })
                    }
                    className="w-full accent-brand-500"
                  />
                </div>
                <div>
                  <label className="text-xs text-surface-500 mb-1 block">
                    Out Duration: {overlay.animation.outDuration}ms
                  </label>
                  <input
                    type="range"
                    min="100"
                    max="2000"
                    step="100"
                    value={overlay.animation.outDuration}
                    onChange={(e) =>
                      updateAnimation({ outDuration: parseInt(e.target.value) })
                    }
                    className="w-full accent-brand-500"
                  />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Timing Section */}
        <div>
          <button
            onClick={() => toggleSection('timing')}
            className="w-full flex items-center justify-between text-sm text-surface-300 mb-2"
          >
            <span>Timing</span>
            {expandedSections.has('timing') ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </button>
          {expandedSections.has('timing') && (
            <div className="space-y-3">
              <div>
                <label className="text-xs text-surface-500 mb-1 block">
                  Start: {(overlay.timing.startTime / 1000).toFixed(1)}s
                </label>
                <input
                  type="range"
                  min="0"
                  max="60000"
                  step="100"
                  value={overlay.timing.startTime}
                  onChange={(e) => updateTiming({ startTime: parseInt(e.target.value) })}
                  className="w-full accent-brand-500"
                />
              </div>
              <div>
                <label className="text-xs text-surface-500 mb-1 block">
                  Duration: {(overlay.timing.duration / 1000).toFixed(1)}s
                </label>
                <input
                  type="range"
                  min="500"
                  max="30000"
                  step="500"
                  value={overlay.timing.duration}
                  onChange={(e) => updateTiming({ duration: parseInt(e.target.value) })}
                  className="w-full accent-brand-500"
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

interface TextOverlayPanelProps {
  overlays: TextOverlay[];
  onChange: (overlays: TextOverlay[]) => void;
  selectedId?: string | null;
  onSelectOverlay?: (id: string | null) => void;
}

export function TextOverlayPanel({
  overlays,
  onChange,
  selectedId,
  onSelectOverlay,
}: TextOverlayPanelProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  const createOverlay = useCallback(
    (type: TextOverlayType) => {
      const preset = PRESETS.find((p) => p.type === type);
      const newOverlay: TextOverlay = {
        id: `text_${Date.now()}`,
        type,
        text: type === 'lower_third' ? 'Name Here\nTitle' : 'Enter text',
        position: type === 'lower_third' ? 'bottom_left' : 'center',
        style: {
          ...DEFAULT_STYLE,
          ...preset?.style,
        },
        animation: {
          in: 'fade_in',
          out: 'fade_out',
          inDuration: 500,
          outDuration: 500,
        },
        timing: {
          startTime: 0,
          duration: 5000,
        },
        isVisible: true,
        zIndex: overlays.length + 1,
      };
      onChange([...overlays, newOverlay]);
      onSelectOverlay?.(newOverlay.id);
    },
    [overlays, onChange, onSelectOverlay]
  );

  const updateOverlay = useCallback(
    (id: string, updated: TextOverlay) => {
      onChange(overlays.map((o) => (o.id === id ? updated : o)));
    },
    [overlays, onChange]
  );

  const deleteOverlay = useCallback(
    (id: string) => {
      onChange(overlays.filter((o) => o.id !== id));
      if (selectedId === id) {
        onSelectOverlay?.(null);
      }
    },
    [overlays, onChange, selectedId, onSelectOverlay]
  );

  const duplicateOverlay = useCallback(
    (id: string) => {
      const overlay = overlays.find((o) => o.id === id);
      if (!overlay) return;

      const duplicate: TextOverlay = {
        ...overlay,
        id: `text_${Date.now()}`,
        text: overlay.text + ' (copy)',
        zIndex: overlays.length + 1,
      };
      onChange([...overlays, duplicate]);
      onSelectOverlay?.(duplicate.id);
    },
    [overlays, onChange, onSelectOverlay]
  );

  return (
    <div className="bg-surface-900 border border-surface-800 rounded-xl overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-surface-800/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <Type className="w-5 h-5 text-brand-400" />
          <span className="font-medium">Text Overlays</span>
          <span className="text-sm text-surface-400">{overlays.length}</span>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-5 h-5 text-surface-400" />
        ) : (
          <ChevronDown className="w-5 h-5 text-surface-400" />
        )}
      </button>

      {isExpanded && (
        <div className="p-4 pt-0">
          {/* Quick add presets */}
          <div className="flex items-center gap-2 mb-4 flex-wrap">
            {PRESETS.map((preset) => (
              <button
                key={preset.type}
                onClick={() => createOverlay(preset.type)}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-surface-800 hover:bg-surface-700 border border-surface-700 rounded-lg text-sm transition-colors"
              >
                <Plus className="w-3 h-3" />
                {preset.label}
              </button>
            ))}
          </div>

          {/* Overlay list */}
          {overlays.length > 0 ? (
            <div className="space-y-3 max-h-[500px] overflow-y-auto">
              {overlays.map((overlay) => (
                <div
                  key={overlay.id}
                  onClick={() => onSelectOverlay?.(overlay.id)}
                  className={cn(
                    'cursor-pointer transition-colors',
                    selectedId === overlay.id && 'ring-1 ring-brand-500 rounded-lg'
                  )}
                >
                  <TextOverlayEditor
                    overlay={overlay}
                    onChange={(updated) => updateOverlay(overlay.id, updated)}
                    onDelete={() => deleteOverlay(overlay.id)}
                    onDuplicate={() => duplicateOverlay(overlay.id)}
                  />
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-surface-400">
              <Type className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>No text overlays</p>
              <p className="text-sm text-surface-500 mt-1">
                Click a preset above to add text
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Preview renderer for text overlay.
 */
export function TextOverlayPreview({
  overlay,
  containerWidth,
  containerHeight,
  isEditing,
  onPositionChange,
}: {
  overlay: TextOverlay;
  containerWidth: number;
  containerHeight: number;
  isEditing?: boolean;
  onPositionChange?: (x: number, y: number) => void;
}) {
  if (!overlay.isVisible) return null;

  const getPositionStyle = (): React.CSSProperties => {
    switch (overlay.position) {
      case 'top_left':
        return { top: '5%', left: '5%', transform: 'none' };
      case 'top_center':
        return { top: '5%', left: '50%', transform: 'translateX(-50%)' };
      case 'top_right':
        return { top: '5%', right: '5%', transform: 'none' };
      case 'center_left':
        return { top: '50%', left: '5%', transform: 'translateY(-50%)' };
      case 'center':
        return { top: '50%', left: '50%', transform: 'translate(-50%, -50%)' };
      case 'center_right':
        return { top: '50%', right: '5%', transform: 'translateY(-50%)' };
      case 'bottom_left':
        return { bottom: '10%', left: '5%', transform: 'none' };
      case 'bottom_center':
        return { bottom: '10%', left: '50%', transform: 'translateX(-50%)' };
      case 'bottom_right':
        return { bottom: '10%', right: '5%', transform: 'none' };
      case 'custom':
        return {
          top: `${overlay.customY ?? 50}%`,
          left: `${overlay.customX ?? 50}%`,
          transform: 'translate(-50%, -50%)',
        };
      default:
        return { top: '50%', left: '50%', transform: 'translate(-50%, -50%)' };
    }
  };

  const style: React.CSSProperties = {
    position: 'absolute',
    ...getPositionStyle(),
    fontFamily: overlay.style.fontFamily,
    fontSize: `${overlay.style.fontSize}px`,
    fontWeight: overlay.style.fontWeight,
    fontStyle: overlay.style.fontStyle,
    textDecoration: overlay.style.textDecoration,
    color: overlay.style.color,
    textAlign: overlay.style.textAlign,
    letterSpacing: `${overlay.style.letterSpacing}px`,
    lineHeight: overlay.style.lineHeight,
    padding: overlay.style.backgroundOpacity > 0 ? '8px 16px' : '0',
    backgroundColor:
      overlay.style.backgroundOpacity > 0
        ? `${overlay.style.backgroundColor}${Math.round(overlay.style.backgroundOpacity * 255)
            .toString(16)
            .padStart(2, '0')}`
        : 'transparent',
    textShadow: overlay.style.textShadow
      ? `0 2px ${overlay.style.textShadowBlur}px ${overlay.style.textShadowColor}`
      : 'none',
    whiteSpace: 'pre-line',
    zIndex: overlay.zIndex,
  };

  return (
    <div
      style={style}
      className={cn(isEditing && 'ring-2 ring-brand-500 ring-offset-2 ring-offset-transparent')}
    >
      {overlay.text}
    </div>
  );
}

/**
 * Compact text overlay button for toolbars.
 */
export function TextOverlayButton({
  onClick,
  hasOverlays,
}: {
  onClick: () => void;
  hasOverlays?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex items-center gap-2 px-3 py-2 border rounded-lg transition-colors',
        hasOverlays
          ? 'bg-brand-500/20 border-brand-500/50 text-brand-400'
          : 'bg-surface-800 border-surface-700 hover:bg-surface-700'
      )}
    >
      <Type className="w-4 h-4" />
      <span className="text-sm">Text</span>
      {hasOverlays && (
        <span className="w-5 h-5 bg-brand-500 rounded-full text-xs text-white flex items-center justify-center">
          !
        </span>
      )}
    </button>
  );
}
