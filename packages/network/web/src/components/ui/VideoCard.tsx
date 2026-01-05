/**
 * Video Card Component - Stunning shadcn/ui Design
 *
 * A beautiful video thumbnail card with hover effects, animations,
 * and polished styling inspired by Orchids and modern streaming platforms.
 */

'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Play, Clock, Eye, CheckCircle2, Sparkles, Crown } from 'lucide-react';
import { cn } from '../../lib/utils';
import { Video } from '../../lib/api-client';

interface VideoCardProps {
  video: Video;
  showCreator?: boolean;
  size?: 'small' | 'medium' | 'large';
  reason?: 'following' | 'trending' | 'recommended' | 'new';
  className?: string;
}

export function VideoCard({
  video,
  showCreator = true,
  size = 'medium',
  reason,
  className,
}: VideoCardProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [imageLoaded, setImageLoaded] = useState(false);

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

  const reasonConfig = {
    following: { label: 'Following', icon: CheckCircle2, color: 'text-emerald-400' },
    trending: { label: 'Trending', icon: Sparkles, color: 'text-amber-400' },
    recommended: { label: 'For You', icon: Sparkles, color: 'text-primary' },
    new: { label: 'New', icon: Crown, color: 'text-violet-400' },
  };

  const sizeClasses = {
    small: 'max-w-[240px]',
    medium: 'max-w-[320px]',
    large: 'max-w-[400px]',
  };

  return (
    <motion.article
      className={cn(
        'group relative flex flex-col gap-3',
        sizeClasses[size],
        className
      )}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      {/* Thumbnail Container */}
      <Link
        href={`/watch/${video.id}`}
        className="thumbnail-hover relative aspect-video overflow-hidden rounded-xl bg-secondary"
      >
        {/* Shimmer Loading State */}
        {!imageLoaded && (
          <div className="shimmer absolute inset-0" />
        )}

        {/* Thumbnail Image */}
        <motion.img
          src={video.thumbnail_url || 'https://picsum.photos/seed/placeholder/640/360'}
          alt={video.title}
          loading="lazy"
          onLoad={() => setImageLoaded(true)}
          className={cn(
            'h-full w-full object-cover transition-all duration-500',
            imageLoaded ? 'opacity-100' : 'opacity-0'
          )}
          animate={{ scale: isHovered ? 1.05 : 1 }}
          transition={{ duration: 0.4 }}
        />

        {/* Gradient Overlay */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100" />

        {/* Play Button Overlay */}
        <motion.div
          className="absolute inset-0 flex items-center justify-center"
          initial={{ opacity: 0 }}
          animate={{ opacity: isHovered ? 1 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <motion.div
            className="flex h-14 w-14 items-center justify-center rounded-full bg-primary/90 shadow-lg shadow-primary/30 backdrop-blur-sm"
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.95 }}
          >
            <Play className="h-6 w-6 text-white ml-1" fill="white" />
          </motion.div>
        </motion.div>

        {/* Duration Badge */}
        <div className="absolute bottom-2 right-2 flex items-center gap-1 rounded-md bg-black/80 px-2 py-1 text-xs font-medium text-white backdrop-blur-sm">
          <Clock className="h-3 w-3" />
          {formatDuration(video.duration_seconds)}
        </div>

        {/* Paid Badge */}
        {video.monetization_type === 'PAID' && video.ticket_price && (
          <div className="absolute left-2 top-2 rounded-md bg-gradient-to-r from-amber-500 to-orange-500 px-2 py-1 text-xs font-bold text-white shadow-lg">
            ${video.ticket_price.toFixed(2)}
          </div>
        )}

        {/* Made with Studio Badge */}
        {video.made_with_studio && (
          <motion.div
            className="absolute right-2 top-2 flex items-center gap-1 rounded-md bg-gradient-to-r from-primary to-violet-500 px-2 py-1 text-xs font-bold text-white shadow-lg"
            whileHover={{ scale: 1.05 }}
          >
            <Sparkles className="h-3 w-3" />
            SM
          </motion.div>
        )}

        {/* Reason Badge (Trending, Following, etc.) */}
        {reason && (
          <div className={cn(
            'absolute left-2 top-2 flex items-center gap-1 rounded-md bg-black/70 px-2 py-1 text-xs font-medium backdrop-blur-sm',
            reasonConfig[reason].color
          )}>
            {React.createElement(reasonConfig[reason].icon, { className: 'h-3 w-3' })}
            {reasonConfig[reason].label}
          </div>
        )}
      </Link>

      {/* Video Info */}
      <div className="flex gap-3">
        {/* Creator Avatar */}
        {showCreator && (
          <Link
            href={`/channel/${video.creator?.id || video.creator_id}`}
            className="flex-shrink-0"
          >
            <motion.div
              className="relative h-9 w-9 overflow-hidden rounded-full ring-2 ring-transparent transition-all duration-300 hover:ring-primary/50"
              whileHover={{ scale: 1.1 }}
            >
              <img
                src={video.creator?.avatar_url || 'https://api.dicebear.com/7.x/avataaars/svg?seed=default'}
                alt={video.creator?.display_name || 'Creator'}
                className="h-full w-full object-cover"
              />
              {video.creator?.is_verified && (
                <div className="absolute -bottom-0.5 -right-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-primary text-[8px] text-white ring-2 ring-background">
                  <CheckCircle2 className="h-2.5 w-2.5" fill="currentColor" />
                </div>
              )}
            </motion.div>
          </Link>
        )}

        {/* Video Details */}
        <div className="flex-1 min-w-0">
          {/* Title */}
          <Link href={`/watch/${video.id}`}>
            <h3 className="mb-1 line-clamp-2 text-sm font-semibold leading-tight text-foreground transition-colors hover:text-primary">
              {video.title}
            </h3>
          </Link>

          {/* Creator Name */}
          {showCreator && (
            <Link
              href={`/channel/${video.creator?.id || video.creator_id}`}
              className="group/creator mb-1 flex items-center gap-1 text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              <span className="truncate">
                {video.creator?.display_name || video.creator?.username || 'Unknown Creator'}
              </span>
              {video.creator?.is_verified && (
                <CheckCircle2 className="h-3.5 w-3.5 flex-shrink-0 text-primary" fill="currentColor" />
              )}
            </Link>
          )}

          {/* Meta Info */}
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <div className="flex items-center gap-1">
              <Eye className="h-3 w-3" />
              <span>{formatViews(video.view_count)} views</span>
            </div>
            <span className="text-muted-foreground/50">•</span>
            <span>{formatDate(video.published_at)}</span>
          </div>
        </div>
      </div>
    </motion.article>
  );
}

export default VideoCard;
