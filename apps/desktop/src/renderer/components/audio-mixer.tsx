/**
 * AudioMixer component for managing multiple audio tracks.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Volume2,
  VolumeX,
  Mic,
  Music,
  Waves,
  Plus,
  Trash2,
  Play,
  Pause,
  Link,
  Unlink,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { AudioLevelMeter } from './audio-waveform';

export interface AudioTrack {
  id: string;
  name: string;
  type: 'dialogue' | 'music' | 'sfx' | 'voiceover';
  src?: string;
  volume: number;
  pan: number;
  muted: boolean;
  solo: boolean;
  color: string;
}

interface AudioMixerProps {
  tracks: AudioTrack[];
  onTrackChange: (trackId: string, changes: Partial<AudioTrack>) => void;
  onTrackAdd?: (type: AudioTrack['type']) => void;
  onTrackRemove?: (trackId: string) => void;
  masterVolume: number;
  onMasterVolumeChange: (volume: number) => void;
  isPlaying?: boolean;
  onPlayPause?: () => void;
  className?: string;
}

const TRACK_COLORS: Record<AudioTrack['type'], string> = {
  dialogue: '#3b82f6',
  music: '#8b5cf6',
  sfx: '#22c55e',
  voiceover: '#f59e0b',
};

const TRACK_ICONS: Record<AudioTrack['type'], React.ReactNode> = {
  dialogue: <Mic className="w-4 h-4" />,
  music: <Music className="w-4 h-4" />,
  sfx: <Waves className="w-4 h-4" />,
  voiceover: <Mic className="w-4 h-4" />,
};

function TrackChannel({
  track,
  onChange,
  onRemove,
  hasSoloedTrack,
}: {
  track: AudioTrack;
  onChange: (changes: Partial<AudioTrack>) => void;
  onRemove?: () => void;
  hasSoloedTrack: boolean;
}) {
  const [level, setLevel] = useState(0);
  const [peakLevel, setPeakLevel] = useState(0);

  // Simulate audio level (in real implementation, this would come from Web Audio API)
  useEffect(() => {
    if (track.muted || (hasSoloedTrack && !track.solo)) {
      setLevel(0);
      return;
    }

    const interval = setInterval(() => {
      const newLevel = Math.random() * 0.6 * track.volume;
      setLevel(newLevel);
      if (newLevel > peakLevel) {
        setPeakLevel(newLevel);
        setTimeout(() => setPeakLevel(0), 1000);
      }
    }, 100);

    return () => clearInterval(interval);
  }, [track.muted, track.solo, track.volume, hasSoloedTrack, peakLevel]);

  const isEffectivelyMuted = track.muted || (hasSoloedTrack && !track.solo);

  return (
    <div
      className={cn(
        'flex flex-col gap-2 p-3 bg-surface-800 rounded-lg min-w-[100px]',
        isEffectivelyMuted && 'opacity-50'
      )}
    >
      {/* Track header */}
      <div className="flex items-center gap-2">
        <div
          className="w-6 h-6 rounded flex items-center justify-center"
          style={{ backgroundColor: track.color }}
        >
          {TRACK_ICONS[track.type]}
        </div>
        <span className="text-xs font-medium truncate flex-1">{track.name}</span>
        {onRemove && (
          <button
            onClick={onRemove}
            className="icon-btn p-2 text-surface-500 hover:text-red-400 transition-colors rounded"
            aria-label={`Remove ${track.name} track`}
          >
            <Trash2 className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Level meter */}
      <div className="h-24 flex justify-center gap-1">
        <AudioLevelMeter
          level={level}
          peakLevel={peakLevel}
          orientation="vertical"
          className="w-3"
        />
        <AudioLevelMeter
          level={level * 0.9}
          peakLevel={peakLevel * 0.9}
          orientation="vertical"
          className="w-3"
        />
      </div>

      {/* Volume fader */}
      <div className="flex flex-col items-center gap-1">
        <input
          type="range"
          min="0"
          max="1"
          step="0.01"
          value={track.volume}
          onChange={(e) => onChange({ volume: parseFloat(e.target.value) })}
          className="h-20 -rotate-90"
          style={{ width: '80px', marginTop: '30px', marginBottom: '30px' }}
        />
        <span className="text-xs text-surface-400 font-mono">
          {Math.round(track.volume * 100)}%
        </span>
      </div>

      {/* Pan knob (simplified as slider) */}
      <div className="flex flex-col items-center gap-1">
        <span className="text-[10px] text-surface-500">PAN</span>
        <input
          type="range"
          min="-1"
          max="1"
          step="0.1"
          value={track.pan}
          onChange={(e) => onChange({ pan: parseFloat(e.target.value) })}
          className="w-16 h-1"
        />
        <span className="text-[10px] text-surface-400 font-mono">
          {track.pan === 0
            ? 'C'
            : track.pan < 0
              ? `L${Math.abs(Math.round(track.pan * 100))}`
              : `R${Math.round(track.pan * 100)}`}
        </span>
      </div>

      {/* Solo/Mute buttons */}
      <div className="flex gap-1 justify-center">
        <button
          onClick={() => onChange({ solo: !track.solo })}
          className={cn(
            'px-2 py-1 text-xs rounded font-medium transition-colors',
            track.solo
              ? 'bg-yellow-500 text-black'
              : 'bg-surface-700 text-surface-400 hover:bg-surface-600'
          )}
        >
          S
        </button>
        <button
          onClick={() => onChange({ muted: !track.muted })}
          className={cn(
            'px-2 py-1 text-xs rounded font-medium transition-colors',
            track.muted
              ? 'bg-red-500 text-white'
              : 'bg-surface-700 text-surface-400 hover:bg-surface-600'
          )}
        >
          M
        </button>
      </div>
    </div>
  );
}

