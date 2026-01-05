/**
 * Mobile-optimized video player component.
 *
 * Features:
 * - Touch gesture controls (tap, double-tap, swipe, pinch)
 * - Adaptive quality based on network
 * - Picture-in-picture support
 * - Fullscreen with rotation lock
 * - Battery-aware quality
 */

import React, {
  useRef,
  useState,
  useEffect,
  useCallback,
  forwardRef,
  useImperativeHandle,
} from 'react';
import { useVideoGestures } from '../hooks/useGestures';
import {
  useIsMobile,
  useOrientation,
  usePrefersReducedMotion,
  useOptimalVideoQuality,
  useNetworkInfo,
} from '../hooks/useMediaQuery';

export interface VideoSource {
  src: string;
  quality: '360p' | '480p' | '720p' | '1080p' | '4k';
  type: string;
}

export interface MobileVideoPlayerProps {
  /** Video sources in different qualities */
  sources: VideoSource[];
  /** Poster/thumbnail image */
  poster?: string;
  /** Video title for accessibility */
  title: string;
  /** Initial playback position in seconds */
  startTime?: number;
  /** Autoplay on load */
  autoPlay?: boolean;
  /** Loop video */
  loop?: boolean;
  /** Mute video */
  muted?: boolean;
  /** Called when video ends */
  onEnded?: () => void;
  /** Called when progress updates */
  onProgress?: (currentTime: number, duration: number) => void;
  /** Called when quality changes */
  onQualityChange?: (quality: string) => void;
  /** Called when error occurs */
  onError?: (error: Error) => void;
  /** Show skip intro button */
  skipIntro?: { start: number; end: number };
  /** Next video to play */
  nextVideo?: { title: string; thumbnail: string; onClick: () => void };
  /** Enable double-tap seek */
  doubleTapSeek?: boolean;
  /** Seek duration for double-tap in seconds */
  seekDuration?: number;
}

export interface MobileVideoPlayerRef {
  play: () => Promise<void>;
  pause: () => void;
  seek: (time: number) => void;
  setVolume: (volume: number) => void;
  setQuality: (quality: string) => void;
  toggleFullscreen: () => void;
  togglePip: () => void;
}

