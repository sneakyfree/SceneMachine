/**
 * AudioWaveform component for audio visualization using Web Audio API.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { Play, Pause, Volume2, VolumeX, Loader2, ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';
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
  /**
   * Enable zoom controls
   */
  zoomable?: boolean;
  /**
   * Initial zoom level (1 = full view, higher = zoomed in)
   */
  initialZoom?: number;
  /**
   * Show time markers
   */
  showTimeMarkers?: boolean;
  /**
   * Cut points from video timeline for snap-to-cut feature
   */
  cutPoints?: number[];
  /**
   * Called when near a cut point during seeking
   */
  onSnapToCut?: (cutTime: number) => void;
  /**
   * Snap threshold in seconds
   */
  snapThreshold?: number;
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
  zoomable = false,
  initialZoom = 1,
  showTimeMarkers = false,
  cutPoints = [],
  onSnapToCut,
  snapThreshold = 0.5,
}: AudioWaveformProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationRef = useRef<number>();
  const containerRef = useRef<HTMLDivElement>(null);

  const [waveformData, setWaveformData] = useState<number[]>([]);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [zoom, setZoom] = useState(initialZoom);
  const [scrollOffset, setScrollOffset] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const [showSnapIndicator, setShowSnapIndicator] = useState(false);
  const [snapTime, setSnapTime] = useState<number | null>(null);

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
        const normalized = waveform.map((v) => v / max);
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

    const visibleWidth = rect.width;
    const totalWidth = visibleWidth * zoom;
    const barWidth = totalWidth / waveformData.length;
    const progress = duration > 0 ? currentTime / duration : 0;
    const progressX = progress * totalWidth - scrollOffset;

    // Clear
    ctx.fillStyle = backgroundColor;
    ctx.fillRect(0, 0, visibleWidth, height);

    // Calculate visible range
    const startIndex = Math.floor((scrollOffset / totalWidth) * waveformData.length);
    const endIndex = Math.ceil(((scrollOffset + visibleWidth) / totalWidth) * waveformData.length);

    // Draw waveform bars
    for (
      let i = Math.max(0, startIndex - 1);
      i < Math.min(waveformData.length, endIndex + 1);
      i++
    ) {
      const value = waveformData[i];
      const x = i * barWidth - scrollOffset;
      const barHeight = value * (height - (showTimeMarkers ? 20 : 10));
      const y = (height - barHeight - (showTimeMarkers ? 10 : 0)) / 2 + (showTimeMarkers ? 10 : 0);

      const barProgress = i / waveformData.length;
      ctx.fillStyle = barProgress < progress ? progressColor : waveColor;
      ctx.fillRect(x, y, Math.max(barWidth - 1, 1), barHeight);
    }

    // Draw time markers
    if (showTimeMarkers && duration > 0) {
      ctx.fillStyle = '#6b7280';
      ctx.font = '10px sans-serif';

      // Calculate marker interval based on zoom
      const markerInterval = zoom > 4 ? 1 : zoom > 2 ? 5 : zoom > 1.5 ? 10 : 30;

      for (let t = 0; t <= duration; t += markerInterval) {
        const x = (t / duration) * totalWidth - scrollOffset;
        if (x >= -20 && x <= visibleWidth + 20) {
          ctx.fillRect(x, 0, 1, 8);
          ctx.fillText(formatTime(t), x + 2, 8);
        }
      }
    }

    // Draw cut points
    if (cutPoints.length > 0 && duration > 0) {
      ctx.strokeStyle = '#f59e0b';
      ctx.setLineDash([4, 4]);
      ctx.lineWidth = 1;

      cutPoints.forEach((cutTime) => {
        const x = (cutTime / duration) * totalWidth - scrollOffset;
        if (x >= 0 && x <= visibleWidth) {
          ctx.beginPath();
          ctx.moveTo(x, 0);
          ctx.lineTo(x, height);
          ctx.stroke();
        }
      });

      ctx.setLineDash([]);
    }

    // Draw snap indicator
    if (showSnapIndicator && snapTime !== null && duration > 0) {
      const snapX = (snapTime / duration) * totalWidth - scrollOffset;
      ctx.fillStyle = '#22c55e';
      ctx.fillRect(snapX - 2, 0, 4, height);
      ctx.fillStyle = '#22c55e';
      ctx.font = 'bold 10px sans-serif';
      ctx.fillText('SNAP', snapX + 5, 15);
    }

    // Draw playhead
    if (progress > 0 && progressX >= 0 && progressX <= visibleWidth) {
      ctx.fillStyle = progressColor;
      ctx.fillRect(progressX - 1, 0, 2, height);

      // Playhead triangle
      ctx.beginPath();
      ctx.moveTo(progressX - 5, 0);
      ctx.lineTo(progressX + 5, 0);
      ctx.lineTo(progressX, 8);
      ctx.closePath();
      ctx.fill();
    }
  }, [
    waveformData,
    currentTime,
    duration,
    height,
    waveColor,
    progressColor,
    backgroundColor,
    zoom,
    scrollOffset,
    showTimeMarkers,
    cutPoints,
    showSnapIndicator,
    snapTime,
  ]);

  const togglePlayPause = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;

    if (audio.paused) {
      audio.play();
    } else {
      audio.pause();
    }
  }, []);

  // Check if seeking should snap to a cut point
  const checkSnapToCut = useCallback(
    (seekTime: number, shiftKey: boolean): number => {
      if (shiftKey || cutPoints.length === 0) {
        // Shift disables snapping
        setShowSnapIndicator(false);
        return seekTime;
      }

      // Find nearest cut point within threshold
      for (const cutTime of cutPoints) {
        if (Math.abs(seekTime - cutTime) <= snapThreshold) {
          setShowSnapIndicator(true);
          setSnapTime(cutTime);
          onSnapToCut?.(cutTime);
          setTimeout(() => {
            setShowSnapIndicator(false);
            setSnapTime(null);
          }, 500);
          return cutTime;
        }
      }

      setShowSnapIndicator(false);
      return seekTime;
    },
    [cutPoints, snapThreshold, onSnapToCut]
  );

  const handleSeek = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const canvas = canvasRef.current;
      const audio = audioRef.current;
      if (!canvas || !audio) return;

      const rect = canvas.getBoundingClientRect();
      const totalWidth = rect.width * zoom;
      const clickX = e.clientX - rect.left + scrollOffset;
      const percent = clickX / totalWidth;
      const rawTime = percent * duration;

      // Check for snap-to-cut
      const newTime = checkSnapToCut(Math.max(0, Math.min(duration, rawTime)), e.shiftKey);

      audio.currentTime = newTime;
      onSeek?.(newTime);
    },
    [duration, onSeek, zoom, scrollOffset, checkSnapToCut]
  );

  // Zoom controls
  const handleZoomIn = useCallback(() => {
    setZoom((prev) => Math.min(prev * 1.5, 10));
  }, []);

  const handleZoomOut = useCallback(() => {
    setZoom((prev) => Math.max(prev / 1.5, 1));
  }, []);

  const handleZoomReset = useCallback(() => {
    setZoom(1);
    setScrollOffset(0);
  }, []);

  // Handle scroll for panning zoomed waveform
  const handleWheel = useCallback(
    (e: React.WheelEvent<HTMLCanvasElement>) => {
      if (zoom <= 1) return;

      const canvas = canvasRef.current;
      if (!canvas) return;

      const rect = canvas.getBoundingClientRect();
      const totalWidth = rect.width * zoom;
      const maxScroll = totalWidth - rect.width;

      if (e.shiftKey) {
        // Horizontal scroll with shift
        e.preventDefault();
        setScrollOffset((prev) => Math.max(0, Math.min(maxScroll, prev + e.deltaY)));
      } else if (e.ctrlKey || e.metaKey) {
        // Zoom with ctrl/cmd
        e.preventDefault();
        const zoomDelta = e.deltaY > 0 ? 0.9 : 1.1;
        setZoom((prev) => Math.max(1, Math.min(10, prev * zoomDelta)));
      }
    },
    [zoom]
  );

  // Keep playhead in view when zoomed
  useEffect(() => {
    if (zoom <= 1 || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const totalWidth = rect.width * zoom;
    const playheadX = (currentTime / duration) * totalWidth;
    const maxScroll = totalWidth - rect.width;

    // Auto-scroll to keep playhead visible
    if (isPlaying) {
      if (playheadX < scrollOffset) {
        setScrollOffset(Math.max(0, playheadX - 50));
      } else if (playheadX > scrollOffset + rect.width - 50) {
        setScrollOffset(Math.min(maxScroll, playheadX - rect.width + 100));
      }
    }
  }, [currentTime, duration, zoom, scrollOffset, isPlaying]);

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
      <div
        className={cn('flex items-center justify-center bg-surface-800 rounded-lg p-4', className)}
      >
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
      <div className="relative" ref={containerRef}>
        {isLoading ? (
          <div className="flex items-center justify-center" style={{ height, backgroundColor }}>
            <Loader2 className="w-6 h-6 text-surface-400 animate-spin" />
          </div>
        ) : (
          <canvas
            ref={canvasRef}
            className="w-full cursor-pointer"
            style={{ height }}
            onClick={handleSeek}
            onWheel={handleWheel}
          />
        )}

        {/* Zoom indicator */}
        {zoom > 1 && (
          <div className="absolute top-1 right-1 px-1.5 py-0.5 bg-surface-900/80 rounded text-xs text-surface-400">
            {zoom.toFixed(1)}x
          </div>
        )}
      </div>

      {/* Controls */}
      {showControls && (
        <div className="flex items-center gap-3 px-3 py-2 bg-surface-900">
          <button
            onClick={togglePlayPause}
            disabled={isLoading}
            className="icon-btn p-2 text-surface-300 hover:text-white transition-colors disabled:opacity-50 rounded"
            aria-label={isPlaying ? 'Pause' : 'Play'}
          >
            {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
          </button>

          <div className="text-xs text-surface-400 font-mono min-w-[80px]">
            {formatTime(currentTime)} / {formatTime(duration)}
          </div>

          <div className="flex-1" />

          {/* Zoom controls */}
          {zoomable && (
            <div className="flex items-center gap-1 border-r border-surface-700 pr-3 mr-2">
              <button
                onClick={handleZoomOut}
                disabled={zoom <= 1}
                className="icon-btn p-1.5 text-surface-400 hover:text-white transition-colors disabled:opacity-30 rounded"
                aria-label="Zoom out"
                title="Zoom out"
              >
                <ZoomOut className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={handleZoomReset}
                disabled={zoom === 1}
                className="icon-btn p-1.5 text-surface-400 hover:text-white transition-colors disabled:opacity-30 rounded"
                aria-label="Reset zoom"
                title="Reset zoom"
              >
                <Maximize2 className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={handleZoomIn}
                disabled={zoom >= 10}
                className="icon-btn p-1.5 text-surface-400 hover:text-white transition-colors disabled:opacity-30 rounded"
                aria-label="Zoom in"
                title="Zoom in"
              >
                <ZoomIn className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          <div className="flex items-center gap-1">
            <button
              onClick={toggleMute}
              className="icon-btn p-2 text-surface-400 hover:text-white transition-colors rounded"
              aria-label={isMuted || volume === 0 ? 'Unmute' : 'Mute'}
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

  return <canvas ref={canvasRef} className={cn('w-full', className)} style={{ height }} />;
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
