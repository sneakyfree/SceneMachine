/**
 * Character Lab page.
 *
 * The central hub for defining and locking character appearances
 * to ensure visual consistency across all generated content.
 */

import { useState, useCallback, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Users,
  Lock,
  AlertTriangle,
  Check,
  ArrowLeft,
  Filter,
  Search,
  Sparkles,
  Keyboard,
} from 'lucide-react';
import { CharacterCard } from '../components/character-card';
import { LoadingContainer, SkeletonProjectCard } from '../components/skeleton';
import { cn } from '../lib/utils';
import { useExperienceStore } from '../stores/experience-store';
import { useToast } from '../components/toast';
import { announce } from '../lib/accessibility';

interface Character {
  id: string;
  name: string;
  screenplayName: string;
  description?: string;
  ageRangeDisplay?: string;
  gender: string;
  physicalDescription?: Record<string, any>;
  personalityTraits?: string[];
  lockState: string;
  isLocked: boolean;
  sceneCount: number;
  dialogueCount: number;
  isProtagonist: boolean;
  referenceAssets?: any[];
  referenceCount?: number;
  voiceId?: string | null;
  voiceProvider?: string | null;
  voiceName?: string | null;
}

type FilterType = 'all' | 'locked' | 'unlocked' | 'protagonist';

