/**
 * Video Comparison View component.
 * Allows side-by-side comparison of up to 3 video takes with synchronized playback.
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import { X, Play, Pause, Volume2, VolumeX } from 'lucide-react';
import { cn } from '../../lib/utils';
import { VideoPlayer } from '../video-player';

interface VideoItem {
  id: string;
  src: string;
  label: string;
  poster?: string;
}

interface ComparisonViewProps {
  videos: VideoItem[];
  onClose: () => void;
  onSelectBest?: (videoId: string) => void;
  className?: string;
}

export function ComparisonView({
  videos,
  onClose,
  onSelectBest,
  className,
}: ComparisonViewProps) {
  const [selectedBest, setSelectedBest] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [volume, setVolume] = useState(0.8);
  const [isMuted, setIsMuted] = useState(false);

  const videoRefs = useRef<Map<string, HTMLVideoElement>>(new Map());

  // Limit to max 3 videos
  const displayVideos = videos.slice(0, 3);

  // Sync playback across all videos
  const syncPlay = useCallback(() => {
    videoRefs.current.forEach((video) => {
      const playPromise = video.play();
      // Handle the promise only if play() returns one (not in test environment)
      if (playPromise !== undefined) {
        playPromise.catch((err) => {
          console.error('Failed to play video:', err);
        });
      }
    });
    setIsPlaying(true);
  }, []);

  const syncPause = useCallback(() => {
    videoRefs.current.forEach((video) => {
      video.pause();
    });
    setIsPlaying(false);
  }, []);

  const syncSeek = useCallback((time: number) => {
    videoRefs.current.forEach((video) => {
      video.currentTime = time;
    });
    setCurrentTime(time);
  }, []);

  const syncVolume = useCallback((newVolume: number) => {
    videoRefs.current.forEach((video) => {
      video.volume = newVolume;
    });
    setVolume(newVolume);
    setIsMuted(newVolume === 0);
  }, []);

  const toggleMute = useCallback(() => {
    const newMuted = !isMuted;
    videoRefs.current.forEach((video) => {
      video.muted = newMuted;
    });
    setIsMuted(newMuted);
  }, [isMuted]);

  const handleSelectBest = useCallback(() => {
    if (selectedBest && onSelectBest) {
      onSelectBest(selectedBest);
      onClose();
    }
  }, [selectedBest, onSelectBest, onClose]);

  // Register video element
  const registerVideo = useCallback((id: string, element: HTMLVideoElement | null) => {
    if (element) {
      videoRefs.current.set(id, element);
      element.volume = volume;
      element.muted = isMuted;
    } else {
      videoRefs.current.delete(id);
    }
  }, [volume, isMuted]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case ' ':
        case 'k':
          e.preventDefault();
          isPlaying ? syncPause() : syncPlay();
          break;
        case 'Escape':
          e.preventDefault();
          onClose();
          break;
        case 'm':
          e.preventDefault();
          toggleMute();
          break;
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isPlaying, syncPlay, syncPause, onClose, toggleMute]);

  // Get duration from first video
  const duration = videoRefs.current.values().next().value?.duration || 0;
  const progress = duration > 0 ? (currentTime / duration) * 100 : 0;

  const gridClass = displayVideos.length === 2
    ? 'grid-cols-2'
    : displayVideos.length === 3
    ? 'grid-cols-3'
    : 'grid-cols-1';

  return (
    <div
      className={cn(
        'fixed inset-0 z-50 bg-black/95 flex flex-col',
        className
      )}
      role="dialog"
      aria-label="Video comparison"
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-surface-700">
        <div>
          <h2 className="text-xl font-bold">Compare Takes</h2>
          <p className="text-sm text-surface-400 mt-1">
            Compare {displayVideos.length} video{displayVideos.length > 1 ? 's' : ''} side-by-side
          </p>
        </div>

        <button
          onClick={onClose}
          className="p-2 hover:bg-surface-700 rounded-lg transition-colors"
          title="Close comparison (Esc)"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Video Grid */}
      <div className={cn('flex-1 grid gap-4 p-4', gridClass)}>
        {displayVideos.map((video) => (
          <div
            key={video.id}
            className={cn(
              'relative bg-surface-900 rounded-lg overflow-hidden',
              selectedBest === video.id && 'ring-4 ring-brand-500'
            )}
          >
            {/* Video Label */}
            <div className="absolute top-3 left-3 z-10 px-3 py-1.5 bg-black/70 backdrop-blur-sm text-white text-sm font-medium rounded-lg">
              {video.label}
            </div>

            {/* Selection Indicator */}
            {selectedBest === video.id && (
              <div className="absolute top-3 right-3 z-10 px-2 py-1 bg-brand-500 text-white text-xs font-medium rounded-full">
                Selected
              </div>
            )}

            {/* Video Element */}
            <video
              ref={(el) => registerVideo(video.id, el)}
              src={video.src.startsWith('file://') ? video.src : `file://${video.src}`}
              poster={video.poster ? (video.poster.startsWith('file://') ? video.poster : `file://${video.poster}`) : undefined}
              className="w-full h-full object-contain"
              playsInline
              onTimeUpdate={(e) => {
                // Sync time from master video (first one)
                if (video.id === displayVideos[0].id) {
                  setCurrentTime(e.currentTarget.currentTime);
                }
              }}
              onEnded={() => {
                if (video.id === displayVideos[0].id) {
                  syncPause();
                }
              }}
            />

            {/* Select Best Button */}
            <button
              onClick={() => setSelectedBest(video.id)}
              className={cn(
                'absolute bottom-3 left-1/2 -translate-x-1/2 px-4 py-2 rounded-lg font-medium text-sm transition-all',
                selectedBest === video.id
                  ? 'bg-brand-500 text-white'
                  : 'bg-white/10 hover:bg-white/20 text-white backdrop-blur-sm'
              )}
            >
              {selectedBest === video.id ? 'Selected' : 'Select This'}
            </button>
          </div>
        ))}
      </div>

      {/* Synchronized Controls */}
      <div className="border-t border-surface-700 bg-surface-900 p-4">
        {/* Progress Bar */}
        <div
          className="h-2 mb-4 bg-surface-700 rounded-full cursor-pointer group"
          onClick={(e) => {
            const rect = e.currentTarget.getBoundingClientRect();
            const percent = (e.clientX - rect.left) / rect.width;
            syncSeek(percent * duration);
          }}
        >
          <div
            className="h-full bg-brand-500 rounded-full transition-all relative"
            style={{ width: `${progress}%` }}
          >
            {/* Scrubber */}
            <div className="absolute -right-1 -top-1 w-4 h-4 bg-brand-500 rounded-full opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
        </div>

        {/* Control Buttons */}
        <div className="flex items-center gap-4">
          {/* Play/Pause */}
          <button
            onClick={isPlaying ? syncPause : syncPlay}
            className="p-3 bg-brand-500 hover:bg-brand-600 rounded-full transition-colors"
            title={isPlaying ? 'Pause (Space)' : 'Play (Space)'}
          >
            {isPlaying ? (
              <Pause className="w-5 h-5 text-white" />
            ) : (
              <Play className="w-5 h-5 text-white ml-0.5" />
            )}
          </button>

          {/* Time Display */}
          <div className="text-sm text-surface-400 font-mono">
            {formatTime(currentTime)} / {formatTime(duration)}
          </div>

          {/* Volume Control */}
          <div className="flex items-center gap-2">
            <button
              onClick={toggleMute}
              className="p-2 hover:bg-surface-700 rounded-lg transition-colors"
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
              onChange={(e) => syncVolume(parseFloat(e.target.value))}
              className="w-24"
            />
          </div>

          {/* Spacer */}
          <div className="flex-1" />

          {/* Select Best Action */}
          {onSelectBest && (
            <button
              onClick={handleSelectBest}
              disabled={!selectedBest}
              className={cn(
                'px-6 py-2 rounded-lg font-medium transition-colors',
                selectedBest
                  ? 'bg-brand-500 hover:bg-brand-600 text-white'
                  : 'bg-surface-700 text-surface-500 cursor-not-allowed'
              )}
            >
              Use Selected Take
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function formatTime(seconds: number): string {
  if (!isFinite(seconds)) return '0:00';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}
