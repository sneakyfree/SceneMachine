/**
 * Comments Panel component.
 *
 * Sidebar panel for viewing and managing project comments.
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import {
  X,
  MessageSquare,
  Send,
  Check,
  CheckCheck,
  MoreVertical,
  Trash2,
  Clock,
  User,
  Film,
  Loader2,
  ChevronDown,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { useSharingStore } from '../stores/sharing-store';
import type { Comment } from '../api/client';

interface CommentsPanelProps {
  projectId: string;
  isOpen: boolean;
  onClose: () => void;
  currentShotId?: string;
  onNavigateToShot?: (shotId: string) => void;
}

export function CommentsPanel({
  projectId,
  isOpen,
  onClose,
  currentShotId,
  onNavigateToShot,
}: CommentsPanelProps) {
  const [newComment, setNewComment] = useState('');
  const [authorName, setAuthorName] = useState(() =>
    localStorage.getItem('scenemachine-comment-author') || ''
  );
  const [showResolved, setShowResolved] = useState(false);
  const [filterShotId, setFilterShotId] = useState<string | 'all'>('all');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const {
    comments,
    isLoadingComments,
    fetchComments,
    addComment,
    resolveComment,
    deleteComment,
  } = useSharingStore();

  // Fetch comments when panel opens
  useEffect(() => {
    if (isOpen && projectId) {
      fetchComments(projectId, { includeResolved: showResolved });
    }
  }, [isOpen, projectId, showResolved, fetchComments]);

  // Save author name to localStorage
  useEffect(() => {
    if (authorName) {
      localStorage.setItem('scenemachine-comment-author', authorName);
    }
  }, [authorName]);

  const handleSubmit = useCallback(async () => {
    if (!newComment.trim() || !authorName.trim()) return;

    setIsSubmitting(true);
    try {
      await addComment({
        projectId,
        authorName: authorName.trim(),
        content: newComment.trim(),
        shotId: currentShotId,
      });
      setNewComment('');
      inputRef.current?.focus();
    } catch (error) {
      console.error('Failed to add comment:', error);
    } finally {
      setIsSubmitting(false);
    }
  }, [projectId, authorName, newComment, currentShotId, addComment]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit]
  );

  const handleResolve = useCallback(
    async (commentId: string) => {
      try {
        await resolveComment(commentId);
      } catch (error) {
        console.error('Failed to resolve comment:', error);
      }
    },
    [resolveComment]
  );

  const handleDelete = useCallback(
    async (commentId: string) => {
      if (confirm('Are you sure you want to delete this comment?')) {
        try {
          await deleteComment(commentId);
        } catch (error) {
          console.error('Failed to delete comment:', error);
        }
      }
    },
    [deleteComment]
  );

  // Filter comments
  const filteredComments = comments.filter((comment) => {
    if (!showResolved && comment.isResolved) return false;
    if (filterShotId !== 'all' && comment.shotId !== filterShotId) return false;
    return true;
  });

  // Group comments by shot
  const groupedComments = filteredComments.reduce(
    (acc, comment) => {
      const key = comment.shotId || 'general';
      if (!acc[key]) acc[key] = [];
      acc[key].push(comment);
      return acc;
    },
    {} as Record<string, Comment[]>
  );

  // Get unique shot IDs for filter
  const shotIds = [...new Set(comments.filter(c => c.shotId).map(c => c.shotId!))];

  if (!isOpen) return null;

  return (
    <div className="fixed right-0 top-0 h-full w-80 bg-surface-900 border-l border-surface-700 shadow-xl z-40 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-surface-800">
        <div className="flex items-center gap-2">
          <MessageSquare className="w-5 h-5 text-brand-400" />
          <h2 className="font-semibold">Comments</h2>
          <span className="px-1.5 py-0.5 bg-surface-700 text-xs rounded">
            {filteredComments.length}
          </span>
        </div>
        <button
          onClick={onClose}
          className="icon-btn p-2 hover:bg-surface-800 rounded transition-colors"
          aria-label="Close comments panel"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2 px-4 py-2 border-b border-surface-800">
        <select
          value={filterShotId}
          onChange={(e) => setFilterShotId(e.target.value)}
          className="flex-1 px-2 py-1 bg-surface-800 border border-surface-700 rounded text-xs focus:outline-none focus:border-brand-500"
        >
          <option value="all">All Comments</option>
          <option value="general">General</option>
          {shotIds.map((shotId) => (
            <option key={shotId} value={shotId}>
              Shot: {shotId.slice(0, 8)}...
            </option>
          ))}
        </select>
        <button
          onClick={() => setShowResolved(!showResolved)}
          className={cn(
            'flex items-center gap-1 px-2 py-1 rounded text-xs transition-colors',
            showResolved
              ? 'bg-brand-500/20 text-brand-300'
              : 'bg-surface-800 text-surface-400 hover:bg-surface-700'
          )}
        >
          <CheckCheck className="w-3 h-3" />
          Resolved
        </button>
      </div>

      {/* Comments List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {isLoadingComments ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-surface-500" />
          </div>
        ) : filteredComments.length === 0 ? (
          <div className="text-center py-8">
            <MessageSquare className="w-12 h-12 mx-auto text-surface-600 mb-3" />
            <h3 className="text-sm font-medium mb-1">No Comments Yet</h3>
            <p className="text-xs text-surface-500">
              Be the first to leave a comment
            </p>
          </div>
        ) : (
          Object.entries(groupedComments).map(([shotKey, shotComments]) => (
            <div key={shotKey} className="space-y-2">
              {shotKey !== 'general' && (
                <button
                  onClick={() => onNavigateToShot?.(shotKey)}
                  className="flex items-center gap-1.5 text-xs text-surface-400 hover:text-brand-400 transition-colors"
                >
                  <Film className="w-3 h-3" />
                  Shot: {shotKey.slice(0, 8)}...
                </button>
              )}
              {shotKey === 'general' && shotComments.length > 0 && (
                <div className="flex items-center gap-1.5 text-xs text-surface-400">
                  <MessageSquare className="w-3 h-3" />
                  General Comments
                </div>
              )}
              {shotComments.map((comment) => (
                <CommentBubble
                  key={comment.id}
                  comment={comment}
                  onResolve={handleResolve}
                  onDelete={handleDelete}
                  onNavigateToShot={onNavigateToShot}
                />
              ))}
            </div>
          ))
        )}
      </div>

      {/* New Comment Form */}
      <div className="border-t border-surface-800 p-4 space-y-3">
        {!authorName && (
          <div>
            <label className="block text-xs text-surface-500 mb-1">Your Name</label>
            <input
              type="text"
              value={authorName}
              onChange={(e) => setAuthorName(e.target.value)}
              placeholder="Enter your name..."
              className="w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded text-sm focus:outline-none focus:border-brand-500"
            />
          </div>
        )}
        <div className="relative">
          <textarea
            ref={inputRef}
            value={newComment}
            onChange={(e) => setNewComment(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              currentShotId
                ? 'Comment on this shot...'
                : 'Add a general comment...'
            }
            rows={3}
            className="w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded text-sm resize-none focus:outline-none focus:border-brand-500"
          />
          <div className="flex items-center justify-between mt-2">
            <span className="text-xs text-surface-500">
              {currentShotId ? (
                <span className="flex items-center gap-1">
                  <Film className="w-3 h-3" />
                  Commenting on shot
                </span>
              ) : (
                'General comment'
              )}
            </span>
            <button
              onClick={handleSubmit}
              disabled={!newComment.trim() || !authorName.trim() || isSubmitting}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-600 hover:bg-brand-500 text-white text-sm rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

interface CommentBubbleProps {
  comment: Comment;
  onResolve: (id: string) => void;
  onDelete: (id: string) => void;
  onNavigateToShot?: (shotId: string) => void;
}

function CommentBubble({
  comment,
  onResolve,
  onDelete,
  onNavigateToShot,
}: CommentBubbleProps) {
  const [showMenu, setShowMenu] = useState(false);

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  const formatTimecode = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div
      className={cn(
        'p-3 rounded-lg border transition-colors',
        comment.isResolved
          ? 'bg-surface-800/50 border-surface-700/50 opacity-60'
          : 'bg-surface-800 border-surface-700'
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 bg-brand-500/20 text-brand-400 rounded-full flex items-center justify-center">
            <User className="w-3 h-3" />
          </div>
          <div>
            <div className="text-sm font-medium">{comment.authorName}</div>
            <div className="flex items-center gap-2 text-xs text-surface-500">
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {formatTime(comment.createdAt)}
              </span>
              {comment.timecodeSeconds !== undefined && (
                <span className="text-brand-400">
                  @ {formatTimecode(comment.timecodeSeconds)}
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="relative">
          <button
            onClick={() => setShowMenu(!showMenu)}
            className="icon-btn p-2 hover:bg-surface-700 rounded transition-colors"
            aria-label="Comment actions"
            aria-expanded={showMenu}
          >
            <MoreVertical className="w-4 h-4 text-surface-500" />
          </button>
          {showMenu && (
            <>
              <div
                className="fixed inset-0 z-10"
                onClick={() => setShowMenu(false)}
              />
              <div className="absolute right-0 top-full mt-1 w-36 bg-surface-800 border border-surface-700 rounded-lg shadow-lg py-1 z-20">
                {!comment.isResolved && (
                  <button
                    onClick={() => {
                      onResolve(comment.id);
                      setShowMenu(false);
                    }}
                    className="flex items-center gap-2 w-full px-3 py-2 text-sm text-left hover:bg-surface-700 transition-colors"
                  >
                    <Check className="w-4 h-4 text-green-400" />
                    Resolve
                  </button>
                )}
                <button
                  onClick={() => {
                    onDelete(comment.id);
                    setShowMenu(false);
                  }}
                  className="flex items-center gap-2 w-full px-3 py-2 text-sm text-left text-red-400 hover:bg-surface-700 transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                  Delete
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Content */}
      <p className="text-sm whitespace-pre-wrap">{comment.content}</p>

      {/* Resolved badge */}
      {comment.isResolved && (
        <div className="flex items-center gap-1 mt-2 text-xs text-green-400">
          <CheckCheck className="w-3 h-3" />
          Resolved
        </div>
      )}
    </div>
  );
}
