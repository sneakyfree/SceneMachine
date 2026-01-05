/**
 * Browse Page
 *
 * Browse content by categories, genres, and content types.
 */

'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { useAuthStore } from '../stores';
import { apiClient, Video } from '../lib/api-client';

interface Category {
  id: string;
  name: string;
  icon: string;
  color: string;
  count?: number;
}

const CONTENT_CATEGORIES: Category[] = [
  { id: 'FILM', name: 'Films', icon: '🎬', color: '#6366f1' },
  { id: 'SHORT', name: 'Short Films', icon: '🎞️', color: '#8b5cf6' },
  { id: 'SERIES', name: 'Series', icon: '📺', color: '#ec4899' },
  { id: 'ANIMATION', name: 'Animation', icon: '✨', color: '#f59e0b' },
  { id: 'MUSIC_VIDEO', name: 'Music Videos', icon: '🎵', color: '#10b981' },
  { id: 'CLIP', name: 'Clips & Trailers', icon: '🎥', color: '#3b82f6' },
];

const GENRE_TAGS = [
  'Drama', 'Comedy', 'Horror', 'Thriller', 'Sci-Fi', 'Fantasy',
  'Documentary', 'Romance', 'Action', 'Mystery', 'Indie', 'Experimental',
  'Art House', 'Coming of Age', 'Noir', 'Western', 'Musical', 'Slice of Life',
];

