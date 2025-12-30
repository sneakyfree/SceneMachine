/**
 * Voice selector component for assigning TTS voices to characters.
 */

import { useEffect, useState, useRef } from 'react';
import {
  Mic,
  Play,
  Pause,
  Loader2,
  Volume2,
  ChevronDown,
  Check,
  User,
  RefreshCw,
} from 'lucide-react';
import { useAudioStore, Voice, TTSProvider } from '../stores/audio-store';
import { cn } from '../lib/utils';

interface VoiceSelectorProps {
  characterId?: string;
  characterName?: string;
  selectedVoiceId?: string | null;
  selectedProvider?: string | null;
  onVoiceSelect?: (voiceId: string, provider: string, voiceName: string) => void;
  compact?: boolean;
  showPreview?: boolean;
}

// Voice preview player
function VoicePreview({
  voiceId,
  provider,
  voiceName,
}: {
  voiceId: string;
  provider: string;
  voiceName: string;
}) {
  const { previewVoice, isGenerating, previewAudioUrl, previewPlaying, setPreviewPlaying } =
    useAudioStore();
  const audioRef = useRef<HTMLAudioElement>(null);
  const [currentPreviewId, setCurrentPreviewId] = useState<string | null>(null);

  const handlePreview = async () => {
    if (previewPlaying && currentPreviewId === voiceId) {
      // Stop current playback
      audioRef.current?.pause();
      setPreviewPlaying(false);
      return;
    }

    setCurrentPreviewId(voiceId);
    await previewVoice(
      voiceId,
      provider,
      `Hello, my name is ${voiceName}. I can voice your characters with natural speech.`
    );
  };

  useEffect(() => {
    if (previewAudioUrl && audioRef.current && currentPreviewId === voiceId) {
      audioRef.current.src = previewAudioUrl;
      audioRef.current.play();
      setPreviewPlaying(true);
    }
  }, [previewAudioUrl, currentPreviewId, voiceId]);

  const handleEnded = () => {
    setPreviewPlaying(false);
    setCurrentPreviewId(null);
  };

  return (
    <>
      <button
        onClick={handlePreview}
        disabled={isGenerating}
        className="p-1.5 text-surface-400 hover:text-surface-200 hover:bg-surface-700 rounded transition-colors disabled:opacity-50"
        title="Preview voice"
      >
        {isGenerating && currentPreviewId === voiceId ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : previewPlaying && currentPreviewId === voiceId ? (
          <Pause className="w-4 h-4" />
        ) : (
          <Play className="w-4 h-4" />
        )}
      </button>
      <audio ref={audioRef} onEnded={handleEnded} className="hidden" />
    </>
  );
}

// Voice item in dropdown
function VoiceItem({
  voice,
  isSelected,
  onSelect,
  showPreview,
}: {
  voice: Voice;
  isSelected: boolean;
  onSelect: () => void;
  showPreview: boolean;
}) {
  return (
    <div
      className={cn(
        'flex items-center justify-between px-3 py-2 cursor-pointer transition-colors',
        isSelected ? 'bg-brand-500/20' : 'hover:bg-surface-700'
      )}
      onClick={onSelect}
    >
      <div className="flex items-center gap-3 flex-1 min-w-0">
        <div
          className={cn(
            'w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0',
            isSelected ? 'bg-brand-500/30' : 'bg-surface-700'
          )}
        >
          <User className="w-4 h-4" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium truncate">{voice.name}</span>
            {isSelected && <Check className="w-4 h-4 text-brand-400 flex-shrink-0" />}
          </div>
          <div className="flex items-center gap-2 text-xs text-surface-400">
            {voice.gender && <span>{voice.gender}</span>}
            {voice.language && (
              <>
                <span>•</span>
                <span>{voice.language}</span>
              </>
            )}
            {voice.labels &&
              Object.entries(voice.labels)
                .slice(0, 2)
                .map(([key, value]) => (
                  <span key={key} className="px-1.5 py-0.5 bg-surface-700 rounded text-surface-300">
                    {value}
                  </span>
                ))}
          </div>
        </div>
      </div>

      {showPreview && (
        <div className="flex-shrink-0 ml-2" onClick={(e) => e.stopPropagation()}>
          <VoicePreview voiceId={voice.id} provider={voice.provider} voiceName={voice.name} />
        </div>
      )}
    </div>
  );
}

