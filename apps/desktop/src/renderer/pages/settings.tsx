/**
 * Comprehensive settings page.
 */

import React, { useEffect, useState, useCallback, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Settings,
  Key,
  Cpu,
  Video,
  Palette,
  HardDrive,
  Save,
  RefreshCw,
  Trash2,
  Check,
  X,
  AlertTriangle,
  Loader2,
  Eye,
  EyeOff,
  Download,
  Upload,
  ExternalLink,
  Info,
  Mic,
  Volume2,
  Play,
  Pause,
} from 'lucide-react';
import { api } from '../api/client';
import { cn } from '../lib/utils';
import {
  useSettingsStore,
  ProviderStatus,
  StorageStats,
} from '../stores/settings-store';
import { useAudioStore, TTSProvider, Voice } from '../stores/audio-store';

// Format bytes to human readable
function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

// API Key input component
function ApiKeyInput({
  provider,
  providerName,
  configured,
  masked,
  onSave,
  onRemove,
  onValidate,
  isSaving,
}: {
  provider: string;
  providerName: string;
  configured: boolean;
  masked: string | null;
  onSave: (key: string) => Promise<void>;
  onRemove: () => Promise<void>;
  onValidate: (key: string) => Promise<ProviderStatus>;
  isSaving: boolean;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [keyValue, setKeyValue] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [validationStatus, setValidationStatus] = useState<ProviderStatus | null>(null);
  const [isValidating, setIsValidating] = useState(false);

  const handleSave = async () => {
    if (!keyValue.trim()) return;
    await onSave(keyValue);
    setKeyValue('');
    setIsEditing(false);
    setValidationStatus(null);
  };

  const handleValidate = async () => {
    if (!keyValue.trim()) return;
    setIsValidating(true);
    try {
      const status = await onValidate(keyValue);
      setValidationStatus(status);
    } finally {
      setIsValidating(false);
    }
  };

  const handleRemove = async () => {
    await onRemove();
    setValidationStatus(null);
  };

  return (
    <div className="p-4 bg-surface-800/50 rounded-lg">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="font-medium">{providerName}</span>
          {configured && (
            <span className="px-2 py-0.5 bg-green-500/20 text-green-400 text-xs rounded">
              Configured
            </span>
          )}
        </div>
        {configured && !isEditing && (
          <div className="flex items-center gap-2">
            <span className="text-sm text-surface-400 font-mono">{masked}</span>
            <button
              onClick={() => setIsEditing(true)}
              className="text-sm text-brand-400 hover:text-brand-300"
            >
              Change
            </button>
            <button
              onClick={handleRemove}
              className="text-sm text-red-400 hover:text-red-300"
              disabled={isSaving}
            >
              Remove
            </button>
          </div>
        )}
      </div>

      {(isEditing || !configured) && (
        <div className="space-y-3">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <input
                type={showKey ? 'text' : 'password'}
                value={keyValue}
                onChange={(e) => setKeyValue(e.target.value)}
                placeholder={`Enter ${providerName} API key`}
                className="w-full bg-surface-900 border border-surface-700 rounded-lg px-3 py-2 pr-10"
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-surface-400 hover:text-surface-300"
              >
                {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            <button
              onClick={handleValidate}
              disabled={!keyValue.trim() || isValidating}
              className="px-3 py-2 bg-surface-700 hover:bg-surface-600 rounded-lg text-sm disabled:opacity-50"
            >
              {isValidating ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                'Test'
              )}
            </button>
            <button
              onClick={handleSave}
              disabled={!keyValue.trim() || isSaving}
              className="px-3 py-2 bg-brand-500 hover:bg-brand-600 rounded-lg text-sm disabled:opacity-50"
            >
              {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Save'}
            </button>
            {isEditing && (
              <button
                onClick={() => {
                  setIsEditing(false);
                  setKeyValue('');
                  setValidationStatus(null);
                }}
                className="px-3 py-2 bg-surface-700 hover:bg-surface-600 rounded-lg text-sm"
              >
                Cancel
              </button>
            )}
          </div>

          {validationStatus && (
            <div
              className={cn(
                'flex items-center gap-2 px-3 py-2 rounded-lg text-sm',
                validationStatus.available
                  ? 'bg-green-500/10 text-green-400'
                  : 'bg-red-500/10 text-red-400'
              )}
            >
              {validationStatus.available ? (
                <Check className="w-4 h-4" />
              ) : (
                <X className="w-4 h-4" />
              )}
              {validationStatus.message}
              {validationStatus.latencyMs && (
                <span className="text-surface-400">
                  ({validationStatus.latencyMs.toFixed(0)}ms)
                </span>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Provider status card
function ProviderStatusCard({ status }: { status: ProviderStatus }) {
  return (
    <div
      className={cn(
        'p-3 rounded-lg border',
        status.available
          ? 'bg-green-500/5 border-green-500/30'
          : status.configured
          ? 'bg-yellow-500/5 border-yellow-500/30'
          : 'bg-surface-800/50 border-surface-700'
      )}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div
            className={cn(
              'w-2 h-2 rounded-full',
              status.available
                ? 'bg-green-400'
                : status.configured
                ? 'bg-yellow-400'
                : 'bg-surface-500'
            )}
          />
          <span className="font-medium">{status.name}</span>
        </div>
        {status.latencyMs && (
          <span className="text-xs text-surface-400">{status.latencyMs.toFixed(0)}ms</span>
        )}
      </div>
      <p className="text-xs text-surface-400 mt-1">{status.message}</p>
    </div>
  );
}

// TTS Settings Section
function TTSSettingsSection() {
  const {
    providers,
    voices,
    selectedProvider,
    isLoadingProviders,
    isLoadingVoices,
    isGenerating,
    previewAudioUrl,
    error,
    fetchProviders,
    fetchVoices,
    setSelectedProvider,
  } = useAudioStore();

  const [previewText, setPreviewText] = useState('Hello, this is a preview of my voice.');
  const [selectedVoice, setSelectedVoice] = useState<Voice | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = React.useRef<HTMLAudioElement>(null);

  // Fetch providers on mount
  useEffect(() => {
    fetchProviders();
  }, []);

  // Fetch voices when provider changes
  useEffect(() => {
    if (selectedProvider) {
      fetchVoices(selectedProvider);
    }
  }, [selectedProvider]);

  const handleProviderChange = (providerId: string) => {
    setSelectedProvider(providerId);
    setSelectedVoice(null);
  };

  const handleVoiceSelect = (voice: Voice) => {
    setSelectedVoice(voice);
  };

  const handlePreview = async () => {
    if (!selectedVoice || isGenerating) return;

    try {
      const result = await window.electronAPI.backendRequest<{
        audio_path: string;
        duration_seconds: number;
      }>('audio.generateSpeech', {
        text: previewText,
        voice_id: selectedVoice.id,
        provider: selectedProvider,
      });

      if (audioRef.current) {
        audioRef.current.src = `file://${result.audio_path}`;
        audioRef.current.play();
        setIsPlaying(true);
      }
    } catch (err) {
      console.error('Failed to preview voice:', err);
    }
  };

  const availableProviders = providers.filter((p) => p.available);
  const currentProvider = providers.find((p) => p.id === selectedProvider);

  return (
    <div className="card mb-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-medium flex items-center gap-2">
          <Volume2 className="w-5 h-5 text-brand-400" />
          Voice & TTS Settings
        </h2>
        <button
          onClick={() => {
            fetchProviders();
            fetchVoices(selectedProvider);
          }}
          disabled={isLoadingProviders || isLoadingVoices}
          className="text-sm text-brand-400 hover:text-brand-300 flex items-center gap-1"
        >
          {(isLoadingProviders || isLoadingVoices) ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <RefreshCw className="w-4 h-4" />
          )}
          Refresh
        </button>
      </div>

      <div className="space-y-4">
        {/* TTS Provider Selection */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-surface-400 mb-2">Default TTS Provider</label>
            <select
              value={selectedProvider}
              onChange={(e) => handleProviderChange(e.target.value)}
              disabled={isLoadingProviders}
              className="w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2"
            >
              {availableProviders.length === 0 ? (
                <option>No providers available</option>
              ) : (
                availableProviders.map((provider) => (
                  <option key={provider.id} value={provider.id}>
                    {provider.name}
                  </option>
                ))
              )}
            </select>
            {currentProvider && (
              <p className="text-xs text-surface-400 mt-1">{currentProvider.description}</p>
            )}
          </div>

          <div>
            <label className="block text-sm text-surface-400 mb-2">Available Voices</label>
            <div className="bg-surface-800/50 rounded-lg px-3 py-2 text-sm">
              {isLoadingVoices ? (
                <span className="text-surface-400">Loading...</span>
              ) : (
                <span>
                  {voices.length} voice{voices.length !== 1 ? 's' : ''} available
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Provider Status Grid */}
        <div>
          <label className="block text-sm text-surface-400 mb-2">Provider Status</label>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {providers.map((provider) => (
              <div
                key={provider.id}
                className={cn(
                  'p-2 rounded-lg border text-sm',
                  provider.available
                    ? 'bg-green-500/5 border-green-500/30'
                    : 'bg-surface-800/50 border-surface-700'
                )}
              >
                <div className="flex items-center gap-2">
                  <div
                    className={cn(
                      'w-2 h-2 rounded-full',
                      provider.available ? 'bg-green-400' : 'bg-surface-500'
                    )}
                  />
                  <span className="font-medium truncate">{provider.name}</span>
                </div>
                <div className="text-xs text-surface-400 mt-1">
                  {provider.voices_count} voices
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Voice Preview */}
        <div className="pt-4 border-t border-surface-700">
          <label className="block text-sm text-surface-400 mb-2">Voice Preview</label>
          <div className="space-y-3">
            {/* Voice Selection */}
            <div className="flex gap-2">
              <select
                value={selectedVoice?.id || ''}
                onChange={(e) => {
                  const voice = voices.find((v) => v.id === e.target.value);
                  if (voice) handleVoiceSelect(voice);
                }}
                disabled={isLoadingVoices || voices.length === 0}
                className="flex-1 bg-surface-800 border border-surface-700 rounded-lg px-3 py-2"
              >
                <option value="">Select a voice to preview...</option>
                {voices.map((voice) => (
                  <option key={voice.id} value={voice.id}>
                    {voice.name}
                    {voice.gender ? ` (${voice.gender})` : ''}
                    {voice.language ? ` - ${voice.language}` : ''}
                  </option>
                ))}
              </select>
            </div>

            {/* Preview Text */}
            <textarea
              value={previewText}
              onChange={(e) => setPreviewText(e.target.value)}
              placeholder="Enter text to preview..."
              rows={2}
              className="w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2 resize-none"
            />

            {/* Preview Button */}
            <div className="flex items-center gap-3">
              <button
                onClick={handlePreview}
                disabled={!selectedVoice || isGenerating || !previewText.trim()}
                className="px-4 py-2 bg-brand-500 hover:bg-brand-600 rounded-lg text-sm flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isGenerating ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : isPlaying ? (
                  <Pause className="w-4 h-4" />
                ) : (
                  <Play className="w-4 h-4" />
                )}
                {isGenerating ? 'Generating...' : isPlaying ? 'Playing' : 'Preview Voice'}
              </button>

              {selectedVoice && (
                <div className="text-sm text-surface-400">
                  Selected: <span className="text-surface-200">{selectedVoice.name}</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Hidden audio element */}
        <audio
          ref={audioRef}
          onEnded={() => setIsPlaying(false)}
          onPause={() => setIsPlaying(false)}
          className="hidden"
        />

        {/* Error Display */}
        {error && (
          <div className="text-sm text-red-400 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            {error}
          </div>
        )}
      </div>
    </div>
  );
}

export function SettingsPage() {
  const queryClient = useQueryClient();
  const {
    settings,
    providerStatuses,
    storageStats,
    llmProviders,
    videoProviders,
    themeOptions,
    isLoading,
    isSaving,
    isValidating,
    error,
    fetchSettings,
    saveSettings,
    setApiKey,
    removeApiKey,
    validateApiKey,
    checkAllProviders,
    fetchStorageStats,
    clearCache,
    fetchProviderOptions,
  } = useSettingsStore();

  // Local state for unsaved changes
  const [localSettings, setLocalSettings] = useState<Record<string, any>>({});
  const [hasChanges, setHasChanges] = useState(false);

  // Fetch version info
  const { data: versionInfo } = useQuery({
    queryKey: ['version'],
    queryFn: () => api.getVersion(),
  });

  // Initial data fetch
  useEffect(() => {
    fetchSettings();
    fetchProviderOptions();
    fetchStorageStats();
    checkAllProviders();
  }, []);

  // Track local changes
  const handleLocalChange = useCallback((key: string, value: any) => {
    setLocalSettings((prev) => ({ ...prev, [key]: value }));
    setHasChanges(true);
  }, []);

  // Save changes
  const handleSave = async () => {
    if (!hasChanges) return;
    try {
      await saveSettings(localSettings);
      setLocalSettings({});
      setHasChanges(false);
    } catch (error) {
      console.error('Failed to save settings:', error);
    }
  };

  // Discard changes
  const handleDiscard = () => {
    setLocalSettings({});
    setHasChanges(false);
  };

  // Clear cache mutation
  const clearCacheMutation = useMutation({
    mutationFn: (cacheType: string) => clearCache(cacheType),
    onSuccess: () => {
      fetchStorageStats();
    },
  });

  // Get current value (local override or saved)
  const getValue = (key: string) => {
    if (key in localSettings) return localSettings[key];
    return settings?.[key as keyof typeof settings];
  };

  if (isLoading && !settings) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 text-brand-400 animate-spin" />
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="p-8 max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Settings className="w-6 h-6 text-brand-400" />
              Settings
            </h1>
            <p className="text-surface-400 mt-1">
              Configure application preferences and API keys
            </p>
          </div>

          {hasChanges && (
            <div className="flex items-center gap-2">
              <button
                onClick={handleDiscard}
                className="px-4 py-2 bg-surface-700 hover:bg-surface-600 rounded-lg text-sm"
              >
                Discard
              </button>
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="px-4 py-2 bg-brand-500 hover:bg-brand-600 rounded-lg text-sm flex items-center gap-2"
              >
                {isSaving ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Save className="w-4 h-4" />
                )}
                Save Changes
              </button>
            </div>
          )}
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-lg flex items-center gap-2 text-red-400">
            <AlertTriangle className="w-5 h-5" />
            {error}
          </div>
        )}

        {/* API Keys Section */}
        <div className="card mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-medium flex items-center gap-2">
              <Key className="w-5 h-5 text-brand-400" />
              API Keys
            </h2>
            <button
              onClick={() => checkAllProviders()}
              disabled={isValidating}
              className="text-sm text-brand-400 hover:text-brand-300 flex items-center gap-1"
            >
              {isValidating ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
              Check All
            </button>
          </div>

          <div className="space-y-4">
            {/* LLM Providers */}
            <div>
              <h3 className="text-sm font-medium text-surface-400 mb-3">LLM Providers</h3>
              <div className="space-y-3">
                <ApiKeyInput
                  provider="anthropic"
                  providerName="Anthropic (Claude)"
                  configured={settings?.apiKeys?.anthropic?.configured || false}
                  masked={settings?.apiKeys?.anthropic?.masked || null}
                  onSave={(key) => setApiKey('anthropic', key)}
                  onRemove={() => removeApiKey('anthropic')}
                  onValidate={(key) => validateApiKey('anthropic', key)}
                  isSaving={isSaving}
                />
                <ApiKeyInput
                  provider="openai"
                  providerName="OpenAI"
                  configured={settings?.apiKeys?.openai?.configured || false}
                  masked={settings?.apiKeys?.openai?.masked || null}
                  onSave={(key) => setApiKey('openai', key)}
                  onRemove={() => removeApiKey('openai')}
                  onValidate={(key) => validateApiKey('openai', key)}
                  isSaving={isSaving}
                />
              </div>
            </div>

            {/* Video Providers */}
            <div>
              <h3 className="text-sm font-medium text-surface-400 mb-3">Video Generation Providers</h3>
              <div className="space-y-3">
                <ApiKeyInput
                  provider="replicate"
                  providerName="Replicate"
                  configured={settings?.apiKeys?.replicate?.configured || false}
                  masked={settings?.apiKeys?.replicate?.masked || null}
                  onSave={(key) => setApiKey('replicate', key)}
                  onRemove={() => removeApiKey('replicate')}
                  onValidate={(key) => validateApiKey('replicate', key)}
                  isSaving={isSaving}
                />
                <ApiKeyInput
                  provider="fal"
                  providerName="Fal.ai"
                  configured={settings?.apiKeys?.fal?.configured || false}
                  masked={settings?.apiKeys?.fal?.masked || null}
                  onSave={(key) => setApiKey('fal', key)}
                  onRemove={() => removeApiKey('fal')}
                  onValidate={(key) => validateApiKey('fal', key)}
                  isSaving={isSaving}
                />
                <ApiKeyInput
                  provider="runwayml"
                  providerName="RunwayML"
                  configured={settings?.apiKeys?.runwayml?.configured || false}
                  masked={settings?.apiKeys?.runwayml?.masked || null}
                  onSave={(key) => setApiKey('runwayml', key)}
                  onRemove={() => removeApiKey('runwayml')}
                  onValidate={(key) => validateApiKey('runwayml', key)}
                  isSaving={isSaving}
                />
              </div>
            </div>

            {/* Voice/TTS Providers */}
            <div>
              <h3 className="text-sm font-medium text-surface-400 mb-3">Voice & TTS Providers</h3>
              <div className="space-y-3">
                <ApiKeyInput
                  provider="elevenlabs"
                  providerName="ElevenLabs"
                  configured={settings?.apiKeys?.elevenlabs?.configured || false}
                  masked={settings?.apiKeys?.elevenlabs?.masked || null}
                  onSave={(key) => setApiKey('elevenlabs', key)}
                  onRemove={() => removeApiKey('elevenlabs')}
                  onValidate={(key) => validateApiKey('elevenlabs', key)}
                  isSaving={isSaving}
                />
                <div className="p-4 bg-surface-800/50 rounded-lg">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">OpenAI TTS</span>
                      {settings?.apiKeys?.openai?.configured && (
                        <span className="px-2 py-0.5 bg-green-500/20 text-green-400 text-xs rounded">
                          Uses OpenAI Key
                        </span>
                      )}
                    </div>
                  </div>
                  <p className="text-sm text-surface-400 mt-2">
                    OpenAI TTS uses your OpenAI API key configured above.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Provider Status */}
        {providerStatuses.length > 0 && (
          <div className="card mb-6">
            <h2 className="text-lg font-medium mb-4 flex items-center gap-2">
              <Cpu className="w-5 h-5 text-brand-400" />
              Provider Status
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {providerStatuses.map((status) => (
                <ProviderStatusCard key={status.provider} status={status} />
              ))}
            </div>
          </div>
        )}

        {/* Generation Settings */}
        <div className="card mb-6">
          <h2 className="text-lg font-medium mb-4 flex items-center gap-2">
            <Video className="w-5 h-5 text-brand-400" />
            Generation Settings
          </h2>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-surface-400 mb-2">
                Default LLM Provider
              </label>
              <select
                value={getValue('llmProvider') || 'anthropic'}
                onChange={(e) => handleLocalChange('llmProvider', e.target.value)}
                className="w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2"
              >
                {llmProviders.map((p) => (
                  <option key={p.value} value={p.value}>
                    {p.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm text-surface-400 mb-2">
                Default Video Provider
              </label>
              <select
                value={getValue('videoProvider') || 'local'}
                onChange={(e) => handleLocalChange('videoProvider', e.target.value)}
                className="w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2"
              >
                {videoProviders.map((p) => (
                  <option key={p.value} value={p.value}>
                    {p.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm text-surface-400 mb-2">
                Default Resolution
              </label>
              <select
                value={getValue('defaultVideoResolution') || '1920x1080'}
                onChange={(e) => handleLocalChange('defaultVideoResolution', e.target.value)}
                className="w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2"
              >
                <option value="1280x720">720p (1280x720)</option>
                <option value="1920x1080">1080p (1920x1080)</option>
                <option value="2560x1440">1440p (2560x1440)</option>
                <option value="3840x2160">4K (3840x2160)</option>
              </select>
            </div>

            <div>
              <label className="block text-sm text-surface-400 mb-2">
                Default Frame Rate
              </label>
              <select
                value={getValue('defaultVideoFps') || 24}
                onChange={(e) => handleLocalChange('defaultVideoFps', parseInt(e.target.value))}
                className="w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2"
              >
                <option value={24}>24 fps (Cinema)</option>
                <option value={25}>25 fps (PAL)</option>
                <option value={30}>30 fps (NTSC)</option>
                <option value={60}>60 fps (Smooth)</option>
              </select>
            </div>

            <div>
              <label className="block text-sm text-surface-400 mb-2">
                Max Concurrent Generations
              </label>
              <input
                type="number"
                min={1}
                max={10}
                value={getValue('maxConcurrentGenerations') || 2}
                onChange={(e) =>
                  handleLocalChange('maxConcurrentGenerations', parseInt(e.target.value))
                }
                className="w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2"
              />
            </div>

            <div>
              <label className="block text-sm text-surface-400 mb-2">
                Generation Timeout (seconds)
              </label>
              <input
                type="number"
                min={60}
                max={3600}
                value={getValue('generationTimeoutSeconds') || 600}
                onChange={(e) =>
                  handleLocalChange('generationTimeoutSeconds', parseInt(e.target.value))
                }
                className="w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2"
              />
            </div>
          </div>
        </div>

        {/* Voice/TTS Settings */}
        <TTSSettingsSection />

        {/* Appearance Settings */}
        <div className="card mb-6">
          <h2 className="text-lg font-medium mb-4 flex items-center gap-2">
            <Palette className="w-5 h-5 text-brand-400" />
            Appearance
          </h2>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-surface-400 mb-2">Theme</label>
              <select
                value={getValue('themeMode') || 'dark'}
                onChange={(e) => handleLocalChange('themeMode', e.target.value)}
                className="w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2"
              >
                {themeOptions.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="mt-4 space-y-3">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={getValue('autoSaveEnabled') ?? true}
                onChange={(e) => handleLocalChange('autoSaveEnabled', e.target.checked)}
                className="w-4 h-4 rounded border-surface-600 bg-surface-800"
              />
              <span className="text-sm">Auto-save projects</span>
            </label>

            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={getValue('showAdvancedOptions') ?? false}
                onChange={(e) => handleLocalChange('showAdvancedOptions', e.target.checked)}
                className="w-4 h-4 rounded border-surface-600 bg-surface-800"
              />
              <span className="text-sm">Show advanced options</span>
            </label>
          </div>
        </div>

        {/* Storage Settings */}
        <div className="card mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-medium flex items-center gap-2">
              <HardDrive className="w-5 h-5 text-brand-400" />
              Storage
            </h2>
            <button
              onClick={() => fetchStorageStats()}
              className="text-sm text-brand-400 hover:text-brand-300 flex items-center gap-1"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>
          </div>

          {storageStats && (
            <div className="space-y-4">
              {/* Storage Stats */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-surface-800/50 rounded-lg p-3">
                  <div className="text-xs text-surface-400 mb-1">Total Data</div>
                  <div className="text-lg font-bold">
                    {formatBytes(storageStats.totalSizeBytes)}
                  </div>
                </div>
                <div className="bg-surface-800/50 rounded-lg p-3">
                  <div className="text-xs text-surface-400 mb-1">Uploads</div>
                  <div className="text-lg font-bold">
                    {formatBytes(storageStats.uploadSizeBytes)}
                  </div>
                </div>
                <div className="bg-surface-800/50 rounded-lg p-3">
                  <div className="text-xs text-surface-400 mb-1">Outputs</div>
                  <div className="text-lg font-bold">
                    {formatBytes(storageStats.outputSizeBytes)}
                  </div>
                </div>
                <div className="bg-surface-800/50 rounded-lg p-3">
                  <div className="text-xs text-surface-400 mb-1">Cache</div>
                  <div className="text-lg font-bold">
                    {formatBytes(storageStats.cacheSizeBytes)}
                  </div>
                </div>
              </div>

              {/* Paths */}
              <div className="text-sm space-y-2">
                <div className="flex justify-between">
                  <span className="text-surface-400">Data Directory</span>
                  <span className="font-mono text-surface-300">{storageStats.dataDir}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-surface-400">Cache Directory</span>
                  <span className="font-mono text-surface-300">{storageStats.cacheDir}</span>
                </div>
                {storageStats.tempFilesCount > 0 && (
                  <div className="flex justify-between text-yellow-400">
                    <span>Temporary Files</span>
                    <span>{storageStats.tempFilesCount} files</span>
                  </div>
                )}
              </div>

              {/* Cache Actions */}
              <div className="flex gap-2 pt-2">
                <button
                  onClick={() => clearCacheMutation.mutate('temp')}
                  disabled={clearCacheMutation.isPending}
                  className="px-3 py-2 bg-surface-700 hover:bg-surface-600 rounded-lg text-sm flex items-center gap-2"
                >
                  {clearCacheMutation.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Trash2 className="w-4 h-4" />
                  )}
                  Clear Temp Files
                </button>
                <button
                  onClick={() => clearCacheMutation.mutate('model')}
                  disabled={clearCacheMutation.isPending}
                  className="px-3 py-2 bg-surface-700 hover:bg-surface-600 rounded-lg text-sm flex items-center gap-2"
                >
                  {clearCacheMutation.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Trash2 className="w-4 h-4" />
                  )}
                  Clear Model Cache
                </button>
              </div>

              {/* Cache Settings */}
              <div className="pt-4 border-t border-surface-700">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-surface-400 mb-2">
                      Max Cache Size (GB)
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={100}
                      value={getValue('maxCacheSizeGb') || 10}
                      onChange={(e) =>
                        handleLocalChange('maxCacheSizeGb', parseInt(e.target.value))
                      }
                      className="w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2"
                    />
                  </div>
                </div>

                <label className="flex items-center gap-3 cursor-pointer mt-4">
                  <input
                    type="checkbox"
                    checked={getValue('autoCleanupTempFiles') ?? true}
                    onChange={(e) =>
                      handleLocalChange('autoCleanupTempFiles', e.target.checked)
                    }
                    className="w-4 h-4 rounded border-surface-600 bg-surface-800"
                  />
                  <span className="text-sm">Automatically cleanup temporary files</span>
                </label>
              </div>
            </div>
          )}
        </div>

        {/* Export Defaults */}
        <div className="card mb-6">
          <h2 className="text-lg font-medium mb-4 flex items-center gap-2">
            <Download className="w-5 h-5 text-brand-400" />
            Export Defaults
          </h2>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-surface-400 mb-2">
                Default Export Format
              </label>
              <select
                value={getValue('defaultExportFormat') || 'mp4_h264'}
                onChange={(e) => handleLocalChange('defaultExportFormat', e.target.value)}
                className="w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2"
              >
                <option value="mp4_h264">MP4 (H.264)</option>
                <option value="mp4_h265">MP4 (H.265/HEVC)</option>
                <option value="mov_prores">MOV (ProRes)</option>
                <option value="webm_vp9">WebM (VP9)</option>
                <option value="mkv_h264">MKV (H.264)</option>
              </select>
            </div>

            <div>
              <label className="block text-sm text-surface-400 mb-2">
                Default Export Quality
              </label>
              <select
                value={getValue('defaultExportQuality') || 'high'}
                onChange={(e) => handleLocalChange('defaultExportQuality', e.target.value)}
                className="w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2"
              >
                <option value="draft">Draft (Fast)</option>
                <option value="standard">Standard</option>
                <option value="high">High</option>
                <option value="master">Master (Slow)</option>
              </select>
            </div>
          </div>
        </div>

        {/* Application Info */}
        <div className="card">
          <h2 className="text-lg font-medium mb-4 flex items-center gap-2">
            <Info className="w-5 h-5 text-brand-400" />
            About
          </h2>

          <div className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-surface-400">Version</span>
              <span>{versionInfo?.version || 'Unknown'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-surface-400">Environment</span>
              <span>{versionInfo?.environment || 'Unknown'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-surface-400">Platform</span>
              <span>{window.electronAPI?.platform || 'Unknown'}</span>
            </div>
          </div>

          <div className="mt-4 pt-4 border-t border-surface-800">
            <p className="text-sm text-surface-400 mb-4">
              SceneMachine.ai is a screenplay-to-movie platform that enables users to
              transform written screenplays into generated video content.
            </p>
            <a
              href="https://scenemachine.ai"
              target="_blank"
              rel="noopener noreferrer"
              className="text-brand-400 hover:text-brand-300 text-sm flex items-center gap-1"
            >
              Visit Website
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