function MasterChannel({
  volume,
  onVolumeChange,
  isPlaying,
  onPlayPause,
}: {
  volume: number;
  onVolumeChange: (volume: number) => void;
  isPlaying?: boolean;
  onPlayPause?: () => void;
}) {
  const [level, setLevel] = useState(0);
  const [peakLevel, setPeakLevel] = useState(0);

  // Simulate master level
  useEffect(() => {
    const interval = setInterval(() => {
      const newLevel = Math.random() * 0.7 * volume;
      setLevel(newLevel);
      if (newLevel > peakLevel) {
        setPeakLevel(newLevel);
        setTimeout(() => setPeakLevel(0), 1000);
      }
    }, 100);

    return () => clearInterval(interval);
  }, [volume, peakLevel]);

  return (
    <div className="flex flex-col gap-2 p-3 bg-surface-900 rounded-lg min-w-[120px] border border-surface-700">
      {/* Header */}
      <div className="flex items-center gap-2 justify-center">
        <Volume2 className="w-4 h-4 text-brand-400" />
        <span className="text-xs font-bold text-brand-400">MASTER</span>
      </div>

      {/* Stereo level meters */}
      <div className="h-28 flex justify-center gap-2">
        <AudioLevelMeter
          level={level}
          peakLevel={peakLevel}
          orientation="vertical"
          className="w-4"
        />
        <AudioLevelMeter
          level={level * 0.95}
          peakLevel={peakLevel * 0.95}
          orientation="vertical"
          className="w-4"
        />
      </div>

      {/* Master fader */}
      <div className="flex flex-col items-center gap-1">
        <input
          type="range"
          min="0"
          max="1"
          step="0.01"
          value={volume}
          onChange={(e) => onVolumeChange(parseFloat(e.target.value))}
          className="h-20 -rotate-90"
          style={{ width: '80px', marginTop: '30px', marginBottom: '30px' }}
        />
        <span className="text-sm text-white font-mono font-bold">{Math.round(volume * 100)}%</span>
      </div>

      {/* Play/Pause */}
      {onPlayPause && (
        <button
          onClick={onPlayPause}
          className="p-2 bg-brand-500 hover:bg-brand-600 text-white rounded transition-colors"
        >
          {isPlaying ? <Pause className="w-5 h-5 mx-auto" /> : <Play className="w-5 h-5 mx-auto" />}
        </button>
      )}
    </div>
  );
}

