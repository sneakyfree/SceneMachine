/**
 * Music library component for browsing and selecting background music.
 * Supports both built-in library and custom uploads.
 */

import { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Music,
  Music2,
  Play,
  Pause,
  Volume2,
  VolumeX,
  Plus,
  Search,
  Filter,
  Clock,
  Tag,
  Heart,
  HeartOff,
  Upload,
  FolderOpen,
  Loader2,
  Check,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { useToast } from './toast';
import { useTranslation } from '../i18n/use-translation';

interface MusicTrack {
  id: string;
  title: string;
  artist?: string;
  duration: number;
  genre: string;
  mood: string[];
  bpm?: number;
  audioUrl: string;
  waveformUrl?: string;
  isFavorite: boolean;
  isCustom: boolean;
  tags: string[];
}

interface MusicCategory {
  id: string;
  name: string;
  icon: string;
  trackCount: number;
}

interface MusicLibraryProps {
  onTrackSelect?: (track: MusicTrack) => void;
  selectedTrackId?: string;
  sceneId?: string;
  compact?: boolean;
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

const GENRES = [
  'Cinematic',
  'Ambient',
  'Electronic',
  'Orchestral',
  'Acoustic',
  'Pop',
  'Rock',
  'Jazz',
  'Classical',
  'World',
];

const MOODS = [
  'Epic',
  'Dramatic',
  'Tense',
  'Peaceful',
  'Romantic',
  'Mysterious',
  'Action',
  'Sad',
  'Happy',
  'Inspiring',
];

function TrackItem({
  track,
  isSelected,
  isPlaying,
  onSelect,
  onPlay,
  onToggleFavorite,
}: {
  track: MusicTrack;
  isSelected: boolean;
  isPlaying: boolean;
  onSelect: () => void;
  onPlay: () => void;
  onToggleFavorite: () => void;
}) {
  const { t } = useTranslation();
  return (
    <div
      className={cn(
        'flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-colors',
        isSelected
          ? 'bg-brand-500/20 border border-brand-500/50'
          : 'bg-surface-800/50 border border-transparent hover:bg-surface-800'
      )}
      onClick={onSelect}
    >
      {/* Play button */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          onPlay();
        }}
        className={cn(
          'w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 transition-colors',
          isPlaying ? 'bg-brand-500 text-white' : 'bg-surface-700 hover:bg-surface-600'
        )}
      >
        {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
      </button>

      {/* Track info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium truncate">{track.title}</span>
          {track.isCustom && (
            <span className="px-1.5 py-0.5 bg-purple-500/20 text-purple-400 text-xs rounded">
              {t('musicLib.custom', 'Custom')}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 text-sm text-surface-400">
          {track.artist && <span>{track.artist}</span>}
          <span>•</span>
          <span>{track.genre}</span>
          {track.bpm && (
            <>
              <span>•</span>
              <span>{track.bpm} {t('musicLib.bpm', 'BPM')}</span>
            </>
          )}
        </div>
      </div>

      {/* Mood tags */}
      <div className="hidden md:flex items-center gap-1">
        {track.mood.slice(0, 2).map((mood) => (
          <span key={mood} className="px-2 py-0.5 bg-surface-700 rounded text-xs text-surface-300">
            {mood}
          </span>
        ))}
      </div>

      {/* Duration */}
      <span className="text-sm text-surface-400 w-12 text-right">
        {formatDuration(track.duration)}
      </span>

      {/* Favorite */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          onToggleFavorite();
        }}
        className={cn(
          'p-2 rounded transition-colors',
          track.isFavorite
            ? 'text-red-400 hover:text-red-300'
            : 'text-surface-500 hover:text-surface-300'
        )}
      >
        {track.isFavorite ? (
          <Heart className="w-4 h-4 fill-current" />
        ) : (
          <HeartOff className="w-4 h-4" />
        )}
      </button>

      {/* Selection indicator */}
      {isSelected && (
        <div className="w-6 h-6 rounded-full bg-brand-500 flex items-center justify-center">
          <Check className="w-4 h-4 text-white" />
        </div>
      )}
    </div>
  );
}

export function MusicLibrary({
  onTrackSelect,
  selectedTrackId,
  sceneId,
  compact = false,
}: MusicLibraryProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const audioRef = useRef<HTMLAudioElement>(null);

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedGenre, setSelectedGenre] = useState<string | null>(null);
  const [selectedMood, setSelectedMood] = useState<string | null>(null);
  const [showFavoritesOnly, setShowFavoritesOnly] = useState(false);
  const [showCustomOnly, setShowCustomOnly] = useState(false);
  const [playingId, setPlayingId] = useState<string | null>(null);
  const [volume, setVolume] = useState(0.7);
  const [showFilters, setShowFilters] = useState(!compact);

  // Localized labels for module-scope genre/mood values (values are sent to the backend as-is).
  const genreLabels: Record<string, string> = {
    Cinematic: t('musicLib.genreCinematic', 'Cinematic'),
    Ambient: t('musicLib.genreAmbient', 'Ambient'),
    Electronic: t('musicLib.genreElectronic', 'Electronic'),
    Orchestral: t('musicLib.genreOrchestral', 'Orchestral'),
    Acoustic: t('musicLib.genreAcoustic', 'Acoustic'),
    Pop: t('musicLib.genrePop', 'Pop'),
    Rock: t('musicLib.genreRock', 'Rock'),
    Jazz: t('musicLib.genreJazz', 'Jazz'),
    Classical: t('musicLib.genreClassical', 'Classical'),
    World: t('musicLib.genreWorld', 'World'),
  };
  const moodLabels: Record<string, string> = {
    Epic: t('musicLib.moodEpic', 'Epic'),
    Dramatic: t('musicLib.moodDramatic', 'Dramatic'),
    Tense: t('musicLib.moodTense', 'Tense'),
    Peaceful: t('musicLib.moodPeaceful', 'Peaceful'),
    Romantic: t('musicLib.moodRomantic', 'Romantic'),
    Mysterious: t('musicLib.moodMysterious', 'Mysterious'),
    Action: t('musicLib.moodAction', 'Action'),
    Sad: t('musicLib.moodSad', 'Sad'),
    Happy: t('musicLib.moodHappy', 'Happy'),
    Inspiring: t('musicLib.moodInspiring', 'Inspiring'),
  };

  // Fetch tracks
  const { data: tracks, isLoading } = useQuery({
    queryKey: ['music-library', selectedGenre, selectedMood, showFavoritesOnly, showCustomOnly],
    queryFn: async () => {
      return window.electronAPI.backendRequest<MusicTrack[]>('music.getTracks', {
        genre: selectedGenre,
        mood: selectedMood,
        favorites_only: showFavoritesOnly,
        custom_only: showCustomOnly,
      });
    },
  });

  // Toggle favorite mutation
  const toggleFavoriteMutation = useMutation({
    mutationFn: async (trackId: string) => {
      return window.electronAPI.backendRequest('music.toggleFavorite', {
        track_id: trackId,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['music-library'] });
    },
  });

  // Upload custom track mutation
  const uploadMutation = useMutation({
    mutationFn: async (filePath: string) => {
      return window.electronAPI.backendRequest('music.uploadTrack', {
        file_path: filePath,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['music-library'] });
      showToast(t('musicLib.trackUploadedSuccessfully', 'Track uploaded successfully'), 'success');
    },
    onError: (error: any) => {
      showToast(`${t('musicLib.uploadFailed', 'Upload failed')}: ${error.message}`, 'error');
    },
  });

  // Filter tracks by search
  const filteredTracks = tracks?.filter((track) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      track.title.toLowerCase().includes(query) ||
      track.artist?.toLowerCase().includes(query) ||
      track.genre.toLowerCase().includes(query) ||
      track.mood.some((m) => m.toLowerCase().includes(query)) ||
      track.tags.some((t) => t.toLowerCase().includes(query))
    );
  });

  // Handle play/pause
  const handlePlay = (track: MusicTrack) => {
    if (!audioRef.current) return;

    if (playingId === track.id) {
      audioRef.current.pause();
      setPlayingId(null);
    } else {
      audioRef.current.src = track.audioUrl;
      audioRef.current.volume = volume;
      audioRef.current.play();
      setPlayingId(track.id);
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

  // Handle upload
  const handleUpload = async () => {
    try {
      const result = await window.electronAPI.openFile({
        title: t('musicLib.selectMusicFile', 'Select Music File'),
        filters: [
          {
            name: t('musicLib.audioFiles', 'Audio Files'),
            extensions: ['mp3', 'wav', 'ogg', 'm4a', 'aac'],
          },
        ],
        properties: ['openFile'],
      });

      if (!result.canceled && result.filePaths.length > 0) {
        uploadMutation.mutate(result.filePaths[0]);
      }
    } catch (error) {
      console.error('Failed to open file:', error);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-surface-800">
        <div className="flex items-center gap-2">
          <Music className="w-5 h-5 text-brand-400" />
          <h2 className="font-semibold">{t('musicLib.musicLibrary', 'Music Library')}</h2>
          {tracks && (
            <span className="text-sm text-surface-400">
              ({filteredTracks?.length ?? 0} {t('musicLib.tracks', 'tracks')})
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Volume */}
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
              className="w-20 accent-brand-500"
            />
          </div>

          {/* Upload button */}
          <button
            onClick={handleUpload}
            disabled={uploadMutation.isPending}
            className="btn-secondary text-sm"
          >
            {uploadMutation.isPending ? (
              <Loader2 className="w-4 h-4 mr-1 animate-spin" />
            ) : (
              <Upload className="w-4 h-4 mr-1" />
            )}
            {t('musicLib.upload', 'Upload')}
          </button>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="p-4 border-b border-surface-800 space-y-3">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t('musicLib.searchByTitleArtistGenre', 'Search by title, artist, genre...')}
            className="w-full pl-10 pr-4 py-2 bg-surface-800 border border-surface-700 rounded-lg text-sm"
          />
        </div>

        {/* Filter toggle */}
        <button
          onClick={() => setShowFilters(!showFilters)}
          className="flex items-center gap-2 text-sm text-surface-400 hover:text-surface-200"
        >
          <Filter className="w-4 h-4" />
          {t('musicLib.filters', 'Filters')}
          {showFilters ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </button>

        {/* Filters */}
        {showFilters && (
          <div className="space-y-3">
            {/* Genre filter */}
            <div>
              <label className="text-xs text-surface-500 mb-1 block">
                {t('musicLib.genre', 'Genre')}
              </label>
              <div className="flex flex-wrap gap-1">
                <button
                  onClick={() => setSelectedGenre(null)}
                  className={cn(
                    'px-2 py-1 rounded text-xs transition-colors',
                    selectedGenre === null
                      ? 'bg-brand-500/20 text-brand-400'
                      : 'bg-surface-700 text-surface-300 hover:bg-surface-600'
                  )}
                >
                  {t('musicLib.all', 'All')}
                </button>
                {GENRES.map((genre) => (
                  <button
                    key={genre}
                    onClick={() => setSelectedGenre(genre)}
                    className={cn(
                      'px-2 py-1 rounded text-xs transition-colors',
                      selectedGenre === genre
                        ? 'bg-brand-500/20 text-brand-400'
                        : 'bg-surface-700 text-surface-300 hover:bg-surface-600'
                    )}
                  >
                    {genreLabels[genre] ?? genre}
                  </button>
                ))}
              </div>
            </div>

            {/* Mood filter */}
            <div>
              <label className="text-xs text-surface-500 mb-1 block">
                {t('musicLib.mood', 'Mood')}
              </label>
              <div className="flex flex-wrap gap-1">
                <button
                  onClick={() => setSelectedMood(null)}
                  className={cn(
                    'px-2 py-1 rounded text-xs transition-colors',
                    selectedMood === null
                      ? 'bg-brand-500/20 text-brand-400'
                      : 'bg-surface-700 text-surface-300 hover:bg-surface-600'
                  )}
                >
                  {t('musicLib.all', 'All')}
                </button>
                {MOODS.map((mood) => (
                  <button
                    key={mood}
                    onClick={() => setSelectedMood(mood)}
                    className={cn(
                      'px-2 py-1 rounded text-xs transition-colors',
                      selectedMood === mood
                        ? 'bg-brand-500/20 text-brand-400'
                        : 'bg-surface-700 text-surface-300 hover:bg-surface-600'
                    )}
                  >
                    {moodLabels[mood] ?? mood}
                  </button>
                ))}
              </div>
            </div>

            {/* Quick filters */}
            <div className="flex gap-2">
              <button
                onClick={() => setShowFavoritesOnly(!showFavoritesOnly)}
                className={cn(
                  'flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm transition-colors',
                  showFavoritesOnly
                    ? 'bg-red-500/20 text-red-400'
                    : 'bg-surface-700 text-surface-300 hover:bg-surface-600'
                )}
              >
                <Heart className={cn('w-4 h-4', showFavoritesOnly && 'fill-current')} />
                {t('musicLib.favorites', 'Favorites')}
              </button>
              <button
                onClick={() => setShowCustomOnly(!showCustomOnly)}
                className={cn(
                  'flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm transition-colors',
                  showCustomOnly
                    ? 'bg-purple-500/20 text-purple-400'
                    : 'bg-surface-700 text-surface-300 hover:bg-surface-600'
                )}
              >
                <FolderOpen className="w-4 h-4" />
                {t('musicLib.myUploads', 'My Uploads')}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Track list */}
      <div className="flex-1 overflow-y-auto p-4">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-surface-400" />
          </div>
        ) : filteredTracks && filteredTracks.length > 0 ? (
          <div className="space-y-2">
            {filteredTracks.map((track) => (
              <TrackItem
                key={track.id}
                track={track}
                isSelected={track.id === selectedTrackId}
                isPlaying={track.id === playingId}
                onSelect={() => onTrackSelect?.(track)}
                onPlay={() => handlePlay(track)}
                onToggleFavorite={() => toggleFavoriteMutation.mutate(track.id)}
              />
            ))}
          </div>
        ) : (
          <div className="text-center py-12 text-surface-400">
            <Music2 className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>{t('musicLib.noTracksFound', 'No tracks found')}</p>
            <p className="text-sm text-surface-500 mt-1">
              {t('musicLib.tryAdjustingFiltersOrUpload', 'Try adjusting your filters or upload custom music')}
            </p>
          </div>
        )}
      </div>

      {/* Hidden audio element */}
      <audio ref={audioRef} className="hidden" />
    </div>
  );
}

/**
 * Compact music selector for scene/shot panels.
 */
export function MusicSelector({
  selectedTrackId,
  onSelect,
}: {
  selectedTrackId?: string;
  onSelect: (track: MusicTrack) => void;
}) {
  const { t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);

  const { data: selectedTrack } = useQuery({
    queryKey: ['music-track', selectedTrackId],
    queryFn: async () => {
      if (!selectedTrackId) return null;
      return window.electronAPI.backendRequest<MusicTrack>('music.getTrack', {
        track_id: selectedTrackId,
      });
    },
    enabled: !!selectedTrackId,
  });

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center gap-3 p-3 bg-surface-800 border border-surface-700 rounded-lg hover:border-surface-600 transition-colors"
      >
        <div className="w-10 h-10 rounded-lg bg-surface-700 flex items-center justify-center">
          <Music className="w-5 h-5 text-surface-400" />
        </div>
        <div className="flex-1 text-left">
          {selectedTrack ? (
            <>
              <div className="font-medium">{selectedTrack.title}</div>
              <div className="text-sm text-surface-400">
                {selectedTrack.artist} • {formatDuration(selectedTrack.duration)}
              </div>
            </>
          ) : (
            <>
              <div className="text-surface-400">
                {t('musicLib.selectBackgroundMusic', 'Select background music')}
              </div>
              <div className="text-sm text-surface-500">
                {t('musicLib.browseLibrary', 'Browse library')}
              </div>
            </>
          )}
        </div>
        <ChevronDown
          className={cn('w-5 h-5 text-surface-400 transition-transform', isOpen && 'rotate-180')}
        />
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 right-0 mt-2 bg-surface-800 border border-surface-700 rounded-lg shadow-xl z-50 h-96 overflow-hidden">
          <MusicLibrary
            selectedTrackId={selectedTrackId}
            onTrackSelect={(track) => {
              onSelect(track);
              setIsOpen(false);
            }}
            compact
          />
        </div>
      )}
    </div>
  );
}
