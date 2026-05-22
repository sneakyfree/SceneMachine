/**
 * Character Card component.
 *
 * Displays a character with their details, reference images,
 * and lock state.
 */

import { useState } from 'react';
import {
  User,
  Lock,
  Unlock,
  Upload,
  Trash2,
  Sparkles,
  ChevronDown,
  ChevronUp,
  Image as ImageIcon,
  MessageSquare,
  Film,
  Star,
  Mic,
  Volume2,
  Edit3,
  X,
  Wand2,
  ScanFace,
  Loader2,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { VoiceSelector } from './voice-selector';
import { FaceSimilarityPanel } from './face-similarity-panel';
import { PhysicalDescriptionForm, type PhysicalDescription } from './physical-description-form';
import { useExperienceStore } from '../stores/experience-store';

interface ReferenceAsset {
  id: string;
  originalFilename: string;
  filePath: string;
  isPrimary: boolean;
}

interface Character {
  id: string;
  name: string;
  screenplayName: string;
  description?: string;
  ageRangeDisplay?: string;
  gender: string;
  physicalDescription?: {
    hair_color?: string;
    hair_style?: string;
    eye_color?: string;
    build?: string;
    height?: string;
    skin_tone?: string;
    clothing_style?: string;
    distinguishing_features?: string[];
  };
  personalityTraits?: string[];
  lockState: string;
  isLocked: boolean;
  sceneCount: number;
  dialogueCount: number;
  isProtagonist: boolean;
  referenceAssets?: ReferenceAsset[];
  referenceCount?: number;
  voiceId?: string | null;
  voiceProvider?: string | null;
  voiceName?: string | null;
}

interface CharacterCardProps {
  character: Character;
  onEdit: (character: Character) => void;
  onLock: (characterId: string) => void;
  onUnlock: (characterId: string) => void;
  onUploadReference: (characterId: string) => void;
  onDeleteReference: (characterId: string, assetId: string) => void;
  onGenerateDescription: (characterId: string) => void;
  onUpdatePhysicalDescription?: (characterId: string, data: PhysicalDescription) => void;
  onVoiceChange?: (
    characterId: string,
    voiceId: string,
    provider: string,
    voiceName: string
  ) => void;
  onSuggestVoice?: (characterId: string) => void;
  onCheckConsistency?: (characterId: string) => void;
  isExpanded?: boolean;
  disabled?: boolean;
}

export function CharacterCard({
  character,
  onEdit,
  onLock,
  onUnlock,
  onUploadReference,
  onDeleteReference,
  onGenerateDescription,
  onUpdatePhysicalDescription,
  onVoiceChange,
  onSuggestVoice,
  onCheckConsistency,
  isExpanded: defaultExpanded = false,
  disabled = false,
}: CharacterCardProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [isEditingPhysical, setIsEditingPhysical] = useState(false);
  const [consistencyScore, setConsistencyScore] = useState<number | null>(null);
  const [isCheckingConsistency, setIsCheckingConsistency] = useState(false);
  const [isSuggestingVoice, setIsSuggestingVoice] = useState(false);
  const { getTerm } = useExperienceStore();

  const getLockStateColor = (state: string) => {
    switch (state) {
      case 'locked':
        return 'text-green-400 bg-green-500/20';
      case 'review':
        return 'text-yellow-400 bg-yellow-500/20';
      case 'generating':
        return 'text-blue-400 bg-blue-500/20';
      case 'reference_uploaded':
        return 'text-purple-400 bg-purple-500/20';
      case 'draft':
        return 'text-orange-400 bg-orange-500/20';
      default:
        return 'text-surface-400 bg-surface-700';
    }
  };

  const getLockStateLabel = (state: string) => {
    switch (state) {
      case 'locked':
        return getTerm('locked', 'characters');
      case 'review':
        return 'In Review';
      case 'generating':
        return 'Generating';
      case 'reference_uploaded':
        return 'Has References';
      case 'draft':
        return 'Draft';
      case 'unlocked':
        return getTerm('unlocked', 'characters');
      default:
        return getTerm('unlocked', 'characters');
    }
  };

  const referenceCount = character.referenceCount ?? character.referenceAssets?.length ?? 0;

  return (
    <div
      className={cn(
        'card border transition-all',
        character.isLocked ? 'border-green-500/30 bg-green-500/5' : 'border-surface-800',
        character.isProtagonist && 'ring-2 ring-brand-500/50'
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          {/* Avatar */}
          <div
            className={cn(
              'w-12 h-12 rounded-full flex items-center justify-center text-lg font-bold',
              character.isProtagonist
                ? 'bg-brand-500/20 text-brand-400'
                : 'bg-surface-700 text-surface-300'
            )}
          >
            {character.name[0]}
          </div>

          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-lg">{character.name}</h3>
              {character.isProtagonist && (
                <Star className="w-4 h-4 text-brand-400 fill-brand-400" />
              )}
              {character.isLocked && <Lock className="w-4 h-4 text-green-400" />}
            </div>
            {character.name !== character.screenplayName && (
              <p className="text-sm text-surface-500">as "{character.screenplayName}"</p>
            )}
          </div>
        </div>

        {/* Lock State Badge */}
        <span
          className={cn(
            'px-2 py-1 rounded-full text-xs font-medium',
            getLockStateColor(character.lockState)
          )}
        >
          {getLockStateLabel(character.lockState)}
        </span>
      </div>

      {/* Stats */}
      <div className="flex flex-wrap gap-4 mt-4 text-sm">
        <div className="flex items-center gap-1 text-surface-400">
          <Film className="w-4 h-4" />
          <span>{character.sceneCount} scenes</span>
        </div>
        <div className="flex items-center gap-1 text-surface-400">
          <MessageSquare className="w-4 h-4" />
          <span>{character.dialogueCount} lines</span>
        </div>
        <div className="flex items-center gap-1 text-surface-400">
          <ImageIcon className="w-4 h-4" />
          <span>{referenceCount} refs</span>
        </div>
        <div className="flex items-center gap-1 text-surface-400">
          <Mic className="w-4 h-4" />
          <span>{character.voiceName || 'No voice'}</span>
        </div>
      </div>

      {/* Description */}
      {character.description && (
        <p className="mt-3 text-sm text-surface-300 line-clamp-2">{character.description}</p>
      )}

      {/* Personality Traits */}
      {character.personalityTraits && character.personalityTraits.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-3">
          {character.personalityTraits.slice(0, 4).map((trait) => (
            <span
              key={trait}
              className="px-2 py-0.5 bg-surface-800 rounded text-xs text-surface-300 capitalize"
            >
              {trait}
            </span>
          ))}
          {character.personalityTraits.length > 4 && (
            <span className="px-2 py-0.5 text-xs text-surface-500">
              +{character.personalityTraits.length - 4} more
            </span>
          )}
        </div>
      )}

      {/* Expand/Collapse Toggle */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-1 mt-4 text-sm text-surface-400 hover:text-surface-200 transition-colors"
      >
        {isExpanded ? (
          <>
            <ChevronUp className="w-4 h-4" />
            <span>Show less</span>
          </>
        ) : (
          <>
            <ChevronDown className="w-4 h-4" />
            <span>Show more</span>
          </>
        )}
      </button>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="mt-4 pt-4 border-t border-surface-800 space-y-4">
          {/* Physical Description */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-medium text-surface-400">Physical Description</h4>
              {!character.isLocked && !isEditingPhysical && (
                <button
                  onClick={() => setIsEditingPhysical(true)}
                  className="flex items-center gap-1 px-2 py-1 text-xs text-surface-400 hover:text-surface-200 hover:bg-surface-800 rounded transition-colors"
                >
                  <Edit3 className="w-3 h-3" />
                  Edit
                </button>
              )}
              {isEditingPhysical && (
                <button
                  onClick={() => setIsEditingPhysical(false)}
                  className="flex items-center gap-1 px-2 py-1 text-xs text-surface-400 hover:text-surface-200 hover:bg-surface-800 rounded transition-colors"
                >
                  <X className="w-3 h-3" />
                  Close
                </button>
              )}
            </div>

            {isEditingPhysical ? (
              <PhysicalDescriptionForm
                initialData={character.physicalDescription as Partial<PhysicalDescription>}
                onSave={(data) => {
                  onUpdatePhysicalDescription?.(character.id, data);
                  setIsEditingPhysical(false);
                }}
                onCancel={() => setIsEditingPhysical(false)}
                isLocked={character.isLocked}
                isLoading={disabled}
                compact
              />
            ) : character.physicalDescription ? (
              <>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  {character.physicalDescription.hair_color && (
                    <div>
                      <span className="text-surface-500">Hair:</span>{' '}
                      <span className="text-surface-200">
                        {character.physicalDescription.hair_color}
                        {character.physicalDescription.hair_style &&
                          `, ${character.physicalDescription.hair_style}`}
                      </span>
                    </div>
                  )}
                  {character.physicalDescription.eye_color && (
                    <div>
                      <span className="text-surface-500">Eyes:</span>{' '}
                      <span className="text-surface-200">
                        {character.physicalDescription.eye_color}
                      </span>
                    </div>
                  )}
                  {character.physicalDescription.build && (
                    <div>
                      <span className="text-surface-500">Build:</span>{' '}
                      <span className="text-surface-200">
                        {character.physicalDescription.build}
                      </span>
                    </div>
                  )}
                  {character.ageRangeDisplay && (
                    <div>
                      <span className="text-surface-500">Age:</span>{' '}
                      <span className="text-surface-200">{character.ageRangeDisplay}</span>
                    </div>
                  )}
                  {character.physicalDescription.height && (
                    <div>
                      <span className="text-surface-500">Height:</span>{' '}
                      <span className="text-surface-200">
                        {character.physicalDescription.height}
                      </span>
                    </div>
                  )}
                  {character.physicalDescription.skin_tone && (
                    <div>
                      <span className="text-surface-500">Skin:</span>{' '}
                      <span className="text-surface-200">
                        {character.physicalDescription.skin_tone}
                      </span>
                    </div>
                  )}
                </div>
                {character.physicalDescription.clothing_style && (
                  <div className="mt-2 text-sm">
                    <span className="text-surface-500">Clothing:</span>{' '}
                    <span className="text-surface-200">
                      {character.physicalDescription.clothing_style}
                    </span>
                  </div>
                )}
                {character.physicalDescription.distinguishing_features &&
                  character.physicalDescription.distinguishing_features.length > 0 && (
                    <div className="mt-2">
                      <span className="text-surface-500 text-sm">Features:</span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {character.physicalDescription.distinguishing_features.map((feature, i) => (
                          <span
                            key={i}
                            className="px-2 py-0.5 bg-surface-800 rounded text-xs text-surface-300"
                          >
                            {feature}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
              </>
            ) : (
              <div className="text-sm text-surface-500 italic">
                No physical description yet.{' '}
                {!character.isLocked && (
                  <button
                    onClick={() => setIsEditingPhysical(true)}
                    className="text-brand-400 hover:text-brand-300 underline"
                  >
                    Add one
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Reference Images */}
          {character.referenceAssets && character.referenceAssets.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-surface-400 mb-2">Reference Images</h4>
              <div className="grid grid-cols-4 gap-2">
                {character.referenceAssets.map((asset) => (
                  <div
                    key={asset.id}
                    className={cn(
                      'relative aspect-square bg-surface-800 rounded-lg overflow-hidden group',
                      asset.isPrimary && 'ring-2 ring-brand-500'
                    )}
                  >
                    <img
                      src={`file://${asset.filePath}`}
                      alt={asset.originalFilename}
                      className="w-full h-full object-cover"
                    />
                    {!character.isLocked && (
                      <button
                        onClick={() => onDeleteReference(character.id, asset.id)}
                        className="absolute top-1 right-1 p-1 bg-red-500/80 rounded opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <Trash2 className="w-3 h-3 text-white" />
                      </button>
                    )}
                    {asset.isPrimary && (
                      <span className="absolute bottom-1 left-1 px-1 py-0.5 bg-brand-500/80 rounded text-xs text-white">
                        Primary
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Voice Assignment */}
          {character.dialogueCount > 0 && (
            <div>
              <h4 className="text-sm font-medium text-surface-400 mb-2 flex items-center gap-2">
                <Volume2 className="w-4 h-4" />
                Voice Assignment
              </h4>
              {character.isLocked ? (
                <div className="flex items-center gap-3 p-3 bg-surface-800/50 rounded-lg">
                  <div
                    className={cn(
                      'w-10 h-10 rounded-full flex items-center justify-center',
                      character.voiceId ? 'bg-brand-500/20' : 'bg-surface-700'
                    )}
                  >
                    <Mic className="w-5 h-5" />
                  </div>
                  <div className="flex-1">
                    <div className="font-medium">{character.voiceName || 'No voice assigned'}</div>
                    {character.voiceProvider && (
                      <div className="text-sm text-surface-400">
                        Provider: {character.voiceProvider}
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <VoiceSelector
                  characterId={character.id}
                  characterName={character.name}
                  selectedVoiceId={character.voiceId}
                  selectedProvider={character.voiceProvider}
                  onVoiceSelect={(voiceId, provider, voiceName) =>
                    onVoiceChange?.(character.id, voiceId, provider, voiceName)
                  }
                  compact
                />
              )}
            </div>
          )}

          {/* Face Similarity Panel */}
          <FaceSimilarityPanel
            characterId={character.id}
            characterName={character.name}
            isLocked={character.isLocked}
          />

          {/* Actions */}
          <div className="flex flex-wrap gap-2 pt-2">
            {!character.isLocked && (
              <>
                <button
                  onClick={() => onEdit(character)}
                  disabled={disabled}
                  className="btn-secondary text-sm"
                >
                  <User className="w-4 h-4 mr-1" />
                  Edit Details
                </button>

                <button
                  onClick={() => onUploadReference(character.id)}
                  disabled={disabled}
                  className="btn-secondary text-sm"
                >
                  <Upload className="w-4 h-4 mr-1" />
                  Add Reference
                </button>

                <button
                  onClick={() => onGenerateDescription(character.id)}
                  disabled={disabled}
                  className="btn-secondary text-sm"
                >
                  <Sparkles className="w-4 h-4 mr-1" />
                  AI Describe
                </button>

                {/* FEAT-062: Suggest Voice */}
                {character.dialogueCount > 0 && !character.voiceId && onSuggestVoice && (
                  <button
                    onClick={async () => {
                      setIsSuggestingVoice(true);
                      try {
                        await onSuggestVoice(character.id);
                      } finally {
                        setIsSuggestingVoice(false);
                      }
                    }}
                    disabled={disabled || isSuggestingVoice}
                    className="btn-secondary text-sm"
                    title="AI will suggest a voice based on character description"
                  >
                    {isSuggestingVoice ? (
                      <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                    ) : (
                      <Wand2 className="w-4 h-4 mr-1" />
                    )}
                    Suggest Voice
                  </button>
                )}

                {/* FEAT-027: Check Consistency */}
                {character.isLocked &&
                  (character.referenceAssets?.length ?? 0) > 0 &&
                  onCheckConsistency && (
                    <button
                      onClick={async () => {
                        setIsCheckingConsistency(true);
                        try {
                          const result = await window.electronAPI.backendRequest<{ score: number }>(
                            'characters.checkConsistency',
                            { character_id: character.id }
                          );
                          setConsistencyScore(result.score);
                        } catch {
                          setConsistencyScore(null);
                        } finally {
                          setIsCheckingConsistency(false);
                        }
                      }}
                      disabled={disabled || isCheckingConsistency}
                      className="btn-secondary text-sm"
                      title="Compare reference images with generated shots"
                    >
                      {isCheckingConsistency ? (
                        <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                      ) : (
                        <ScanFace className="w-4 h-4 mr-1" />
                      )}
                      Check Consistency
                    </button>
                  )}

                <button
                  onClick={() => onLock(character.id)}
                  disabled={disabled || !character.physicalDescription}
                  className="btn-primary text-sm ml-auto"
                  title="Once saved, this character will look the same in every scene"
                >
                  <Lock className="w-4 h-4 mr-1" />
                  {getTerm('lock', 'characters')}
                </button>
              </>
            )}

            {character.isLocked && (
              <>
                <button
                  onClick={() => onUnlock(character.id)}
                  disabled={disabled}
                  className="btn-secondary text-sm"
                >
                  <Unlock className="w-4 h-4 mr-1" />
                  {getTerm('unlock', 'characters')}
                </button>

                {/* FEAT-027: Consistency score display */}
                {consistencyScore !== null && (
                  <div
                    className={cn(
                      'flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium',
                      consistencyScore >= 80
                        ? 'bg-green-500/20 text-green-400'
                        : consistencyScore >= 60
                          ? 'bg-yellow-500/20 text-yellow-400'
                          : 'bg-red-500/20 text-red-400'
                    )}
                  >
                    <ScanFace className="w-4 h-4" />
                    Consistency: {consistencyScore}%
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
