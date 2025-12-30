/**
 * AudioWaveform component for audio visualization using Web Audio API.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { Play, Pause, Volume2, VolumeX, Loader2 } from 'lucide-react';
import { cn } from '../lib/utils';

interface AudioWaveformProps {
  src: string;
  className?: string;
  height?: number;
  waveColor?: string;
  progressColor?: string;
  backgroundColor?: string;
  showControls?: boolean;
  autoPlay?: boolean;
  loop?: boolean;
  onTimeUpdate?: (currentTime: number, duration: number) => void;
  onEnded?: () => void;
  externalCurrentTime?: number;
  onSeek?: (time: number) => void;
}

function formatTime(seconds: number): string {
  if (!isFinite(seconds)) return '0:00';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export function AudioWaveform({
  src,
  className,
  height = 80,
  waveColor = '#4b5563',
  progressColor = '#8b5cf6',
  backgroundColor = '#1f2937',
  showControls = true,
  autoPlay = false,
  loop = false,
  onTimeUpdate,
  onEnded,
  externalCurrentTime,
  onSeek,
}: AudioWaveformProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationRef = useRef<number>();

  const [waveformData, setWaveformData] = useState<number[]>([]);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load and analyze audio file
  useEffect(() => {
    const loadAudio = async () => {
      try {
        setIsLoading(true);
        setError(null);

        // Create audio context
        const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
        audioContextRef.current = audioContext;

        // Fetch and decode audio
        const response = await fetch(src.startsWith('file://') ? src : `file://${src}`);
        const arrayBuffer = await response.arrayBuffer();
        const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);

        // Extract waveform data
        const channelData = audioBuffer.getChannelData(0);
        const samples = 200; // Number of bars in waveform
        const blockSize = Math.floor(channelData.length / samples);
        const waveform: number[] = [];

        for (let i = 0; i < samples; i++) {
          let sum = 0;
          for (let j = 0; j < blockSize; j++) {
            sum += Math.abs(channelData[i * blockSize + j]);
          }
          waveform.push(sum / blockSize);
        }

        // Normalize
        const max = Math.max(...waveform);
        const normalized = waveform.map(v => v / max);
        setWaveformData(normalized);

        setIsLoading(false);
      } catch (err) {
        console.error('Failed to load audio:', err);
        setError('Failed to load audio file');
        setIsLoading(false);
      }
    };

    if (src) {
      loadAudio();
    }

    return () => {
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, [src]);

  // Set up audio element listeners
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleTimeUpdate = () => {
      setCurrentTime(audio.currentTime);
      onTimeUpdate?.(audio.currentTime, audio.duration);
    };

    const handleLoadedMetadata = () => {
      setDuration(audio.duration);
      if (autoPlay) {
        audio.play();
      }
    };

    const handleEnded = () => {
      setIsPlaying(false);
      onEnded?.();
    };

    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);

    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('loadedmetadata', handleLoadedMetadata);
    audio.addEventListener('ended', handleEnded);
    audio.addEventListener('play', handlePlay);
    audio.addEventListener('pause', handlePause);

    return () => {
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
      audio.removeEventListener('ended', handleEnded);
      audio.removeEventListener('play', handlePlay);
      audio.removeEventListener('pause', handlePause);
    };
  }, [autoPlay, onTimeUpdate, onEnded]);

  // Sync with external time control
  useEffect(() => {
    if (externalCurrentTime !== undefined && audioRef.current) {
      audioRef.current.currentTime = externalCurrentTime;
    }
  }, [externalCurrentTime]);

  // Draw waveform
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || waveformData.length === 0) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();

    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const width = rect.width;
    const barWidth = width / waveformData.length;
    const progress = duration > 0 ? currentTime / duration : 0;
    const progressX = progress * width;

    // Clear
    ctx.fillStyle = backgroundColor;
    ctx.fillRect(0, 0, width, height);

    // Draw waveform bars
    waveformData.forEach((value, index) => {
      const x = index * barWidth;
      const barHeight = value * (height - 10);
      const y = (height - barHeight) / 2;

      ctx.fillStyle = x < progressX ? progressColor : waveColor;
      ctx.fillRect(x, y, barWidth - 1, barHeight);
    });

    // Draw playhead
    if (progress > 0) {
      ctx.fillStyle = progressColor;
      ctx.fillRect(progressX - 1, 0, 2, height);
    }
  }, [waveformData, currentTime, duration, height, waveColor, progressColor, backgroundColor]);

  const togglePlayPause = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;

    if (audio.paused) {
      audio.play();
    } else {
      audio.pause();
    }
  }, []);

  const handleSeek = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    const audio = audioRef.current;
    if (!canvas || !audio) return;

    const rect = canvas.getBoundingClientRect();
    const percent = (e.clientX - rect.left) / rect.width;
    const newTime = percent * duration;

    audio.currentTime = newTime;
    onSeek?.(newTime);
  }, [duration, onSeek]);

  const toggleMute = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.muted = !audio.muted;
    setIsMuted(audio.muted);
  }, []);

  const handleVolumeChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const audio = audioRef.current;
    if (!audio) return;
    const newVolume = parseFloat(e.target.value);
    audio.volume = newVolume;
    setVolume(newVolume);
    setIsMuted(newVolume === 0);
  }, []);

  if (error) {
    return (
      <div className={cn('flex items-center justify-center bg-surface-800 rounded-lg p-4', className)}>
        <p className="text-red-400 text-sm">{error}</p>
      </div>
    );
  }

  return (
    <div className={cn('bg-surface-800 rounded-lg overflow-hidden', className)}>
      {/* Hidden audio element */}
      <audio
        ref={audioRef}
        src={src.startsWith('file://') ? src : `file://${src}`}
        loop={loop}
        preload="metadata"
      />

      {/* Waveform canvas */}
      <div className="relative">
        {isLoading ? (
          <div
            className="flex items-center justify-center"
            style={{ height, backgroundColor }}
          >
            <Loader2 className="w-6 h-6 text-surface-400 animate-spin" />
          </div>
        ) : (
          <canvas
            ref={canvasRef}
            className="w-full cursor-pointer"
            style={{ height }}
            onClick={handleSeek}
          />
        )}
      </div>

      {/* Controls */}
      {showControls && (
        <div className="flex items-center gap-3 px-3 py-2 bg-surface-900">
          <button
            onClick={togglePlayPause}
            disabled={isLoading}
            className="p-1.5 text-surface-300 hover:text-white transition-colors disabled:opacity-50"
          >
            {isPlaying ? (
              <Pause className="w-4 h-4" />
            ) : (
              <Play className="w-4 h-4" />
            )}
          </button>

          <div className="text-xs text-surface-400 font-mono min-w-[80px]">
            {formatTime(currentTime)} / {formatTime(duration)}
          </div>

          <div className="flex-1" />

          <div className="flex items-center gap-1">
            <button
              onClick={toggleMute}
              className="p-1 text-surface-400 hover:text-white transition-colors"
            >
              {isMuted || volume === 0 ? (
                <VolumeX className="w-4 h-4" />
              ) : (
                <Volume2 className="w-4 h-4" />
              )}
            </button>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={isMuted ? 0 : volume}
              onChange={handleVolumeChange}
              className="w-16 h-1"
            />
          </div>
        </div>
      )}
    </div>
  );
}

