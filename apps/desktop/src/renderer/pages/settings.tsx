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
  DollarSign,
  Sparkles,
  MessageCircle,
  User,
  Accessibility,
  Type,
  Contrast,
  MousePointer,
  Minimize2,
  Keyboard,
} from 'lucide-react';
import { api } from '../api/client';
import { cn } from '../lib/utils';
import {
  useSettingsStore,
  ProviderStatus,
  StorageStats,
  FontSizeScale,
} from '../stores/settings-store';
import { useExperienceStore } from '../stores/experience-store';
import { useAudioStore, TTSProvider, Voice } from '../stores/audio-store';
import { BudgetSettings } from '../components/budget-settings';
import { CircuitBreakerPanel } from '../components/circuit-breaker-status';
import { ExperienceModeSelector } from '../components/experience-mode-selector';
import { useToast } from '../components/toast';
import { announce } from '../lib/accessibility';
import { useTranslation } from '../i18n/use-translation';

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
  const { t } = useTranslation();
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
              {t('settings.configured', 'Configured')}
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
              {t('settings.change', 'Change')}
            </button>
            <button
              onClick={handleRemove}
              className="text-sm text-red-400 hover:text-red-300"
              disabled={isSaving}
            >
              {t('settings.remove', 'Remove')}
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
                placeholder={`${t('settings.enter', 'Enter')} ${providerName} ${t('settings.apiKeyLower', 'API key')}`}
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
              {isValidating ? <Loader2 className="w-4 h-4 animate-spin" /> : t('settings.test', 'Test')}
            </button>
            <button
              onClick={handleSave}
              disabled={!keyValue.trim() || isSaving}
              className="px-3 py-2 bg-brand-500 hover:bg-brand-600 rounded-lg text-sm disabled:opacity-50"
            >
              {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : t('settings.save', 'Save')}
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
                {t('settings.cancel', 'Cancel')}
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
  const { t } = useTranslation();
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

  const [previewText, setPreviewText] = useState(
    t('settings.voicePreviewDefaultText', 'Hello, this is a preview of my voice.')
  );
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
          {t('settings.voiceTtsSettings', 'Voice & TTS Settings')}
        </h2>
        <button
          onClick={() => {
            fetchProviders();
            fetchVoices(selectedProvider);
          }}
          disabled={isLoadingProviders || isLoadingVoices}
          className="text-sm text-brand-400 hover:text-brand-300 flex items-center gap-1"
        >
          {isLoadingProviders || isLoadingVoices ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <RefreshCw className="w-4 h-4" />
          )}
          {t('settings.refresh', 'Refresh')}
        </button>
      </div>

      <div className="space-y-4">
        {/* TTS Provider Selection */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-surface-400 mb-2">{t('settings.defaultTtsProvider', 'Default TTS Provider')}</label>
            <select
              value={selectedProvider}
              onChange={(e) => handleProviderChange(e.target.value)}
              disabled={isLoadingProviders}
              className="w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2"
            >
              {availableProviders.length === 0 ? (
                <option>{t('settings.noProvidersAvailable', 'No providers available')}</option>
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
            <label className="block text-sm text-surface-400 mb-2">{t('settings.availableVoices', 'Available Voices')}</label>
            <div className="bg-surface-800/50 rounded-lg px-3 py-2 text-sm">
              {isLoadingVoices ? (
                <span className="text-surface-400">{t('settings.loading', 'Loading...')}</span>
              ) : (
                <span>
                  {voices.length} voice{voices.length !== 1 ? 's' : ''} {t('settings.available', 'available')}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Provider Status Grid */}
        <div>
          <label className="block text-sm text-surface-400 mb-2">{t('settings.providerStatus', 'Provider Status')}</label>
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
                <div className="text-xs text-surface-400 mt-1">{provider.voices_count} {t('settings.voicesUnit', 'voices')}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Voice Preview */}
        <div className="pt-4 border-t border-surface-700">
          <label className="block text-sm text-surface-400 mb-2">{t('settings.voicePreview', 'Voice Preview')}</label>
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
                <option value="">{t('settings.selectVoiceToPreview', 'Select a voice to preview...')}</option>
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
              placeholder={t('settings.enterTextToPreview', 'Enter text to preview...')}
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
                {isGenerating
                  ? t('settings.generating', 'Generating...')
                  : isPlaying
                    ? t('settings.playing', 'Playing')
                    : t('settings.previewVoice', 'Preview Voice')}
              </button>

              {selectedVoice && (
                <div className="text-sm text-surface-400">
                  {t('settings.selected', 'Selected:')} <span className="text-surface-200">{selectedVoice.name}</span>
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

// Accessibility Settings Section
function AccessibilitySettingsSection() {
  const { t } = useTranslation();
  const { settings, saveSettings, isSaving } = useSettingsStore();

  const [localFontSize, setLocalFontSize] = useState<FontSizeScale>(
    settings?.fontSizeScale || 'medium'
  );
  const [localHighContrast, setLocalHighContrast] = useState(
    settings?.highContrastEnabled || false
  );
  const [localReduceMotion, setLocalReduceMotion] = useState(
    settings?.reduceMotionEnabled || false
  );
  const [localLargeTargets, setLocalLargeTargets] = useState(
    settings?.largeClickTargetsEnabled || false
  );
  const [hasChanges, setHasChanges] = useState(false);

  // Sync local state when settings load
  useEffect(() => {
    if (settings) {
      setLocalFontSize(settings.fontSizeScale || 'medium');
      setLocalHighContrast(settings.highContrastEnabled || false);
      setLocalReduceMotion(settings.reduceMotionEnabled || false);
      setLocalLargeTargets(settings.largeClickTargetsEnabled || false);
      setHasChanges(false);
    }
  }, [settings]);

  const handleFontSizeChange = (size: FontSizeScale) => {
    setLocalFontSize(size);
    setHasChanges(true);
  };

  const handleSave = async () => {
    try {
      await saveSettings({
        fontSizeScale: localFontSize,
        highContrastEnabled: localHighContrast,
        reduceMotionEnabled: localReduceMotion,
        largeClickTargetsEnabled: localLargeTargets,
      });
      setHasChanges(false);
    } catch (error) {
      console.error('Failed to save accessibility settings:', error);
    }
  };

  const FONT_SIZE_OPTIONS: { value: FontSizeScale; label: string; preview: string }[] = [
    { value: 'small', label: t('settings.fontSizeSmall', 'Small'), preview: 'Aa' },
    { value: 'medium', label: t('settings.fontSizeMedium', 'Medium'), preview: 'Aa' },
    { value: 'large', label: t('settings.fontSizeLarge', 'Large'), preview: 'Aa' },
    { value: 'extra-large', label: t('settings.fontSizeExtraLarge', 'Extra Large'), preview: 'Aa' },
  ];

  const fontSizePreviewClasses: Record<FontSizeScale, string> = {
    small: 'text-sm',
    medium: 'text-base',
    large: 'text-lg',
    'extra-large': 'text-xl',
  };

  return (
    <div className="card mb-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-medium flex items-center gap-2">
          <Accessibility className="w-5 h-5 text-brand-400" />
          {t('settings.accessibility', 'Accessibility')}
        </h2>
        {hasChanges && (
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="px-4 py-2 bg-brand-500 hover:bg-brand-600 rounded-lg text-sm flex items-center gap-2"
          >
            {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            {t('settings.saveChanges', 'Save Changes')}
          </button>
        )}
      </div>

      <p className="text-sm text-surface-400 mb-6">
        {t(
          'settings.accessibilityIntro',
          'Customize the interface to make it easier to use. These settings help with visibility and navigation.'
        )}
      </p>

      {/* Font Size Selection */}
      <div className="mb-6">
        <label className="flex items-center gap-2 text-sm text-surface-400 mb-3">
          <Type className="w-4 h-4" />
          {t('settings.textSize', 'Text Size')}
        </label>
        <div className="grid grid-cols-4 gap-3">
          {FONT_SIZE_OPTIONS.map((option) => {
            const isSelected = localFontSize === option.value;
            return (
              <button
                key={option.value}
                onClick={() => handleFontSizeChange(option.value)}
                className={cn(
                  'p-4 rounded-lg border text-center transition-all',
                  isSelected
                    ? 'bg-brand-500/20 border-brand-500/50 text-brand-400'
                    : 'bg-surface-800/50 border-surface-700 hover:border-surface-600'
                )}
              >
                <div className={cn('font-bold mb-1', fontSizePreviewClasses[option.value])}>
                  {option.preview}
                </div>
                <div className="text-xs text-surface-400">{option.label}</div>
              </button>
            );
          })}
        </div>

        {/* Live Preview */}
        <div className="mt-4 p-4 bg-surface-800/30 rounded-lg border border-surface-700">
          <div className="text-xs text-surface-500 mb-2">{t('settings.previewLabel', 'Preview:')}</div>
          <p className={cn('text-surface-200', fontSizePreviewClasses[localFontSize])}>
            {t(
              'settings.fontSizePreviewText',
              'This is how text will appear with the selected size. Larger text is easier to read.'
            )}
          </p>
        </div>
      </div>

      {/* Toggle Options */}
      <div className="space-y-4">
        {/* High Contrast */}
        <div className="flex items-center justify-between p-4 bg-surface-800/50 rounded-lg">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-surface-700 rounded-lg flex items-center justify-center">
              <Contrast className="w-5 h-5 text-surface-300" />
            </div>
            <div>
              <h3 className="font-medium">{t('settings.highContrast', 'High Contrast')}</h3>
              <p className="text-sm text-surface-400">
                {t('settings.highContrastDesc', 'Increases contrast between elements for better visibility')}
              </p>
            </div>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={localHighContrast}
              onChange={() => {
                setLocalHighContrast(!localHighContrast);
                setHasChanges(true);
              }}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-surface-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-brand-500"></div>
          </label>
        </div>

        {/* Reduce Motion */}
        <div className="flex items-center justify-between p-4 bg-surface-800/50 rounded-lg">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-surface-700 rounded-lg flex items-center justify-center">
              <Minimize2 className="w-5 h-5 text-surface-300" />
            </div>
            <div>
              <h3 className="font-medium">{t('settings.reduceMotion', 'Reduce Motion')}</h3>
              <p className="text-sm text-surface-400">
                {t('settings.reduceMotionDesc', 'Minimizes animations and transitions throughout the app')}
              </p>
            </div>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={localReduceMotion}
              onChange={() => {
                setLocalReduceMotion(!localReduceMotion);
                setHasChanges(true);
              }}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-surface-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-brand-500"></div>
          </label>
        </div>

        {/* Large Click Targets */}
        <div className="flex items-center justify-between p-4 bg-surface-800/50 rounded-lg">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-surface-700 rounded-lg flex items-center justify-center">
              <MousePointer className="w-5 h-5 text-surface-300" />
            </div>
            <div>
              <h3 className="font-medium">{t('settings.largeClickTargets', 'Large Click Targets')}</h3>
              <p className="text-sm text-surface-400">
                {t('settings.largeClickTargetsDesc', 'Makes buttons and interactive elements larger and easier to click')}
              </p>
            </div>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={localLargeTargets}
              onChange={() => {
                setLocalLargeTargets(!localLargeTargets);
                setHasChanges(true);
              }}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-surface-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-brand-500"></div>
          </label>
        </div>
      </div>

      {/* System Preferences Note */}
      <div className="mt-6 p-3 bg-surface-800/30 rounded-lg border border-surface-700">
        <p className="text-xs text-surface-400">
          <Info className="w-3 h-3 inline mr-1" />
          {t(
            'settings.systemPrefsNote',
            'SceneMachine also respects your system accessibility preferences for reduced motion and high contrast.'
          )}
        </p>
      </div>
    </div>
  );
}

// Experience Mode Settings Section
function ExperienceModeSettingsSection() {
  const { t } = useTranslation();
  const {
    globalMode,
    featureOverrides,
    stevenEnabled,
    setGlobalMode,
    setStevenEnabled,
    setFeatureMode,
    resetFeatureOverrides,
  } = useExperienceStore();

  const FEATURE_LABELS: Record<string, { label: string; description: string }> = {
    screenplay: {
      label: t('settings.featureScreenplay', 'Screenplay'),
      description: t('settings.featureScreenplayDesc', 'Script upload and parsing'),
    },
    characters: {
      label: t('settings.featureCharacters', 'Characters'),
      description: t('settings.featureCharactersDesc', 'Character management'),
    },
    scenes: {
      label: t('settings.featureScenes', 'Scenes'),
      description: t('settings.featureScenesDesc', 'Scene planning and breakdown'),
    },
    generation: {
      label: t('settings.featureGeneration', 'Generation'),
      description: t('settings.featureGenerationDesc', 'Video generation queue'),
    },
    timeline: {
      label: t('settings.featureTimeline', 'Timeline'),
      description: t('settings.featureTimelineDesc', 'Timeline editing'),
    },
    export: {
      label: t('settings.featureExport', 'Export'),
      description: t('settings.featureExportDesc', 'Export settings'),
    },
    settings: {
      label: t('settings.featureSettings', 'Settings'),
      description: t('settings.featureSettingsDesc', 'App configuration'),
    },
  };

  const MODE_INFO = {
    story: {
      label: t('settings.storyMode', 'Story Mode'),
      icon: '📖',
      description: t(
        'settings.storyModeDesc',
        'Simplified interface with friendly language. Perfect for beginners.'
      ),
      color: 'bg-green-500/20 text-green-400 border-green-500/30',
    },
    creator: {
      label: t('settings.creatorMode', 'Creator Mode'),
      icon: '🎬',
      description: t(
        'settings.creatorModeDesc',
        'Balanced interface with helpful guidance. Great for most users.'
      ),
      color: 'bg-brand-500/20 text-brand-400 border-brand-500/30',
    },
    pro: {
      label: t('settings.proMode', 'Pro Mode'),
      icon: '🎥',
      description: t(
        'settings.proModeDesc',
        'Full interface with technical details. For experienced filmmakers.'
      ),
      color: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
    },
  };

  const hasOverrides = Object.keys(featureOverrides).length > 0;

  return (
    <div className="card mb-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-medium flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-brand-400" />
          {t('settings.experienceMode', 'Experience Mode')}
        </h2>
        {hasOverrides && (
          <button
            onClick={resetFeatureOverrides}
            className="text-sm text-surface-400 hover:text-surface-300"
          >
            {t('settings.resetToDefaults', 'Reset to Defaults')}
          </button>
        )}
      </div>

      <p className="text-sm text-surface-400 mb-6">
        {t(
          'settings.experienceModeIntro',
          'Choose how much detail you want to see. You can customize each feature individually.'
        )}
      </p>

      {/* Global Mode Selection */}
      <div className="mb-6">
        <label className="block text-sm text-surface-400 mb-3">{t('settings.globalExperienceLevel', 'Global Experience Level')}</label>
        <div className="grid grid-cols-3 gap-3">
          {(['story', 'creator', 'pro'] as const).map((mode) => {
            const info = MODE_INFO[mode];
            const isSelected = globalMode === mode;
            return (
              <button
                key={mode}
                onClick={() => setGlobalMode(mode)}
                className={cn(
                  'p-4 rounded-lg border text-left transition-all',
                  isSelected
                    ? info.color
                    : 'bg-surface-800/50 border-surface-700 hover:border-surface-600'
                )}
              >
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xl">{info.icon}</span>
                  <span className="font-medium">{info.label}</span>
                </div>
                <p className="text-xs text-surface-400">{info.description}</p>
              </button>
            );
          })}
        </div>
      </div>

      {/* Steven AI Assistant Toggle */}
      <div className="mb-6 p-4 bg-surface-800/50 rounded-lg">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-brand-500/20 rounded-full flex items-center justify-center">
              <MessageCircle className="w-5 h-5 text-brand-400" />
            </div>
            <div>
              <h3 className="font-medium">{t('settings.stevenAiAssistant', 'Steven AI Assistant')}</h3>
              <p className="text-sm text-surface-400">{t('settings.stevenAiTagline', 'Your personal movie-making guide')}</p>
            </div>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={stevenEnabled}
              onChange={() => setStevenEnabled(!stevenEnabled)}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-surface-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-brand-500"></div>
          </label>
        </div>
        {stevenEnabled && (
          <p className="text-xs text-surface-400 mt-3">
            {t(
              'settings.stevenAiHelp',
              'Steven will appear in the corner to help you through each step. Click on him anytime for tips!'
            )}
          </p>
        )}
      </div>

      {/* Per-Feature Overrides */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <label className="block text-sm text-surface-400">{t('settings.perFeatureCustomization', 'Per-Feature Customization')}</label>
          <span className="text-xs text-surface-500">
            {t('settings.perFeatureOverrideHint', 'Override global mode for specific features')}
          </span>
        </div>
        <div className="space-y-2">
          {Object.entries(FEATURE_LABELS).map(([feature, info]) => {
            const override = featureOverrides[feature as keyof typeof featureOverrides];
            return (
              <div
                key={feature}
                className="flex items-center justify-between p-3 bg-surface-800/30 rounded-lg"
              >
                <div>
                  <span className="font-medium text-sm">{info.label}</span>
                  <span className="text-xs text-surface-500 ml-2">{info.description}</span>
                </div>
                <select
                  value={override || ''}
                  onChange={(e) =>
                    setFeatureMode(
                      feature as
                        | 'screenplay'
                        | 'characters'
                        | 'scenes'
                        | 'generation'
                        | 'timeline'
                        | 'export'
                        | 'settings',
                      e.target.value ? (e.target.value as 'story' | 'creator' | 'pro') : null
                    )
                  }
                  className={cn(
                    'bg-surface-800 border rounded px-2 py-1 text-sm',
                    override
                      ? 'border-brand-500/50 text-brand-400'
                      : 'border-surface-700 text-surface-400'
                  )}
                >
                  <option value="">{t('settings.useGlobal', 'Use Global')} ({globalMode})</option>
                  <option value="story">{t('settings.storyMode', 'Story Mode')}</option>
                  <option value="creator">{t('settings.creatorMode', 'Creator Mode')}</option>
                  <option value="pro">{t('settings.proMode', 'Pro Mode')}</option>
                </select>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export function SettingsPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { addToast } = useToast();
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
  const [showShortcuts, setShowShortcuts] = useState(false);

  // Fetch version info
  const { data: versionInfo } = useQuery({
    queryKey: ['version'],
    queryFn: () => api.getVersion(),
  });

  // Fetch cost stats for budget display
  const { data: costStats } = useQuery({
    queryKey: ['cost-stats'],
    queryFn: async () => {
      const periodDays = settings?.budgetPeriodDays || 30;
      return api.getCostStats({
        timeRange: periodDays <= 7 ? '7d' : periodDays <= 30 ? '30d' : 'all',
      });
    },
    refetchInterval: 60000, // Refresh every minute
  });

  // Handle budget save
  const handleBudgetSave = async (limit: number | null, periodDays: number) => {
    await saveSettings({
      budgetLimitUsd: limit,
      budgetPeriodDays: periodDays,
    });
  };

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
      addToast({
        type: 'success',
        title: t('settings.toastSettingsSavedTitle', 'Settings Saved'),
        message: t('settings.toastSettingsSavedMessage', 'Your preferences have been saved successfully.'),
      });
      announce(t('settings.announceSettingsSaved', 'Settings saved successfully'));
    } catch (err) {
      console.error('Failed to save settings:', err);
      addToast({
        type: 'error',
        title: t('settings.toastSaveFailedTitle', 'Save Failed'),
        message: t('settings.toastSaveFailedMessage', 'Failed to save settings. Please try again.'),
      });
      announce(t('settings.announceSaveFailed', 'Failed to save settings'));
    }
  };

  // Discard changes
  const handleDiscard = () => {
    setLocalSettings({});
    setHasChanges(false);
    addToast({
      type: 'info',
      title: t('settings.toastChangesDiscardedTitle', 'Changes Discarded'),
      message: t('settings.toastChangesDiscardedMessage', 'Your changes have been discarded.'),
    });
    announce(t('settings.announceChangesDiscarded', 'Changes discarded'));
  };

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // ? - Show shortcuts help
      if (e.key === '?' && !e.ctrlKey && !e.metaKey) {
        const target = e.target as HTMLElement;
        if (
          target.tagName !== 'INPUT' &&
          target.tagName !== 'TEXTAREA' &&
          target.tagName !== 'SELECT'
        ) {
          e.preventDefault();
          setShowShortcuts(true);
          announce(t('settings.announceShortcutsOpened', 'Keyboard shortcuts opened'));
        }
      }
      // Escape - Close shortcuts or discard changes
      if (e.key === 'Escape') {
        if (showShortcuts) {
          setShowShortcuts(false);
          announce(t('settings.announceShortcutsClosed', 'Keyboard shortcuts closed'));
        } else if (hasChanges) {
          handleDiscard();
        }
      }
      // Ctrl/Cmd + S - Save changes
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        if (hasChanges) {
          handleSave();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [hasChanges, showShortcuts]);

  // Clear cache mutation
  const clearCacheMutation = useMutation({
    mutationFn: (cacheType: string) => clearCache(cacheType),
    onSuccess: (_data, cacheType) => {
      fetchStorageStats();
      addToast({
        type: 'success',
        title: t('settings.toastCacheClearedTitle', 'Cache Cleared'),
        message: `${cacheType.charAt(0).toUpperCase() + cacheType.slice(1)} ${t('settings.toastCacheClearedMessage', 'cache has been cleared.')}`,
      });
      announce(`${cacheType} ${t('settings.announceCacheCleared', 'cache cleared')}`);
    },
    onError: (_error, cacheType) => {
      addToast({
        type: 'error',
        title: t('settings.toastClearFailedTitle', 'Clear Failed'),
        message: `${t('settings.toastClearFailedMessagePrefix', 'Failed to clear')} ${cacheType} ${t('settings.toastClearFailedMessageSuffix', 'cache.')}`,
      });
      announce(`${t('settings.announceClearFailedPrefix', 'Failed to clear')} ${cacheType} ${t('settings.announceClearFailedSuffix', 'cache')}`);
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
              {t('settings.title', 'Settings')}
            </h1>
            <p className="text-surface-400 mt-1">{t('settings.subtitle', 'Configure application preferences and API keys')}</p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowShortcuts(true)}
              className="p-2 text-surface-400 hover:text-surface-200 hover:bg-surface-700 rounded-lg"
              title={t('settings.keyboardShortcutsTitle', 'Keyboard shortcuts (?)')}
              aria-label={t('settings.showKeyboardShortcutsAria', 'Show keyboard shortcuts')}
            >
              <Keyboard className="w-5 h-5" />
            </button>
            {hasChanges && (
              <>
                <button
                  onClick={handleDiscard}
                  className="px-4 py-2 bg-surface-700 hover:bg-surface-600 rounded-lg text-sm"
                  title={t('settings.discardChangesTitle', 'Discard changes (Escape)')}
                >
                  {t('settings.discard', 'Discard')}
                </button>
                <button
                  onClick={handleSave}
                  disabled={isSaving}
                  className="px-4 py-2 bg-brand-500 hover:bg-brand-600 rounded-lg text-sm flex items-center gap-2"
                  title={t('settings.saveChangesTitle', 'Save changes (Ctrl+S)')}
                >
                  {isSaving ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Save className="w-4 h-4" />
                  )}
                  {t('settings.saveChanges', 'Save Changes')}
                </button>
              </>
            )}
          </div>
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
              {t('settings.apiKeys', 'API Keys')}
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
              {t('settings.checkAll', 'Check All')}
            </button>
          </div>

          <div className="space-y-4">
            {/* LLM Providers */}
            <div>
              <h3 className="text-sm font-medium text-surface-400 mb-3">{t('settings.llmProviders', 'LLM Providers')}</h3>
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
              <h3 className="text-sm font-medium text-surface-400 mb-3">
                {t('settings.videoGenerationProviders', 'Video Generation Providers')}
              </h3>
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
              <h3 className="text-sm font-medium text-surface-400 mb-3">{t('settings.voiceTtsProviders', 'Voice & TTS Providers')}</h3>
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
                          {t('settings.usesOpenaiKey', 'Uses OpenAI Key')}
                        </span>
                      )}
                    </div>
                  </div>
                  <p className="text-sm text-surface-400 mt-2">
                    {t('settings.openaiTtsNote', 'OpenAI TTS uses your OpenAI API key configured above.')}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Accessibility Settings - Placed prominently for elderly users */}
        <AccessibilitySettingsSection />

        {/* Provider Status */}
        {providerStatuses.length > 0 && (
          <div className="card mb-6">
            <h2 className="text-lg font-medium mb-4 flex items-center gap-2">
              <Cpu className="w-5 h-5 text-brand-400" />
              {t('settings.providerStatus', 'Provider Status')}
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {providerStatuses.map((status) => (
                <ProviderStatusCard key={status.provider} status={status} />
              ))}
            </div>
          </div>
        )}

        {/* Circuit Breaker Status */}
        <div className="card mb-6">
          <CircuitBreakerPanel />
        </div>

        {/* Generation Settings */}
        <div className="card mb-6">
          <h2 className="text-lg font-medium mb-4 flex items-center gap-2">
            <Video className="w-5 h-5 text-brand-400" />
            {t('settings.generationSettings', 'Generation Settings')}
          </h2>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-surface-400 mb-2">{t('settings.defaultLlmProvider', 'Default LLM Provider')}</label>
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
              <label className="block text-sm text-surface-400 mb-2">{t('settings.defaultVideoProvider', 'Default Video Provider')}</label>
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
              <label className="block text-sm text-surface-400 mb-2">{t('settings.defaultResolution', 'Default Resolution')}</label>
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
              <label className="block text-sm text-surface-400 mb-2">{t('settings.defaultFrameRate', 'Default Frame Rate')}</label>
              <select
                value={getValue('defaultVideoFps') || 24}
                onChange={(e) => handleLocalChange('defaultVideoFps', parseInt(e.target.value))}
                className="w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2"
              >
                <option value={24}>24 fps ({t('settings.fpsCinema', 'Cinema')})</option>
                <option value={25}>25 fps (PAL)</option>
                <option value={30}>30 fps (NTSC)</option>
                <option value={60}>60 fps ({t('settings.fpsSmooth', 'Smooth')})</option>
              </select>
            </div>

            <div>
              <label className="block text-sm text-surface-400 mb-2">
                {t('settings.maxConcurrentGenerations', 'Max Concurrent Generations')}
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
                {t('settings.generationTimeoutSeconds', 'Generation Timeout (seconds)')}
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

        {/* Budget Settings */}
        <div className="card mb-6">
          <h2 className="text-lg font-medium mb-4 flex items-center gap-2">
            <DollarSign className="w-5 h-5 text-brand-400" />
            {t('settings.budgetCostAlerts', 'Budget & Cost Alerts')}
          </h2>
          <p className="text-sm text-surface-400 mb-4">
            {t(
              'settings.budgetIntro',
              'Set a spending limit to receive alerts when approaching or exceeding your budget.'
            )}
          </p>
          <BudgetSettings
            currentBudgetLimit={settings?.budgetLimitUsd ?? null}
            currentPeriodDays={settings?.budgetPeriodDays ?? 30}
            currentSpent={costStats?.totalCostUsd ?? 0}
            onSave={handleBudgetSave}
            isSaving={isSaving}
          />
        </div>

        {/* Voice/TTS Settings */}
        <TTSSettingsSection />

        {/* Appearance Settings */}
        <div className="card mb-6">
          <h2 className="text-lg font-medium mb-4 flex items-center gap-2">
            <Palette className="w-5 h-5 text-brand-400" />
            {t('settings.appearance', 'Appearance')}
          </h2>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-surface-400 mb-2">{t('settings.theme', 'Theme')}</label>
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
              <span className="text-sm">{t('settings.autoSaveProjects', 'Auto-save projects')}</span>
            </label>

            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={getValue('showAdvancedOptions') ?? false}
                onChange={(e) => handleLocalChange('showAdvancedOptions', e.target.checked)}
                className="w-4 h-4 rounded border-surface-600 bg-surface-800"
              />
              <span className="text-sm">{t('settings.showAdvancedOptions', 'Show advanced options')}</span>
            </label>
          </div>
        </div>

        {/* Experience Mode Settings */}
        <ExperienceModeSettingsSection />

        {/* Storage Settings */}
        <div className="card mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-medium flex items-center gap-2">
              <HardDrive className="w-5 h-5 text-brand-400" />
              {t('settings.storage', 'Storage')}
            </h2>
            <button
              onClick={() => fetchStorageStats()}
              className="text-sm text-brand-400 hover:text-brand-300 flex items-center gap-1"
            >
              <RefreshCw className="w-4 h-4" />
              {t('settings.refresh', 'Refresh')}
            </button>
          </div>

          {storageStats && (
            <div className="space-y-4">
              {/* Storage Stats */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-surface-800/50 rounded-lg p-3">
                  <div className="text-xs text-surface-400 mb-1">{t('settings.totalData', 'Total Data')}</div>
                  <div className="text-lg font-bold">
                    {formatBytes(storageStats.totalSizeBytes)}
                  </div>
                </div>
                <div className="bg-surface-800/50 rounded-lg p-3">
                  <div className="text-xs text-surface-400 mb-1">{t('settings.uploads', 'Uploads')}</div>
                  <div className="text-lg font-bold">
                    {formatBytes(storageStats.uploadSizeBytes)}
                  </div>
                </div>
                <div className="bg-surface-800/50 rounded-lg p-3">
                  <div className="text-xs text-surface-400 mb-1">{t('settings.outputs', 'Outputs')}</div>
                  <div className="text-lg font-bold">
                    {formatBytes(storageStats.outputSizeBytes)}
                  </div>
                </div>
                <div className="bg-surface-800/50 rounded-lg p-3">
                  <div className="text-xs text-surface-400 mb-1">{t('settings.cache', 'Cache')}</div>
                  <div className="text-lg font-bold">
                    {formatBytes(storageStats.cacheSizeBytes)}
                  </div>
                </div>
              </div>

              {/* Paths */}
              <div className="text-sm space-y-2">
                <div className="flex justify-between">
                  <span className="text-surface-400">{t('settings.dataDirectory', 'Data Directory')}</span>
                  <span className="font-mono text-surface-300">{storageStats.dataDir}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-surface-400">{t('settings.cacheDirectory', 'Cache Directory')}</span>
                  <span className="font-mono text-surface-300">{storageStats.cacheDir}</span>
                </div>
                {storageStats.tempFilesCount > 0 && (
                  <div className="flex justify-between text-yellow-400">
                    <span>{t('settings.temporaryFiles', 'Temporary Files')}</span>
                    <span>{storageStats.tempFilesCount} {t('settings.filesUnit', 'files')}</span>
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
                  {t('settings.clearTempFiles', 'Clear Temp Files')}
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
                  {t('settings.clearModelCache', 'Clear Model Cache')}
                </button>
              </div>

              {/* Cache Settings */}
              <div className="pt-4 border-t border-surface-700">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-surface-400 mb-2">
                      {t('settings.maxCacheSizeGb', 'Max Cache Size (GB)')}
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
                    onChange={(e) => handleLocalChange('autoCleanupTempFiles', e.target.checked)}
                    className="w-4 h-4 rounded border-surface-600 bg-surface-800"
                  />
                  <span className="text-sm">{t('settings.autoCleanupTempFiles', 'Automatically cleanup temporary files')}</span>
                </label>
              </div>
            </div>
          )}
        </div>

        {/* Export Defaults */}
        <div className="card mb-6">
          <h2 className="text-lg font-medium mb-4 flex items-center gap-2">
            <Download className="w-5 h-5 text-brand-400" />
            {t('settings.exportDefaults', 'Export Defaults')}
          </h2>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-surface-400 mb-2">{t('settings.defaultExportFormat', 'Default Export Format')}</label>
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
              <label className="block text-sm text-surface-400 mb-2">{t('settings.defaultExportQuality', 'Default Export Quality')}</label>
              <select
                value={getValue('defaultExportQuality') || 'high'}
                onChange={(e) => handleLocalChange('defaultExportQuality', e.target.value)}
                className="w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2"
              >
                <option value="draft">{t('settings.exportQualityDraft', 'Draft (Fast)')}</option>
                <option value="standard">{t('settings.exportQualityStandard', 'Standard')}</option>
                <option value="high">{t('settings.exportQualityHigh', 'High')}</option>
                <option value="master">{t('settings.exportQualityMaster', 'Master (Slow)')}</option>
              </select>
            </div>
          </div>
        </div>

        {/* Application Info */}
        <div className="card">
          <h2 className="text-lg font-medium mb-4 flex items-center gap-2">
            <Info className="w-5 h-5 text-brand-400" />
            {t('settings.about', 'About')}
          </h2>

          <div className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-surface-400">{t('settings.version', 'Version')}</span>
              <span>{versionInfo?.version || t('settings.unknown', 'Unknown')}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-surface-400">{t('settings.environment', 'Environment')}</span>
              <span>{versionInfo?.environment || t('settings.unknown', 'Unknown')}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-surface-400">{t('settings.platform', 'Platform')}</span>
              <span>{window.electronAPI?.platform || t('settings.unknown', 'Unknown')}</span>
            </div>
          </div>

          <div className="mt-4 pt-4 border-t border-surface-800">
            <p className="text-sm text-surface-400 mb-4">
              {t(
                'settings.aboutDescription',
                'SceneMachine.ai is a screenplay-to-movie platform that enables users to transform written screenplays into generated video content.'
              )}
            </p>
            <a
              href="https://scenemachine.ai"
              target="_blank"
              rel="noopener noreferrer"
              className="text-brand-400 hover:text-brand-300 text-sm flex items-center gap-1"
            >
              {t('settings.visitWebsite', 'Visit Website')}
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </div>
      </div>

      {/* Keyboard Shortcuts Modal */}
      {showShortcuts && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
          onClick={() => setShowShortcuts(false)}
          role="dialog"
          aria-modal="true"
          aria-labelledby="shortcuts-title"
        >
          <div
            className="bg-surface-900 rounded-lg shadow-xl max-w-md w-full mx-4 overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-4 border-b border-surface-700 flex items-center justify-between">
              <h2 id="shortcuts-title" className="text-lg font-medium flex items-center gap-2">
                <Keyboard className="w-5 h-5 text-brand-400" />
                {t('settings.keyboardShortcuts', 'Keyboard Shortcuts')}
              </h2>
              <button
                onClick={() => setShowShortcuts(false)}
                className="p-1 hover:bg-surface-700 rounded"
                aria-label={t('settings.closeShortcutsAria', 'Close shortcuts')}
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-4 space-y-3">
              <div className="flex items-center justify-between py-2 border-b border-surface-800">
                <span className="text-surface-300">{t('settings.shortcutSaveChanges', 'Save changes')}</span>
                <kbd className="px-2 py-1 bg-surface-800 rounded text-sm font-mono">Ctrl+S</kbd>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-surface-800">
                <span className="text-surface-300">{t('settings.shortcutDiscardChanges', 'Discard changes')}</span>
                <kbd className="px-2 py-1 bg-surface-800 rounded text-sm font-mono">Escape</kbd>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-surface-800">
                <span className="text-surface-300">{t('settings.shortcutShowShortcuts', 'Show shortcuts')}</span>
                <kbd className="px-2 py-1 bg-surface-800 rounded text-sm font-mono">?</kbd>
              </div>
              <div className="flex items-center justify-between py-2">
                <span className="text-surface-300">{t('settings.shortcutCloseModal', 'Close modal')}</span>
                <kbd className="px-2 py-1 bg-surface-800 rounded text-sm font-mono">Escape</kbd>
              </div>
            </div>
            <div className="p-4 bg-surface-800/50 text-center">
              <p className="text-sm text-surface-400">
                {t('settings.press', 'Press')}{' '}
                <kbd className="px-1.5 py-0.5 bg-surface-700 rounded text-xs font-mono">?</kbd>{' '}
                {t('settings.anytimeToSeeShortcuts', 'anytime to see shortcuts')}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