export function VoiceSelector({
  characterId,
  characterName,
  selectedVoiceId,
  selectedProvider,
  onVoiceSelect,
  compact = false,
  showPreview = true,
}: VoiceSelectorProps) {
  const {
    providers,
    voices,
    selectedProvider: storeProvider,
    isLoadingProviders,
    isLoadingVoices,
    error,
    fetchProviders,
    fetchVoices,
    setSelectedProvider,
  } = useAudioStore();

  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Determine active provider
  const activeProvider = selectedProvider || storeProvider;

  // Find selected voice
  const selectedVoice = voices.find((v) => v.id === selectedVoiceId);

  // Filter voices by search
  const filteredVoices = voices.filter(
    (voice) =>
      voice.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      voice.gender?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      voice.language?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Available providers
  const availableProviders = providers.filter((p) => p.available);

  // Fetch providers on mount
  useEffect(() => {
    if (providers.length === 0) {
      fetchProviders();
    }
  }, []);

  // Fetch voices when provider changes
  useEffect(() => {
    if (activeProvider) {
      fetchVoices(activeProvider);
    }
  }, [activeProvider]);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleProviderChange = (providerId: string) => {
    setSelectedProvider(providerId);
    fetchVoices(providerId);
  };

  const handleVoiceSelect = (voice: Voice) => {
    onVoiceSelect?.(voice.id, voice.provider, voice.name);
    setIsOpen(false);
    setSearchQuery('');
  };

  if (compact) {
    return (
      <div className="relative" ref={dropdownRef}>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className={cn(
            'flex items-center gap-2 px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg hover:border-surface-600 transition-colors text-sm w-full',
            isOpen && 'border-brand-500'
          )}
        >
          <Mic className="w-4 h-4 text-surface-400 flex-shrink-0" />
          <span className="flex-1 truncate text-left">
            {selectedVoice ? selectedVoice.name : 'Select voice...'}
          </span>
          <ChevronDown
            className={cn('w-4 h-4 text-surface-400 transition-transform', isOpen && 'rotate-180')}
          />
        </button>

        {isOpen && (
          <div className="absolute top-full left-0 right-0 mt-1 bg-surface-800 border border-surface-700 rounded-lg shadow-xl z-50 overflow-hidden">
            {/* Search */}
            <div className="p-2 border-b border-surface-700">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search voices..."
                className="w-full px-3 py-1.5 bg-surface-900 border border-surface-700 rounded text-sm"
                autoFocus
              />
            </div>

            {/* Voice list */}
            <div className="max-h-64 overflow-y-auto">
              {isLoadingVoices ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-5 h-5 animate-spin text-surface-400" />
                </div>
              ) : filteredVoices.length === 0 ? (
                <div className="py-8 text-center text-surface-400 text-sm">
                  {searchQuery ? 'No voices found' : 'No voices available'}
                </div>
              ) : (
                filteredVoices.map((voice) => (
                  <VoiceItem
                    key={voice.id}
                    voice={voice}
                    isSelected={voice.id === selectedVoiceId}
                    onSelect={() => handleVoiceSelect(voice)}
                    showPreview={showPreview}
                  />
                ))
              )}
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      {characterName && (
        <div className="flex items-center gap-2">
          <Volume2 className="w-5 h-5 text-brand-400" />
          <span className="font-medium">Voice for {characterName}</span>
        </div>
      )}

      {/* Provider selector */}
      <div>
        <label className="block text-sm text-surface-400 mb-2">TTS Provider</label>
        <div className="flex items-center gap-2">
          <select
            value={activeProvider}
            onChange={(e) => handleProviderChange(e.target.value)}
            disabled={isLoadingProviders}
            className="flex-1 bg-surface-800 border border-surface-700 rounded-lg px-3 py-2"
          >
            {availableProviders.map((provider) => (
              <option key={provider.id} value={provider.id}>
                {provider.name} ({provider.voices_count} voices)
              </option>
            ))}
          </select>
          <button
            onClick={() => {
              fetchProviders();
              fetchVoices(activeProvider);
            }}
            disabled={isLoadingProviders || isLoadingVoices}
            className="p-2 bg-surface-700 hover:bg-surface-600 rounded-lg transition-colors disabled:opacity-50"
            title="Refresh"
          >
            <RefreshCw
              className={cn('w-5 h-5', (isLoadingProviders || isLoadingVoices) && 'animate-spin')}
            />
          </button>
        </div>
      </div>

      {/* Voice selector */}
      <div ref={dropdownRef} className="relative">
        <label className="block text-sm text-surface-400 mb-2">Voice</label>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className={cn(
            'flex items-center gap-3 w-full px-4 py-3 bg-surface-800 border border-surface-700 rounded-lg hover:border-surface-600 transition-colors text-left',
            isOpen && 'border-brand-500'
          )}
        >
          <div
            className={cn(
              'w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0',
              selectedVoice ? 'bg-brand-500/20' : 'bg-surface-700'
            )}
          >
            <Mic className="w-5 h-5" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-medium truncate">
              {selectedVoice ? selectedVoice.name : 'Select a voice...'}
            </div>
            {selectedVoice && (
              <div className="text-sm text-surface-400 flex items-center gap-2">
                {selectedVoice.gender && <span>{selectedVoice.gender}</span>}
                {selectedVoice.language && (
                  <>
                    <span>•</span>
                    <span>{selectedVoice.language}</span>
                  </>
                )}
              </div>
            )}
          </div>
          <ChevronDown
            className={cn('w-5 h-5 text-surface-400 transition-transform', isOpen && 'rotate-180')}
          />
        </button>

        {isOpen && (
          <div className="absolute top-full left-0 right-0 mt-1 bg-surface-800 border border-surface-700 rounded-lg shadow-xl z-50 overflow-hidden">
            {/* Search */}
            <div className="p-3 border-b border-surface-700">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search voices..."
                className="w-full px-3 py-2 bg-surface-900 border border-surface-700 rounded-lg"
                autoFocus
              />
            </div>

            {/* Voice list */}
            <div className="max-h-80 overflow-y-auto">
              {isLoadingVoices ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-6 h-6 animate-spin text-surface-400" />
                </div>
              ) : filteredVoices.length === 0 ? (
                <div className="py-12 text-center text-surface-400">
                  {searchQuery ? 'No voices match your search' : 'No voices available'}
                </div>
              ) : (
                filteredVoices.map((voice) => (
                  <VoiceItem
                    key={voice.id}
                    voice={voice}
                    isSelected={voice.id === selectedVoiceId}
                    onSelect={() => handleVoiceSelect(voice)}
                    showPreview={showPreview}
                  />
                ))
              )}
            </div>
          </div>
        )}
      </div>

      {/* Selected voice preview */}
      {selectedVoice && showPreview && (
        <div className="flex items-center gap-3 p-3 bg-surface-800/50 rounded-lg">
          <div className="flex-1">
            <div className="text-sm text-surface-400">Preview selected voice</div>
          </div>
          <VoicePreview
            voiceId={selectedVoice.id}
            provider={selectedVoice.provider}
            voiceName={selectedVoice.name}
          />
        </div>
      )}

      {/* Error */}
      {error && <div className="text-sm text-red-400">{error}</div>}
    </div>
  );
}
