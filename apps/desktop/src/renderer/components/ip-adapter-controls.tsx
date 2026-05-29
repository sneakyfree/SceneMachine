/**
 * IP-Adapter Controls component.
 *
 * Exposes the 3 character consistency modes (balanced, strong, face_only)
 * and a strength slider for fine-tuning IP-Adapter injection during generation.
 */

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Sliders, Shield, User, Zap, Save, RotateCcw, Loader2, Check } from 'lucide-react';
import { cn } from '../lib/utils';
import { useTranslation } from '../i18n/use-translation';

interface IPAdapterSettings {
  mode: 'balanced' | 'strong' | 'face_only';
  strength: number;
  available_modes: string[];
}

const MODE_INFO: Record<
  string,
  { icon: typeof Shield; labelKey: string; labelEn: string; descKey: string; descEn: string }
> = {
  balanced: {
    icon: Shield,
    labelKey: 'ipAdapter.modeBalanced',
    labelEn: 'Balanced',
    descKey: 'ipAdapter.modeBalancedDesc',
    descEn:
      'Moderate character consistency with creative freedom for the AI to interpret scenes naturally.',
  },
  strong: {
    icon: Zap,
    labelKey: 'ipAdapter.modeStrong',
    labelEn: 'Strong',
    descKey: 'ipAdapter.modeStrongDesc',
    descEn:
      'High character consistency. Best for close-ups and dialogue scenes where face accuracy is critical.',
  },
  face_only: {
    icon: User,
    labelKey: 'ipAdapter.modeFaceOnly',
    labelEn: 'Face Only',
    descKey: 'ipAdapter.modeFaceOnlyDesc',
    descEn:
      'Preserves facial features while allowing body/clothing variation. Ideal for costume changes.',
  },
};

interface IPAdapterControlsProps {
  className?: string;
}

