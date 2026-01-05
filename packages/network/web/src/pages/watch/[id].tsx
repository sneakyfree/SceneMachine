/**
 * Watch Page
 *
 * Video playback page with player, comments, and recommendations.
 */

'use client';

import React, { useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { useVideoStore, useAuthStore } from '../../stores';
import { VideoCard } from '../../components/ui/VideoCard';

export default function WatchPage() {
  const router = useRouter();
  const { id } = router.query;

  const {
    currentVideo,
    isLoading,
    error,
    isPlaying,
    currentTime,
    duration,
    volume,
    isMuted,
    userReaction,
    isInWatchlist,
    comments,
    commentsLoading,
    hasMoreComments,
    recommendations,
    loadVideo,
    clearVideo,
    setPlaying,
    setCurrentTime,
    setDuration,
    setVolume,
    setMuted,
    toggleReaction,
    toggleWatchlist,
    loadMoreComments,
    addComment,
    saveProgress,
  } = useVideoStore();

  const { isAuthenticated, user } = useAuthStore();

  const videoRef = useRef<HTMLVideoElement>(null);
  const progressSaveInterval = useRef<NodeJS.Timeout | null>(null);
  const commentInputRef = useRef<HTMLTextAreaElement>(null);

  // Load video on mount
  useEffect(() => {
    if (id && typeof id === 'string') {
      loadVideo(id);
    }

    return () => {
      clearVideo();
      if (progressSaveInterval.current) {
        clearInterval(progressSaveInterval.current);
      }
    };
  }, [id, loadVideo, clearVideo]);

  // Save progress periodically
  useEffect(() => {
    if (isPlaying && isAuthenticated) {
      progressSaveInterval.current = setInterval(() => {
        saveProgress();
      }, 30000); // Every 30 seconds
    }

    return () => {
      if (progressSaveInterval.current) {
        clearInterval(progressSaveInterval.current);
      }
    };
  }, [isPlaying, isAuthenticated, saveProgress]);

  // Video event handlers
  const handleTimeUpdate = useCallback(() => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
    }
  }, [setCurrentTime]);

  const handleDurationChange = useCallback(() => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration);
    }
  }, [setDuration]);

  const handlePlay = useCallback(() => setPlaying(true), [setPlaying]);
  const handlePause = useCallback(() => setPlaying(false), [setPlaying]);

  const handleSeek = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const time = parseFloat(e.target.value);
    if (videoRef.current) {
      videoRef.current.currentTime = time;
      setCurrentTime(time);
    }
  }, [setCurrentTime]);

  const handleVolumeChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const vol = parseFloat(e.target.value);
    if (videoRef.current) {
      videoRef.current.volume = vol;
      setVolume(vol);
    }
  }, [setVolume]);

  const toggleMute = useCallback(() => {
    if (videoRef.current) {
      videoRef.current.muted = !isMuted;
      setMuted(!isMuted);
    }
  }, [isMuted, setMuted]);

  const togglePlayPause = useCallback(() => {
    if (videoRef.current) {
      if (videoRef.current.paused) {
        videoRef.current.play();
      } else {
        videoRef.current.pause();
      }
    }
  }, []);

  const handleCommentSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!commentInputRef.current?.value.trim()) return;

    try {
      await addComment(commentInputRef.current.value);
      commentInputRef.current.value = '';
    } catch {
      // Error handled by store
    }
  };

  const formatTime = (seconds: number): string => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (hrs > 0) {
      return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatViews = (views: number): string => {
    if (views >= 1000000) return `${(views / 1000000).toFixed(1)}M`;
    if (views >= 1000) return `${(views / 1000).toFixed(1)}K`;
    return views.toString();
  };

  const formatDate = (dateStr: string | null): string => {
    if (!dateStr) return '';
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  if (isLoading) {
    return (
      <div className="watch-page loading">
        <div className="spinner" />
        <style jsx>{`
          .watch-page.loading {
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background: var(--color-bg-primary);
          }
        `}</style>
      </div>
    );
  }

  if (error || !currentVideo) {
    return (
      <div className="watch-page error">
        <div className="error-content">
          <span className="emoji">😕</span>
          <h1>Video not found</h1>
          <p>{error || 'This video may have been removed or is unavailable.'}</p>
          <Link href="/" className="back-btn">Back to Home</Link>
        </div>
        <style jsx>{`
          .watch-page.error {
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background: var(--color-bg-primary);
            text-align: center;
            padding: var(--space-4);
          }
          .error-content .emoji {
            font-size: 64px;
            display: block;
            margin-bottom: var(--space-4);
          }
          .error-content h1 {
            margin-bottom: var(--space-2);
          }
          .error-content p {
            color: var(--color-text-secondary);
            margin-bottom: var(--space-6);
          }
          .back-btn {
            display: inline-block;
            padding: var(--space-3) var(--space-6);
            background: var(--gradient-primary);
            color: white;
            border-radius: var(--radius-md);
            font-weight: 600;
          }
        `}</style>
      </div>
    );
  }

  return (
    <div className="watch-page">
      {/* Header */}
      <header className="header">
        <Link href="/" className="back-link">
          ← Back
        </Link>
      </header>

      <div className="content">
        {/* Main Column */}
        <main className="main-column">
          {/* Video Player */}
          <div className="player-container">
            <video
              ref={videoRef}
              src={`/api/stream/${currentVideo.id}/master.m3u8`}
              poster={currentVideo.thumbnail_url}
              onTimeUpdate={handleTimeUpdate}
              onDurationChange={handleDurationChange}
              onPlay={handlePlay}
              onPause={handlePause}
              onClick={togglePlayPause}
              playsInline
            />

            {/* Custom Controls */}
            <div className="controls">
              <button onClick={togglePlayPause} className="play-btn">
                {isPlaying ? '⏸️' : '▶️'}
              </button>

              <div className="progress">
                <span className="time">{formatTime(currentTime)}</span>
                <input
                  type="range"
                  min={0}
                  max={duration || 100}
                  value={currentTime}
                  onChange={handleSeek}
                  className="progress-bar"
                />
                <span className="time">{formatTime(duration)}</span>
              </div>

              <div className="volume">
                <button onClick={toggleMute} className="mute-btn">
                  {isMuted || volume === 0 ? '🔇' : volume < 0.5 ? '🔉' : '🔊'}
                </button>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.1}
                  value={isMuted ? 0 : volume}
                  onChange={handleVolumeChange}
                  className="volume-bar"
                />
              </div>

              <button className="fullscreen-btn">⛶</button>
            </div>
          </div>

          {/* Video Info */}
          <div className="video-info">
            <h1 className="title">{currentVideo.title}</h1>

            <div className="meta-row">
              <span className="views">{formatViews(currentVideo.view_count)} views</span>
              <span className="dot">•</span>
              <span className="date">{formatDate(currentVideo.published_at)}</span>

              <div className="actions">
                <button
                  onClick={() => toggleReaction('like')}
                  className={`action-btn ${userReaction === 'like' ? 'active' : ''}`}
                >
                  👍 {formatViews(currentVideo.like_count)}
                </button>

                <button
                  onClick={toggleWatchlist}
                  className={`action-btn ${isInWatchlist ? 'active' : ''}`}
                >
                  {isInWatchlist ? '✓ Saved' : '+ Save'}
                </button>

                <button className="action-btn">
                  ↗ Share
                </button>
              </div>
            </div>

            {/* Creator Info */}
            <div className="creator-row">
              <Link href={`/channel/${currentVideo.creator_id}`} className="creator-link">
                <img
                  src={currentVideo.creator?.avatar_url || '/default-avatar.jpg'}
                  alt={currentVideo.creator?.display_name}
                  className="avatar"
                />
                <div className="creator-info">
                  <span className="name">
                    {currentVideo.creator?.display_name || currentVideo.creator?.username}
                    {currentVideo.creator?.is_verified && <span className="verified">✓</span>}
                  </span>
                  <span className="followers">
                    {formatViews(currentVideo.creator?.follower_count || 0)} followers
                  </span>
                </div>
              </Link>

              {isAuthenticated && currentVideo.creator_id !== user?.id && (
                <button className="follow-btn">Follow</button>
              )}
            </div>

            {/* Description */}
            <div className="description">
              <p>{currentVideo.description || 'No description provided.'}</p>

              {currentVideo.tags && currentVideo.tags.length > 0 && (
                <div className="tags">
                  {currentVideo.tags.map((tag) => (
                    <Link key={tag} href={`/search?q=${encodeURIComponent(tag)}`} className="tag">
                      #{tag}
                    </Link>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Comments */}
          <div className="comments-section">
            <h2>{currentVideo.comment_count} Comments</h2>

            {isAuthenticated && (
              <form onSubmit={handleCommentSubmit} className="comment-form">
                <img
                  src={user?.avatar_url || '/default-avatar.jpg'}
                  alt={user?.display_name}
                  className="avatar"
                />
                <textarea
                  ref={commentInputRef}
                  placeholder="Add a comment..."
                  rows={2}
                />
                <button type="submit">Post</button>
              </form>
            )}

            <div className="comments-list">
              {comments.map((comment) => (
                <div key={comment.id} className="comment">
                  <Link href={`/channel/${comment.user_id}`}>
                    <img
                      src={comment.user?.avatar_url || '/default-avatar.jpg'}
                      alt={comment.user?.display_name}
                      className="avatar"
                    />
                  </Link>
                  <div className="comment-content">
                    <div className="comment-header">
                      <Link href={`/channel/${comment.user_id}`} className="username">
                        {comment.user?.display_name || comment.user?.username}
                      </Link>
                      <span className="time">
                        {formatDate(comment.created_at)}
                      </span>
                    </div>
                    <p>{comment.content}</p>
                    <div className="comment-actions">
                      <button>👍 {comment.like_count}</button>
                      <button>Reply</button>
                    </div>
                  </div>
                </div>
              ))}

              {hasMoreComments && (
                <button
                  onClick={loadMoreComments}
                  className="load-more-btn"
                  disabled={commentsLoading}
                >
                  {commentsLoading ? 'Loading...' : 'Load more comments'}
                </button>
              )}
            </div>
          </div>
        </main>

        {/* Sidebar - Recommendations */}
        <aside className="sidebar">
          <h3>Up Next</h3>
          <div className="recommendations">
            {recommendations.map((video) => (
              <VideoCard key={video.id} video={video} size="small" />
            ))}
          </div>
        </aside>
      </div>

      <style jsx>{`
        .watch-page {
          min-height: 100vh;
          background: var(--color-bg-primary);
        }

        .header {
          padding: var(--space-3) var(--space-4);
          border-bottom: 1px solid var(--color-border);
        }

        .back-link {
          color: var(--color-text-secondary);
          font-size: var(--text-sm);
        }

        .content {
          display: grid;
          grid-template-columns: 1fr 360px;
          gap: var(--space-6);
          max-width: 1600px;
          margin: 0 auto;
          padding: var(--space-4);
        }

        @media (max-width: 1024px) {
          .content {
            grid-template-columns: 1fr;
          }

          .sidebar {
            order: 1;
          }
        }

        .player-container {
          position: relative;
          aspect-ratio: 16 / 9;
          background: black;
          border-radius: var(--radius-lg);
          overflow: hidden;
        }

        .player-container video {
          width: 100%;
          height: 100%;
          object-fit: contain;
        }

        .controls {
          position: absolute;
          bottom: 0;
          left: 0;
          right: 0;
          display: flex;
          align-items: center;
          gap: var(--space-3);
          padding: var(--space-4);
          background: linear-gradient(transparent, rgba(0, 0, 0, 0.8));
        }

        .controls button {
          color: white;
          font-size: var(--text-lg);
        }

        .progress {
          flex: 1;
          display: flex;
          align-items: center;
          gap: var(--space-2);
        }

        .progress .time {
          font-size: var(--text-xs);
          color: white;
          min-width: 45px;
        }

        .progress-bar {
          flex: 1;
          height: 4px;
          accent-color: var(--color-accent);
        }

        .volume {
          display: flex;
          align-items: center;
          gap: var(--space-2);
        }

        .volume-bar {
          width: 80px;
          height: 4px;
          accent-color: var(--color-accent);
        }

        @media (max-width: 640px) {
          .volume-bar {
            display: none;
          }
        }

        .video-info {
          padding: var(--space-4) 0;
        }

        .title {
          font-size: var(--text-xl);
          margin-bottom: var(--space-3);
        }

        .meta-row {
          display: flex;
          align-items: center;
          flex-wrap: wrap;
          gap: var(--space-2);
          color: var(--color-text-secondary);
          font-size: var(--text-sm);
          margin-bottom: var(--space-4);
        }

        .dot {
          font-size: 8px;
        }

        .actions {
          margin-left: auto;
          display: flex;
          gap: var(--space-2);
        }

        .action-btn {
          padding: var(--space-2) var(--space-3);
          background: var(--color-bg-secondary);
          border: 1px solid var(--color-border);
          border-radius: var(--radius-full);
          color: var(--color-text-primary);
          font-size: var(--text-sm);
          font-weight: 500;
        }

        .action-btn.active {
          background: var(--color-accent-light);
          border-color: var(--color-accent);
          color: var(--color-accent);
        }

        .creator-row {
          display: flex;
          align-items: center;
          gap: var(--space-4);
          padding: var(--space-4);
          background: var(--color-bg-secondary);
          border-radius: var(--radius-lg);
          margin-bottom: var(--space-4);
        }

        .creator-link {
          display: flex;
          align-items: center;
          gap: var(--space-3);
          text-decoration: none;
          flex: 1;
        }

        .creator-row .avatar {
          width: 48px;
          height: 48px;
          border-radius: 50%;
          object-fit: cover;
        }

        .creator-info {
          display: flex;
          flex-direction: column;
        }

        .creator-info .name {
          font-weight: 600;
          color: var(--color-text-primary);
          display: flex;
          align-items: center;
          gap: var(--space-1);
        }

        .verified {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 16px;
          height: 16px;
          background: var(--color-accent);
          color: white;
          font-size: 10px;
          border-radius: 50%;
        }

        .creator-info .followers {
          font-size: var(--text-sm);
          color: var(--color-text-secondary);
        }

        .follow-btn {
          padding: var(--space-2) var(--space-5);
          background: var(--gradient-primary);
          color: white;
          font-weight: 600;
          border-radius: var(--radius-full);
        }

        .description {
          padding: var(--space-4);
          background: var(--color-bg-secondary);
          border-radius: var(--radius-lg);
        }

        .description p {
          white-space: pre-wrap;
          margin-bottom: var(--space-3);
        }

        .tags {
          display: flex;
          flex-wrap: wrap;
          gap: var(--space-2);
        }

        .tag {
          color: var(--color-accent);
          font-size: var(--text-sm);
        }

        .comments-section {
          margin-top: var(--space-6);
        }

        .comments-section h2 {
          font-size: var(--text-lg);
          margin-bottom: var(--space-4);
        }

        .comment-form {
          display: flex;
          gap: var(--space-3);
          margin-bottom: var(--space-6);
        }

        .comment-form .avatar {
          width: 40px;
          height: 40px;
          border-radius: 50%;
          object-fit: cover;
        }

        .comment-form textarea {
          flex: 1;
          padding: var(--space-3);
          background: var(--color-bg-secondary);
          border: 1px solid var(--color-border);
          border-radius: var(--radius-md);
          color: var(--color-text-primary);
          resize: none;
        }

        .comment-form button {
          padding: var(--space-2) var(--space-4);
          background: var(--gradient-primary);
          color: white;
          font-weight: 600;
          border-radius: var(--radius-md);
          align-self: flex-end;
        }

        .comments-list {
          display: flex;
          flex-direction: column;
          gap: var(--space-4);
        }

        .comment {
          display: flex;
          gap: var(--space-3);
        }

        .comment .avatar {
          width: 40px;
          height: 40px;
          border-radius: 50%;
          object-fit: cover;
        }

        .comment-content {
          flex: 1;
        }

        .comment-header {
          display: flex;
          align-items: center;
          gap: var(--space-2);
          margin-bottom: var(--space-1);
        }

        .comment-header .username {
          font-weight: 600;
          font-size: var(--text-sm);
          color: var(--color-text-primary);
        }

        .comment-header .time {
          font-size: var(--text-xs);
          color: var(--color-text-tertiary);
        }

        .comment-content p {
          font-size: var(--text-sm);
          margin-bottom: var(--space-2);
        }

        .comment-actions {
          display: flex;
          gap: var(--space-3);
        }

        .comment-actions button {
          font-size: var(--text-xs);
          color: var(--color-text-secondary);
        }

        .load-more-btn {
          padding: var(--space-3);
          background: var(--color-bg-secondary);
          border: 1px solid var(--color-border);
          border-radius: var(--radius-md);
          color: var(--color-text-primary);
          font-weight: 500;
        }

        .sidebar h3 {
          font-size: var(--text-lg);
          margin-bottom: var(--space-4);
        }

        .recommendations {
          display: flex;
          flex-direction: column;
          gap: var(--space-4);
        }
      `}</style>
    </div>
  );
}
