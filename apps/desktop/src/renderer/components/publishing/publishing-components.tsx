/**
 * Publishing and Distribution Components
 * YouTube upload, multi-platform publishing, and analytics
 */

import React from 'react';
import {
  Upload,
  Youtube,
  Twitter,
  Instagram,
  Loader2,
  Check,
  X,
  AlertCircle,
  Calendar,
  Clock,
  Eye,
  ThumbsUp,
  MessageSquare,
  TrendingUp,
  BarChart3,
  ExternalLink,
} from 'lucide-react';
import { cn } from '../../lib/utils';

// Platform types
export type Platform = 'youtube' | 'twitter' | 'instagram' | 'tiktok';

// Upload status
export type UploadStatus = 'idle' | 'preparing' | 'uploading' | 'processing' | 'complete' | 'error';

// Video metadata
export interface VideoMetadata {
  title: string;
  description: string;
  tags: string[];
  visibility: 'public' | 'unlisted' | 'private';
  category?: string;
  scheduledAt?: Date;
}

// Upload state
export interface UploadState {
  status: UploadStatus;
  progress: number;
  error?: string;
  url?: string;
}

// Platform icons
const PLATFORM_ICONS: Record<Platform, React.ReactNode> = {
  youtube: <Youtube className="w-5 h-5 text-red-500" />,
  twitter: <Twitter className="w-5 h-5 text-blue-400" />,
  instagram: <Instagram className="w-5 h-5 text-pink-500" />,
  tiktok: <span className="w-5 h-5 text-black font-bold">TT</span>,
};

