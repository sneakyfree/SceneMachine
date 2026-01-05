/**
 * Dashboard Comments Page
 *
 * Manage and respond to comments on all videos.
 */

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { api, Comment, Video } from '../../lib/api-client';
import { Button, Badge, Avatar, Tabs, Input, Modal, EmptyState } from '../../components/ui';

type CommentFilter = 'all' | 'unread' | 'held';

interface CommentWithVideo extends Comment {
  video?: Pick<Video, 'id' | 'title' | 'thumbnail_url'>;
}

export default function CommentsPage() {
  const [comments, setComments] = useState<CommentWithVideo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState<CommentFilter>('all');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [total, setTotal] = useState(0);
  const [replyModal, setReplyModal] = useState<{ open: boolean; comment?: CommentWithVideo }>({
    open: false,
  });
  const [replyText, setReplyText] = useState('');
  const [isReplying, setIsReplying] = useState(false);
  const [deleteModal, setDeleteModal] = useState<{ open: boolean; commentId?: string }>({
    open: false,
  });
  const [isDeleting, setIsDeleting] = useState(false);

  const loadComments = useCallback(async (resetPage = false) => {
    try {
      setIsLoading(true);
      const currentPage = resetPage ? 1 : page;
      if (resetPage) setPage(1);

      const response = await api.getMyVideoComments(currentPage, 20, filter);

      if (resetPage) {
        setComments(response.items as CommentWithVideo[]);
      } else {
        setComments(prev => [...prev, ...(response.items as CommentWithVideo[])]);
      }
      setTotal(response.total);
      setHasMore(response.has_more);
    } catch (error) {
      console.error('Failed to load comments:', error);
      // If API fails, set empty state
      setComments([]);
      setTotal(0);
      setHasMore(false);
    } finally {
      setIsLoading(false);
    }
  }, [page, filter]);

  useEffect(() => {
    loadComments(true);
  }, [filter]);

  const loadMore = () => {
    if (hasMore && !isLoading) {
      setPage(prev => prev + 1);
      loadComments();
    }
  };

  const handleReply = async () => {
    if (!replyModal.comment || !replyText.trim()) return;

    try {
      setIsReplying(true);
      await api.addComment(
        replyModal.comment.video_id,
        replyText,
        replyModal.comment.id
      );
      setReplyModal({ open: false });
      setReplyText('');
      // Refresh comments
      loadComments();
    } catch (error) {
      console.error('Failed to reply:', error);
    } finally {
      setIsReplying(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteModal.commentId) return;

    try {
      setIsDeleting(true);
      await api.deleteComment(deleteModal.commentId);
      setComments((prev) => prev.filter((c) => c.id !== deleteModal.commentId));
      setDeleteModal({ open: false });
    } catch (error) {
      console.error('Failed to delete:', error);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleHeart = async (comment: CommentWithVideo) => {
    try {
      if (comment.is_creator_heart) {
        await api.unheartComment(comment.id);
      } else {
        await api.heartComment(comment.id);
      }
      setComments((prev) =>
        prev.map((c) =>
          c.id === comment.id ? { ...c, is_creator_heart: !c.is_creator_heart } : c
        )
      );
    } catch (error) {
      console.error('Failed to heart comment:', error);
    }
  };

  const formatTimeAgo = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (seconds < 60) return 'just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
    return date.toLocaleDateString();
  };

  const filteredComments = comments
    .filter((comment) => {
      if (!search) return true;
      return (
        comment.content.toLowerCase().includes(search.toLowerCase()) ||
        comment.user.display_name.toLowerCase().includes(search.toLowerCase())
      );
    });

  const tabs = [
    { id: 'all', label: 'All Comments', badge: filter === 'all' ? total : undefined },
    { id: 'unread', label: 'Unread', badge: undefined },
    { id: 'held', label: 'Held for Review', badge: undefined },
  ];

  return (
    <>
      <div className="comments-page">
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
            <Link href="/dashboard/content" className="nav-item">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polygon points="23 7 16 12 23 17 23 7" />
                <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
              </svg>
              Content
            </Link>
            <Link href="/dashboard/comments" className="nav-item active">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
              Comments
            </Link>
            <Link href="/dashboard/analytics" className="nav-item">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="18" y1="20" x2="18" y2="10" />
                <line x1="12" y1="20" x2="12" y2="4" />
                <line x1="6" y1="20" x2="6" y2="14" />
              </svg>
              Analytics
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
              <h1>Comments</h1>
              <p className="subtitle">Manage and respond to your audience</p>
            </div>
          </header>

          {/* Filters */}
          <div className="filters">
            <Tabs
              tabs={tabs}
              activeTab={filter}
              onTabChange={(id) => setFilter(id as CommentFilter)}
              variant="underline"
            />

            <div className="filter-controls">
              <Input
                placeholder="Search comments..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                leftIcon={
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="11" cy="11" r="8" />
                    <line x1="21" y1="21" x2="16.65" y2="16.65" />
                  </svg>
                }
              />
            </div>
          </div>

          {/* Comment List */}
          {isLoading ? (
            <div className="loading">Loading comments...</div>
          ) : filteredComments.length === 0 ? (
            <EmptyState
              icon={
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                </svg>
              }
              title="No comments yet"
              description="When viewers comment on your videos, they'll appear here"
            />
          ) : (
            <div className="comment-list">
              {filteredComments.map((comment) => (
                <div key={comment.id} className="comment-card">
                  {/* Video Reference */}
                  {comment.video && (
                    <div className="comment-video">
                      <Link href={`/watch/${comment.video.id}`} className="video-link">
                        <div className="video-thumbnail">
                          {comment.video.thumbnail_url ? (
                            <img src={comment.video.thumbnail_url} alt="" />
                          ) : (
                            <div className="thumbnail-placeholder" />
                          )}
                        </div>
                        <span className="video-title">{comment.video.title}</span>
                      </Link>
                    </div>
                  )}

                  {/* Comment Content */}
                  <div className="comment-main">
                    <div className="comment-header">
                      <Avatar
                        src={comment.user.avatar_url}
                        name={comment.user.display_name}
                        size="sm"
                      />
                      <div className="comment-meta">
                        <span className="commenter-name">{comment.user.display_name}</span>
                        <span className="comment-time">{formatTimeAgo(comment.created_at)}</span>
                      </div>
                      {comment.is_creator_heart && (
                        <Badge variant="error" size="sm">
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
                          </svg>
                        </Badge>
                      )}
                    </div>

                    <p className="comment-text">{comment.content}</p>

                    <div className="comment-stats">
                      <span className="stat">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3" />
                        </svg>
                        {comment.like_count}
                      </span>
                      {comment.replies && comment.replies.length > 0 && (
                        <span className="stat">{comment.replies.length} replies</span>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="comment-actions">
                    <button
                      className="action-btn"
                      onClick={() => handleHeart(comment)}
                      title={comment.is_creator_heart ? 'Remove heart' : 'Heart this comment'}
                    >
                      <svg
                        width="16"
                        height="16"
                        viewBox="0 0 24 24"
                        fill={comment.is_creator_heart ? 'currentColor' : 'none'}
                        stroke="currentColor"
                        strokeWidth="2"
                      >
                        <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
                      </svg>
                    </button>
                    <button
                      className="action-btn"
                      onClick={() => {
                        setReplyModal({ open: true, comment });
                        setReplyText('');
                      }}
                      title="Reply"
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <polyline points="9 17 4 12 9 7" />
                        <path d="M20 18v-2a4 4 0 0 0-4-4H4" />
                      </svg>
                    </button>
                    <button
                      className="action-btn danger"
                      onClick={() => setDeleteModal({ open: true, commentId: comment.id })}
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
              {hasMore && (
                <div className="load-more">
                  <Button
                    variant="secondary"
                    onClick={loadMore}
                    loading={isLoading}
                  >
                    Load More Comments
                  </Button>
                </div>
              )}
            </div>
          )}
        </main>
      </div>

      {/* Reply Modal */}
      <Modal
        isOpen={replyModal.open}
        onClose={() => setReplyModal({ open: false })}
        title="Reply to Comment"
        size="md"
        footer={
          <>
            <Button variant="ghost" onClick={() => setReplyModal({ open: false })}>
              Cancel
            </Button>
            <Button onClick={handleReply} loading={isReplying} disabled={!replyText.trim()}>
              Reply
            </Button>
          </>
        }
      >
        {replyModal.comment && (
          <div className="reply-modal-content">
            <div className="original-comment">
              <div className="original-header">
                <Avatar
                  src={replyModal.comment.user.avatar_url}
                  name={replyModal.comment.user.display_name}
                  size="xs"
                />
                <span className="original-name">{replyModal.comment.user.display_name}</span>
              </div>
              <p className="original-text">{replyModal.comment.content}</p>
            </div>
            <textarea
              className="reply-input"
              placeholder="Write your reply..."
              value={replyText}
              onChange={(e) => setReplyText(e.target.value)}
              rows={3}
            />
          </div>
        )}
      </Modal>

      {/* Delete Modal */}
      <Modal
        isOpen={deleteModal.open}
        onClose={() => setDeleteModal({ open: false })}
        title="Delete Comment"
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
        <p>Are you sure you want to delete this comment? This action cannot be undone.</p>
      </Modal>

      <style jsx>{`
        .comments-page {
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
          margin-top: 1rem;
          max-width: 400px;
        }

        .loading {
          text-align: center;
          padding: 4rem;
          color: var(--color-text-secondary);
        }

        .comment-list {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .comment-card {
          background: var(--color-bg-secondary);
          border: 1px solid var(--color-border);
          border-radius: var(--radius-lg);
          padding: 1rem;
        }

        .comment-video {
          margin-bottom: 1rem;
          padding-bottom: 1rem;
          border-bottom: 1px solid var(--color-border);
        }

        .video-link {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          text-decoration: none;
        }

        .video-thumbnail {
          width: 64px;
          height: 36px;
          border-radius: var(--radius-sm);
          overflow: hidden;
          background: var(--color-bg-tertiary);
        }

        .video-thumbnail img {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }

        .video-title {
          color: var(--color-text-primary);
          font-size: var(--text-sm);
          font-weight: 500;
        }

        .video-link:hover .video-title {
          text-decoration: underline;
        }

        .comment-main {
          flex: 1;
        }

        .comment-header {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          margin-bottom: 0.5rem;
        }

        .comment-meta {
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }

        .commenter-name {
          font-weight: 500;
          font-size: var(--text-sm);
        }

        .comment-time {
          color: var(--color-text-tertiary);
          font-size: var(--text-xs);
        }

        .comment-text {
          margin: 0;
          color: var(--color-text-primary);
          line-height: 1.5;
        }

        .comment-stats {
          display: flex;
          gap: 1rem;
          margin-top: 0.75rem;
        }

        .stat {
          display: flex;
          align-items: center;
          gap: 0.25rem;
          font-size: var(--text-xs);
          color: var(--color-text-tertiary);
        }

        .comment-actions {
          display: flex;
          gap: 0.5rem;
          margin-top: 1rem;
          padding-top: 1rem;
          border-top: 1px solid var(--color-border);
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

        .reply-modal-content {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .original-comment {
          background: var(--color-bg-secondary);
          padding: 1rem;
          border-radius: var(--radius-md);
        }

        .original-header {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          margin-bottom: 0.5rem;
        }

        .original-name {
          font-size: var(--text-sm);
          font-weight: 500;
        }

        .original-text {
          margin: 0;
          font-size: var(--text-sm);
          color: var(--color-text-secondary);
        }

        .reply-input {
          width: 100%;
          padding: 0.75rem;
          background: var(--color-bg-secondary);
          border: 1px solid var(--color-border);
          border-radius: var(--radius-md);
          color: var(--color-text-primary);
          font-size: var(--text-base);
          font-family: inherit;
          resize: vertical;
        }

        .reply-input:focus {
          outline: none;
          border-color: var(--color-accent);
        }

        .load-more {
          display: flex;
          justify-content: center;
          padding: 1.5rem;
        }

        @media (max-width: 1024px) {
          .sidebar {
            display: none;
          }
        }

        @media (max-width: 640px) {
          .main-content {
            padding: 1rem;
          }
        }
      `}</style>
    </>
  );
}
