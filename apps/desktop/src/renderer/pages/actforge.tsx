/**
 * ActForge - Talent Marketplace Page.
 *
 * Browse performers, view leaderboards, and create bookings
 * for ActCore performer-driven video generation.
 */

import React, { useEffect, useState } from 'react';
import {
  Search,
  Filter,
  Trophy,
  Star,
  Users,
  Zap,
  TrendingUp,
  ChevronDown,
  RefreshCw,
} from 'lucide-react';
import { useActForgeStore } from '../stores/actforge-store';
import { useProjectStore } from '../stores/project-store';
import { PerformerCard } from '../components/performer-card';
import { BookingModal } from '../components/booking-modal';
import type { Performer, BookingMode, PerformerType } from '../api/client';

export function ActForgePage(): JSX.Element {
  const {
    performers,
    featuredPerformers,
    leaderboard,
    searchParams,
    searchTotal,
    searchHasMore,
    isLoadingPerformers,
    showBookingModal,
    bookingMode,
    searchPerformers,
    loadMorePerformers,
    fetchFeaturedPerformers,
    fetchLeaderboard,
    openBookingModal,
    closeBookingModal,
  } = useActForgeStore();

  // Get current project for booking context
  const currentProject = useProjectStore((state) => state.currentProject);

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedPerformer, setSelectedPerformer] = useState<Performer | null>(null);
  const [showFilters, setShowFilters] = useState(false);
  const [filterType, setFilterType] = useState<PerformerType | undefined>(undefined);
  const [filterVerified, setFilterVerified] = useState<boolean | undefined>(undefined);
  const [sortBy, setSortBy] = useState<'aci_score' | 'price' | 'rating' | 'bookings'>('aci_score');

  // Initial load
  useEffect(() => {
    searchPerformers();
    fetchFeaturedPerformers();
    fetchLeaderboard();
  }, [searchPerformers, fetchFeaturedPerformers, fetchLeaderboard]);

  const handleSearch = () => {
    searchPerformers({
      query: searchQuery || undefined,
      type: filterType,
      is_verified: filterVerified,
      sort_by: sortBy,
    });
  };

  const handlePerformerSelect = (performer: Performer) => {
    setSelectedPerformer(performer);
  };

  const handleBook = (performer: Performer, mode: BookingMode) => {
    setSelectedPerformer(performer);
    openBookingModal(mode);
  };

  const handleRefresh = () => {
    searchPerformers();
    fetchFeaturedPerformers();
    fetchLeaderboard();
  };

  return (
    <div className="min-h-full bg-gray-950">
      {/* Header */}
      <div className="border-b border-gray-800 bg-gray-900/50 backdrop-blur sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                <Users className="w-7 h-7 text-blue-400" />
                ActForge
              </h1>
              <p className="text-gray-400 text-sm">Talent Marketplace for ActCore Performers</p>
            </div>
            <button
              onClick={handleRefresh}
              disabled={isLoadingPerformers}
              className="p-2 hover:bg-gray-800 rounded-lg transition-colors disabled:opacity-50"
              aria-label="Refresh"
            >
              <RefreshCw
                className={`w-5 h-5 text-gray-400 ${isLoadingPerformers ? 'animate-spin' : ''}`}
              />
            </button>
          </div>

          {/* Search and filters */}
          <div className="flex gap-3">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search performers..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                className="w-full pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-400 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none"
              />
            </div>
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`px-4 py-2 rounded-lg border transition-colors flex items-center gap-2 ${
                showFilters
                  ? 'bg-blue-500 border-blue-500 text-white'
                  : 'bg-gray-800 border-gray-700 text-gray-300 hover:bg-gray-700'
              }`}
            >
              <Filter className="w-4 h-4" />
              Filters
              <ChevronDown
                className={`w-4 h-4 transition-transform ${showFilters ? 'rotate-180' : ''}`}
              />
            </button>
            <button
              onClick={handleSearch}
              className="px-6 py-2 bg-blue-500 hover:bg-blue-400 text-white rounded-lg font-medium transition-colors"
            >
              Search
            </button>
          </div>

          {/* Filter panel */}
          {showFilters && (
            <div className="mt-4 p-4 bg-gray-800 rounded-lg grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Type</label>
                <select
                  value={filterType ?? ''}
                  onChange={(e) => setFilterType((e.target.value as PerformerType) || undefined)}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white"
                >
                  <option value="">All Types</option>
                  <option value="HUMAN">Human</option>
                  <option value="SYNTHETIC">Synthetic</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Verified</label>
                <select
                  value={filterVerified === undefined ? '' : filterVerified ? 'true' : 'false'}
                  onChange={(e) =>
                    setFilterVerified(e.target.value === '' ? undefined : e.target.value === 'true')
                  }
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white"
                >
                  <option value="">All</option>
                  <option value="true">Verified Only</option>
                  <option value="false">Unverified Only</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Sort By</label>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white"
                >
                  <option value="aci_score">ACI Score</option>
                  <option value="price">Price (Low to High)</option>
                  <option value="rating">Rating</option>
                  <option value="bookings">Most Bookings</option>
                </select>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* Featured Section */}
        {featuredPerformers.length > 0 && (
          <section className="mb-8">
            <div className="flex items-center gap-2 mb-4">
              <Star className="w-5 h-5 text-yellow-400" />
              <h2 className="text-lg font-semibold text-white">Featured Performers</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {featuredPerformers.map((performer) => (
                <PerformerCard
                  key={performer.id}
                  performer={performer}
                  onSelect={handlePerformerSelect}
                  onBook={handleBook}
                />
              ))}
            </div>
          </section>
        )}

        {/* Quick Book Section */}
        <section className="mb-8 p-4 bg-gradient-to-r from-gray-900 to-gray-800 rounded-xl border border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <Zap className="w-5 h-5 text-yellow-400" />
                Quick Blink Booking
              </h2>
              <p className="text-sm text-gray-400 mt-1">
                Get a 10-second auto-matched performer instantly
              </p>
            </div>
            <button
              onClick={() => openBookingModal('BLINK')}
              className="px-6 py-3 bg-yellow-500 hover:bg-yellow-400 text-black font-bold rounded-lg transition-colors flex items-center gap-2"
            >
              <Zap className="w-5 h-5" />
              Quick Book
            </button>
          </div>
        </section>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Main content - Performer grid */}
          <div className="lg:col-span-3">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-blue-400" />
                All Performers
                <span className="text-sm text-gray-400 font-normal">({searchTotal} total)</span>
              </h2>
            </div>

            {isLoadingPerformers && performers.length === 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {[...Array(6)].map((_, i) => (
                  <div
                    key={i}
                    className="bg-gray-900 rounded-xl border border-gray-800 p-4 animate-pulse"
                  >
                    <div className="aspect-[4/3] bg-gray-800 rounded-lg mb-4" />
                    <div className="h-4 bg-gray-800 rounded w-2/3 mb-2" />
                    <div className="h-3 bg-gray-800 rounded w-1/2" />
                  </div>
                ))}
              </div>
            ) : performers.length === 0 ? (
              <div className="text-center py-12 bg-gray-900 rounded-xl border border-gray-800">
                <Users className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                <h3 className="text-lg font-medium text-white mb-1">No performers found</h3>
                <p className="text-gray-400">Try adjusting your search filters</p>
              </div>
            ) : (
              <>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {performers.map((performer) => (
                    <PerformerCard
                      key={performer.id}
                      performer={performer}
                      onSelect={handlePerformerSelect}
                      onBook={handleBook}
                    />
                  ))}
                </div>

                {searchHasMore && (
                  <div className="mt-6 text-center">
                    <button
                      onClick={loadMorePerformers}
                      disabled={isLoadingPerformers}
                      className="px-6 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-lg transition-colors disabled:opacity-50"
                    >
                      {isLoadingPerformers ? 'Loading...' : 'Load More'}
                    </button>
                  </div>
                )}
              </>
            )}
          </div>

          {/* Sidebar - Leaderboard */}
          <div className="lg:col-span-1">
            <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 sticky top-28">
              <h2 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
                <Trophy className="w-5 h-5 text-yellow-400" />
                ACI Leaderboard
              </h2>

              {leaderboard.length === 0 ? (
                <div className="text-center py-8 text-gray-400">
                  <Trophy className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">Loading leaderboard...</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {leaderboard.map((entry, index) => (
                    <div
                      key={entry.performer_id}
                      className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-800 transition-colors cursor-pointer"
                    >
                      {/* Rank */}
                      <div
                        className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                          index === 0
                            ? 'bg-yellow-500 text-black'
                            : index === 1
                              ? 'bg-gray-400 text-black'
                              : index === 2
                                ? 'bg-amber-600 text-white'
                                : 'bg-gray-700 text-gray-300'
                        }`}
                      >
                        {entry.rank}
                      </div>

                      {/* Avatar */}
                      <div className="w-8 h-8 rounded-full bg-gray-700 overflow-hidden flex-shrink-0">
                        {entry.avatar_url ? (
                          <img
                            src={entry.avatar_url}
                            alt={entry.stage_name}
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center text-gray-400 text-xs">
                            ?
                          </div>
                        )}
                      </div>

                      {/* Info */}
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-white truncate">
                          {entry.stage_name}
                        </div>
                        <div className="text-xs text-gray-400">
                          {entry.completed_bookings} bookings
                        </div>
                      </div>

                      {/* ACI */}
                      <div className="text-sm font-bold text-blue-400">
                        {entry.aci_score.toFixed(0)}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Booking Modal */}
      <BookingModal
        isOpen={showBookingModal}
        onClose={closeBookingModal}
        performer={selectedPerformer}
        mode={bookingMode ?? 'BLINK'}
        projectId={currentProject?.id ?? ''}
        onSuccess={() => {
          setSelectedPerformer(null);
        }}
      />
    </div>
  );
}

export default ActForgePage;