export function CharacterLabPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { getTerm, isSimplifiedMode } = useExperienceStore();
  const isStoryMode = isSimplifiedMode('characters');
  const { addToast } = useToast();

  const [filter, setFilter] = useState<FilterType>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCharacter, setSelectedCharacter] = useState<Character | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [showShortcuts, setShowShortcuts] = useState(false);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if typing in an input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }

      // ? - Show shortcuts help
      if (e.key === '?' && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        setShowShortcuts((prev) => !prev);
        return;
      }

      // / - Focus search
      if (e.key === '/' && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        const searchInput = document.querySelector<HTMLInputElement>('input[type="text"]');
        searchInput?.focus();
        return;
      }

      // Escape - Clear search or close shortcuts
      if (e.key === 'Escape') {
        if (showShortcuts) {
          setShowShortcuts(false);
        } else if (searchQuery) {
          setSearchQuery('');
        }
        return;
      }

      // 1-4 - Quick filter
      if (e.key >= '1' && e.key <= '4' && !e.ctrlKey && !e.metaKey) {
        const filters: FilterType[] = ['all', 'locked', 'unlocked', 'protagonist'];
        const index = parseInt(e.key) - 1;
        if (index < filters.length) {
          setFilter(filters[index]);
          announce(`Filter set to ${filters[index]}`);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [searchQuery, showShortcuts]);

  // Fetch characters
  const { data: characters, isLoading } = useQuery({
    queryKey: ['characters', projectId],
    queryFn: async () => {
      const result = await window.electronAPI.backendRequest<Character[]>(
        'characters.list',
        { project_id: projectId }
      );
      return result;
    },
    enabled: !!projectId,
  });

  // Lock character mutation
  const lockMutation = useMutation({
    mutationFn: async (characterId: string) => {
      return window.electronAPI.backendRequest('characters.lock', {
        character_id: characterId,
      });
    },
    onSuccess: (_data, characterId) => {
      queryClient.invalidateQueries({ queryKey: ['characters', projectId] });
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
      const char = characters?.find((c) => c.id === characterId);
      addToast({
        type: 'success',
        title: 'Character Locked',
        message: `${char?.name || 'Character'} appearance is now locked for consistency.`,
      });
      announce(`${char?.name || 'Character'} locked`);
    },
    onError: (error) => {
      addToast({
        type: 'error',
        title: 'Failed to Lock',
        message: error instanceof Error ? error.message : 'Please try again.',
      });
    },
  });

  // Unlock character mutation
  const unlockMutation = useMutation({
    mutationFn: async (characterId: string) => {
      return window.electronAPI.backendRequest('characters.unlock', {
        character_id: characterId,
      });
    },
    onSuccess: (_data, characterId) => {
      queryClient.invalidateQueries({ queryKey: ['characters', projectId] });
      const char = characters?.find((c) => c.id === characterId);
      addToast({
        type: 'info',
        title: 'Character Unlocked',
        message: `${char?.name || 'Character'} can now be edited.`,
      });
      announce(`${char?.name || 'Character'} unlocked`);
    },
    onError: (error) => {
      addToast({
        type: 'error',
        title: 'Failed to Unlock',
        message: error instanceof Error ? error.message : 'Please try again.',
      });
    },
  });

  // Generate description mutation
  const generateDescriptionMutation = useMutation({
    mutationFn: async (characterId: string) => {
      return window.electronAPI.backendRequest('characters.generateDescription', {
        character_id: characterId,
      });
    },
    onSuccess: (_data, characterId) => {
      queryClient.invalidateQueries({ queryKey: ['characters', projectId] });
      const char = characters?.find((c) => c.id === characterId);
      addToast({
        type: 'success',
        title: 'Description Generated',
        message: `AI description created for ${char?.name || 'character'}.`,
      });
    },
    onError: (error) => {
      addToast({
        type: 'error',
        title: 'Generation Failed',
        message: error instanceof Error ? error.message : 'Please try again.',
      });
    },
  });

  // Update voice mutation
  const updateVoiceMutation = useMutation({
    mutationFn: async ({
      characterId,
      voiceId,
      provider,
      voiceName,
    }: {
      characterId: string;
      voiceId: string;
      provider: string;
      voiceName: string;
    }) => {
      return window.electronAPI.backendRequest('characters.updateVoice', {
        character_id: characterId,
        voice_id: voiceId,
        voice_provider: provider,
        voice_name: voiceName,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['characters', projectId] });
    },
  });

  // Update physical description mutation
  const updatePhysicalDescriptionMutation = useMutation({
    mutationFn: async ({
      characterId,
      physicalDescription,
    }: {
      characterId: string;
      physicalDescription: Record<string, any>;
    }) => {
      return window.electronAPI.backendRequest('characters.update', {
        character_id: characterId,
        physical_description: physicalDescription,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['characters', projectId] });
    },
  });

  // Upload reference handler
  const handleUploadReference = useCallback(
    async (characterId: string) => {
      try {
        const result = await window.electronAPI.openFile({
          title: 'Select Reference Image',
          filters: [
            { name: 'Images', extensions: ['png', 'jpg', 'jpeg', 'webp'] },
          ],
          properties: ['openFile'],
        });

        if (result.canceled || result.filePaths.length === 0) return;

        const filePath = result.filePaths[0];
        const filename = filePath.split(/[\\/]/).pop() || 'reference.png';

        await window.electronAPI.backendRequest('characters.uploadReference', {
          character_id: characterId,
          file_path: filePath,
          filename,
          is_primary: false,
        });

        queryClient.invalidateQueries({ queryKey: ['characters', projectId] });
      } catch (error) {
        console.error('Failed to upload reference:', error);
      }
    },
    [projectId, queryClient]
  );

  // Delete reference handler
  const handleDeleteReference = useCallback(
    async (characterId: string, assetId: string) => {
      try {
        await window.electronAPI.backendRequest('characters.deleteReference', {
          character_id: characterId,
          asset_id: assetId,
        });
        queryClient.invalidateQueries({ queryKey: ['characters', projectId] });
      } catch (error) {
        console.error('Failed to delete reference:', error);
      }
    },
    [projectId, queryClient]
  );

  // Filter characters
  const filteredCharacters = characters?.filter((char) => {
    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      if (
        !char.name.toLowerCase().includes(query) &&
        !char.screenplayName.toLowerCase().includes(query)
      ) {
        return false;
      }
    }

    // Type filter
    switch (filter) {
      case 'locked':
        return char.isLocked;
      case 'unlocked':
        return !char.isLocked;
      case 'protagonist':
        return char.isProtagonist;
      default:
        return true;
    }
  });

  // Stats
  const totalCharacters = characters?.length ?? 0;
  const lockedCharacters = characters?.filter((c) => c.isLocked).length ?? 0;
  const allLocked = totalCharacters > 0 && lockedCharacters === totalCharacters;

  // Determine loading state
  const loadingState = isLoading
    ? 'loading'
    : !characters || characters.length === 0
      ? 'empty'
      : 'success';

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate(`/project/${projectId}`)}
            className="p-2 hover:bg-surface-800 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Users className="w-7 h-7 text-brand-400" />
              Character Lab
            </h1>
            <p className="text-surface-400 mt-1">
              {isStoryMode
                ? 'Define how your characters look so they stay consistent'
                : 'Define and lock character appearances for consistent generation'}
            </p>
          </div>
        </div>

        {/* Progress */}
        <div className="flex items-center gap-4">
          <div className="text-right">
            <div className="text-sm text-surface-400">
              {isStoryMode ? 'Characters Saved' : 'Characters Locked'}
            </div>
            <div className="text-2xl font-bold">
              {lockedCharacters}/{totalCharacters}
            </div>
          </div>
          {allLocked ? (
            <div className="flex items-center gap-2 px-4 py-2 bg-green-500/20 text-green-400 rounded-lg">
              <Check className="w-5 h-5" />
              <span>{isStoryMode ? 'All Saved' : 'All Locked'}</span>
            </div>
          ) : (
            <div className="flex items-center gap-2 px-4 py-2 bg-yellow-500/20 text-yellow-400 rounded-lg">
              <AlertTriangle className="w-5 h-5" />
              <span>Incomplete</span>
            </div>
          )}
        </div>
      </div>

      {/* Info Banner */}
      <div className="bg-brand-500/10 border border-brand-500/30 rounded-lg p-4 mb-6">
        <div className="flex items-start gap-3">
          <Lock className="w-5 h-5 text-brand-400 mt-0.5" />
          <div>
            <h3 className="font-medium text-brand-300">
              {isStoryMode ? 'Why Save Character Looks?' : 'Why Lock Characters?'}
            </h3>
            <p className="text-sm text-surface-300 mt-1">
              {isStoryMode
                ? 'Saving a character\'s look ensures they appear the same in every scene of your movie. Describe how they look, add reference photos if you have them, and save their appearance before creating your scenes.'
                : 'Locking a character\'s appearance ensures they look consistent across all generated scenes. Define their physical features, upload reference images, and lock them before proceeding to scene generation.'}
            </p>
          </div>
        </div>
      </div>

      {/* Toolbar */}
      <div className="flex items-center justify-between mb-6">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-500" />
          <input
            type="text"
            placeholder="Search characters..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 pr-4 py-2 bg-surface-800 border border-surface-700 rounded-lg text-sm focus:outline-none focus:border-brand-500 w-64"
          />
        </div>

        {/* Filters */}
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-surface-500" />
          {(['all', 'locked', 'unlocked', 'protagonist'] as FilterType[]).map(
            (filterType) => {
              // Use friendly terms for filter labels
              const getFilterLabel = (type: FilterType) => {
                switch (type) {
                  case 'locked':
                    return getTerm('locked', 'characters');
                  case 'unlocked':
                    return getTerm('unlocked', 'characters');
                  default:
                    return type.charAt(0).toUpperCase() + type.slice(1);
                }
              };
              return (
                <button
                  key={filterType}
                  onClick={() => setFilter(filterType)}
                  className={cn(
                    'px-3 py-1.5 rounded-lg text-sm transition-colors',
                    filter === filterType
                      ? 'bg-brand-500/20 text-brand-400'
                      : 'bg-surface-800 text-surface-400 hover:bg-surface-700'
                  )}
                >
                  {getFilterLabel(filterType)}
                </button>
              );
            }
          )}
        </div>

        {/* Bulk Actions */}
        <div className="flex gap-2">
          <button
            onClick={() => {
              filteredCharacters?.forEach((char) => {
                if (!char.isLocked) {
                  generateDescriptionMutation.mutate(char.id);
                }
              });
            }}
            disabled={generateDescriptionMutation.isPending}
            className="btn-secondary text-sm"
          >
            <Sparkles className="w-4 h-4 mr-1" />
            AI Describe All
          </button>
        </div>
      </div>

      {/* Character Grid */}
      <LoadingContainer
        state={loadingState}
        skeleton={<SkeletonProjectCard />}
        skeletonCount={4}
        loadingMessage="Loading characters..."
        emptyMessage={
          searchQuery || filter !== 'all'
            ? 'No characters match your search or filter.'
            : 'Characters will appear here once a screenplay is parsed.'
        }
        emptyIcon={<Users className="w-16 h-16 text-surface-600" />}
        emptyAction={searchQuery || filter !== 'all' ? 'Clear filters' : undefined}
        onEmptyAction={
          searchQuery || filter !== 'all'
            ? () => {
                setSearchQuery('');
                setFilter('all');
              }
            : undefined
        }
      >
        {filteredCharacters && filteredCharacters.length > 0 ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4" role="list" aria-label="Characters">
            {filteredCharacters.map((character) => (
              <div key={character.id} role="listitem">
                <CharacterCard
                  character={character}
                  onEdit={(char) => {
                    setSelectedCharacter(char);
                    setIsEditing(true);
                  }}
                  onLock={(id) => lockMutation.mutate(id)}
                  onUnlock={(id) => unlockMutation.mutate(id)}
                  onUploadReference={handleUploadReference}
                  onDeleteReference={handleDeleteReference}
                  onGenerateDescription={(id) => generateDescriptionMutation.mutate(id)}
                  onUpdatePhysicalDescription={(characterId, physicalDescription) =>
                    updatePhysicalDescriptionMutation.mutate({ characterId, physicalDescription })
                  }
                  onVoiceChange={(characterId, voiceId, provider, voiceName) =>
                    updateVoiceMutation.mutate({ characterId, voiceId, provider, voiceName })
                  }
                  disabled={
                    lockMutation.isPending ||
                    unlockMutation.isPending ||
                    generateDescriptionMutation.isPending ||
                    updateVoiceMutation.isPending ||
                    updatePhysicalDescriptionMutation.isPending
                  }
                />
              </div>
            ))}
          </div>
        ) : null}
      </LoadingContainer>

      {/* Keyboard Shortcuts Help */}
      {showShortcuts && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          onClick={() => setShowShortcuts(false)}
          role="dialog"
          aria-modal="true"
          aria-label="Keyboard shortcuts"
        >
          <div
            className="bg-surface-800 rounded-xl p-6 max-w-md w-full mx-4 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-2 mb-4">
              <Keyboard className="w-5 h-5 text-brand-400" />
              <h2 className="text-lg font-semibold">Keyboard Shortcuts</h2>
            </div>
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-surface-400">Focus search</span>
                <kbd className="px-2 py-1 bg-surface-700 rounded text-surface-200">/</kbd>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-surface-400">Show all</span>
                <kbd className="px-2 py-1 bg-surface-700 rounded text-surface-200">1</kbd>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-surface-400">Show locked</span>
                <kbd className="px-2 py-1 bg-surface-700 rounded text-surface-200">2</kbd>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-surface-400">Show unlocked</span>
                <kbd className="px-2 py-1 bg-surface-700 rounded text-surface-200">3</kbd>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-surface-400">Show protagonists</span>
                <kbd className="px-2 py-1 bg-surface-700 rounded text-surface-200">4</kbd>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-surface-400">Clear / Close</span>
                <kbd className="px-2 py-1 bg-surface-700 rounded text-surface-200">Esc</kbd>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-surface-400">Show this help</span>
                <kbd className="px-2 py-1 bg-surface-700 rounded text-surface-200">?</kbd>
              </div>
            </div>
            <button
              onClick={() => setShowShortcuts(false)}
              className="mt-4 w-full py-2 bg-surface-700 hover:bg-surface-600 rounded-lg text-sm transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      )}

      {/* Continue Button */}
      {allLocked && (
        <div className="fixed bottom-8 right-8">
          <button
            onClick={() => navigate(`/project/${projectId}`)}
            className="btn-primary shadow-lg"
          >
            <Check className="w-4 h-4 mr-2" />
            Continue to Scene Planning
          </button>
        </div>
      )}
    </div>
  );
}
