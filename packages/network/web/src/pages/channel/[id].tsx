/**
 * Channel Page
 *
 * Public creator profile with videos, about section, and follow functionality.
 */

'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { useAuthStore } from '../../stores';
import { apiClient, Video, User } from '../../lib/api-client';

type TabType = 'videos' | 'shorts' | 'about';

interface ChannelData {
  user: User;
  videos: Video[];
  followerCount: number;
  isFollowing: boolean;
  totalViews: number;
}

export default function ChannelPage() {
  const router = useRouter();
  const { id } = router.query;
  const { user: currentUser, isAuthenticated } = useAuthStore();

  const [channel, setChannel] = useState<ChannelData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('videos');
  const [isFollowLoading, setIsFollowLoading] = useState(false);

  const isOwnChannel = currentUser?.id === id;

  useEffect(() => {
    if (!id) return;

    const loadChannel = async () => {
      setIsLoading(true);
      setError(null);

      try {
        // Fetch user profile, videos, and follow status in parallel
        const [userRes, videosRes, followStatus] = await Promise.all([
          apiClient.getUser(id as string),
          apiClient.getVideosByCreator(id as string),
          isAuthenticated ? apiClient.getFollowStatus(id as string) : Promise.resolve({ is_following: false }),
        ]);

        // Calculate total views from paginated response
        const videos = videosRes.items;
        const totalViews = videos.reduce((sum: number, v: Video) => sum + v.view_count, 0);

        setChannel({
          user: userRes,
          videos,
          followerCount: userRes.follower_count || 0,
          isFollowing: followStatus.is_following,
          totalViews,
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load channel');
      } finally {
        setIsLoading(false);
      }
    };

    loadChannel();
  }, [id, isAuthenticated]);

  const handleFollow = async () => {
    if (!isAuthenticated) {
      router.push(`/login?redirect=/channel/${id}`);
      return;
    }

    if (!channel) return;

    setIsFollowLoading(true);
    try {
      if (channel.isFollowing) {
        await apiClient.unfollow(id as string);
        setChannel(prev => prev ? {
          ...prev,
          isFollowing: false,
          followerCount: prev.followerCount - 1,
        } : null);
      } else {
        await apiClient.follow(id as string);
        setChannel(prev => prev ? {
          ...prev,
          isFollowing: true,
          followerCount: prev.followerCount + 1,
        } : null);
      }
    } catch (err) {
      console.error('Follow error:', err);
    } finally {
      setIsFollowLoading(false);
    }
  };

  const formatNumber = (num: number): string => {
    if (num >= 1000000) {
      return `${(num / 1000000).toFixed(1)}M`;
    }
    if (num >= 1000) {
      return `${(num / 1000).toFixed(1)}K`;
    }
    return num.toString();
  };

  const formatDuration = (seconds: number): string => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    if (hrs > 0) {
      return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatDate = (dateStr: string | null): string => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  if (isLoading) {
    return (
      <div className="channel-page">
        <div className="loading-state">
          <div className="skeleton banner" />
          <div className="channel-header-skeleton">
            <div className="skeleton avatar" />
            <div className="skeleton title" />
            <div className="skeleton stats" />
          </div>
          <div className="video-grid-skeleton">
            {[1, 2, 3, 4, 5, 6].map(i => (
              <div key={i} className="skeleton video-card" />
            ))}
          </div>
        </div>
        <style jsx>{`
          .channel-page { min-height: 100vh; background: var(--color-bg-primary); }
          .loading-state { max-width: 1280px; margin: 0 auto; }
          .skeleton { background: var(--color-bg-tertiary); border-radius: var(--radius-md); }
          .skeleton.banner { height: 200px; }
          .channel-header-skeleton { padding: var(--space-6); display: flex; align-items: center; gap: var(--space-4); }
          .skeleton.avatar { width: 120px; height: 120px; border-radius: 50%; }
          .skeleton.title { width: 200px; height: 32px; }
          .skeleton.stats { width: 150px; height: 20px; margin-left: auto; }
          .video-grid-skeleton { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: var(--space-4); padding: var(--space-6); }
          .skeleton.video-card { aspect-ratio: 16/9; }
        `}</style>
      </div>
    );
  }

  if (error || !channel) {
    return (
      <div className="channel-page">
        <div className="error-state">
          <h1>Channel not found</h1>
          <p>{error || 'The channel you are looking for does not exist.'}</p>
          <Link href="/">Go Home</Link>
        </div>
        <style jsx>{`
          .channel-page { min-height: 100vh; background: var(--color-bg-primary); display: flex; align-items: center; justify-content: center; }
          .error-state { text-align: center; }
          .error-state h1 { font-size: var(--text-2xl); margin-bottom: var(--space-2); }
          .error-state p { color: var(--color-text-secondary); margin-bottom: var(--space-6); }
          .error-state a { color: var(--color-accent); }
        `}</style>
      </div>
    );
  }

  const filteredVideos = channel.videos.filter(v => {
    if (activeTab === 'shorts') return v.duration_seconds <= 60;
    if (activeTab === 'videos') return v.duration_seconds > 60;
    return true;
  });

  return (
    <div className="channel-page">
      {/* Banner */}
      <div
        className="banner"
        style={{
          backgroundImage: channel.user.banner_url
            ? `url(${channel.user.banner_url})`
            : undefined,
        }}
      />

      {/* Channel Header */}
      <div className="channel-header">
        <div className="container">
          <div className="header-content">
            <div className="avatar">
              <img
                src={channel.user.avatar_url || '/default-avatar.jpg'}
                alt={channel.user.display_name || channel.user.username}
              />
              {channel.user.is_verified && (
                <span className="verified-badge" title="Verified">✓</span>
              )}
            </div>

            <div className="channel-info">
              <h1 className="channel-name">
                {channel.user.display_name || channel.user.username}
              </h1>
              <div className="channel-handle">@{channel.user.username}</div>
              <div className="channel-stats">
                <span>{formatNumber(channel.followerCount)} followers</span>
                <span className="dot">•</span>
                <span>{channel.videos.length} videos</span>
                <span className="dot">•</span>
                <span>{formatNumber(channel.totalViews)} total views</span>
              </div>
            </div>

            <div className="header-actions">
              {isOwnChannel ? (
                <>
                  <Link href="/settings/channel" className="btn-secondary">
                    Edit Channel
                  </Link>
                  <Link href="/upload" className="btn-primary">
                    Upload Video
                  </Link>
                </>
              ) : (
                <button
                  className={`btn-follow ${channel.isFollowing ? 'following' : ''}`}
                  onClick={handleFollow}
                  disabled={isFollowLoading}
                >
                  {isFollowLoading ? (
                    <span className="spinner" />
                  ) : channel.isFollowing ? (
                    'Following'
                  ) : (
                    'Follow'
                  )}
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="tabs-container">
        <div className="container">
          <nav className="tabs">
            <button
              className={`tab ${activeTab === 'videos' ? 'active' : ''}`}
              onClick={() => setActiveTab('videos')}
            >
              Videos
            </button>
            <button
              className={`tab ${activeTab === 'shorts' ? 'active' : ''}`}
              onClick={() => setActiveTab('shorts')}
            >
              Shorts
            </button>
            <button
              className={`tab ${activeTab === 'about' ? 'active' : ''}`}
              onClick={() => setActiveTab('about')}
            >
              About
            </button>
          </nav>
        </div>
      </div>

      {/* Content */}
      <main className="content">
        <div className="container">
          {activeTab === 'about' ? (
            <div className="about-section">
              <div className="about-card">
                <h2>About</h2>
                <p className="bio">
                  {channel.user.bio || 'No bio yet.'}
                </p>

                <div className="about-stats">
                  <div className="stat">
                    <span className="stat-value">{formatNumber(channel.followerCount)}</span>
                    <span className="stat-label">Followers</span>
                  </div>
                  <div className="stat">
                    <span className="stat-value">{channel.videos.length}</span>
                    <span className="stat-label">Videos</span>
                  </div>
                  <div className="stat">
                    <span className="stat-value">{formatNumber(channel.totalViews)}</span>
                    <span className="stat-label">Total Views</span>
                  </div>
                </div>

                {channel.user.created_at && (
                  <div className="joined-date">
                    Joined {formatDate(channel.user.created_at)}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <>
              {filteredVideos.length === 0 ? (
                <div className="empty-state">
                  <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <polygon points="23 7 16 12 23 17 23 7" />
                    <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
                  </svg>
                  <h3>No {activeTab} yet</h3>
                  <p>This channel hasn't uploaded any {activeTab} yet.</p>
                </div>
              ) : (
                <div className="video-grid">
                  {filteredVideos.map(video => (
                    <article key={video.id} className="video-card">
                      <Link href={`/watch/${video.id}`} className="thumbnail">
                        <img
                          src={video.thumbnail_url || '/placeholder-thumbnail.jpg'}
                          alt={video.title}
                          loading="lazy"
                        />
                        <span className="duration">{formatDuration(video.duration_seconds)}</span>

                        {video.monetization_type === 'PAID' && video.ticket_price && (
                          <span className="badge paid">${video.ticket_price.toFixed(2)}</span>
                        )}

                        {video.made_with_studio && (
                          <span className="badge studio" title="Made with SceneMachine Studio">
                            SM
                          </span>
                        )}
                      </Link>

                      <div className="video-info">
                        <Link href={`/watch/${video.id}`} className="video-title">
                          {video.title}
                        </Link>
                        <div className="video-meta">
                          <span>{formatNumber(video.view_count)} views</span>
                          <span className="dot">•</span>
                          <span>{formatDate(video.published_at)}</span>
                        </div>
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </main>

      <style jsx>{`
        .channel-page {
          min-height: 100vh;
          background: var(--color-bg-primary);
        }

        .banner {
          height: 200px;
          background: var(--gradient-primary);
          background-size: cover;
          background-position: center;
        }

        @media (max-width: 640px) {
          .banner {
            height: 120px;
          }
        }

        .container {
          max-width: 1280px;
          margin: 0 auto;
          padding: 0 var(--space-4);
        }

        .channel-header {
          background: var(--color-bg-secondary);
          border-bottom: 1px solid var(--color-border);
        }

        .header-content {
          display: flex;
          align-items: center;
          gap: var(--space-6);
          padding: var(--space-6) 0;
        }

        @media (max-width: 768px) {
          .header-content {
            flex-direction: column;
            text-align: center;
          }
        }

        .avatar {
          position: relative;
          flex-shrink: 0;
        }

        .avatar img {
          width: 120px;
          height: 120px;
          border-radius: 50%;
          object-fit: cover;
          border: 4px solid var(--color-bg-primary);
          margin-top: -60px;
        }

        @media (max-width: 640px) {
          .avatar img {
            width: 80px;
            height: 80px;
            margin-top: -40px;
          }
        }

        .verified-badge {
          position: absolute;
          bottom: 4px;
          right: 4px;
          width: 24px;
          height: 24px;
          background: var(--color-accent);
          color: white;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 14px;
          border: 2px solid var(--color-bg-primary);
        }

        .channel-info {
          flex: 1;
        }

        .channel-name {
          font-size: var(--text-2xl);
          margin-bottom: var(--space-1);
        }

        .channel-handle {
          color: var(--color-text-secondary);
          font-size: var(--text-sm);
          margin-bottom: var(--space-2);
        }

        .channel-stats {
          display: flex;
          align-items: center;
          gap: var(--space-2);
          font-size: var(--text-sm);
          color: var(--color-text-tertiary);
        }

        @media (max-width: 768px) {
          .channel-stats {
            justify-content: center;
            flex-wrap: wrap;
          }
        }

        .dot {
          font-size: 8px;
        }

        .header-actions {
          display: flex;
          gap: var(--space-3);
        }

        @media (max-width: 768px) {
          .header-actions {
            width: 100%;
            justify-content: center;
          }
        }

        .btn-primary,
        .btn-secondary,
        .btn-follow {
          padding: var(--space-2) var(--space-4);
          border-radius: var(--radius-md);
          font-weight: 600;
          font-size: var(--text-sm);
          transition: all var(--transition-fast);
        }

        .btn-primary {
          background: var(--gradient-primary);
          color: white;
        }

        .btn-secondary {
          background: var(--color-bg-tertiary);
          border: 1px solid var(--color-border);
          color: var(--color-text-primary);
        }

        .btn-follow {
          min-width: 100px;
          background: var(--color-accent);
          color: white;
        }

        .btn-follow.following {
          background: var(--color-bg-tertiary);
          color: var(--color-text-primary);
          border: 1px solid var(--color-border);
        }

        .btn-follow:hover:not(:disabled) {
          opacity: 0.9;
        }

        .tabs-container {
          background: var(--color-bg-secondary);
          border-bottom: 1px solid var(--color-border);
        }

        .tabs {
          display: flex;
          gap: var(--space-1);
        }

        .tab {
          padding: var(--space-4) var(--space-6);
          font-weight: 500;
          color: var(--color-text-secondary);
          border-bottom: 2px solid transparent;
          transition: all var(--transition-fast);
        }

        .tab:hover {
          color: var(--color-text-primary);
        }

        .tab.active {
          color: var(--color-accent);
          border-bottom-color: var(--color-accent);
        }

        .content {
          padding: var(--space-6) 0;
        }

        /* Video Grid */
        .video-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
          gap: var(--space-6);
        }

        .video-card {
          display: flex;
          flex-direction: column;
          gap: var(--space-3);
        }

        .thumbnail {
          position: relative;
          aspect-ratio: 16 / 9;
          border-radius: var(--radius-md);
          overflow: hidden;
          background: var(--color-bg-tertiary);
        }

        .thumbnail img {
          width: 100%;
          height: 100%;
          object-fit: cover;
          transition: transform var(--transition-normal);
        }

        .thumbnail:hover img {
          transform: scale(1.05);
        }

        .duration {
          position: absolute;
          bottom: var(--space-2);
          right: var(--space-2);
          background: rgba(0, 0, 0, 0.8);
          color: white;
          font-size: var(--text-xs);
          font-weight: 500;
          padding: 2px 6px;
          border-radius: var(--radius-sm);
        }

        .badge {
          position: absolute;
          top: var(--space-2);
          font-size: var(--text-xs);
          font-weight: 600;
          padding: 2px 6px;
          border-radius: var(--radius-sm);
        }

        .badge.paid {
          left: var(--space-2);
          background: var(--color-accent);
          color: white;
        }

        .badge.studio {
          right: var(--space-2);
          background: var(--gradient-primary);
          color: white;
        }

        .video-info {
          padding: 0 var(--space-1);
        }

        .video-title {
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
          font-weight: 600;
          color: var(--color-text-primary);
          text-decoration: none;
          line-height: 1.3;
          margin-bottom: var(--space-1);
        }

        .video-title:hover {
          color: var(--color-accent);
        }

        .video-meta {
          display: flex;
          align-items: center;
          gap: var(--space-1);
          font-size: var(--text-sm);
          color: var(--color-text-tertiary);
        }

        /* Empty State */
        .empty-state {
          text-align: center;
          padding: var(--space-16) 0;
          color: var(--color-text-tertiary);
        }

        .empty-state svg {
          margin-bottom: var(--space-4);
        }

        .empty-state h3 {
          font-size: var(--text-lg);
          color: var(--color-text-primary);
          margin-bottom: var(--space-2);
        }

        /* About Section */
        .about-section {
          max-width: 640px;
        }

        .about-card {
          background: var(--color-bg-secondary);
          border-radius: var(--radius-xl);
          padding: var(--space-6);
          border: 1px solid var(--color-border);
        }

        .about-card h2 {
          font-size: var(--text-lg);
          margin-bottom: var(--space-4);
        }

        .bio {
          color: var(--color-text-secondary);
          line-height: var(--leading-relaxed);
          margin-bottom: var(--space-6);
          white-space: pre-wrap;
        }

        .about-stats {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: var(--space-4);
          margin-bottom: var(--space-6);
          padding: var(--space-4) 0;
          border-top: 1px solid var(--color-border);
          border-bottom: 1px solid var(--color-border);
        }

        .stat {
          text-align: center;
        }

        .stat-value {
          display: block;
          font-size: var(--text-2xl);
          font-weight: 700;
          margin-bottom: var(--space-1);
        }

        .stat-label {
          font-size: var(--text-sm);
          color: var(--color-text-secondary);
        }

        .joined-date {
          font-size: var(--text-sm);
          color: var(--color-text-tertiary);
        }

        .spinner {
          width: 16px;
          height: 16px;
          border-width: 2px;
        }
      `}</style>
    </div>
  );
}
