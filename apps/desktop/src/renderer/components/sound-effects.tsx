/**
 * Sound effects library component.
 * Browse, preview, and add sound effects to timeline.
 */

import { useState, useRef, useEffect, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Zap,
  Play,
  Pause,
  Volume2,
  Search,
  Plus,
  Loader2,
  ChevronRight,
  ChevronDown,
  Folder,
  Upload,
  Clock,
  Star,
  Tag,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { useToast } from './toast';
import { useTranslation } from '../i18n/use-translation';

interface SoundEffect {
  id: string;
  name: string;
  category: string;
  subcategory?: string;
  duration: number;
  audioUrl: string;
  tags: string[];
  isFavorite: boolean;
  isCustom: boolean;
}

interface SoundCategory {
  id: string;
  name: string;
  nameKey: string;
  icon: string;
  subcategories: string[];
  /** i18n key per subcategory, aligned by index with `subcategories` */
  subKeys: string[];
  count: number;
}

interface SoundEffectsProps {
  onEffectSelect?: (effect: SoundEffect) => void;
  onEffectAdd?: (effect: SoundEffect, position: number) => void;
  currentTime?: number;
}

const DEFAULT_CATEGORIES: SoundCategory[] = [
  {
    id: 'ambience',
    name: 'Ambience',
    nameKey: 'soundFx.catAmbience',
    icon: '🌿',
    subcategories: ['Nature', 'Urban', 'Indoor', 'Weather'],
    subKeys: ['soundFx.subNature', 'soundFx.subUrban', 'soundFx.subIndoor', 'soundFx.subWeather'],
    count: 0,
  },
  {
    id: 'foley',
    name: 'Foley',
    nameKey: 'soundFx.catFoley',
    icon: '👣',
    subcategories: ['Footsteps', 'Clothing', 'Doors', 'Props'],
    subKeys: ['soundFx.subFootsteps', 'soundFx.subClothing', 'soundFx.subDoors', 'soundFx.subProps'],
    count: 0,
  },
  {
    id: 'impacts',
    name: 'Impacts',
    nameKey: 'soundFx.catImpacts',
    icon: '💥',
    subcategories: ['Hits', 'Crashes', 'Explosions', 'Glass'],
    subKeys: ['soundFx.subHits', 'soundFx.subCrashes', 'soundFx.subExplosions', 'soundFx.subGlass'],
    count: 0,
  },
  {
    id: 'whooshes',
    name: 'Whooshes',
    nameKey: 'soundFx.catWhooshes',
    icon: '💨',
    subcategories: ['Swishes', 'Swooshes', 'Transitions'],
    subKeys: ['soundFx.subSwishes', 'soundFx.subSwooshes', 'soundFx.subTransitions'],
    count: 0,
  },
  {
    id: 'risers',
    name: 'Risers & Stingers',
    nameKey: 'soundFx.catRisers',
    icon: '📈',
    subcategories: ['Tension', 'Horror', 'Action'],
    subKeys: ['soundFx.subTension', 'soundFx.subHorror', 'soundFx.subAction'],
    count: 0,
  },
  {
    id: 'ui',
    name: 'UI Sounds',
    nameKey: 'soundFx.catUiSounds',
    icon: '🔔',
    subcategories: ['Clicks', 'Notifications', 'Error'],
    subKeys: ['soundFx.subClicks', 'soundFx.subNotifications', 'soundFx.subError'],
    count: 0,
  },
  {
    id: 'vehicles',
    name: 'Vehicles',
    nameKey: 'soundFx.catVehicles',
    icon: '🚗',
    subcategories: ['Cars', 'Motorcycles', 'Aircraft'],
    subKeys: ['soundFx.subCars', 'soundFx.subMotorcycles', 'soundFx.subAircraft'],
    count: 0,
  },
  {
    id: 'weapons',
    name: 'Weapons',
    nameKey: 'soundFx.catWeapons',
    icon: '⚔️',
    subcategories: ['Guns', 'Swords', 'Punches'],
    subKeys: ['soundFx.subGuns', 'soundFx.subSwords', 'soundFx.subPunches'],
    count: 0,
  },
  {
    id: 'animals',
    name: 'Animals',
    nameKey: 'soundFx.catAnimals',
    icon: '🐕',
    subcategories: ['Dogs', 'Cats', 'Birds', 'Wildlife'],
    subKeys: ['soundFx.subDogs', 'soundFx.subCats', 'soundFx.subBirds', 'soundFx.subWildlife'],
    count: 0,
  },
  {
    id: 'voice',
    name: 'Voice FX',
    nameKey: 'soundFx.catVoiceFx',
    icon: '🗣️',
    subcategories: ['Crowds', 'Reactions', 'Vocalizations'],
    subKeys: ['soundFx.subCrowds', 'soundFx.subReactions', 'soundFx.subVocalizations'],
    count: 0,
  },
];

function formatDuration(seconds: number): string {
  if (seconds < 1) return `${Math.round(seconds * 1000)}ms`;
  return `${seconds.toFixed(1)}s`;
}

function EffectItem({
  effect,
  isPlaying,
  onPlay,
  onAdd,
  onToggleFavorite,
}: {
  effect: SoundEffect;
  isPlaying: boolean;
  onPlay: () => void;
  onAdd: () => void;
  onToggleFavorite: () => void;
}) {
  const { t } = useTranslation();
  return (
    <div className="flex items-center gap-2 p-2 rounded-lg bg-surface-800/50 hover:bg-surface-800 transition-colors group">
      {/* Play button */}
      <button
        onClick={onPlay}
        className={cn(
          'w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 transition-colors',
          isPlaying ? 'bg-brand-500 text-white' : 'bg-surface-700 hover:bg-surface-600'
        )}
      >
        {isPlaying ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3 ml-0.5" />}
      </button>

      {/* Effect info */}
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium truncate">{effect.name}</div>
        <div className="flex items-center gap-2 text-xs text-surface-400">
          <Clock className="w-3 h-3" />
          <span>{formatDuration(effect.duration)}</span>
          {effect.subcategory && (
            <>
              <span>•</span>
              <span>{effect.subcategory}</span>
            </>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={onToggleFavorite}
          className={cn(
            'p-1.5 rounded transition-colors',
            effect.isFavorite ? 'text-yellow-400' : 'text-surface-500 hover:text-surface-300'
          )}
        >
          <Star className={cn('w-4 h-4', effect.isFavorite && 'fill-current')} />
        </button>
        <button
          onClick={onAdd}
          className="icon-btn p-2 text-brand-400 hover:text-brand-300 hover:bg-brand-500/20 rounded transition-colors"
          title={t('soundFx.addToTimeline', 'Add to timeline')}
          aria-label={`${t('soundFx.add', 'Add')} ${effect.name} ${t('soundFx.toTimeline', 'to timeline')}`}
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

function CategoryItem({
  category,
  isExpanded,
  onToggle,
  onSelect,
}: {
  category: SoundCategory;
  isExpanded: boolean;
  onToggle: () => void;
  onSelect: (subcategory?: string) => void;
}) {
  const { t } = useTranslation();
  const categoryName = t(category.nameKey, category.name);
  return (
    <div>
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-2 p-2 rounded-lg hover:bg-surface-800 transition-colors"
      >
        <span className="text-lg">{category.icon}</span>
        <span className="font-medium flex-1 text-left">{categoryName}</span>
        <span className="text-xs text-surface-500">{category.count}</span>
        {isExpanded ? (
          <ChevronDown className="w-4 h-4 text-surface-400" />
        ) : (
          <ChevronRight className="w-4 h-4 text-surface-400" />
        )}
      </button>

      {isExpanded && category.subcategories.length > 0 && (
        <div className="ml-8 mt-1 space-y-1">
          <button
            onClick={() => onSelect()}
            className="w-full text-left px-2 py-1 text-sm text-surface-300 hover:text-surface-100 hover:bg-surface-800 rounded transition-colors"
          >
            {t('soundFx.allPrefix', 'All')} {categoryName}
          </button>
          {category.subcategories.map((sub, i) => (
            <button
              key={sub}
              onClick={() => onSelect(sub)}
              className="w-full text-left px-2 py-1 text-sm text-surface-400 hover:text-surface-200 hover:bg-surface-800 rounded transition-colors"
            >
              {t(category.subKeys[i], sub)}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function SoundEffectsLibrary({
  onEffectSelect,
  onEffectAdd,
  currentTime = 0,
}: SoundEffectsProps) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const { t } = useTranslation();
  const audioRef = useRef<HTMLAudioElement>(null);

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedSubcategory, setSelectedSubcategory] = useState<string | null>(null);
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());
  const [showFavoritesOnly, setShowFavoritesOnly] = useState(false);
  const [playingId, setPlayingId] = useState<string | null>(null);
  const [volume, setVolume] = useState(0.7);

  // Fetch effects
  const { data: effects, isLoading } = useQuery({
    queryKey: ['sound-effects', selectedCategory, selectedSubcategory, showFavoritesOnly],
    queryFn: async () => {
      return window.electronAPI.backendRequest<SoundEffect[]>('sfx.getEffects', {
        category: selectedCategory,
        subcategory: selectedSubcategory,
        favorites_only: showFavoritesOnly,
      });
    },
  });

  // Get category counts
  const categories = useMemo(() => {
    return DEFAULT_CATEGORIES.map((cat) => ({
      ...cat,
      count: effects?.filter((e) => e.category === cat.id).length ?? 0,
    }));
  }, [effects]);

  // Filter effects by search
  const filteredEffects = useMemo(() => {
    if (!effects) return [];
    if (!searchQuery) return effects;

    const query = searchQuery.toLowerCase();
    return effects.filter(
      (effect) =>
        effect.name.toLowerCase().includes(query) ||
        effect.tags.some((t) => t.toLowerCase().includes(query)) ||
        effect.subcategory?.toLowerCase().includes(query)
    );
  }, [effects, searchQuery]);

  // Toggle favorite mutation
  const toggleFavoriteMutation = useMutation({
    mutationFn: async (effectId: string) => {
      return window.electronAPI.backendRequest('sfx.toggleFavorite', {
        effect_id: effectId,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sound-effects'] });
    },
  });

  // Handle play/pause
  const handlePlay = (effect: SoundEffect) => {
    if (!audioRef.current) return;

    if (playingId === effect.id) {
      audioRef.current.pause();
      setPlayingId(null);
    } else {
      audioRef.current.src = effect.audioUrl;
      audioRef.current.volume = volume;
      audioRef.current.play();
      setPlayingId(effect.id);
    }
  };

  // Handle audio ended
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleEnded = () => setPlayingId(null);
    audio.addEventListener('ended', handleEnded);
    return () => audio.removeEventListener('ended', handleEnded);
  }, []);

  // Toggle category expansion
  const toggleCategory = (categoryId: string) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(categoryId)) {
        next.delete(categoryId);
      } else {
        next.add(categoryId);
      }
      return next;
    });
  };

  // Select category/subcategory
  const handleSelectCategory = (categoryId: string, subcategory?: string) => {
    setSelectedCategory(categoryId);
    setSelectedSubcategory(subcategory ?? null);
  };

  // Resolve a raw English subcategory string to its translated label.
  const translateSubcategory = (sub: string): string => {
    for (const cat of DEFAULT_CATEGORIES) {
      const idx = cat.subcategories.indexOf(sub);
      if (idx !== -1) return t(cat.subKeys[idx], sub);
    }
    return sub;
  };

  return (
    <div className="flex h-full">
      {/* Categories sidebar */}
      <div className="w-48 border-r border-surface-800 p-2 overflow-y-auto">
        <div className="mb-2">
          <button
            onClick={() => {
              setSelectedCategory(null);
              setSelectedSubcategory(null);
            }}
            className={cn(
              'w-full flex items-center gap-2 p-2 rounded-lg transition-colors',
              !selectedCategory ? 'bg-brand-500/20 text-brand-400' : 'hover:bg-surface-800'
            )}
          >
            <Folder className="w-4 h-4" />
            <span className="font-medium">{t('soundFx.allEffects', 'All Effects')}</span>
          </button>
          <button
            onClick={() => setShowFavoritesOnly(!showFavoritesOnly)}
            className={cn(
              'w-full flex items-center gap-2 p-2 rounded-lg transition-colors',
              showFavoritesOnly
                ? 'bg-yellow-500/20 text-yellow-400'
                : 'hover:bg-surface-800 text-surface-400'
            )}
          >
            <Star className={cn('w-4 h-4', showFavoritesOnly && 'fill-current')} />
            <span>{t('soundFx.favorites', 'Favorites')}</span>
          </button>
        </div>

        <div className="space-y-1">
          {categories.map((category) => (
            <CategoryItem
              key={category.id}
              category={category}
              isExpanded={expandedCategories.has(category.id)}
              onToggle={() => toggleCategory(category.id)}
              onSelect={(sub) => handleSelectCategory(category.id, sub)}
            />
          ))}
        </div>
      </div>

      {/* Effects list */}
      <div className="flex-1 flex flex-col">
        {/* Search header */}
        <div className="p-3 border-b border-surface-800">
          <div className="flex items-center gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={t('soundFx.searchPlaceholder', 'Search effects...')}
                className="w-full pl-10 pr-4 py-2 bg-surface-800 border border-surface-700 rounded-lg text-sm"
              />
            </div>
            <div className="flex items-center gap-2">
              <Volume2 className="w-4 h-4 text-surface-400" />
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={volume}
                onChange={(e) => {
                  const v = parseFloat(e.target.value);
                  setVolume(v);
                  if (audioRef.current) audioRef.current.volume = v;
                }}
                className="w-16 accent-brand-500"
              />
            </div>
          </div>

          {/* Active filters */}
          {(selectedCategory || selectedSubcategory) && (
            <div className="flex items-center gap-2 mt-2">
              <span className="text-xs text-surface-500">{t('soundFx.showing', 'Showing:')}</span>
              {selectedCategory &&
                (() => {
                  const cat = categories.find((c) => c.id === selectedCategory);
                  return cat ? (
                    <span className="px-2 py-0.5 bg-surface-700 rounded text-xs">
                      {t(cat.nameKey, cat.name)}
                    </span>
                  ) : null;
                })()}
              {selectedSubcategory && (
                <span className="px-2 py-0.5 bg-surface-700 rounded text-xs">
                  {translateSubcategory(selectedSubcategory)}
                </span>
              )}
              <button
                onClick={() => {
                  setSelectedCategory(null);
                  setSelectedSubcategory(null);
                }}
                className="text-xs text-surface-400 hover:text-surface-200"
              >
                {t('soundFx.clear', 'Clear')}
              </button>
            </div>
          )}
        </div>

        {/* Effects grid */}
        <div className="flex-1 overflow-y-auto p-3">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin text-surface-400" />
            </div>
          ) : filteredEffects.length > 0 ? (
            <div className="space-y-1">
              {filteredEffects.map((effect) => (
                <EffectItem
                  key={effect.id}
                  effect={effect}
                  isPlaying={effect.id === playingId}
                  onPlay={() => handlePlay(effect)}
                  onAdd={() => {
                    onEffectAdd?.(effect, currentTime);
                    showToast(
                      `${t('soundFx.added', 'Added')} "${effect.name}" ${t('soundFx.toTimeline', 'to timeline')}`,
                      'success'
                    );
                  }}
                  onToggleFavorite={() => toggleFavoriteMutation.mutate(effect.id)}
                />
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-surface-400">
              <Zap className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>{t('soundFx.noEffectsFound', 'No effects found')}</p>
              <p className="text-sm text-surface-500 mt-1">
                {t('soundFx.adjustSearchHint', 'Try adjusting your search or category')}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Hidden audio element */}
      <audio ref={audioRef} className="hidden" />
    </div>
  );
}

/**
 * Compact SFX button for quick access.
 */
export function SFXButton({ onClick }: { onClick: () => void }) {
  const { t } = useTranslation();
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-2 px-3 py-2 bg-surface-800 hover:bg-surface-700 border border-surface-700 rounded-lg transition-colors"
    >
      <Zap className="w-4 h-4 text-brand-400" />
      <span className="text-sm">{t('soundFx.addSoundEffect', 'Add Sound Effect')}</span>
    </button>
  );
}
