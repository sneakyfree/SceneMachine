/**
 * Shot card component for displaying and editing individual shots.
 */

import { useState } from 'react';
import {
  Video,
  Camera,
  Clock,
  Edit2,
  Trash2,
  ChevronDown,
  ChevronUp,
  GripVertical,
  Users,
  DollarSign,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { useGenerationStore } from '../stores/generation-store';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';

interface Shot {
  id: string;
  shotNumber: string;
  sequenceNumber: number;
  shotType: string;
  cameraMovement: string;
  description: string;
  dialogue?: string;
  action?: string;
  characterIds?: string[];
  durationSeconds: number;
  compositionNotes?: string;
  lightingNotes?: string;
  state: string;
}

interface Character {
  id: string;
  name: string;
}

interface ShotCardProps {
  shot: Shot;
  characters?: Character[];
  shotTypes: Array<{ value: string; label: string; description: string }>;
  cameraMovements: Array<{ value: string; label: string; description: string }>;
  onUpdate: (shotId: string, data: Partial<Shot>) => void;
  onDelete: (shotId: string) => void;
  disabled?: boolean;
  isDragging?: boolean;
  showCost?: boolean;
}

// Inline cost badge component for shots
function ShotCostBadge({
  provider,
  modelId,
  durationSeconds,
}: {
  provider: string;
  modelId?: string;
  durationSeconds: number;
}) {
  const { data: estimate, isLoading } = useQuery({
    queryKey: ['shot-cost', provider, modelId, durationSeconds],
    queryFn: () =>
      api.estimateCost({
        provider,
        model_id: modelId,
        duration_seconds: durationSeconds,
      }),
    enabled: !!provider,
    staleTime: 60000, // Cache for 1 minute
  });

  if (isLoading) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs bg-surface-700 text-surface-400">
        <DollarSign className="w-3 h-3" />
        ...
      </span>
    );
  }

  if (!estimate) {
    return null;
  }

  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs bg-surface-800 text-surface-300">
      <DollarSign className="w-3 h-3" />${estimate.total_cost.toFixed(2)}
    </span>
  );
}

