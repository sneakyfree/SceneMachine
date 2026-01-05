/**
 * Search Page
 *
 * Search results with filters for videos, channels, and content types.
 */

'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { useFeedStore, useAuthStore } from '../stores';
import { Video } from '../lib/api-client';

type FilterType = 'all' | 'videos' | 'channels';
type SortType = 'relevance' | 'date' | 'views';
type ContentTypeFilter = Video['content_type'] | 'ALL';

interface Filter {
  type: FilterType;
  contentType: ContentTypeFilter;
  duration: 'any' | 'short' | 'medium' | 'long';
  uploadDate: 'any' | 'today' | 'week' | 'month' | 'year';
  sort: SortType;
}

const CONTENT_TYPES: { value: ContentTypeFilter; label: string }[] = [
  { value: 'ALL', label: 'All Types' },
  { value: 'FILM', label: 'Films' },
  { value: 'SHORT', label: 'Short Films' },
  { value: 'SERIES', label: 'Series' },
  { value: 'ANIMATION', label: 'Animation' },
  { value: 'MUSIC_VIDEO', label: 'Music Videos' },
  { value: 'CLIP', label: 'Clips' },
];

const DURATION_OPTIONS = [
  { value: 'any', label: 'Any duration' },
  { value: 'short', label: 'Under 4 minutes' },
  { value: 'medium', label: '4-20 minutes' },
  { value: 'long', label: 'Over 20 minutes' },
];

const UPLOAD_DATE_OPTIONS = [
  { value: 'any', label: 'Any time' },
  { value: 'today', label: 'Today' },
  { value: 'week', label: 'This week' },
  { value: 'month', label: 'This month' },
  { value: 'year', label: 'This year' },
];

const SORT_OPTIONS = [
  { value: 'relevance', label: 'Relevance' },
  { value: 'date', label: 'Upload date' },
  { value: 'views', label: 'View count' },
];

