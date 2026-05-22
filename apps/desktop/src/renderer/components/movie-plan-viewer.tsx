/**
 * Movie Plan Viewer component.
 *
 * Displays the generated movie plan with all analysis sections
 * and allows the user to approve it.
 */

import { useState } from 'react';
import {
  Film,
  Users,
  MapPin,
  Clock,
  Palette,
  Camera,
  AlertTriangle,
  Check,
  ChevronDown,
  ChevronRight,
  Sparkles,
  Clapperboard,
} from 'lucide-react';
import { cn } from '../lib/utils';

interface MoviePlan {
  screenplayId: string;
  generatedAt: string;
  aiModel: string;
  title: string;
  logline: string;
  genre: string;
  tone: string;
  themes: string[];
  estimatedRuntimeMinutes: number;
  visualStyle: {
    overall_look?: string;
    lighting_style?: string;
    camera_movement?: string;
    aspect_ratio?: string;
    frame_rate?: number;
  };
  colorPalette: string[];
  cinematographyNotes: string;
  characters: Array<{
    name: string;
    dialogue_count: number;
    scene_count: number;
    estimated_screen_time_percent: number;
  }>;
  protagonist?: string;
  antagonist?: string;
  scenes: Array<{
    scene_number: string;
    location: string;
    time_of_day: string;
    estimated_duration_seconds: number;
    suggested_shot_count: number;
  }>;
  actStructure: {
    act_1: string[];
    act_2: string[];
    act_3: string[];
  };
  locationRequirements: Array<{
    name: string;
    scene_type: string;
    scene_count: number;
  }>;
  propRequirements: string[];
  specialEffectsNotes: string[];
  generationNotes: string[];
  warnings: string[];
}

interface MoviePlanViewerProps {
  plan: MoviePlan;
  onApprove: () => void;
  onRegenerate: () => void;
  isApproving?: boolean;
  isRegenerating?: boolean;
}

function CollapsibleSection({
  title,
  icon: Icon,
  defaultOpen = false,
  children,
}: {
  title: string;
  icon: React.ElementType;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="border border-surface-800 rounded-lg overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-4 bg-surface-900 hover:bg-surface-800 transition-colors"
      >
        <div className="flex items-center gap-3">
          <Icon className="w-5 h-5 text-brand-400" />
          <span className="font-medium">{title}</span>
        </div>
        {isOpen ? (
          <ChevronDown className="w-5 h-5 text-surface-400" />
        ) : (
          <ChevronRight className="w-5 h-5 text-surface-400" />
        )}
      </button>
      {isOpen && <div className="p-4 border-t border-surface-800">{children}</div>}
    </div>
  );
}