// Upload progress component
export const UploadProgress: React.FC<{
  state: UploadState;
  onCancel?: () => void;
  className?: string;
}> = ({ state, onCancel, className }) => (
  <div className={cn('bg-surface-800 rounded-lg p-4', className)}>
    <div className="flex items-center justify-between mb-2">
      <div className="flex items-center gap-2">
        {state.status === 'complete' ? (
          <Check className="w-5 h-5 text-green-500" />
        ) : state.status === 'error' ? (
          <X className="w-5 h-5 text-red-500" />
        ) : (
          <Loader2 className="w-5 h-5 animate-spin text-brand-500" />
        )}
        <span className="font-medium capitalize">
          {state.status === 'idle' ? 'Ready to upload' : state.status}
        </span>
      </div>
      {state.status !== 'complete' && state.status !== 'error' && onCancel && (
        <button onClick={onCancel} className="text-surface-400 hover:text-red-400">
          <X className="w-4 h-4" />
        </button>
      )}
    </div>

    {/* Progress bar */}
    <div className="h-2 bg-surface-700 rounded-full overflow-hidden">
      <div
        className={cn(
          'h-full transition-all duration-300',
          state.status === 'complete'
            ? 'bg-green-500'
            : state.status === 'error'
              ? 'bg-red-500'
              : 'bg-brand-500'
        )}
        style={{ width: `${state.progress}%` }}
      />
    </div>

    {/* Progress text */}
    <div className="flex justify-between mt-1 text-xs text-surface-400">
      <span>{state.progress}%</span>
      {state.url && (
        <a
          href={state.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-brand-400 hover:underline flex items-center gap-1"
        >
          View <ExternalLink className="w-3 h-3" />
        </a>
      )}
    </div>

    {/* Error message */}
    {state.error && (
      <div className="mt-2 p-2 bg-red-500/10 rounded text-red-400 text-sm flex items-center gap-2">
        <AlertCircle className="w-4 h-4" />
        {state.error}
      </div>
    )}
  </div>
);

// Metadata editor
export const MetadataEditor: React.FC<{
  metadata: VideoMetadata;
  onChange: (metadata: VideoMetadata) => void;
  className?: string;
}> = ({ metadata, onChange, className }) => {
  const [tagInput, setTagInput] = React.useState('');

  const addTag = () => {
    if (tagInput.trim() && !metadata.tags.includes(tagInput.trim())) {
      onChange({ ...metadata, tags: [...metadata.tags, tagInput.trim()] });
      setTagInput('');
    }
  };

  const removeTag = (tag: string) => {
    onChange({ ...metadata, tags: metadata.tags.filter((t) => t !== tag) });
  };

  return (
    <div className={cn('space-y-4', className)}>
      {/* Title */}
      <div>
        <label className="block text-sm font-medium mb-1.5">Title</label>
        <input
          type="text"
          value={metadata.title}
          onChange={(e) => onChange({ ...metadata, title: e.target.value })}
          placeholder="Enter video title..."
          maxLength={100}
          className="w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg focus:border-brand-500 focus:outline-none"
        />
        <div className="text-xs text-surface-500 mt-1">{metadata.title.length}/100</div>
      </div>

      {/* Description */}
      <div>
        <label className="block text-sm font-medium mb-1.5">Description</label>
        <textarea
          value={metadata.description}
          onChange={(e) => onChange({ ...metadata, description: e.target.value })}
          placeholder="Enter video description..."
          rows={4}
          maxLength={5000}
          className="w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg focus:border-brand-500 focus:outline-none resize-none"
        />
        <div className="text-xs text-surface-500 mt-1">{metadata.description.length}/5000</div>
      </div>

      {/* Tags */}
      <div>
        <label className="block text-sm font-medium mb-1.5">Tags</label>
        <div className="flex flex-wrap gap-1 p-2 bg-surface-800 border border-surface-700 rounded-lg min-h-[40px]">
          {metadata.tags.map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center gap-1 px-2 py-0.5 bg-brand-500/20 text-brand-400 rounded text-xs"
            >
              {tag}
              <button onClick={() => removeTag(tag)} className="hover:text-red-400">
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}
          <input
            type="text"
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && addTag()}
            placeholder={metadata.tags.length === 0 ? 'Add tags...' : ''}
            className="flex-1 min-w-[80px] bg-transparent border-none outline-none text-sm"
          />
        </div>
      </div>

      {/* Visibility */}
      <div>
        <label className="block text-sm font-medium mb-1.5">Visibility</label>
        <div className="flex gap-2">
          {(['public', 'unlisted', 'private'] as const).map((v) => (
            <button
              key={v}
              onClick={() => onChange({ ...metadata, visibility: v })}
              className={cn(
                'flex-1 py-2 rounded-lg border capitalize transition-colors',
                metadata.visibility === v
                  ? 'border-brand-500 bg-brand-500/10 text-brand-400'
                  : 'border-surface-700 hover:border-surface-600'
              )}
            >
              {v}
            </button>
          ))}
        </div>
      </div>

      {/* Schedule */}
      <div>
        <label className="flex items-center gap-2 text-sm font-medium mb-1.5">
          <Calendar className="w-4 h-4" />
          Schedule (optional)
        </label>
        <input
          type="datetime-local"
          value={metadata.scheduledAt?.toISOString().slice(0, 16) || ''}
          onChange={(e) =>
            onChange({
              ...metadata,
              scheduledAt: e.target.value ? new Date(e.target.value) : undefined,
            })
          }
          className="w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg focus:border-brand-500 focus:outline-none"
        />
      </div>
    </div>
  );
};

// Platform selector
export const PlatformSelector: React.FC<{
  selected: Platform[];
  onChange: (platforms: Platform[]) => void;
  connected?: Platform[];
  className?: string;
}> = ({ selected, onChange, connected = [], className }) => {
  const toggle = (platform: Platform) => {
    if (selected.includes(platform)) {
      onChange(selected.filter((p) => p !== platform));
    } else {
      onChange([...selected, platform]);
    }
  };

  return (
    <div className={cn('grid grid-cols-2 gap-2', className)}>
      {(Object.keys(PLATFORM_ICONS) as Platform[]).map((platform) => {
        const isConnected = connected.includes(platform);
        const isSelected = selected.includes(platform);

        return (
          <button
            key={platform}
            onClick={() => isConnected && toggle(platform)}
            disabled={!isConnected}
            className={cn(
              'flex items-center gap-3 p-3 rounded-lg border transition-colors',
              isSelected
                ? 'border-brand-500 bg-brand-500/10'
                : isConnected
                  ? 'border-surface-700 hover:border-surface-600'
                  : 'border-surface-800 opacity-50 cursor-not-allowed'
            )}
          >
            {PLATFORM_ICONS[platform]}
            <div className="text-left flex-1">
              <div className="font-medium capitalize">{platform}</div>
              <div className="text-xs text-surface-400">
                {isConnected ? 'Connected' : 'Not connected'}
              </div>
            </div>
            {isSelected && <Check className="w-5 h-5 text-brand-500" />}
          </button>
        );
      })}
    </div>
  );
};

