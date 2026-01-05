/**
 * Home Page - Stunning SceneMachine Network Design
 *
 * Main feed page with beautiful video discovery, inspired by Orchids.
 */

'use client';

import React, { useEffect, useCallback, useRef, useState } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  Upload,
  Bell,
  Menu,
  X,
  Flame,
  Sparkles,
  Clock,
  Users,
  TrendingUp,
  Film,
  Clapperboard,
} from 'lucide-react';
import { useFeedStore, useAuthStore } from '../stores';
import { VideoCard } from '../components/ui/VideoCard';
import { cn } from '../lib/utils';

type FeedTab = 'for-you' | 'following' | 'trending' | 'new';

export default function HomePage() {
  const {
    feeds,
    activeFeed,
    setActiveFeed,
    loadFeed,
    loadMore,
    searchQuery,
    searchResults,
    searchLoading,
    search,
    clearSearch,
  } = useFeedStore();

  const { isAuthenticated, user } = useAuthStore();
  const [searchFocused, setSearchFocused] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const observerRef = useRef<IntersectionObserver | null>(null);
  const loadMoreRef = useRef<HTMLDivElement>(null);

  const currentFeed = feeds[activeFeed];

  // Initial load
  useEffect(() => {
    if (currentFeed.items.length === 0 && !currentFeed.isLoading) {
      loadFeed();
    }
  }, [activeFeed, currentFeed.items.length, currentFeed.isLoading, loadFeed]);

  // Infinite scroll
  useEffect(() => {
    observerRef.current = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && currentFeed.hasMore && !currentFeed.isLoading) {
          loadMore();
        }
      },
      { threshold: 0.1 }
    );

    if (loadMoreRef.current) {
      observerRef.current.observe(loadMoreRef.current);
    }

    return () => {
      observerRef.current?.disconnect();
    };
  }, [currentFeed.hasMore, currentFeed.isLoading, loadMore]);

  const handleTabChange = (tab: FeedTab) => {
    setActiveFeed(tab);
    clearSearch();
  };

  const handleSearch = useCallback((query: string) => {
    search(query);
  }, [search]);

  const tabs: { id: FeedTab; label: string; icon: React.ElementType; requiresAuth?: boolean }[] = [
    { id: 'for-you', label: 'For You', icon: Sparkles },
    { id: 'following', label: 'Following', icon: Users, requiresAuth: true },
    { id: 'trending', label: 'Trending', icon: TrendingUp },
    { id: 'new', label: 'New Releases', icon: Clock },
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 w-full border-b border-border/50 bg-background/80 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 lg:px-8">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2">
            <motion.div
              className="relative"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-violet-500 shadow-lg shadow-primary/25">
                <Clapperboard className="h-5 w-5 text-white" />
              </div>
              <div className="absolute -right-1 -top-1 h-3 w-3 rounded-full bg-emerald-400 ring-2 ring-background" />
            </motion.div>
            <span className="hidden bg-gradient-to-r from-primary to-violet-400 bg-clip-text text-xl font-bold text-transparent sm:inline">
              Network
            </span>
          </Link>

          {/* Search Bar */}
          <motion.div
            className={cn(
              'relative flex-1 mx-4 max-w-xl transition-all duration-300',
              searchFocused && 'max-w-2xl'
            )}
          >
            <div className={cn(
              'relative flex items-center rounded-full border bg-secondary/50 transition-all duration-300',
              searchFocused
                ? 'border-primary/50 ring-4 ring-primary/10'
                : 'border-border hover:border-border/80'
            )}>
              <Search className="absolute left-4 h-4 w-4 text-muted-foreground" />
              <input
                type="search"
                placeholder="Search videos, creators, genres..."
                value={searchQuery}
                onChange={(e) => handleSearch(e.target.value)}
                onFocus={() => setSearchFocused(true)}
                onBlur={() => setSearchFocused(false)}
                className="h-10 w-full bg-transparent pl-11 pr-4 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
              />
              {searchQuery && (
                <button
                  onClick={clearSearch}
                  className="absolute right-3 rounded-full p-1 hover:bg-muted"
                >
                  <X className="h-4 w-4 text-muted-foreground" />
                </button>
              )}
            </div>
          </motion.div>

          {/* Actions */}
          <div className="flex items-center gap-2">
            {isAuthenticated ? (
              <>
                {/* Upload Button */}
                <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                  <Link
                    href="/upload"
                    className="hidden items-center gap-2 rounded-full bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-lg shadow-primary/25 transition-all hover:bg-primary/90 hover:shadow-xl hover:shadow-primary/30 sm:flex"
                  >
                    <Upload className="h-4 w-4" />
                    Upload
                  </Link>
                </motion.div>

                {/* Notifications */}
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="relative rounded-full p-2 hover:bg-secondary"
                >
                  <Bell className="h-5 w-5 text-muted-foreground" />
                  <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-destructive" />
                </motion.button>

                {/* Avatar */}
                <Link href={`/channel/${user?.id}`}>
                  <motion.div
                    whileHover={{ scale: 1.05 }}
                    className="h-9 w-9 overflow-hidden rounded-full ring-2 ring-transparent transition-all hover:ring-primary/50"
                  >
                    <img
                      src={user?.avatar_url || 'https://api.dicebear.com/7.x/avataaars/svg?seed=default'}
                      alt={user?.display_name || user?.username}
                      className="h-full w-full object-cover"
                    />
                  </motion.div>
                </Link>
              </>
            ) : (
              <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                <Link
                  href="/login"
                  className="flex items-center gap-2 rounded-full border border-primary bg-primary/10 px-4 py-2 text-sm font-semibold text-primary transition-all hover:bg-primary hover:text-primary-foreground"
                >
                  Sign In
                </Link>
              </motion.div>
            )}

            {/* Mobile Menu Toggle */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="rounded-full p-2 hover:bg-secondary sm:hidden"
            >
              {mobileMenuOpen ? (
                <X className="h-5 w-5" />
              ) : (
                <Menu className="h-5 w-5" />
              )}
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        {/* Tabs */}
        {!searchQuery && (
          <motion.nav
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-8 flex gap-2 overflow-x-auto pb-2 no-scrollbar"
            role="tablist"
          >
            {tabs.map((tab) => (
              (!tab.requiresAuth || isAuthenticated) && (
                <motion.button
                  key={tab.id}
                  role="tab"
                  aria-selected={activeFeed === tab.id}
                  onClick={() => handleTabChange(tab.id)}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className={cn(
                    'flex items-center gap-2 whitespace-nowrap rounded-full px-4 py-2 text-sm font-medium transition-all duration-300',
                    activeFeed === tab.id
                      ? 'bg-primary text-primary-foreground shadow-lg shadow-primary/25'
                      : 'bg-secondary/50 text-muted-foreground hover:bg-secondary hover:text-foreground'
                  )}
                >
                  <tab.icon className="h-4 w-4" />
                  {tab.label}
                </motion.button>
              )
            ))}
          </motion.nav>
        )}

        {/* Search Results Header */}
        <AnimatePresence>
          {searchQuery && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="mb-8 flex items-center justify-between"
            >
              <h2 className="text-xl font-semibold">
                Results for <span className="text-primary">"{searchQuery}"</span>
              </h2>
              <button
                onClick={clearSearch}
                className="text-sm font-medium text-primary hover:underline"
              >
                Clear search
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Feed Grid */}
        <motion.div
          className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
          layout
        >
          <AnimatePresence mode="popLayout">
            {searchQuery ? (
              // Search results
              searchLoading && searchResults.length === 0 ? (
                [...Array(8)].map((_, i) => (
                  <SkeletonCard key={`skeleton-${i}`} index={i} />
                ))
              ) : searchResults.length > 0 ? (
                searchResults.map((video, index) => (
                  <motion.div
                    key={video.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    transition={{ delay: index * 0.05 }}
                  >
                    <VideoCard video={video} />
                  </motion.div>
                ))
              ) : (
                <EmptyState
                  icon={Search}
                  title="No results found"
                  description="Try different keywords or browse our categories"
                />
              )
            ) : (
              // Feed items
              currentFeed.isLoading && currentFeed.items.length === 0 ? (
                [...Array(8)].map((_, i) => (
                  <SkeletonCard key={`skeleton-${i}`} index={i} />
                ))
              ) : currentFeed.items.length > 0 ? (
                currentFeed.items.map((item, index) => (
                  <motion.div
                    key={item.video.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    transition={{ delay: index * 0.03 }}
                  >
                    <VideoCard video={item.video} reason={item.reason} />
                  </motion.div>
                ))
              ) : (
                <EmptyState
                  icon={activeFeed === 'following' ? Users : Film}
                  title="No videos yet"
                  description={
                    activeFeed === 'following'
                      ? 'Follow creators to see their videos here'
                      : 'Check back later for new content'
                  }
                />
              )
            )}
          </AnimatePresence>
        </motion.div>

        {/* Load More Trigger */}
        {!searchQuery && currentFeed.hasMore && (
          <div ref={loadMoreRef} className="mt-12 flex justify-center">
            {currentFeed.isLoading && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex items-center gap-3"
              >
                <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                <span className="text-sm text-muted-foreground">Loading more...</span>
              </motion.div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

// Skeleton Card Component
function SkeletonCard({ index }: { index: number }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: index * 0.05 }}
      className="flex flex-col gap-3"
    >
      <div className="shimmer aspect-video rounded-xl" />
      <div className="flex gap-3">
        <div className="shimmer h-9 w-9 rounded-full" />
        <div className="flex-1 space-y-2">
          <div className="shimmer h-4 w-[90%] rounded" />
          <div className="shimmer h-3 w-[60%] rounded" />
        </div>
      </div>
    </motion.div>
  );
}

// Empty State Component
function EmptyState({
  icon: Icon,
  title,
  description,
}: {
  icon: React.ElementType;
  title: string;
  description: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="col-span-full flex flex-col items-center justify-center py-20 text-center"
    >
      <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-secondary">
        <Icon className="h-10 w-10 text-muted-foreground" />
      </div>
      <h3 className="mb-2 text-xl font-semibold">{title}</h3>
      <p className="max-w-md text-muted-foreground">{description}</p>
    </motion.div>
  );
}