export default function BrowsePage() {
  const router = useRouter();
  const { type, genre } = router.query;
  const { user } = useAuthStore();

  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedGenre, setSelectedGenre] = useState<string | null>(null);
  const [videos, setVideos] = useState<Video[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [categoryCounts, setCategoryCounts] = useState<Record<string, number>>({});

  // Sync with URL params
  useEffect(() => {
    if (type && typeof type === 'string') {
      setSelectedCategory(type);
    }
    if (genre && typeof genre === 'string') {
      setSelectedGenre(genre);
    }
  }, [type, genre]);

  // Load category counts on mount
  useEffect(() => {
    const loadCategoryCounts = async () => {
      try {
        const categories = await apiClient.getCategories();
        const counts: Record<string, number> = {};
        categories.forEach((cat) => {
          counts[cat.id] = cat.count;
        });
        setCategoryCounts(counts);
      } catch (err) {
        console.error('Failed to load category counts:', err);
      }
    };
    loadCategoryCounts();
  }, []);

  // Load videos when category or genre changes
  useEffect(() => {
    const loadVideos = async () => {
      if (!selectedCategory && !selectedGenre) {
        setVideos([]);
        return;
      }

      setIsLoading(true);
      try {
        let results: Video[] = [];
        if (selectedCategory) {
          const response = await apiClient.getVideosByCategory(
            selectedCategory as Video['content_type']
          );
          results = response.items;
        } else if (selectedGenre) {
          const response = await apiClient.search(selectedGenre);
          results = response.items;
        }
        setVideos(results);
      } catch (err) {
        console.error('Failed to load videos:', err);
        setVideos([]);
      } finally {
        setIsLoading(false);
      }
    };

    loadVideos();
  }, [selectedCategory, selectedGenre]);

  const handleCategorySelect = (categoryId: string) => {
    if (selectedCategory === categoryId) {
      setSelectedCategory(null);
      router.push('/browse', undefined, { shallow: true });
    } else {
      setSelectedCategory(categoryId);
      setSelectedGenre(null);
      router.push(`/browse?type=${categoryId}`, undefined, { shallow: true });
    }
  };

  const handleGenreSelect = (genreName: string) => {
    if (selectedGenre === genreName) {
      setSelectedGenre(null);
      router.push('/browse', undefined, { shallow: true });
    } else {
      setSelectedGenre(genreName);
      setSelectedCategory(null);
      router.push(`/browse?genre=${encodeURIComponent(genreName)}`, undefined, { shallow: true });
    }
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

  const formatViews = (views: number): string => {
    if (views >= 1000000) {
      return `${(views / 1000000).toFixed(1)}M`;
    }
    if (views >= 1000) {
      return `${(views / 1000).toFixed(1)}K`;
    }
    return views.toString();
  };

  const formatDate = (dateStr: string | null): string => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays}d ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
    if (diffDays < 365) return `${Math.floor(diffDays / 30)}mo ago`;
    return `${Math.floor(diffDays / 365)}y ago`;
  };

  return (
    <div className="browse-page">
      {/* Header */}
      <header className="header">
        <Link href="/" className="logo">
          SceneMachine
        </Link>

        <nav className="nav">
          <Link href="/">Home</Link>
          <Link href="/browse" className="active">Browse</Link>
          <Link href="/search">Search</Link>
        </nav>

        {user ? (
          <Link href={`/channel/${user.id}`} className="profile">
            <img src={user.avatar_url || '/default-avatar.jpg'} alt={user.display_name} />
          </Link>
        ) : (
          <Link href="/login" className="login-btn">Sign In</Link>
        )}
      </header>

      <main className="content">
        <div className="container">
          {/* Hero Section */}
          <section className="hero">
            <h1>Browse</h1>
            <p>Discover indie films by category and genre</p>
          </section>

          {/* Categories Grid */}
          <section className="categories-section">
            <h2>Content Types</h2>
            <div className="categories-grid">
              {CONTENT_CATEGORIES.map(category => (
                <button
                  key={category.id}
                  className={`category-card ${selectedCategory === category.id ? 'selected' : ''}`}
                  onClick={() => handleCategorySelect(category.id)}
                  style={{ '--category-color': category.color } as React.CSSProperties}
                >
                  <span className="category-icon">{category.icon}</span>
                  <span className="category-name">{category.name}</span>
                  {categoryCounts[category.id] !== undefined && (
                    <span className="category-count">
                      {categoryCounts[category.id]} videos
                    </span>
                  )}
                </button>
              ))}
            </div>
          </section>

          {/* Genres */}
          <section className="genres-section">
            <h2>Genres</h2>
            <div className="genres-list">
              {GENRE_TAGS.map(genreName => (
                <button
                  key={genreName}
                  className={`genre-tag ${selectedGenre === genreName ? 'selected' : ''}`}
                  onClick={() => handleGenreSelect(genreName)}
                >
                  {genreName}
                </button>
              ))}
            </div>
          </section>

          {/* Results */}
          {(selectedCategory || selectedGenre) && (
            <section className="results-section">
              <div className="results-header">
                <h2>
                  {selectedCategory
                    ? CONTENT_CATEGORIES.find(c => c.id === selectedCategory)?.name
                    : selectedGenre}
                </h2>
                <span className="results-count">{videos.length} videos</span>
              </div>

              {isLoading ? (
                <div className="video-grid">
                  {[1, 2, 3, 4, 5, 6, 7, 8].map(i => (
                    <div key={i} className="skeleton-card">
                      <div className="skeleton thumbnail" />
                      <div className="skeleton title" />
                      <div className="skeleton meta" />
                    </div>
                  ))}
                </div>
              ) : videos.length === 0 ? (
                <div className="empty-state">
                  <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <polygon points="23 7 16 12 23 17 23 7" />
                    <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
                  </svg>
                  <h3>No videos found</h3>
                  <p>There are no videos in this category yet.</p>
                </div>
              ) : (
                <div className="video-grid">
                  {videos.map(video => (
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
                        <Link href={`/channel/${video.creator_id}`} className="avatar">
                          <img
                            src={video.creator?.avatar_url || '/default-avatar.jpg'}
                            alt={video.creator?.display_name}
                          />
                        </Link>

                        <div className="details">
                          <Link href={`/watch/${video.id}`} className="video-title">
                            {video.title}
                          </Link>

                          <Link href={`/channel/${video.creator_id}`} className="creator-name">
                            {video.creator?.display_name || video.creator?.username}
                            {video.creator?.is_verified && <span className="verified">✓</span>}
                          </Link>

                          <div className="video-meta">
                            <span>{formatViews(video.view_count)} views</span>
                            <span className="dot">•</span>
                            <span>{formatDate(video.published_at)}</span>
                          </div>
                        </div>
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </section>
          )}

          {/* Featured / Trending when no selection */}
          {!selectedCategory && !selectedGenre && (
            <section className="featured-section">
              <h2>Trending Now</h2>
              <p className="section-description">
                Select a category or genre above to explore content
              </p>
            </section>
          )}
        </div>
      </main>

      <style jsx>{`
        .browse-page {
          min-height: 100vh;
          background: var(--color-bg-primary);
        }

        .header {
          display: flex;
          align-items: center;
          gap: var(--space-6);
          padding: var(--space-4) var(--space-6);
          background: var(--color-bg-secondary);
          border-bottom: 1px solid var(--color-border);
          position: sticky;
          top: 0;
          z-index: 100;
        }

        .logo {
          font-size: var(--text-xl);
          font-weight: 700;
          background: var(--gradient-primary);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          text-decoration: none;
        }

        .nav {
          flex: 1;
          display: flex;
          gap: var(--space-4);
        }

        .nav a {
          color: var(--color-text-secondary);
          font-weight: 500;
          padding: var(--space-2) var(--space-3);
          border-radius: var(--radius-md);
          transition: all var(--transition-fast);
        }

        .nav a:hover {
          color: var(--color-text-primary);
        }

        .nav a.active {
          color: var(--color-accent);
          background: var(--color-accent-light);
        }

        .profile img {
          width: 36px;
          height: 36px;
          border-radius: 50%;
          object-fit: cover;
        }

        .login-btn {
          padding: var(--space-2) var(--space-4);
          background: var(--gradient-primary);
          color: white;
          border-radius: var(--radius-md);
          font-weight: 500;
          font-size: var(--text-sm);
        }

        .container {
          max-width: 1280px;
          margin: 0 auto;
          padding: var(--space-8) var(--space-4);
        }

        /* Hero */
        .hero {
          text-align: center;
          margin-bottom: var(--space-10);
        }

        .hero h1 {
          font-size: var(--text-4xl);
          margin-bottom: var(--space-2);
        }

        .hero p {
          font-size: var(--text-lg);
          color: var(--color-text-secondary);
        }

        /* Categories */
        .categories-section,
        .genres-section,
        .results-section,
        .featured-section {
          margin-bottom: var(--space-10);
        }

        section h2 {
          font-size: var(--text-xl);
          margin-bottom: var(--space-4);
        }

        .categories-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
          gap: var(--space-4);
        }

        .category-card {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: var(--space-2);
          padding: var(--space-6);
          background: var(--color-bg-secondary);
          border: 2px solid var(--color-border);
          border-radius: var(--radius-xl);
          cursor: pointer;
          transition: all var(--transition-fast);
        }

        .category-card:hover {
          border-color: var(--category-color);
          transform: translateY(-2px);
        }

        .category-card.selected {
          border-color: var(--category-color);
          background: color-mix(in srgb, var(--category-color) 10%, transparent);
        }

        .category-icon {
          font-size: 40px;
        }

        .category-name {
          font-weight: 600;
          font-size: var(--text-lg);
        }

        .category-count {
          font-size: var(--text-sm);
          color: var(--color-text-tertiary);
        }

        /* Genres */
        .genres-list {
          display: flex;
          flex-wrap: wrap;
          gap: var(--space-2);
        }

        .genre-tag {
          padding: var(--space-2) var(--space-4);
          background: var(--color-bg-secondary);
          border: 1px solid var(--color-border);
          border-radius: var(--radius-full);
          color: var(--color-text-secondary);
          font-weight: 500;
          font-size: var(--text-sm);
          transition: all var(--transition-fast);
        }

        .genre-tag:hover {
          border-color: var(--color-accent);
          color: var(--color-accent);
        }

        .genre-tag.selected {
          background: var(--color-accent);
          border-color: var(--color-accent);
          color: white;
        }

        /* Results */
        .results-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: var(--space-6);
        }

        .results-count {
          color: var(--color-text-tertiary);
          font-size: var(--text-sm);
        }

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
          display: flex;
          gap: var(--space-3);
        }

        .avatar img {
          width: 36px;
          height: 36px;
          border-radius: 50%;
          object-fit: cover;
        }

        .details {
          flex: 1;
          min-width: 0;
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

        .creator-name {
          display: flex;
          align-items: center;
          gap: var(--space-1);
          font-size: var(--text-sm);
          color: var(--color-text-secondary);
          text-decoration: none;
          margin-bottom: var(--space-1);
        }

        .creator-name:hover {
          color: var(--color-text-primary);
        }

        .verified {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 14px;
          height: 14px;
          background: var(--color-accent);
          color: white;
          font-size: 10px;
          border-radius: 50%;
        }

        .video-meta {
          display: flex;
          align-items: center;
          gap: var(--space-1);
          font-size: var(--text-sm);
          color: var(--color-text-tertiary);
        }

        .dot {
          font-size: 8px;
        }

        /* Skeleton */
        .skeleton-card {
          display: flex;
          flex-direction: column;
          gap: var(--space-3);
        }

        .skeleton {
          background: linear-gradient(
            90deg,
            var(--color-bg-tertiary) 25%,
            var(--color-bg-elevated) 50%,
            var(--color-bg-tertiary) 75%
          );
          background-size: 200% 100%;
          animation: skeleton-pulse 1.5s ease-in-out infinite;
          border-radius: var(--radius-md);
        }

        .skeleton.thumbnail {
          aspect-ratio: 16 / 9;
        }

        .skeleton.title {
          height: 20px;
          width: 90%;
        }

        .skeleton.meta {
          height: 16px;
          width: 60%;
        }

        @keyframes skeleton-pulse {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
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

        /* Featured */
        .section-description {
          color: var(--color-text-tertiary);
        }

        @media (max-width: 768px) {
          .header {
            padding: var(--space-3) var(--space-4);
          }

          .nav {
            display: none;
          }

          .container {
            padding: var(--space-6) var(--space-4);
          }

          .hero h1 {
            font-size: var(--text-2xl);
          }

          .categories-grid {
            grid-template-columns: repeat(2, 1fr);
          }

          .category-card {
            padding: var(--space-4);
          }

          .category-icon {
            font-size: 32px;
          }

          .category-name {
            font-size: var(--text-base);
          }
        }
      `}</style>
    </div>
  );
}