export default function SearchPage() {
  const router = useRouter();
  const { q: query } = router.query;
  const { user } = useAuthStore();
  const { searchResults, searchQuery, searchLoading, search } = useFeedStore();

  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<Filter>({
    type: 'all',
    contentType: 'ALL',
    duration: 'any',
    uploadDate: 'any',
    sort: 'relevance',
  });

  useEffect(() => {
    if (query && typeof query === 'string') {
      search(query);
    }
  }, [query, search]);

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
      return `${(views / 1000000).toFixed(1)}M views`;
    }
    if (views >= 1000) {
      return `${(views / 1000).toFixed(1)}K views`;
    }
    return `${views} views`;
  };

  const formatDate = (dateStr: string | null): string => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
    if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
    return `${Math.floor(diffDays / 365)} years ago`;
  };

  // Apply client-side filters
  const filteredResults = searchResults.filter(video => {
    // Content type filter
    if (filters.contentType !== 'ALL' && video.content_type !== filters.contentType) {
      return false;
    }

    // Duration filter
    if (filters.duration === 'short' && video.duration_seconds >= 240) return false;
    if (filters.duration === 'medium' && (video.duration_seconds < 240 || video.duration_seconds >= 1200)) return false;
    if (filters.duration === 'long' && video.duration_seconds < 1200) return false;

    // Upload date filter
    if (filters.uploadDate !== 'any' && video.published_at) {
      const date = new Date(video.published_at);
      const now = new Date();
      const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

      if (filters.uploadDate === 'today' && diffDays > 0) return false;
      if (filters.uploadDate === 'week' && diffDays > 7) return false;
      if (filters.uploadDate === 'month' && diffDays > 30) return false;
      if (filters.uploadDate === 'year' && diffDays > 365) return false;
    }

    return true;
  }).sort((a, b) => {
    // Sort
    if (filters.sort === 'date') {
      return new Date(b.published_at || 0).getTime() - new Date(a.published_at || 0).getTime();
    }
    if (filters.sort === 'views') {
      return b.view_count - a.view_count;
    }
    // Relevance - keep original order
    return 0;
  });

  return (
    <div className="search-page">
      {/* Header */}
      <header className="header">
        <Link href="/" className="logo">
          SceneMachine
        </Link>

        <form
          className="search-form"
          onSubmit={(e) => {
            e.preventDefault();
            const form = e.target as HTMLFormElement;
            const input = form.querySelector('input') as HTMLInputElement;
            if (input.value.trim()) {
              router.push(`/search?q=${encodeURIComponent(input.value.trim())}`);
            }
          }}
        >
          <input
            type="search"
            placeholder="Search videos..."
            defaultValue={query || ''}
            autoFocus
          />
          <button type="submit">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8" />
              <path d="M21 21l-4.35-4.35" />
            </svg>
          </button>
        </form>

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
          {/* Results Header */}
          <div className="results-header">
            <div className="results-info">
              {query && (
                <h1>
                  Search results for "<span className="query">{query}</span>"
                </h1>
              )}
              {!searchLoading && (
                <span className="count">{filteredResults.length} results</span>
              )}
            </div>

            <button
              className="filter-toggle"
              onClick={() => setShowFilters(!showFilters)}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
              </svg>
              Filters
              {showFilters && <span className="active-indicator" />}
            </button>
          </div>

          {/* Filters Panel */}
          {showFilters && (
            <div className="filters-panel">
              <div className="filter-group">
                <label>Type</label>
                <div className="filter-options">
                  {(['all', 'videos', 'channels'] as FilterType[]).map(type => (
                    <button
                      key={type}
                      className={`filter-btn ${filters.type === type ? 'active' : ''}`}
                      onClick={() => setFilters(f => ({ ...f, type }))}
                    >
                      {type.charAt(0).toUpperCase() + type.slice(1)}
                    </button>
                  ))}
                </div>
              </div>

              <div className="filter-group">
                <label>Content Type</label>
                <select
                  value={filters.contentType}
                  onChange={(e) => setFilters(f => ({ ...f, contentType: e.target.value as ContentTypeFilter }))}
                >
                  {CONTENT_TYPES.map(ct => (
                    <option key={ct.value} value={ct.value}>{ct.label}</option>
                  ))}
                </select>
              </div>

              <div className="filter-group">
                <label>Duration</label>
                <select
                  value={filters.duration}
                  onChange={(e) => setFilters(f => ({ ...f, duration: e.target.value as Filter['duration'] }))}
                >
                  {DURATION_OPTIONS.map(opt => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>

              <div className="filter-group">
                <label>Upload Date</label>
                <select
                  value={filters.uploadDate}
                  onChange={(e) => setFilters(f => ({ ...f, uploadDate: e.target.value as Filter['uploadDate'] }))}
                >
                  {UPLOAD_DATE_OPTIONS.map(opt => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>

              <div className="filter-group">
                <label>Sort By</label>
                <select
                  value={filters.sort}
                  onChange={(e) => setFilters(f => ({ ...f, sort: e.target.value as SortType }))}
                >
                  {SORT_OPTIONS.map(opt => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>
            </div>
          )}

          {/* Results */}
          {searchLoading ? (
            <div className="loading-state">
              {[1, 2, 3, 4, 5].map(i => (
                <div key={i} className="skeleton-result">
                  <div className="skeleton thumbnail" />
                  <div className="skeleton-content">
                    <div className="skeleton title" />
                    <div className="skeleton meta" />
                    <div className="skeleton description" />
                  </div>
                </div>
              ))}
            </div>
          ) : filteredResults.length === 0 ? (
            <div className="empty-state">
              <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <circle cx="11" cy="11" r="8" />
                <path d="M21 21l-4.35-4.35" />
              </svg>
              <h2>No results found</h2>
              <p>
                Try different keywords or remove search filters
              </p>
            </div>
          ) : (
            <div className="results-list">
              {filteredResults.map((video: Video) => (
                <article key={video.id} className="result-item">
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
                  </Link>

                  <div className="result-content">
                    <Link href={`/watch/${video.id}`} className="result-title">
                      {video.title}
                    </Link>

                    <div className="result-meta">
                      <span>{formatViews(video.view_count)}</span>
                      <span className="dot">•</span>
                      <span>{formatDate(video.published_at)}</span>
                    </div>

                    <Link href={`/channel/${video.creator_id}`} className="creator">
                      <img
                        src={video.creator?.avatar_url || '/default-avatar.jpg'}
                        alt={video.creator?.display_name}
                      />
                      <span>{video.creator?.display_name || video.creator?.username}</span>
                      {video.creator?.is_verified && <span className="verified">✓</span>}
                    </Link>

                    {video.description && (
                      <p className="result-description">
                        {video.description.slice(0, 150)}
                        {video.description.length > 150 && '...'}
                      </p>
                    )}

                    {video.tags && video.tags.length > 0 && (
                      <div className="result-tags">
                        {video.tags.slice(0, 3).map((tag: string) => (
                          <Link
                            key={tag}
                            href={`/search?q=${encodeURIComponent(tag)}`}
                            className="tag"
                          >
                            #{tag}
                          </Link>
                        ))}
                      </div>
                    )}
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>
      </main>

      <style jsx>{`
        .search-page {
          min-height: 100vh;
          background: var(--color-bg-primary);
        }

        .header {
          display: flex;
          align-items: center;
          gap: var(--space-4);
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
          flex-shrink: 0;
        }

        .search-form {
          flex: 1;
          max-width: 640px;
          display: flex;
          background: var(--color-bg-tertiary);
          border: 1px solid var(--color-border);
          border-radius: var(--radius-full);
          overflow: hidden;
        }

        .search-form input {
          flex: 1;
          padding: var(--space-3) var(--space-4);
          background: transparent;
          border: none;
          color: var(--color-text-primary);
          font-size: var(--text-base);
        }

        .search-form input:focus {
          outline: none;
        }

        .search-form button {
          padding: var(--space-3) var(--space-4);
          color: var(--color-text-secondary);
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
          max-width: 1024px;
          margin: 0 auto;
          padding: var(--space-6);
        }

        .results-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: var(--space-6);
        }

        .results-info h1 {
          font-size: var(--text-lg);
          font-weight: 500;
          margin-bottom: var(--space-1);
        }

        .query {
          color: var(--color-accent);
        }

        .count {
          font-size: var(--text-sm);
          color: var(--color-text-tertiary);
        }

        .filter-toggle {
          display: flex;
          align-items: center;
          gap: var(--space-2);
          padding: var(--space-2) var(--space-4);
          background: var(--color-bg-secondary);
          border: 1px solid var(--color-border);
          border-radius: var(--radius-md);
          color: var(--color-text-primary);
          font-weight: 500;
          position: relative;
        }

        .active-indicator {
          position: absolute;
          top: -2px;
          right: -2px;
          width: 8px;
          height: 8px;
          background: var(--color-accent);
          border-radius: 50%;
        }

        /* Filters Panel */
        .filters-panel {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
          gap: var(--space-4);
          padding: var(--space-4);
          background: var(--color-bg-secondary);
          border: 1px solid var(--color-border);
          border-radius: var(--radius-lg);
          margin-bottom: var(--space-6);
        }

        .filter-group label {
          display: block;
          font-size: var(--text-xs);
          font-weight: 500;
          color: var(--color-text-secondary);
          margin-bottom: var(--space-2);
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }

        .filter-group select {
          width: 100%;
          padding: var(--space-2) var(--space-3);
          background: var(--color-bg-tertiary);
          border: 1px solid var(--color-border);
          border-radius: var(--radius-md);
          color: var(--color-text-primary);
          font-size: var(--text-sm);
        }

        .filter-options {
          display: flex;
          gap: var(--space-1);
        }

        .filter-btn {
          padding: var(--space-2) var(--space-3);
          background: var(--color-bg-tertiary);
          border: 1px solid var(--color-border);
          border-radius: var(--radius-md);
          color: var(--color-text-secondary);
          font-size: var(--text-sm);
          transition: all var(--transition-fast);
        }

        .filter-btn.active {
          background: var(--color-accent);
          border-color: var(--color-accent);
          color: white;
        }

        /* Results List */
        .results-list {
          display: flex;
          flex-direction: column;
          gap: var(--space-4);
        }

        .result-item {
          display: flex;
          gap: var(--space-4);
          padding: var(--space-4);
          background: var(--color-bg-secondary);
          border-radius: var(--radius-lg);
          border: 1px solid var(--color-border);
        }

        @media (max-width: 640px) {
          .result-item {
            flex-direction: column;
          }
        }

        .thumbnail {
          position: relative;
          flex-shrink: 0;
          width: 320px;
          aspect-ratio: 16 / 9;
          border-radius: var(--radius-md);
          overflow: hidden;
          background: var(--color-bg-tertiary);
        }

        @media (max-width: 640px) {
          .thumbnail {
            width: 100%;
          }
        }

        .thumbnail img {
          width: 100%;
          height: 100%;
          object-fit: cover;
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
          left: var(--space-2);
          font-size: var(--text-xs);
          font-weight: 600;
          padding: 2px 6px;
          border-radius: var(--radius-sm);
        }

        .badge.paid {
          background: var(--color-accent);
          color: white;
        }

        .result-content {
          flex: 1;
          min-width: 0;
        }

        .result-title {
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
          font-weight: 600;
          font-size: var(--text-lg);
          color: var(--color-text-primary);
          text-decoration: none;
          line-height: 1.3;
          margin-bottom: var(--space-2);
        }

        .result-title:hover {
          color: var(--color-accent);
        }

        .result-meta {
          display: flex;
          align-items: center;
          gap: var(--space-2);
          font-size: var(--text-sm);
          color: var(--color-text-tertiary);
          margin-bottom: var(--space-2);
        }

        .dot {
          font-size: 8px;
        }

        .creator {
          display: flex;
          align-items: center;
          gap: var(--space-2);
          margin-bottom: var(--space-2);
          text-decoration: none;
        }

        .creator img {
          width: 24px;
          height: 24px;
          border-radius: 50%;
          object-fit: cover;
        }

        .creator span {
          font-size: var(--text-sm);
          color: var(--color-text-secondary);
        }

        .creator:hover span {
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

        .result-description {
          font-size: var(--text-sm);
          color: var(--color-text-tertiary);
          line-height: 1.5;
          margin-bottom: var(--space-2);
        }

        .result-tags {
          display: flex;
          flex-wrap: wrap;
          gap: var(--space-2);
        }

        .tag {
          font-size: var(--text-xs);
          color: var(--color-text-secondary);
          background: var(--color-bg-tertiary);
          padding: var(--space-1) var(--space-2);
          border-radius: var(--radius-sm);
        }

        .tag:hover {
          color: var(--color-accent);
          background: var(--color-accent-light);
        }

        /* Loading State */
        .loading-state {
          display: flex;
          flex-direction: column;
          gap: var(--space-4);
        }

        .skeleton-result {
          display: flex;
          gap: var(--space-4);
          padding: var(--space-4);
          background: var(--color-bg-secondary);
          border-radius: var(--radius-lg);
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
          width: 320px;
          aspect-ratio: 16 / 9;
          flex-shrink: 0;
        }

        .skeleton-content {
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: var(--space-2);
        }

        .skeleton.title {
          height: 24px;
          width: 80%;
        }

        .skeleton.meta {
          height: 16px;
          width: 50%;
        }

        .skeleton.description {
          height: 40px;
          width: 100%;
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

        .empty-state h2 {
          font-size: var(--text-xl);
          color: var(--color-text-primary);
          margin-bottom: var(--space-2);
        }

        @media (max-width: 640px) {
          .header {
            padding: var(--space-3);
          }

          .logo {
            display: none;
          }

          .container {
            padding: var(--space-4);
          }

          .results-header {
            flex-direction: column;
            align-items: flex-start;
            gap: var(--space-3);
          }

          .filter-toggle {
            width: 100%;
            justify-content: center;
          }

          .filters-panel {
            grid-template-columns: 1fr 1fr;
          }

          .skeleton.thumbnail {
            width: 100%;
          }
        }
      `}</style>
    </div>
  );
}