// Real-time audio analyzer component
interface AudioAnalyzerProps {
  audioElement?: HTMLAudioElement | null;
  className?: string;
  barCount?: number;
  barColor?: string;
  height?: number;
}

export function AudioAnalyzer({
  audioElement,
  className,
  barCount = 32,
  barColor = '#8b5cf6',
  height = 60,
}: AudioAnalyzerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationRef = useRef<number>();

  useEffect(() => {
    if (!audioElement) return;

    const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
    const analyser = audioContext.createAnalyser();
    analyser.fftSize = 64;

    const source = audioContext.createMediaElementSource(audioElement);
    source.connect(analyser);
    analyser.connect(audioContext.destination);

    analyserRef.current = analyser;

    const draw = () => {
      const canvas = canvasRef.current;
      if (!canvas || !analyserRef.current) return;

      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
      analyserRef.current.getByteFrequencyData(dataArray);

      const dpr = window.devicePixelRatio || 1;
      const rect = canvas.getBoundingClientRect();

      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      ctx.scale(dpr, dpr);

      const width = rect.width;
      const barWidth = width / barCount;

      ctx.clearRect(0, 0, width, height);

      for (let i = 0; i < barCount; i++) {
        const value = dataArray[i] || 0;
        const barHeight = (value / 255) * height;
        const x = i * barWidth;
        const y = height - barHeight;

        ctx.fillStyle = barColor;
        ctx.fillRect(x, y, barWidth - 2, barHeight);
      }

      animationRef.current = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
      audioContext.close();
    };
  }, [audioElement, barCount, barColor, height]);

  return (
    <canvas
      ref={canvasRef}
      className={cn('w-full', className)}
      style={{ height }}
    />
  );
}

// Audio level meter component
interface AudioLevelMeterProps {
  level: number; // 0-1
  className?: string;
  orientation?: 'horizontal' | 'vertical';
  showPeak?: boolean;
  peakLevel?: number;
}

export function AudioLevelMeter({
  level,
  className,
  orientation = 'horizontal',
  showPeak = true,
  peakLevel,
}: AudioLevelMeterProps) {
  const clampedLevel = Math.max(0, Math.min(1, level));
  const clampedPeak = peakLevel !== undefined ? Math.max(0, Math.min(1, peakLevel)) : clampedLevel;

  // Color gradient from green to yellow to red
  const getColor = (value: number) => {
    if (value < 0.6) return '#22c55e'; // green
    if (value < 0.8) return '#eab308'; // yellow
    return '#ef4444'; // red
  };

  if (orientation === 'vertical') {
    return (
      <div className={cn('w-4 h-full bg-surface-800 rounded relative', className)}>
        <div
          className="absolute bottom-0 left-0 right-0 rounded transition-all"
          style={{
            height: `${clampedLevel * 100}%`,
            backgroundColor: getColor(clampedLevel),
          }}
        />
        {showPeak && (
          <div
            className="absolute left-0 right-0 h-0.5 bg-white transition-all"
            style={{ bottom: `${clampedPeak * 100}%` }}
          />
        )}
      </div>
    );
  }

  return (
    <div className={cn('h-2 bg-surface-800 rounded relative', className)}>
      <div
        className="absolute top-0 left-0 bottom-0 rounded transition-all"
        style={{
          width: `${clampedLevel * 100}%`,
          backgroundColor: getColor(clampedLevel),
        }}
      />
      {showPeak && (
        <div
          className="absolute top-0 bottom-0 w-0.5 bg-white transition-all"
          style={{ left: `${clampedPeak * 100}%` }}
        />
      )}
    </div>
  );
}