export function AudioMixer({
  tracks,
  onTrackChange,
  onTrackAdd,
  onTrackRemove,
  masterVolume,
  onMasterVolumeChange,
  isPlaying,
  onPlayPause,
  className,
}: AudioMixerProps) {
  const [isLinked, setIsLinked] = useState(false);
  const hasSoloedTrack = tracks.some((t) => t.solo);

  const handleTrackChange = useCallback(
    (trackId: string, changes: Partial<AudioTrack>) => {
      if (isLinked && 'volume' in changes) {
        // When linked, change all track volumes proportionally
        const track = tracks.find((t) => t.id === trackId);
        if (track) {
          const ratio = changes.volume! / track.volume;
          tracks.forEach((t) => {
            onTrackChange(t.id, { volume: Math.min(1, t.volume * ratio) });
          });
        }
      } else {
        onTrackChange(trackId, changes);
      }
    },
    [isLinked, tracks, onTrackChange]
  );

  return (
    <div className={cn('bg-surface-950 rounded-xl p-4', className)}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-surface-300">Audio Mixer</h3>
        <div className="flex items-center gap-2">
          {/* Link toggle */}
          <button
            onClick={() => setIsLinked(!isLinked)}
            className={cn(
              'p-1.5 rounded transition-colors',
              isLinked
                ? 'bg-brand-500 text-white'
                : 'bg-surface-800 text-surface-400 hover:text-white'
            )}
            title={isLinked ? 'Unlink tracks' : 'Link tracks'}
          >
            {isLinked ? <Link className="w-4 h-4" /> : <Unlink className="w-4 h-4" />}
          </button>

          {/* Add track dropdown */}
          {onTrackAdd && (
            <div className="relative group">
              <button
                className="icon-btn p-2 bg-surface-800 text-surface-400 hover:text-white rounded transition-colors"
                aria-label="Add audio track"
              >
                <Plus className="w-4 h-4" />
              </button>
              <div className="absolute right-0 top-full mt-1 bg-surface-800 rounded-lg shadow-lg overflow-hidden opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10">
                {(['dialogue', 'music', 'sfx', 'voiceover'] as const).map((type) => (
                  <button
                    key={type}
                    onClick={() => onTrackAdd(type)}
                    className="flex items-center gap-2 w-full px-3 py-2 text-sm hover:bg-surface-700 text-left"
                  >
                    <div
                      className="w-4 h-4 rounded flex items-center justify-center"
                      style={{ backgroundColor: TRACK_COLORS[type] }}
                    >
                      {TRACK_ICONS[type]}
                    </div>
                    {type.charAt(0).toUpperCase() + type.slice(1)}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Mixer channels */}
      <div className="flex gap-2 overflow-x-auto pb-2">
        {tracks.map((track) => (
          <TrackChannel
            key={track.id}
            track={track}
            onChange={(changes) => handleTrackChange(track.id, changes)}
            onRemove={onTrackRemove ? () => onTrackRemove(track.id) : undefined}
            hasSoloedTrack={hasSoloedTrack}
          />
        ))}

        {/* Master channel */}
        <div className="border-l border-surface-700 pl-2 ml-2">
          <MasterChannel
            volume={masterVolume}
            onVolumeChange={onMasterVolumeChange}
            isPlaying={isPlaying}
            onPlayPause={onPlayPause}
          />
        </div>
      </div>

      {/* Quick tips */}
      <div className="mt-3 pt-3 border-t border-surface-800">
        <p className="text-xs text-surface-500">
          <span className="font-medium">Tips:</span> S = Solo (hear only this track), M = Mute
          (silence this track)
        </p>
      </div>
    </div>
  );
}

// Audio mixer state hook
export function useAudioMixer(initialTracks: AudioTrack[] = []) {
  const [tracks, setTracks] = useState<AudioTrack[]>(initialTracks);
  const [masterVolume, setMasterVolume] = useState(0.8);

  const addTrack = useCallback(
    (type: AudioTrack['type']) => {
      const newTrack: AudioTrack = {
        id: `track-${Date.now()}`,
        name: `${type.charAt(0).toUpperCase() + type.slice(1)} ${tracks.filter((t) => t.type === type).length + 1}`,
        type,
        volume: 0.75,
        pan: 0,
        muted: false,
        solo: false,
        color: TRACK_COLORS[type],
      };
      setTracks((prev) => [...prev, newTrack]);
    },
    [tracks]
  );

  const removeTrack = useCallback((trackId: string) => {
    setTracks((prev) => prev.filter((t) => t.id !== trackId));
  }, []);

  const updateTrack = useCallback((trackId: string, changes: Partial<AudioTrack>) => {
    setTracks((prev) => prev.map((t) => (t.id === trackId ? { ...t, ...changes } : t)));
  }, []);

  return {
    tracks,
    masterVolume,
    setMasterVolume,
    addTrack,
    removeTrack,
    updateTrack,
    setTracks,
  };
}