const MobileVideoPlayer = forwardRef<MobileVideoPlayerRef, MobileVideoPlayerProps>(
  (
    {
      sources,
      poster,
      title,
      startTime = 0,
      autoPlay = false,
      loop = false,
      muted = false,
      onEnded,
      onProgress,
      onQualityChange,
      onError,
      skipIntro,
      nextVideo,
      doubleTapSeek = true,
      seekDuration = 10,
    },
    ref
  ) => {
    const videoRef = useRef<HTMLVideoElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    // State
    const [isPlaying, setIsPlaying] = useState(false);
    const [currentTime, setCurrentTime] = useState(0);
    const [duration, setDuration] = useState(0);
    const [volume, setVolume] = useState(1);
    const [isMuted, setIsMuted] = useState(muted);
    const [isFullscreen, setIsFullscreen] = useState(false);
    const [isPip, setIsPip] = useState(false);
    const [isBuffering, setIsBuffering] = useState(false);
    const [quality, setQuality] = useState<string>('auto');
    const [showControls, setShowControls] = useState(true);
    const [showSkipIntro, setShowSkipIntro] = useState(false);
    const [showNextVideo, setShowNextVideo] = useState(false);
    const [seekIndicator, setSeekIndicator] = useState<{
      direction: 'forward' | 'backward';
      seconds: number;
    } | null>(null);

    // Hooks
    const isMobile = useIsMobile();
    const orientation = useOrientation();
    const reducedMotion = usePrefersReducedMotion();
    const optimalQuality = useOptimalVideoQuality();
    const networkInfo = useNetworkInfo();

    // Auto-hide controls timer
    const controlsTimerRef = useRef<NodeJS.Timeout | null>(null);

    // Get current source based on quality
    const getCurrentSource = useCallback(() => {
      if (quality === 'auto') {
        return sources.find((s) => s.quality === optimalQuality) || sources[0];
      }
      return sources.find((s) => s.quality === quality) || sources[0];
    }, [sources, quality, optimalQuality]);

    // Seek handler
    const seek = useCallback((time: number) => {
      if (videoRef.current) {
        videoRef.current.currentTime = Math.max(
          0,
          Math.min(time, videoRef.current.duration)
        );
      }
    }, []);

    // Play/Pause toggle
    const togglePlayPause = useCallback(() => {
      if (videoRef.current) {
        if (videoRef.current.paused) {
          videoRef.current.play();
        } else {
          videoRef.current.pause();
        }
      }
    }, []);

    // Fullscreen toggle
    const toggleFullscreen = useCallback(async () => {
      if (!containerRef.current) return;

      try {
        if (!document.fullscreenElement) {
          await containerRef.current.requestFullscreen();
          // Lock orientation on mobile
          if (isMobile && screen.orientation) {
            try {
              await (screen.orientation as any).lock('landscape');
            } catch (e) {
              // Orientation lock may not be supported
            }
          }
        } else {
          await document.exitFullscreen();
          if (screen.orientation) {
            try {
              screen.orientation.unlock();
            } catch (e) {
              // Ignore unlock errors
            }
          }
        }
      } catch (error) {
        console.error('Fullscreen error:', error);
      }
    }, [isMobile]);

    // PiP toggle
    const togglePip = useCallback(async () => {
      if (!videoRef.current) return;

      try {
        if (document.pictureInPictureElement) {
          await document.exitPictureInPicture();
        } else if (document.pictureInPictureEnabled) {
          await videoRef.current.requestPictureInPicture();
        }
      } catch (error) {
        console.error('PiP error:', error);
      }
    }, []);

    // Volume change handler
    const handleVolumeChange = useCallback((delta: number) => {
      if (videoRef.current) {
        const newVolume = Math.max(0, Math.min(1, volume + delta));
        videoRef.current.volume = newVolume;
        setVolume(newVolume);
        setIsMuted(newVolume === 0);
      }
    }, [volume]);

    // Seek forward/backward
    const seekForward = useCallback((seconds: number) => {
      if (videoRef.current) {
        seek(videoRef.current.currentTime + seconds);
        setSeekIndicator({ direction: 'forward', seconds });
        setTimeout(() => setSeekIndicator(null), 500);
      }
    }, [seek]);

    const seekBackward = useCallback((seconds: number) => {
      if (videoRef.current) {
        seek(videoRef.current.currentTime - seconds);
        setSeekIndicator({ direction: 'backward', seconds });
        setTimeout(() => setSeekIndicator(null), 500);
      }
    }, [seek]);

    // Touch gesture handlers
    const { ref: gestureRef, controlsVisible } = useVideoGestures({
      onSeekForward: (seconds) => seekForward(seconds),
      onSeekBackward: (seconds) => seekBackward(seconds),
      onVolumeChange: handleVolumeChange,
      onTogglePlayPause: togglePlayPause,
      onToggleFullscreen: toggleFullscreen,
      onToggleControls: () => {
        setShowControls((prev) => !prev);
        resetControlsTimer();
      },
      seekSeconds: seekDuration,
    });

    // Reset controls auto-hide timer
    const resetControlsTimer = useCallback(() => {
      if (controlsTimerRef.current) {
        clearTimeout(controlsTimerRef.current);
      }
      setShowControls(true);
      controlsTimerRef.current = setTimeout(() => {
        if (isPlaying) {
          setShowControls(false);
        }
      }, 3000);
    }, [isPlaying]);

    // Video event handlers
    useEffect(() => {
      const video = videoRef.current;
      if (!video) return;

      const handlePlay = () => setIsPlaying(true);
      const handlePause = () => setIsPlaying(false);
      const handleTimeUpdate = () => {
        setCurrentTime(video.currentTime);
        onProgress?.(video.currentTime, video.duration);

        // Check skip intro
        if (skipIntro && video.currentTime >= skipIntro.start && video.currentTime < skipIntro.end) {
          setShowSkipIntro(true);
        } else {
          setShowSkipIntro(false);
        }

        // Check next video
        if (nextVideo && video.duration - video.currentTime < 10) {
          setShowNextVideo(true);
        }
      };
      const handleDurationChange = () => setDuration(video.duration);
      const handleWaiting = () => setIsBuffering(true);
      const handleCanPlay = () => setIsBuffering(false);
      const handleEnded = () => {
        setIsPlaying(false);
        onEnded?.();
      };
      const handleError = () => {
        onError?.(new Error('Video playback error'));
      };

      video.addEventListener('play', handlePlay);
      video.addEventListener('pause', handlePause);
      video.addEventListener('timeupdate', handleTimeUpdate);
      video.addEventListener('durationchange', handleDurationChange);
      video.addEventListener('waiting', handleWaiting);
      video.addEventListener('canplay', handleCanPlay);
      video.addEventListener('ended', handleEnded);
      video.addEventListener('error', handleError);

      return () => {
        video.removeEventListener('play', handlePlay);
        video.removeEventListener('pause', handlePause);
        video.removeEventListener('timeupdate', handleTimeUpdate);
        video.removeEventListener('durationchange', handleDurationChange);
        video.removeEventListener('waiting', handleWaiting);
        video.removeEventListener('canplay', handleCanPlay);
        video.removeEventListener('ended', handleEnded);
        video.removeEventListener('error', handleError);
      };
    }, [onProgress, onEnded, onError, skipIntro, nextVideo]);

    // Fullscreen change listener
    useEffect(() => {
      const handleFullscreenChange = () => {
        setIsFullscreen(!!document.fullscreenElement);
      };

      document.addEventListener('fullscreenchange', handleFullscreenChange);
      return () => {
        document.removeEventListener('fullscreenchange', handleFullscreenChange);
      };
    }, []);

    // PiP change listener
    useEffect(() => {
      const handlePipChange = () => {
        setIsPip(!!document.pictureInPictureElement);
      };

      const video = videoRef.current;
      if (video) {
        video.addEventListener('enterpictureinpicture', handlePipChange);
        video.addEventListener('leavepictureinpicture', handlePipChange);
        return () => {
          video.removeEventListener('enterpictureinpicture', handlePipChange);
          video.removeEventListener('leavepictureinpicture', handlePipChange);
        };
      }
    }, []);

    // Set initial time
    useEffect(() => {
      if (videoRef.current && startTime > 0) {
        videoRef.current.currentTime = startTime;
      }
    }, [startTime]);

    // Auto quality based on network
    useEffect(() => {
      if (quality === 'auto' && networkInfo.saveData) {
        // Force lower quality on data saver
        const lowQuality = sources.find((s) => s.quality === '360p' || s.quality === '480p');
        if (lowQuality) {
          onQualityChange?.(lowQuality.quality);
        }
      }
    }, [quality, networkInfo.saveData, sources, onQualityChange]);

    // Expose methods via ref
    useImperativeHandle(ref, () => ({
      play: async () => {
        await videoRef.current?.play();
      },
      pause: () => {
        videoRef.current?.pause();
      },
      seek,
      setVolume: (vol: number) => {
        if (videoRef.current) {
          videoRef.current.volume = vol;
          setVolume(vol);
        }
      },
      setQuality: (q: string) => {
        setQuality(q);
        onQualityChange?.(q);
      },
      toggleFullscreen,
      togglePip,
    }));

    // Format time (mm:ss or hh:mm:ss)
    const formatTime = (seconds: number): string => {
      const hrs = Math.floor(seconds / 3600);
      const mins = Math.floor((seconds % 3600) / 60);
      const secs = Math.floor(seconds % 60);

      if (hrs > 0) {
        return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
      }
      return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    const source = getCurrentSource();

    return (
      <div
        ref={containerRef}
        className={`mobile-video-player ${isFullscreen ? 'fullscreen' : ''}`}
        style={{
          position: 'relative',
          width: '100%',
          aspectRatio: '16/9',
          backgroundColor: '#000',
          overflow: 'hidden',
        }}
      >
        {/* Video element */}
        <video
          ref={(el) => {
            (videoRef as any).current = el;
            if (gestureRef) {
              (gestureRef as any).current = el?.parentElement;
            }
          }}
          src={source.src}
          poster={poster}
          autoPlay={autoPlay}
          loop={loop}
          muted={isMuted}
          playsInline
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'contain',
          }}
          aria-label={title}
        />

        {/* Seek indicator */}
        {seekIndicator && !reducedMotion && (
          <div
            style={{
              position: 'absolute',
              top: '50%',
              left: seekIndicator.direction === 'backward' ? '20%' : '80%',
              transform: 'translate(-50%, -50%)',
              background: 'rgba(0,0,0,0.7)',
              borderRadius: '50%',
              padding: '1rem',
              color: 'white',
            }}
          >
            {seekIndicator.direction === 'forward' ? '⏩' : '⏪'} {seekIndicator.seconds}s
          </div>
        )}

        {/* Buffering indicator */}
        {isBuffering && (
          <div
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
            }}
          >
            <div className="spinner" aria-label="Loading" />
          </div>
        )}

        {/* Controls overlay */}
        {showControls && (
          <div
            className="video-controls"
            style={{
              position: 'absolute',
              bottom: 0,
              left: 0,
              right: 0,
              background: 'linear-gradient(transparent, rgba(0,0,0,0.8))',
              padding: '1rem',
              transition: reducedMotion ? 'none' : 'opacity 0.3s',
            }}
          >
            {/* Progress bar */}
            <input
              type="range"
              min={0}
              max={duration || 100}
              value={currentTime}
              onChange={(e) => seek(parseFloat(e.target.value))}
              style={{ width: '100%' }}
              aria-label="Video progress"
            />

            {/* Time display */}
            <div style={{ display: 'flex', justifyContent: 'space-between', color: 'white' }}>
              <span>{formatTime(currentTime)}</span>
              <span>{formatTime(duration)}</span>
            </div>

            {/* Control buttons */}
            <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center' }}>
              <button onClick={togglePlayPause} aria-label={isPlaying ? 'Pause' : 'Play'}>
                {isPlaying ? '⏸️' : '▶️'}
              </button>
              <button onClick={() => setIsMuted(!isMuted)} aria-label={isMuted ? 'Unmute' : 'Mute'}>
                {isMuted ? '🔇' : '🔊'}
              </button>
              <button onClick={toggleFullscreen} aria-label="Toggle fullscreen">
                {isFullscreen ? '⏹️' : '⛶'}
              </button>
              {document.pictureInPictureEnabled && (
                <button onClick={togglePip} aria-label="Picture in Picture">
                  📺
                </button>
              )}
            </div>
          </div>
        )}

        {/* Skip intro button */}
        {showSkipIntro && skipIntro && (
          <button
            onClick={() => seek(skipIntro.end)}
            style={{
              position: 'absolute',
              bottom: '5rem',
              right: '1rem',
              background: 'rgba(255,255,255,0.9)',
              color: 'black',
              border: 'none',
              padding: '0.5rem 1rem',
              borderRadius: '4px',
            }}
          >
            Skip Intro
          </button>
        )}

        {/* Next video overlay */}
        {showNextVideo && nextVideo && (
          <div
            style={{
              position: 'absolute',
              bottom: '5rem',
              right: '1rem',
              background: 'rgba(0,0,0,0.8)',
              padding: '0.5rem',
              borderRadius: '4px',
              color: 'white',
            }}
          >
            <p>Up Next: {nextVideo.title}</p>
            <button onClick={nextVideo.onClick}>Play Now</button>
          </div>
        )}
      </div>
    );
  }
);

MobileVideoPlayer.displayName = 'MobileVideoPlayer';

export default MobileVideoPlayer;