export function ShotCard({
  shot,
  characters = [],
  shotTypes,
  cameraMovements,
  onUpdate,
  onDelete,
  disabled = false,
  isDragging = false,
  showCost = false,
}: ShotCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editData, setEditData] = useState<Partial<Shot>>({});

  // Get provider info for cost estimation
  const { selectedProvider, selectedModel } = useGenerationStore();

  const shotType = shotTypes.find((st) => st.value === shot.shotType);
  const cameraMovement = cameraMovements.find((cm) => cm.value === shot.cameraMovement);
  const shotCharacters = characters.filter((c) => shot.characterIds?.includes(c.id));

  const handleStartEdit = () => {
    setEditData({
      shotType: shot.shotType,
      cameraMovement: shot.cameraMovement,
      description: shot.description,
      durationSeconds: shot.durationSeconds,
      compositionNotes: shot.compositionNotes,
      lightingNotes: shot.lightingNotes,
    });
    setIsEditing(true);
  };

  const handleSaveEdit = () => {
    onUpdate(shot.id, editData);
    setIsEditing(false);
    setEditData({});
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
    setEditData({});
  };

  return (
    <div
      className={cn(
        'bg-surface-800/50 border border-surface-700 rounded-lg transition-all',
        isExpanded && 'ring-1 ring-brand-500/30',
        isDragging && 'opacity-50 scale-95',
        disabled && 'opacity-50 pointer-events-none'
      )}
    >
      {/* Header Row */}
      <div className="flex items-center gap-3 p-3">
        {/* Drag Handle */}
        <div className="cursor-grab text-surface-500 hover:text-surface-400">
          <GripVertical className="w-4 h-4" />
        </div>

        {/* Shot Number Badge */}
        <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-brand-500/20 text-brand-400 font-mono text-sm font-bold">
          {shot.shotNumber.split('-').pop()}
        </div>

        {/* Shot Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-medium">{shotType?.label || shot.shotType}</span>
            <span className="text-surface-500">•</span>
            <span className="text-sm text-surface-400">
              {cameraMovement?.label || shot.cameraMovement}
            </span>
          </div>
          <p className="text-sm text-surface-400 truncate">{shot.description}</p>
        </div>

        {/* Duration */}
        <div className="flex items-center gap-1 text-surface-400 text-sm">
          <Clock className="w-3.5 h-3.5" />
          <span>{shot.durationSeconds.toFixed(1)}s</span>
        </div>

        {/* Characters */}
        {shotCharacters.length > 0 && (
          <div className="flex items-center gap-1 text-surface-400 text-sm">
            <Users className="w-3.5 h-3.5" />
            <span>{shotCharacters.length}</span>
          </div>
        )}

        {/* Cost Estimate */}
        {showCost && selectedProvider && shot.state === 'planned' && (
          <ShotCostBadge
            provider={selectedProvider}
            modelId={selectedModel || undefined}
            durationSeconds={shot.durationSeconds}
          />
        )}

        {/* Actions */}
        <div className="flex items-center gap-1">
          <button
            onClick={handleStartEdit}
            disabled={disabled || isEditing}
            className="icon-btn p-2 text-surface-400 hover:text-surface-300 hover:bg-surface-700 rounded transition-colors"
            title="Edit shot"
            aria-label="Edit shot"
          >
            <Edit2 className="w-4 h-4" />
          </button>
          <button
            onClick={() => onDelete(shot.id)}
            disabled={disabled}
            className="icon-btn p-2 text-surface-400 hover:text-red-400 hover:bg-surface-700 rounded transition-colors"
            title="Delete shot"
            aria-label="Delete shot"
          >
            <Trash2 className="w-4 h-4" />
          </button>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="icon-btn p-2 text-surface-400 hover:text-surface-300 hover:bg-surface-700 rounded transition-colors"
            aria-label={isExpanded ? 'Collapse shot details' : 'Expand shot details'}
          >
            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="border-t border-surface-700 p-4">
          {isEditing ? (
            /* Edit Mode */
            <div className="space-y-4">
              {/* Shot Type & Camera Movement */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-surface-400 mb-1">Shot Type</label>
                  <select
                    value={editData.shotType || shot.shotType}
                    onChange={(e) => setEditData({ ...editData, shotType: e.target.value })}
                    className="w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg text-sm focus:outline-none focus:border-brand-500"
                  >
                    {shotTypes.map((st) => (
                      <option key={st.value} value={st.value}>
                        {st.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-surface-400 mb-1">Camera Movement</label>
                  <select
                    value={editData.cameraMovement || shot.cameraMovement}
                    onChange={(e) => setEditData({ ...editData, cameraMovement: e.target.value })}
                    className="w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg text-sm focus:outline-none focus:border-brand-500"
                  >
                    {cameraMovements.map((cm) => (
                      <option key={cm.value} value={cm.value}>
                        {cm.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Description */}
              <div>
                <label className="block text-sm text-surface-400 mb-1">Description</label>
                <textarea
                  value={editData.description ?? shot.description}
                  onChange={(e) => setEditData({ ...editData, description: e.target.value })}
                  rows={2}
                  className="w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg text-sm focus:outline-none focus:border-brand-500 resize-none"
                />
              </div>

              {/* Duration */}
              <div>
                <label
                  htmlFor={`duration-${shot.id}`}
                  className="block text-sm text-surface-400 mb-1"
                >
                  Duration (seconds)
                </label>
                <input
                  id={`duration-${shot.id}`}
                  type="number"
                  value={editData.durationSeconds ?? shot.durationSeconds}
                  onChange={(e) =>
                    setEditData({
                      ...editData,
                      durationSeconds: parseFloat(e.target.value) || 1,
                    })
                  }
                  min={0.5}
                  max={30}
                  step={0.5}
                  className="w-32 px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg text-sm focus:outline-none focus:border-brand-500"
                />
              </div>

              {/* Notes */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-surface-400 mb-1">Composition Notes</label>
                  <textarea
                    value={editData.compositionNotes ?? shot.compositionNotes ?? ''}
                    onChange={(e) => setEditData({ ...editData, compositionNotes: e.target.value })}
                    rows={2}
                    placeholder="Framing, rule of thirds, etc."
                    className="w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg text-sm focus:outline-none focus:border-brand-500 resize-none"
                  />
                </div>
                <div>
                  <label className="block text-sm text-surface-400 mb-1">Lighting Notes</label>
                  <textarea
                    value={editData.lightingNotes ?? shot.lightingNotes ?? ''}
                    onChange={(e) => setEditData({ ...editData, lightingNotes: e.target.value })}
                    rows={2}
                    placeholder="Key light, mood, etc."
                    className="w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg text-sm focus:outline-none focus:border-brand-500 resize-none"
                  />
                </div>
              </div>

              {/* Edit Actions */}
              <div className="flex justify-end gap-2">
                <button
                  onClick={handleCancelEdit}
                  className="px-3 py-1.5 text-sm text-surface-400 hover:text-surface-300 hover:bg-surface-700 rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveEdit}
                  className="px-3 py-1.5 text-sm bg-brand-500 hover:bg-brand-600 text-white rounded-lg transition-colors"
                >
                  Save Changes
                </button>
              </div>
            </div>
          ) : (
            /* View Mode */
            <div className="space-y-4">
              {/* Type Descriptions */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="flex items-center gap-2 text-sm text-surface-400 mb-1">
                    <Video className="w-4 h-4" />
                    <span>Shot Type</span>
                  </div>
                  <p className="text-sm">{shotType?.label}</p>
                  <p className="text-xs text-surface-500 mt-0.5">{shotType?.description}</p>
                </div>
                <div>
                  <div className="flex items-center gap-2 text-sm text-surface-400 mb-1">
                    <Camera className="w-4 h-4" />
                    <span>Camera</span>
                  </div>
                  <p className="text-sm">{cameraMovement?.label}</p>
                  <p className="text-xs text-surface-500 mt-0.5">{cameraMovement?.description}</p>
                </div>
              </div>

              {/* Full Description */}
              <div>
                <h4 className="text-sm text-surface-400 mb-1">Description</h4>
                <p className="text-sm">{shot.description}</p>
              </div>

              {/* Dialogue */}
              {shot.dialogue && (
                <div>
                  <h4 className="text-sm text-surface-400 mb-1">Dialogue</h4>
                  <p className="text-sm italic text-surface-300">"{shot.dialogue}"</p>
                </div>
              )}

              {/* Action */}
              {shot.action && (
                <div>
                  <h4 className="text-sm text-surface-400 mb-1">Action</h4>
                  <p className="text-sm text-surface-300">{shot.action}</p>
                </div>
              )}

              {/* Characters */}
              {shotCharacters.length > 0 && (
                <div>
                  <h4 className="text-sm text-surface-400 mb-1">Characters</h4>
                  <div className="flex flex-wrap gap-2">
                    {shotCharacters.map((char) => (
                      <span key={char.id} className="px-2 py-1 bg-surface-700 rounded text-xs">
                        {char.name}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Technical Notes */}
              {(shot.compositionNotes || shot.lightingNotes) && (
                <div className="grid grid-cols-2 gap-4 pt-2 border-t border-surface-700">
                  {shot.compositionNotes && (
                    <div>
                      <h4 className="text-xs text-surface-500 mb-1">Composition</h4>
                      <p className="text-xs text-surface-400">{shot.compositionNotes}</p>
                    </div>
                  )}
                  {shot.lightingNotes && (
                    <div>
                      <h4 className="text-xs text-surface-500 mb-1">Lighting</h4>
                      <p className="text-xs text-surface-400">{shot.lightingNotes}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