export function IPAdapterControls({ className }: IPAdapterControlsProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [localMode, setLocalMode] = useState<string>('balanced');
  const [localStrength, setLocalStrength] = useState<number>(0.6);
  const [isDirty, setIsDirty] = useState(false);
  const [saved, setSaved] = useState(false);

  // NOTE: Until 2026-05-14 this component used fetch('/api/...') to
  // hit a FastAPI HTTP endpoint that the Electron desktop app does
  // NOT run — only the IPC socket. Every interaction with this panel
  // silently fell through to the "endpoint not available, return
  // defaults" branch, so user changes never persisted. Caught by the
  // DNA-strand audit (Ghost feature: "IPAdapter settings via Electron").
  // Now uses the IPC pattern that every other panel in the app uses.
  const { data: settings, isLoading } = useQuery<IPAdapterSettings>({
    queryKey: ['ip-adapter-settings'],
    queryFn: async () => {
      return await window.electronAPI.backendRequest<IPAdapterSettings>(
        'ipAdapter.getSettings',
        {}
      );
    },
  });

  useEffect(() => {
    if (settings) {
      setLocalMode(settings.mode);
      setLocalStrength(settings.strength);
      setIsDirty(false);
    }
  }, [settings]);

  const saveMutation = useMutation({
    mutationFn: async (newSettings: { mode?: string; strength?: number }) => {
      return await window.electronAPI.backendRequest<IPAdapterSettings>(
        'ipAdapter.updateSettings',
        newSettings
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ip-adapter-settings'] });
      setIsDirty(false);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    },
  });

  const handleModeChange = (mode: string) => {
    setLocalMode(mode);
    setIsDirty(true);
  };

  const handleStrengthChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setLocalStrength(parseFloat(e.target.value));
    setIsDirty(true);
  };

  const handleSave = () => {
    saveMutation.mutate({ mode: localMode, strength: localStrength });
  };

  const handleReset = () => {
    if (settings) {
      setLocalMode(settings.mode);
      setLocalStrength(settings.strength);
      setIsDirty(false);
    }
  };

  if (isLoading) {
    return (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '16px',
          color: 'var(--text-secondary, #999)',
        }}
      >
        <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} />
        <span style={{ fontSize: '13px' }}>
          {t('ipAdapter.loading', 'Loading IP-Adapter settings…')}
        </span>
      </div>
    );
  }

  const currentModeInfo = MODE_INFO[localMode] || MODE_INFO.balanced;

  return (
    <div
      className={cn('ip-adapter-controls', className)}
      style={{
        background: 'var(--bg-secondary, #1a1a2e)',
        borderRadius: '12px',
        border: '1px solid var(--border-primary, #2a2a4a)',
        padding: '16px',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '16px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Sliders size={16} color="var(--accent-primary, #6366f1)" />
          <span
            style={{
              fontSize: '13px',
              fontWeight: 600,
              color: 'var(--text-primary, #e0e0e0)',
            }}
          >
            {t('ipAdapter.title', 'Character Consistency (IP-Adapter)')}
          </span>
        </div>
      </div>

      {/* Mode selector */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: '8px',
          marginBottom: '16px',
        }}
      >
        {Object.entries(MODE_INFO).map(([mode, info]) => {
          const Icon = info.icon;
          const isActive = localMode === mode;
          return (
            <button
              key={mode}
              onClick={() => handleModeChange(mode)}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '6px',
                padding: '12px 8px',
                background: isActive
                  ? 'var(--accent-primary-alpha, rgba(99,102,241,0.15))'
                  : 'var(--bg-tertiary, #222244)',
                border: `2px solid ${isActive ? 'var(--accent-primary, #6366f1)' : 'transparent'}`,
                borderRadius: '10px',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                color: isActive ? 'var(--accent-primary, #6366f1)' : 'var(--text-secondary, #999)',
              }}
            >
              <Icon size={20} />
              <span style={{ fontSize: '11px', fontWeight: 600 }}>{t(info.labelKey, info.labelEn)}</span>
            </button>
          );
        })}
      </div>

      {/* Mode description */}
      <div
        style={{
          fontSize: '12px',
          color: 'var(--text-secondary, #999)',
          marginBottom: '16px',
          lineHeight: '1.5',
          padding: '8px 12px',
          background: 'var(--bg-tertiary, #222244)',
          borderRadius: '8px',
        }}
      >
        {t(currentModeInfo.descKey, currentModeInfo.descEn)}
      </div>

      {/* Strength slider */}
      <div style={{ marginBottom: '16px' }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '8px',
          }}
        >
          <span style={{ fontSize: '12px', color: 'var(--text-secondary, #999)' }}>
            {t('ipAdapter.strength', 'Strength')}
          </span>
          <span
            style={{
              fontSize: '14px',
              fontWeight: 700,
              color: 'var(--accent-primary, #6366f1)',
            }}
          >
            {Math.round(localStrength * 100)}%
          </span>
        </div>
        <input
          type="range"
          min="0"
          max="1"
          step="0.05"
          value={localStrength}
          onChange={handleStrengthChange}
          style={{
            width: '100%',
            height: '6px',
            WebkitAppearance: 'none',
            appearance: 'none',
            background: `linear-gradient(to right, var(--accent-primary, #6366f1) ${localStrength * 100}%, var(--bg-tertiary, #333) ${localStrength * 100}%)`,
            borderRadius: '3px',
            outline: 'none',
            cursor: 'pointer',
          }}
        />
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            fontSize: '10px',
            color: 'var(--text-tertiary, #666)',
            marginTop: '4px',
          }}
        >
          <span>{t('ipAdapter.creative', 'Creative')}</span>
          <span>{t('ipAdapter.consistent', 'Consistent')}</span>
        </div>
      </div>

      {/* Actions */}
      {isDirty && (
        <div
          style={{
            display: 'flex',
            gap: '8px',
            paddingTop: '12px',
            borderTop: '1px solid var(--border-secondary, #333)',
          }}
        >
          <button
            onClick={handleSave}
            disabled={saveMutation.isPending}
            style={{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              padding: '8px 16px',
              background: 'var(--accent-primary, #6366f1)',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
              opacity: saveMutation.isPending ? 0.7 : 1,
            }}
          >
            {saveMutation.isPending ? (
              <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} />
            ) : (
              <Save size={14} />
            )}
            {t('ipAdapter.save', 'Save')}
          </button>
          <button
            onClick={handleReset}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              padding: '8px 16px',
              background: 'var(--bg-tertiary, #333)',
              color: 'var(--text-secondary, #999)',
              border: 'none',
              borderRadius: '8px',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <RotateCcw size={14} />
            {t('ipAdapter.reset', 'Reset')}
          </button>
        </div>
      )}

      {/* Saved toast */}
      {saved && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            marginTop: '8px',
            padding: '8px 12px',
            background: 'rgba(34,197,94,0.1)',
            border: '1px solid rgba(34,197,94,0.3)',
            borderRadius: '8px',
            fontSize: '12px',
            color: '#22c55e',
          }}
        >
          <Check size={14} />
          {t('ipAdapter.settingsSaved', 'Settings saved')}
        </div>
      )}
    </div>
  );
}

export type { IPAdapterSettings };
export default IPAdapterControls;