export function MoviePlanViewer({
  plan,
  onApprove,
  onRegenerate,
  isApproving = false,
  isRegenerating = false,
}: MoviePlanViewerProps) {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold">{plan.title}</h2>
          <p className="text-surface-400 mt-1 max-w-2xl">{plan.logline}</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={onRegenerate}
            disabled={isRegenerating || isApproving}
            className="btn-secondary"
          >
            <Sparkles className="w-4 h-4 mr-2" />
            {isRegenerating ? 'Regenerating...' : 'Regenerate'}
          </button>
          <button
            onClick={onApprove}
            disabled={isApproving || isRegenerating}
            className="btn-primary"
          >
            <Check className="w-4 h-4 mr-2" />
            {isApproving ? 'Approving...' : 'Approve Plan'}
          </button>
        </div>
      </div>

      {/* Warnings */}
      {plan.warnings.length > 0 && (
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4">
          <div className="flex items-center gap-2 text-yellow-400 mb-2">
            <AlertTriangle className="w-5 h-5" />
            <span className="font-medium">Production Warnings</span>
          </div>
          <ul className="space-y-1 text-sm text-yellow-200">
            {plan.warnings.map((warning, i) => (
              <li key={i}>{warning}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Quick Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="card">
          <div className="text-surface-400 text-sm">Genre</div>
          <div className="text-lg font-semibold capitalize">{plan.genre}</div>
        </div>
        <div className="card">
          <div className="text-surface-400 text-sm">Runtime</div>
          <div className="text-lg font-semibold">~{plan.estimatedRuntimeMinutes} min</div>
        </div>
        <div className="card">
          <div className="text-surface-400 text-sm">Scenes</div>
          <div className="text-lg font-semibold">{plan.scenes.length}</div>
        </div>
        <div className="card">
          <div className="text-surface-400 text-sm">Characters</div>
          <div className="text-lg font-semibold">{plan.characters.length}</div>
        </div>
      </div>

      {/* Themes & Tone */}
      <div className="card">
        <h3 className="font-medium mb-3">Themes & Tone</h3>
        <div className="flex flex-wrap gap-2 mb-3">
          {plan.themes.map((theme) => (
            <span
              key={theme}
              className="px-3 py-1 bg-brand-500/20 text-brand-300 rounded-full text-sm capitalize"
            >
              {theme}
            </span>
          ))}
        </div>
        <p className="text-surface-300">{plan.tone}</p>
      </div>

      {/* Collapsible Sections */}
      <div className="space-y-3">
        {/* Visual Style */}
        <CollapsibleSection title="Visual Style" icon={Palette} defaultOpen>
          <div className="space-y-4">
            {/* Color Palette */}
            <div>
              <h4 className="text-sm text-surface-400 mb-2">Color Palette</h4>
              <div className="flex gap-2">
                {plan.colorPalette.map((color) => (
                  <div key={color} className="flex flex-col items-center">
                    <div
                      className="w-12 h-12 rounded-lg shadow-inner"
                      style={{ backgroundColor: color }}
                    />
                    <span className="text-xs text-surface-500 mt-1">{color}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Style Details */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <h4 className="text-sm text-surface-400 mb-1">Overall Look</h4>
                <p className="text-surface-200">{plan.visualStyle.overall_look}</p>
              </div>
              <div>
                <h4 className="text-sm text-surface-400 mb-1">Lighting</h4>
                <p className="text-surface-200">{plan.visualStyle.lighting_style}</p>
              </div>
              <div>
                <h4 className="text-sm text-surface-400 mb-1">Camera Movement</h4>
                <p className="text-surface-200">{plan.visualStyle.camera_movement}</p>
              </div>
              <div>
                <h4 className="text-sm text-surface-400 mb-1">Aspect Ratio</h4>
                <p className="text-surface-200">{plan.visualStyle.aspect_ratio}</p>
              </div>
            </div>

            {/* Cinematography Notes */}
            <div>
              <h4 className="text-sm text-surface-400 mb-1">Cinematography Notes</h4>
              <p className="text-surface-200 text-sm">{plan.cinematographyNotes}</p>
            </div>
          </div>
        </CollapsibleSection>

        {/* Characters */}
        <CollapsibleSection title="Characters" icon={Users} defaultOpen>
          <div className="space-y-4">
            {/* Protagonist & Antagonist */}
            <div className="flex gap-4">
              {plan.protagonist && (
                <div className="flex-1 bg-green-500/10 border border-green-500/30 rounded-lg p-3">
                  <div className="text-sm text-green-400 mb-1">Protagonist</div>
                  <div className="font-medium">{plan.protagonist}</div>
                </div>
              )}
              {plan.antagonist && (
                <div className="flex-1 bg-red-500/10 border border-red-500/30 rounded-lg p-3">
                  <div className="text-sm text-red-400 mb-1">Antagonist</div>
                  <div className="font-medium">{plan.antagonist}</div>
                </div>
              )}
            </div>

            {/* Character List */}
            <div className="space-y-2">
              {plan.characters.map((char) => (
                <div
                  key={char.name}
                  className="flex items-center justify-between p-3 bg-surface-800/50 rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-surface-700 flex items-center justify-center text-sm font-medium">
                      {char.name[0]}
                    </div>
                    <div>
                      <div className="font-medium">{char.name}</div>
                      <div className="text-sm text-surface-400">
                        {char.scene_count} scenes, {char.dialogue_count} lines
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm text-surface-300">
                      {char.estimated_screen_time_percent}%
                    </div>
                    <div className="text-xs text-surface-500">screen time</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </CollapsibleSection>

        {/* Act Structure */}
        <CollapsibleSection title="Act Structure" icon={Film}>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <h4 className="text-sm text-surface-400 mb-2">Act 1 - Setup</h4>
              <div className="text-surface-200">
                Scenes: {plan.actStructure.act_1?.join(', ') || 'None'}
              </div>
              <div className="text-xs text-surface-500 mt-1">
                {plan.actStructure.act_1?.length || 0} scenes
              </div>
            </div>
            <div>
              <h4 className="text-sm text-surface-400 mb-2">Act 2 - Confrontation</h4>
              <div className="text-surface-200">
                Scenes: {plan.actStructure.act_2?.join(', ') || 'None'}
              </div>
              <div className="text-xs text-surface-500 mt-1">
                {plan.actStructure.act_2?.length || 0} scenes
              </div>
            </div>
            <div>
              <h4 className="text-sm text-surface-400 mb-2">Act 3 - Resolution</h4>
              <div className="text-surface-200">
                Scenes: {plan.actStructure.act_3?.join(', ') || 'None'}
              </div>
              <div className="text-xs text-surface-500 mt-1">
                {plan.actStructure.act_3?.length || 0} scenes
              </div>
            </div>
          </div>
        </CollapsibleSection>

        {/* Scenes */}
        <CollapsibleSection title="Scene Breakdown" icon={Clapperboard}>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {plan.scenes.map((scene) => (
              <div
                key={scene.scene_number}
                className="flex items-center justify-between p-3 bg-surface-800/50 rounded-lg"
              >
                <div>
                  <div className="font-medium">Scene {scene.scene_number}</div>
                  <div className="text-sm text-surface-400">
                    {scene.location} - {scene.time_of_day}
                  </div>
                </div>
                <div className="text-right text-sm">
                  <div className="text-surface-300">
                    ~{Math.round(scene.estimated_duration_seconds / 60)} min
                  </div>
                  <div className="text-surface-500">{scene.suggested_shot_count} shots</div>
                </div>
              </div>
            ))}
          </div>
        </CollapsibleSection>

        {/* Locations */}
        <CollapsibleSection title="Locations" icon={MapPin}>
          <div className="grid grid-cols-2 gap-3">
            {plan.locationRequirements.map((loc) => (
              <div key={loc.name} className="p-3 bg-surface-800/50 rounded-lg">
                <div className="font-medium">{loc.name}</div>
                <div className="text-sm text-surface-400">
                  {loc.scene_type} - {loc.scene_count} scenes
                </div>
              </div>
            ))}
          </div>
        </CollapsibleSection>

        {/* Production Notes */}
        <CollapsibleSection title="Production Notes" icon={Camera}>
          <div className="space-y-4">
            {/* Props */}
            {plan.propRequirements.length > 0 && (
              <div>
                <h4 className="text-sm text-surface-400 mb-2">Props Required</h4>
                <div className="flex flex-wrap gap-2">
                  {plan.propRequirements.map((prop) => (
                    <span
                      key={prop}
                      className="px-2 py-1 bg-surface-800 rounded text-sm capitalize"
                    >
                      {prop}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Special Effects */}
            {plan.specialEffectsNotes.length > 0 && (
              <div>
                <h4 className="text-sm text-surface-400 mb-2">Special Effects</h4>
                <ul className="space-y-1">
                  {plan.specialEffectsNotes.map((note, i) => (
                    <li key={i} className="text-surface-200 text-sm">
                      {note}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </CollapsibleSection>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between pt-4 border-t border-surface-800">
        <div className="text-sm text-surface-500">
          Generated by {plan.aiModel} on {new Date(plan.generatedAt).toLocaleDateString()}
        </div>
        <div className="flex gap-2">
          <button
            onClick={onRegenerate}
            disabled={isRegenerating || isApproving}
            className="btn-secondary"
          >
            {isRegenerating ? 'Regenerating...' : 'Regenerate Plan'}
          </button>
          <button
            onClick={onApprove}
            disabled={isApproving || isRegenerating}
            className="btn-primary"
          >
            <Check className="w-4 h-4 mr-2" />
            {isApproving ? 'Approving...' : 'Approve & Continue'}
          </button>
        </div>
      </div>
    </div>
  );
}
