/**
 * VideoPlayer component with full playback controls.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Play,
  Pause,
  Volume2,
  VolumeX,
  Maximize2,
  Minimize2,
  SkipBack,
  SkipForward,
  Settings,
  Loader2,
} from 'lucide-react';
import { cn } from '../lib/utils';

interface VideoPlayerProps {
  src: string;
  poster?: string;
  autoPlay?: boolean;
  loop?: boolean;
  muted?: boolean;
  className?: string;
  onTimeUpdate?: (currentTime: number, duration: number) => void;
  onEnded?: () => void;
  onError?: (error: string) => void;
  showControls?: boolean;
  initialTime?: number;
}

const PLAYBACK_RATES = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 2];

function formatTime(seconds: number): string {
  if (!isFinite(seconds)) return '0:00';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export function VideoPlayer({
  src,
  poster,
  autoPlay = false,
  loop = false,
  muted = false,
  className,
  onTimeUpdate,
  onEnded,
  onError,
  showControls = true,
  initialTime = 0,
}: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const progressRef = useRef<HTMLDivElement>(null);

  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(muted ? 0 : 1);
  const [isMuted, setIsMuted] = useState(muted);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [showSpeedMenu, setShowSpeedMenu] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showControlsOverlay, setShowControlsOverlay] = useState(true);
  const [buffered, setBuffered] = useState(0);

  const hideControlsTimeout = useRef<NodeJS.Timeout>();

  // Initialize video
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleLoadedMetadata = () => {
      setDuration(video.duration);
      setIsLoading(false);
      if (initialTime > 0) {
        video.currentTime = initialTime;
      }
    };

    const handleTimeUpdate = () => {
      setCurrentTime(video.currentTime);
      onTimeUpdate?.(video.currentTime, video.duration);
    };

    const handleProgress = () => {
      if (video.buffered.length > 0) {
        setBuffered(video.buffered.end(video.buffered.length - 1));
      }
    };

    const handleEnded = () => {
      setIsPlaying(false);
      onEnded?.();
    };

    const handleError = () => {
      const errorMessage = video.error?.message || 'Failed to load video';
      setError(errorMessage);
      setIsLoading(false);
      onError?.(errorMessage);
    };

    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);
    const handleWaiting = () => setIsLoading(true);
    const handleCanPlay = () => setIsLoading(false);

    video.addEventListener('loadedmetadata', handleLoadedMetadata);
    video.addEventListener('timeupdate', handleTimeUpdate);
    video.addEventListener('progress', handleProgress);
    video.addEventListener('ended', handleEnded);
    video.addEventListener('error', handleError);
    video.addEventListener('play', handlePlay);
    video.addEventListener('pause', handlePause);
    video.addEventListener('waiting', handleWaiting);
    video.addEventListener('canplay', handleCanPlay);

    return () => {
      video.removeEventListener('loadedmetadata', handleLoadedMetadata);
      video.removeEventListener('timeupdate', handleTimeUpdate);
      video.removeEventListener('progress', handleProgress);
      video.removeEventListener('ended', handleEnded);
      video.removeEventListener('error', handleError);
      video.removeEventListener('play', handlePlay);
      video.removeEventListener('pause', handlePause);
      video.removeEventListener('waiting', handleWaiting);
      video.removeEventListener('canplay', handleCanPlay);
    };
  }, [src, initialTime, onTimeUpdate, onEnded, onError]);

  // Auto-hide controls
  useEffect(() => {
    if (!showControls) return;

    const resetHideTimeout = () => {
      setShowControlsOverlay(true);
      if (hideControlsTimeout.current) {
        clearTimeout(hideControlsTimeout.current);
      }
      if (isPlaying) {
        hideControlsTimeout.current = setTimeout(() => {
          setShowControlsOverlay(false);
        }, 3000);
      }
    };

    const container = containerRef.current;
    if (container) {
      container.addEventListener('mousemove', resetHideTimeout);
      container.addEventListener('mouseenter', resetHideTimeout);
      container.addEventListener('mouseleave', () => {
        if (isPlaying) setShowControlsOverlay(false);
      });
    }

    return () => {
      if (hideControlsTimeout.current) {
        clearTimeout(hideControlsTimeout.current);
      }
      if (container) {
        container.removeEventListener('mousemove', resetHideTimeout);
        container.removeEventListener('mouseenter', resetHideTimeout);
      }
    };
  }, [isPlaying, showControls]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!containerRef.current?.contains(document.activeElement) &&
          document.activeElement !== containerRef.current) {
        return;
      }

      switch (e.key) {
        case ' ':
        case 'k':
          e.preventDefault();
          togglePlayPause();
          break;
        case 'ArrowLeft':
          e.preventDefault();
          skip(-5);
          break;
        case 'ArrowRight':
          e.preventDefault();
          skip(5);
          break;
        case 'ArrowUp':
          e.preventDefault();
          adjustVolume(0.1);
          break;
        case 'ArrowDown':
          e.preventDefault();
          adjustVolume(-0.1);
          break;
        case 'm':
          e.preventDefault();
          toggleMute();
          break;
        case 'f':
          e.preventDefault();
          toggleFullscreen();
          break;
        case 'j':
          e.preventDefault();
          skip(-10);
          break;
        case 'l':
          e.preventDefault();
          skip(10);
          break;
        case '0':
        case 'Home':
          e.preventDefault();
          seek(0);
          break;
        case 'End':
          e.preventDefault();
          seek(duration);
          break;
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [duration]);

  // Fullscreen change detection
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, []);

  const togglePlayPause = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;

    if (video.paused) {
      video.play();
    } else {
      video.pause();
    }
  }, []);

  const seek = useCallback((time: number) => {
    const video = videoRef.current;
    if (!video) return;
    video.currentTime = Math.max(0, Math.min(time, duration));
  }, [duration]);

  const skip = useCallback((seconds: number) => {
    const video = videoRef.current;
    if (!video) return;
    video.currentTime = Math.max(0, Math.min(video.currentTime + seconds, duration));
  }, [duration]);

  const adjustVolume = useCallback((delta: number) => {
    const video = videoRef.current;
    if (!video) return;
    const newVolume = Math.max(0, Math.min(1, volume + delta));
    video.volume = newVolume;
    setVolume(newVolume);
    setIsMuted(newVolume === 0);
  }, [volume]);

  const toggleMute = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;
    video.muted = !video.muted;
    setIsMuted(video.muted);
  }, []);

  const toggleFullscreen = useCallback(async () => {
    const container = containerRef.current;
    if (!container) return;

    try {
      if (document.fullscreenElement) {
        await document.exitFullscreen();
      } else {
        await container.requestFullscreen();
      }
    } catch (err) {
      console.error('Fullscreen error:', err);
    }
  }, []);

  const handleProgressClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const progress = progressRef.current;
    if (!progress) return;

    const rect = progress.getBoundingClientRect();
    const percent = (e.clientX - rect.left) / rect.width;
    seek(percent * duration);
  }, [duration, seek]);

  const handleVolumeChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const video = videoRef.current;
    if (!video) return;

    const newVolume = parseFloat(e.target.value);
    video.volume = newVolume;
    setVolume(newVolume);
    setIsMuted(newVolume === 0);
  }, []);

  const handlePlaybackRateChange = useCallback((rate: number) => {
    const video = videoRef.current;
    if (!video) return;
    video.playbackRate = rate;
    setPlaybackRate(rate);
    setShowSpeedMenu(false);
  }, []);

  const progress = duration > 0 ? (currentTime / duration) * 100 : 0;
  const bufferedProgress = duration > 0 ? (buffered / duration) * 100 : 0;

  if (error) {
    return (
      <div className={cn('relative bg-surface-900 flex items-center justify-center', className)}>
        <div className="text-center text-red-400">
          <p className="mb-2">Failed to load video</p>
          <p className="text-sm text-surface-500">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={cn(
        'relative bg-black group',
        isFullscreen && 'fixed inset-0 z-50',
        className
      )}
      tabIndex={0}
    >
      {/* Video Element */}
      <video
        ref={videoRef}
        src={src.startsWith('file://') ? src : `file://${src}`}
        poster={poster ? (poster.startsWith('file://') ? poster : `file://${poster}`) : undefined}
        autoPlay={autoPlay}
        loop={loop}
        muted={isMuted}
        className="w-full h-full object-contain"
        onClick={togglePlayPause}
        playsInline
      />

      {/* Loading Indicator */}
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/50">
          <Loader2 className="w-12 h-12 text-white animate-spin" />
        </div>
      )}

      {/* Play/Pause overlay on click */}
      {!isPlaying && !isLoading && (
        <button
          onClick={togglePlayPause}
          className="absolute inset-0 flex items-center justify-center bg-black/30"
        >
          <div className="w-20 h-20 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center transition-transform hover:scale-110">
            <Play className="w-10 h-10 text-white ml-1" />
          </div>
        </button>
      )}

      {/* Controls */}
      {showControls && (
        <div
          className={cn(
            'absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/90 via-black/50 to-transparent transition-opacity duration-300',
            showControlsOverlay ? 'opacity-100' : 'opacity-0 pointer-events-none'
          )}
        >
          {/* Progress Bar */}
          <div
            ref={progressRef}
            className="h-1 mx-4 mb-2 bg-surface-700 cursor-pointer group/progress"
            onClick={handleProgressClick}
          >
            {/* Buffered */}
            <div
              className="absolute h-1 bg-surface-500"
              style={{ width: `${bufferedProgress}%` }}
            />
            {/* Progress */}
            <div
              className="absolute h-1 bg-brand-500 transition-all"
              style={{ width: `${progress}%` }}
            />
            {/* Hover indicator */}
            <div
              className="absolute h-3 w-3 -top-1 bg-brand-500 rounded-full opacity-0 group-hover/progress:opacity-100 transition-opacity"
              style={{ left: `calc(${progress}% - 6px)` }}
            />
          </div>

          {/* Control buttons */}
          <div className="flex items-center gap-2 px-4 pb-3">
            {/* Play/Pause */}
            <button
              onClick={togglePlayPause}
              className="p-2 text-white hover:text-brand-400 transition-colors"
              title={isPlaying ? 'Pause (Space)' : 'Play (Space)'}
            >
              {isPlaying ? (
                <Pause className="w-5 h-5" />
              ) : (
                <Play className="w-5 h-5" />
              )}
            </button>

            {/* Skip back */}
            <button
              onClick={() => skip(-10)}
              className="p-2 text-white hover:text-brand-400 transition-colors"
              title="Skip back 10s (J)"
            >
              <SkipBack className="w-4 h-4" />
            </button>

            {/* Skip forward */}
            <button
              onClick={() => skip(10)}
              className="p-2 text-white hover:text-brand-400 transition-colors"
              title="Skip forward 10s (L)"
            >
              <SkipForward className="w-4 h-4" />
            </button>

            {/* Volume */}
            <div className="flex items-center gap-1 group/volume">
              <button
                onClick={toggleMute}
                className="p-2 text-white hover:text-brand-400 transition-colors"
                title={isMuted ? 'Unmute (M)' : 'Mute (M)'}
              >
                {isMuted || volume === 0 ? (
                  <VolumeX className="w-5 h-5" />
                ) : (
                  <Volume2 className="w-5 h-5" />
                )}
              </button>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={isMuted ? 0 : volume}
                onChange={handleVolumeChange}
                className="w-0 group-hover/volume:w-20 transition-all opacity-0 group-hover/volume:opacity-100"
              />
            </div>

            {/* Time display */}
            <div className="text-sm text-white font-mono ml-2">
              {formatTime(currentTime)} / {formatTime(duration)}
            </div>

            {/* Spacer */}
            <div className="flex-1" />

            {/* Playback speed */}
            <div className="relative">
              <button
                onClick={() => setShowSpeedMenu(!showSpeedMenu)}
                className="p-2 text-white hover:text-brand-400 transition-colors text-sm font-mono"
                title="Playback speed"
              >
                {playbackRate}x
              </button>
              {showSpeedMenu && (
                <div className="absolute bottom-full right-0 mb-2 bg-surface-800 rounded-lg shadow-lg overflow-hidden">
                  {PLAYBACK_RATES.map((rate) => (
                    <button
                      key={rate}
                      onClick={() => handlePlaybackRateChange(rate)}
                      className={cn(
                        'block w-full px-4 py-2 text-sm text-left hover:bg-surface-700',
                        rate === playbackRate ? 'text-brand-400' : 'text-white'
                      )}
                    >
                      {rate}x
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Fullscreen */}
            <button
              onClick={toggleFullscreen}
              className="p-2 text-white hover:text-brand-400 transition-colors"
              title={isFullscreen ? 'Exit fullscreen (F)' : 'Fullscreen (F)'}
            >
              {isFullscreen ? (
                <Minimize2 className="w-5 h-5" />
              ) : (
                <Maximize2 className="w-5 h-5" />
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// Export hook for external control
export function useVideoPlayer() {
  const videoRef = useRef<HTMLVideoElement>(null);

  return {
    ref: videoRef,
    play: () => videoRef.current?.play(),
    pause: () => videoRef.current?.pause(),
    seek: (time: number) => {
      if (videoRef.current) videoRef.current.currentTime = time;
    },
    getCurrentTime: () => videoRef.current?.currentTime || 0,
    getDuration: () => videoRef.current?.duration || 0,
  };
}