// Analytics dashboard
export const AnalyticsDashboard: React.FC<{
  views: number;
  likes: number;
  comments: number;
  subscribers: number;
  viewsChange?: number;
  className?: string;
}> = ({ views, likes, comments, subscribers, viewsChange, className }) => {
  const formatNumber = (n: number): string => {
    if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`;
    if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
    return n.toString();
  };

  return (
    <div className={cn('bg-surface-900 rounded-xl p-4', className)}>
      <h3 className="font-medium mb-4 flex items-center gap-2">
        <BarChart3 className="w-5 h-5 text-brand-400" />
        Analytics Overview
      </h3>

      <div className="grid grid-cols-2 gap-3">
        <div className="bg-surface-800 rounded-lg p-3">
          <div className="flex items-center justify-between mb-1">
            <Eye className="w-4 h-4 text-surface-400" />
            {viewsChange && (
              <span className={cn('text-xs', viewsChange > 0 ? 'text-green-400' : 'text-red-400')}>
                {viewsChange > 0 ? '+' : ''}
                {viewsChange}%
              </span>
            )}
          </div>
          <div className="text-2xl font-bold">{formatNumber(views)}</div>
          <div className="text-xs text-surface-400">Views</div>
        </div>

        <div className="bg-surface-800 rounded-lg p-3">
          <ThumbsUp className="w-4 h-4 text-surface-400 mb-1" />
          <div className="text-2xl font-bold">{formatNumber(likes)}</div>
          <div className="text-xs text-surface-400">Likes</div>
        </div>

        <div className="bg-surface-800 rounded-lg p-3">
          <MessageSquare className="w-4 h-4 text-surface-400 mb-1" />
          <div className="text-2xl font-bold">{formatNumber(comments)}</div>
          <div className="text-xs text-surface-400">Comments</div>
        </div>

        <div className="bg-surface-800 rounded-lg p-3">
          <TrendingUp className="w-4 h-4 text-surface-400 mb-1" />
          <div className="text-2xl font-bold">{formatNumber(subscribers)}</div>
          <div className="text-xs text-surface-400">Subscribers</div>
        </div>
      </div>
    </div>
  );
};

// Upload hook
export function useUpload(onComplete?: (url: string) => void) {
  const [state, setState] = React.useState<UploadState>({
    status: 'idle',
    progress: 0,
  });

  const upload = React.useCallback(
    async (file: File, metadata: VideoMetadata, platforms: Platform[]) => {
      setState({ status: 'preparing', progress: 0 });

      try {
        // Simulate upload progress
        for (let i = 0; i <= 100; i += 10) {
          await new Promise((r) => setTimeout(r, 200));
          setState((s) => ({
            ...s,
            status: i < 30 ? 'preparing' : i < 90 ? 'uploading' : 'processing',
            progress: i,
          }));
        }

        const url = `https://youtube.com/watch?v=${Date.now()}`;
        setState({ status: 'complete', progress: 100, url });
        onComplete?.(url);
      } catch (error) {
        setState({ status: 'error', progress: 0, error: 'Upload failed' });
      }
    },
    [onComplete]
  );

  const reset = React.useCallback(() => {
    setState({ status: 'idle', progress: 0 });
  }, []);

  return { state, upload, reset };
}
