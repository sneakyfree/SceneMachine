/**
 * Dashboard Content Management Page
 *
 * Manage all uploaded videos with bulk actions.
 */

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { api, Video } from '../../lib/api-client';
import { Button, Badge, Modal, Select, Input, EmptyState, Tabs } from '../../components/ui';

type VideoFilter = 'all' | 'published' | 'unlisted' | 'private' | 'processing';
type SortOption = 'newest' | 'oldest' | 'views' | 'title';

export default function ContentManagementPage() {
  const router = useRouter();
  const [videos, setVideos] = useState<Video[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState<VideoFilter>('all');
  const [sort, setSort] = useState<SortOption>('newest');
  const [search, setSearch] = useState('');
  const [selectedVideos, setSelectedVideos] = useState<Set<string>>(new Set());
  const [deleteModal, setDeleteModal] = useState<{ open: boolean; videoId?: string; bulk?: boolean }>({
    open: false,
  });
  const [isDeleting, setIsDeleting] = useState(false);

  const loadVideos = useCallback(async () => {
    try {
      setIsLoading(true);
      // In a real app, this would accept filter/sort params
      const response = await api.getVideosByCreator('me', 1, 100);
      setVideos(response.items);
    } catch (error) {
      console.error('Failed to load videos:', error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadVideos();
  }, [loadVideos]);

  // Filter and sort videos
  const filteredVideos = videos
    .filter((video) => {
      if (filter === 'all') return true;
      if (filter === 'published') return video.status === 'PUBLISHED';
      if (filter === 'unlisted') return video.status === 'UNLISTED';
      if (filter === 'private') return video.status === 'PRIVATE';
      if (filter === 'processing') return video.status === 'PROCESSING' || video.status === 'UPLOADING';
      return true;
    })
    .filter((video) => {
      if (!search) return true;
      return video.title.toLowerCase().includes(search.toLowerCase());
    })
    .sort((a, b) => {
      switch (sort) {
        case 'oldest':
          return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
        case 'views':
          return b.view_count - a.view_count;
        case 'title':
          return a.title.localeCompare(b.title);
        default: // newest
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      }
    });

  const toggleSelect = (videoId: string) => {
    setSelectedVideos((prev) => {
      const next = new Set(prev);
      if (next.has(videoId)) {
        next.delete(videoId);
      } else {
        next.add(videoId);
      }
      return next;
    });
  };

  const selectAll = () => {
    if (selectedVideos.size === filteredVideos.length) {
      setSelectedVideos(new Set());
    } else {
      setSelectedVideos(new Set(filteredVideos.map((v) => v.id)));
    }
  };

  const handleDelete = async () => {
    try {
      setIsDeleting(true);
      if (deleteModal.bulk) {
        await Promise.all(Array.from(selectedVideos).map((id) => api.deleteVideo(id)));
        setVideos((prev) => prev.filter((v) => !selectedVideos.has(v.id)));
        setSelectedVideos(new Set());
      } else if (deleteModal.videoId) {
        await api.deleteVideo(deleteModal.videoId);
        setVideos((prev) => prev.filter((v) => v.id !== deleteModal.videoId));
      }
      setDeleteModal({ open: false });
    } catch (error) {
      console.error('Failed to delete:', error);
    } finally {
      setIsDeleting(false);
    }
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const getStatusBadge = (status: Video['status']) => {
    switch (status) {
      case 'PUBLISHED':
        return <Badge variant="success">Published</Badge>;
      case 'UNLISTED':
        return <Badge variant="info">Unlisted</Badge>;
      case 'PRIVATE':
        return <Badge variant="default">Private</Badge>;
      case 'PROCESSING':
      case 'UPLOADING':
        return <Badge variant="warning">Processing</Badge>;
      case 'READY':
        return <Badge variant="info">Ready</Badge>;
      case 'FAILED':
        return <Badge variant="error">Failed</Badge>;
      default:
        return <Badge>{status}</Badge>;
    }
  };

  const tabs = [
    { id: 'all', label: 'All', badge: videos.length },
    { id: 'published', label: 'Published', badge: videos.filter((v) => v.status === 'PUBLISHED').length },
    { id: 'unlisted', label: 'Unlisted', badge: videos.filter((v) => v.status === 'UNLISTED').length },
    { id: 'private', label: 'Private', badge: videos.filter((v) => v.status === 'PRIVATE').length },
    { id: 'processing', label: 'Processing', badge: videos.filter((v) => ['PROCESSING', 'UPLOADING'].includes(v.status)).length },
  ];

  return (
    <>
      <div className="content-page">
        {/* Sidebar */}
        <aside className="sidebar">
          <nav className="sidebar-nav">
            <Link href="/dashboard" className="nav-item">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="3" width="7" height="7" />
                <rect x="14" y="3" width="7" height="7" />
                <rect x="14" y="14" width="7" height="7" />
                <rect x="3" y="14" width="7" height="7" />
              </svg>
              Dashboard
            </Link>
            <Link href="/dashboard/content" className="nav-item active">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polygon points="23 7 16 12 23 17 23 7" />
                <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
              </svg>
              Content
            </Link>
            <Link href="/dashboard/comments" className="nav-item">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
              Comments
            </Link>
            <Link href="/dashboard/earnings" className="nav-item">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="12" y1="1" x2="12" y2="23" />
                <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
              </svg>
              Earnings
            </Link>
          </nav>
        </aside>

        {/* Main Content */}
        <main className="main-content">
          <header className="page-header">
            <div className="header-left">
              <h1>Content</h1>
              <p className="subtitle">{videos.length} videos</p>
            </div>
            <Button onClick={() => router.push('/upload')}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              Upload Video
            </Button>
          </header>

          {/* Filters */}
          <div className="filters">
            <Tabs
              tabs={tabs}
              activeTab={filter}
              onTabChange={(id) => setFilter(id as VideoFilter)}
              variant="underline"
            />

            <div className="filter-controls">
              <Input
                placeholder="Search videos..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                leftIcon={
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="11" cy="11" r="8" />
                    <line x1="21" y1="21" x2="16.65" y2="16.65" />
                  </svg>
                }
              />
              <Select
                value={sort}
                onChange={(e) => setSort(e.target.value as SortOption)}
                options={[
                  { value: 'newest', label: 'Newest first' },
                  { value: 'oldest', label: 'Oldest first' },
                  { value: 'views', label: 'Most views' },
                  { value: 'title', label: 'Title A-Z' },
                ]}
              />
            </div>
          </div>

          {/* Bulk Actions */}
          {selectedVideos.size > 0 && (
            <div className="bulk-actions">
              <span className="selected-count">{selectedVideos.size} selected</span>
              <Button
                variant="danger"
                size="sm"
                onClick={() => setDeleteModal({ open: true, bulk: true })}
              >
                Delete Selected
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setSelectedVideos(new Set())}>
                Cancel
              </Button>
            </div>
          )}

          {/* Video List */}
          {isLoading ? (
            <div className="loading">Loading videos...</div>
          ) : filteredVideos.length === 0 ? (
            <EmptyState
              icon={
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <polygon points="23 7 16 12 23 17 23 7" />
                  <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
                </svg>
              }
              title="No videos found"
              description={search ? 'Try a different search term' : 'Upload your first video to get started'}
              action={!search ? { label: 'Upload Video', onClick: () => router.push('/upload') } : undefined}
            />
          ) : (
            <div className="video-list">
              <div className="list-header">
                <label className="checkbox-cell">
                  <input
                    type="checkbox"
                    checked={selectedVideos.size === filteredVideos.length && filteredVideos.length > 0}
                    onChange={selectAll}
                  />
                </label>
                <span className="col-video">Video</span>
                <span className="col-status">Status</span>
                <span className="col-date">Date</span>
                <span className="col-views">Views</span>
                <span className="col-likes">Likes</span>
                <span className="col-comments">Comments</span>
                <span className="col-actions" />
              </div>

              {filteredVideos.map((video) => (
                <div key={video.id} className="video-row">
                  <label className="checkbox-cell">
                    <input
                      type="checkbox"
                      checked={selectedVideos.has(video.id)}
                      onChange={() => toggleSelect(video.id)}
                    />
                  </label>

                  <div className="col-video">
                    <div className="video-thumbnail">
                      {video.thumbnail_url ? (
                        <img src={video.thumbnail_url} alt="" />
                      ) : (
                        <div className="thumbnail-placeholder">
                          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <polygon points="5 3 19 12 5 21 5 3" />
                          </svg>
                        </div>
                      )}
                      <span className="duration">{formatDuration(video.duration_seconds)}</span>
                    </div>
                    <div className="video-info">
                      <Link href={`/watch/${video.id}`} className="video-title">
                        {video.title}
                      </Link>
                      <p className="video-description">
                        {video.description?.slice(0, 80)}
                        {video.description && video.description.length > 80 ? '...' : ''}
                      </p>
                    </div>
                  </div>

                  <div className="col-status">{getStatusBadge(video.status)}</div>
                  <div className="col-date">{formatDate(video.created_at)}</div>
                  <div className="col-views">{video.view_count.toLocaleString()}</div>
                  <div className="col-likes">{video.like_count.toLocaleString()}</div>
                  <div className="col-comments">{video.comment_count.toLocaleString()}</div>

                  <div className="col-actions">
                    <button
                      className="action-btn"
                      onClick={() => router.push(`/dashboard/video/${video.id}/edit`)}
                      title="Edit"
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                      </svg>
                    </button>
                    <button
                      className="action-btn"
                      onClick={() => router.push(`/dashboard/video/${video.id}/analytics`)}
                      title="Analytics"
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <line x1="18" y1="20" x2="18" y2="10" />
                        <line x1="12" y1="20" x2="12" y2="4" />
                        <line x1="6" y1="20" x2="6" y2="14" />
                      </svg>
                    </button>
                    <button
                      className="action-btn danger"
                      onClick={() => setDeleteModal({ open: true, videoId: video.id })}
                      title="Delete"
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <polyline points="3 6 5 6 21 6" />
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                      </svg>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </main>
      </div>

      {/* Delete Modal */}
      <Modal
        isOpen={deleteModal.open}
        onClose={() => setDeleteModal({ open: false })}
        title={deleteModal.bulk ? 'Delete Videos' : 'Delete Video'}
        size="sm"
        footer={
          <>
            <Button variant="ghost" onClick={() => setDeleteModal({ open: false })}>
              Cancel
            </Button>
            <Button variant="danger" onClick={handleDelete} loading={isDeleting}>
              Delete
            </Button>
          </>
        }
      >
        <p>
          {deleteModal.bulk
            ? `Are you sure you want to delete ${selectedVideos.size} videos? This action cannot be undone.`
            : 'Are you sure you want to delete this video? This action cannot be undone.'}
        </p>
      </Modal>

      <style jsx>{`
        .content-page {
          display: flex;
          min-height: 100vh;
          background: var(--color-bg-primary);
        }

        .sidebar {
          width: 240px;
          background: var(--color-bg-secondary);
          border-right: 1px solid var(--color-border);
          padding: 1.5rem 1rem;
        }

        .sidebar-nav {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
        }

        .sidebar-nav :global(.nav-item) {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          padding: 0.75rem 1rem;
          border-radius: var(--radius-md);
          color: var(--color-text-secondary);
          text-decoration: none;
          font-weight: 500;
          transition: all var(--transition-fast);
        }

        .sidebar-nav :global(.nav-item:hover) {
          background: var(--color-bg-tertiary);
          color: var(--color-text-primary);
        }

        .sidebar-nav :global(.nav-item.active) {
          background: var(--color-accent);
          color: white;
        }

        .main-content {
          flex: 1;
          padding: 2rem;
        }

        .page-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 2rem;
        }

        .page-header h1 {
          font-size: var(--text-2xl);
          margin: 0;
        }

        .subtitle {
          color: var(--color-text-secondary);
          margin: 0.25rem 0 0;
        }

        .filters {
          margin-bottom: 1.5rem;
        }

        .filter-controls {
          display: flex;
          gap: 1rem;
          margin-top: 1rem;
        }

        .filter-controls :global(.input-wrapper) {
          flex: 1;
          max-width: 300px;
        }

        .filter-controls :global(.select-wrapper) {
          width: 180px;
        }

        .bulk-actions {
          display: flex;
          align-items: center;
          gap: 1rem;
          padding: 0.75rem 1rem;
          background: var(--color-bg-secondary);
          border-radius: var(--radius-md);
          margin-bottom: 1rem;
        }

        .selected-count {
          font-weight: 500;
        }

        .loading {
          text-align: center;
          padding: 4rem;
          color: var(--color-text-secondary);
        }

        .video-list {
          border: 1px solid var(--color-border);
          border-radius: var(--radius-lg);
          overflow: hidden;
        }

        .list-header {
          display: grid;
          grid-template-columns: 40px 1fr 100px 100px 80px 80px 100px 100px;
          align-items: center;
          gap: 1rem;
          padding: 0.75rem 1rem;
          background: var(--color-bg-secondary);
          border-bottom: 1px solid var(--color-border);
          font-size: var(--text-sm);
          font-weight: 500;
          color: var(--color-text-secondary);
        }

        .video-row {
          display: grid;
          grid-template-columns: 40px 1fr 100px 100px 80px 80px 100px 100px;
          align-items: center;
          gap: 1rem;
          padding: 1rem;
          border-bottom: 1px solid var(--color-border);
          transition: background-color var(--transition-fast);
        }

        .video-row:last-child {
          border-bottom: none;
        }

        .video-row:hover {
          background: var(--color-bg-secondary);
        }

        .checkbox-cell {
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .checkbox-cell input {
          width: 1rem;
          height: 1rem;
          cursor: pointer;
        }

        .col-video {
          display: flex;
          gap: 1rem;
          align-items: center;
        }

        .video-thumbnail {
          position: relative;
          width: 120px;
          height: 68px;
          border-radius: var(--radius-sm);
          overflow: hidden;
          background: var(--color-bg-tertiary);
          flex-shrink: 0;
        }

        .video-thumbnail img {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }

        .thumbnail-placeholder {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 100%;
          height: 100%;
          color: var(--color-text-tertiary);
        }

        .duration {
          position: absolute;
          bottom: 4px;
          right: 4px;
          background: rgba(0, 0, 0, 0.8);
          padding: 0.125rem 0.375rem;
          border-radius: var(--radius-sm);
          font-size: var(--text-xs);
          color: white;
        }

        .video-info {
          flex: 1;
          min-width: 0;
        }

        .video-title {
          font-weight: 500;
          color: var(--color-text-primary);
          text-decoration: none;
          display: -webkit-box;
          -webkit-line-clamp: 1;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }

        .video-title:hover {
          text-decoration: underline;
        }

        .video-description {
          color: var(--color-text-tertiary);
          font-size: var(--text-sm);
          margin: 0.25rem 0 0;
          display: -webkit-box;
          -webkit-line-clamp: 1;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }

        .col-status,
        .col-date,
        .col-views,
        .col-likes,
        .col-comments {
          font-size: var(--text-sm);
          color: var(--color-text-secondary);
        }

        .col-actions {
          display: flex;
          gap: 0.5rem;
          justify-content: flex-end;
        }

        .action-btn {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 2rem;
          height: 2rem;
          background: transparent;
          border: none;
          border-radius: var(--radius-sm);
          color: var(--color-text-secondary);
          cursor: pointer;
          transition: all var(--transition-fast);
        }

        .action-btn:hover {
          background: var(--color-bg-tertiary);
          color: var(--color-text-primary);
        }

        .action-btn.danger:hover {
          color: var(--color-error);
        }

        @media (max-width: 1024px) {
          .sidebar {
            display: none;
          }

          .list-header,
          .video-row {
            grid-template-columns: 40px 1fr 100px 80px 80px;
          }

          .col-date,
          .col-comments,
          .col-likes {
            display: none;
          }
        }

        @media (max-width: 640px) {
          .main-content {
            padding: 1rem;
          }

          .list-header,
          .video-row {
            grid-template-columns: 1fr 80px 80px;
          }

          .checkbox-cell,
          .col-status {
            display: none;
          }

          .video-thumbnail {
            width: 80px;
            height: 45px;
          }
        }
      `}</style>
    </>
  );
}
