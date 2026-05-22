/**
 * ActForge state store using Zustand.
 *
 * Manages state for the ActForge talent marketplace including
 * performer search, bookings, and payout calculations.
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
import {
  api,
  type Performer,
  type PerformerSearchParams,
  type Booking,
  type BookingMode,
  type BookingStatus,
  type PayoutCalculation,
  type ACIBreakdown,
  type PerformerLeaderboardEntry,
} from '../api/client';

interface ActForgeStoreState {
  // Performers
  performers: Performer[];
  featuredPerformers: Performer[];
  leaderboard: PerformerLeaderboardEntry[];
  selectedPerformer: Performer | null;
  selectedPerformerACI: ACIBreakdown | null;

  // Search state
  searchParams: PerformerSearchParams;
  searchTotal: number;
  searchHasMore: boolean;

  // Bookings
  activeBookings: Booking[];
  selectedBooking: Booking | null;

  // Payout calculator
  payoutEstimate: PayoutCalculation | null;

  // UI state
  isLoadingPerformers: boolean;
  isLoadingBookings: boolean;
  isCreatingBooking: boolean;
  bookingMode: BookingMode | null;
  showBookingModal: boolean;

  // Error state
  error: string | null;

  // Actions: Performers
  searchPerformers: (params?: PerformerSearchParams) => Promise<void>;
  loadMorePerformers: () => Promise<void>;
  fetchFeaturedPerformers: () => Promise<void>;
  fetchLeaderboard: () => Promise<void>;
  selectPerformer: (performerId: string) => Promise<void>;
  clearSelectedPerformer: () => void;

  // Actions: Bookings
  fetchProjectBookings: (projectId: string, status?: BookingStatus) => Promise<void>;
  createBlinkBooking: (
    projectId: string,
    shotId?: string,
    performerId?: string,
    durationSeconds?: number
  ) => Promise<Booking | null>;
  createDeepBooking: (
    projectId: string,
    performerId: string,
    shotId?: string,
    durationSeconds?: number,
    requirements?: { emotion_markers?: string[]; special_instructions?: string }
  ) => Promise<Booking | null>;
  createEpicBooking: (
    projectId: string,
    performerId: string,
    shotId?: string,
    durationSeconds?: number,
    requirements?: { emotion_markers?: string[]; special_instructions?: string }
  ) => Promise<Booking | null>;
  acceptBooking: (bookingId: string) => Promise<boolean>;
  deliverBooking: (bookingId: string, deliveryUrl: string, notes?: string) => Promise<boolean>;
  approveBooking: (bookingId: string) => Promise<boolean>;
  disputeBooking: (bookingId: string, reason: string) => Promise<boolean>;
  rateBooking: (
    bookingId: string,
    rating: number,
    review?: string,
    wouldRehire?: boolean
  ) => Promise<boolean>;
  selectBooking: (booking: Booking | null) => void;

  // Actions: Payout Calculator
  calculatePayout: (bookingPriceUsd: number, lifetimeEarningsUsd: number) => Promise<void>;

  // Actions: UI
  setBookingMode: (mode: BookingMode | null) => void;
  openBookingModal: (mode: BookingMode) => void;
  closeBookingModal: () => void;
  clearError: () => void;

  // Computed helpers
  getPerformerById: (id: string) => Performer | undefined;
  getBookingsByStatus: (status: BookingStatus) => Booking[];
}

const initialState = {
  performers: [],
  featuredPerformers: [],
  leaderboard: [],
  selectedPerformer: null,
  selectedPerformerACI: null,
  searchParams: {
    limit: 20,
    offset: 0,
    sort_by: 'aci_score' as const,
    sort_order: 'desc' as const,
  },
  searchTotal: 0,
  searchHasMore: false,
  activeBookings: [],
  selectedBooking: null,
  payoutEstimate: null,
  isLoadingPerformers: false,
  isLoadingBookings: false,
  isCreatingBooking: false,
  bookingMode: null,
  showBookingModal: false,
  error: null,
};

export const useActForgeStore = create<ActForgeStoreState>()(
  devtools(
    persist(
      immer((set, get) => ({
        ...initialState,

        // ============ Performer Actions ============

        searchPerformers: async (params?: PerformerSearchParams) => {
          set((state) => {
            state.isLoadingPerformers = true;
            state.error = null;
            if (params) {
              state.searchParams = { ...state.searchParams, ...params, offset: 0 };
            }
          });

          try {
            const currentParams = get().searchParams;
            const result = await api.searchPerformers(currentParams);
            set((state) => {
              state.performers = result.performers;
              state.searchTotal = result.total;
              state.searchHasMore = result.hasMore;
              state.isLoadingPerformers = false;
            });
          } catch (error) {
            console.error('Failed to search performers:', error);
            set((state) => {
              state.isLoadingPerformers = false;
              state.error = error instanceof Error ? error.message : 'Failed to search performers';
            });
          }
        },

        loadMorePerformers: async () => {
          const { searchParams, searchHasMore, isLoadingPerformers } = get();
          if (!searchHasMore || isLoadingPerformers) return;

          set((state) => {
            state.isLoadingPerformers = true;
          });

          try {
            const newOffset = (searchParams.offset ?? 0) + (searchParams.limit ?? 20);
            const result = await api.searchPerformers({ ...searchParams, offset: newOffset });
            set((state) => {
              state.performers = [...state.performers, ...result.performers];
              state.searchParams.offset = newOffset;
              state.searchHasMore = result.hasMore;
              state.isLoadingPerformers = false;
            });
          } catch (error) {
            console.error('Failed to load more performers:', error);
            set((state) => {
              state.isLoadingPerformers = false;
            });
          }
        },

        fetchFeaturedPerformers: async () => {
          try {
            const featured = await api.getFeaturedPerformers(6);
            set((state) => {
              state.featuredPerformers = featured;
            });
          } catch (error) {
            console.error('Failed to fetch featured performers:', error);
          }
        },

        fetchLeaderboard: async () => {
          try {
            const leaderboard = await api.getPerformerLeaderboard(10);
            set((state) => {
              state.leaderboard = leaderboard;
            });
          } catch (error) {
            console.error('Failed to fetch leaderboard:', error);
          }
        },

        selectPerformer: async (performerId: string) => {
          set((state) => {
            state.isLoadingPerformers = true;
          });

          try {
            const [performer, aci] = await Promise.all([
              api.getPerformer(performerId),
              api.getPerformerACI(performerId),
            ]);
            set((state) => {
              state.selectedPerformer = performer;
              state.selectedPerformerACI = aci;
              state.isLoadingPerformers = false;
            });
          } catch (error) {
            console.error('Failed to select performer:', error);
            set((state) => {
              state.isLoadingPerformers = false;
              state.error = error instanceof Error ? error.message : 'Failed to load performer';
            });
          }
        },

        clearSelectedPerformer: () => {
          set((state) => {
            state.selectedPerformer = null;
            state.selectedPerformerACI = null;
          });
        },

        // ============ Booking Actions ============

        fetchProjectBookings: async (projectId: string, status?: BookingStatus) => {
          set((state) => {
            state.isLoadingBookings = true;
          });

          try {
            const bookings = await api.listProjectBookings(projectId, status);
            set((state) => {
              state.activeBookings = bookings;
              state.isLoadingBookings = false;
            });
          } catch (error) {
            console.error('Failed to fetch bookings:', error);
            set((state) => {
              state.isLoadingBookings = false;
              state.error = error instanceof Error ? error.message : 'Failed to fetch bookings';
            });
          }
        },

        createBlinkBooking: async (projectId, shotId, performerId, durationSeconds = 10) => {
          set((state) => {
            state.isCreatingBooking = true;
            state.error = null;
          });

          try {
            const booking = await api.createBlinkBooking({
              project_id: projectId,
              shot_id: shotId,
              performer_id: performerId,
              duration_seconds: durationSeconds,
            });
            set((state) => {
              state.activeBookings.push(booking);
              state.isCreatingBooking = false;
              state.showBookingModal = false;
            });
            return booking;
          } catch (error) {
            console.error('Failed to create BLINK booking:', error);
            set((state) => {
              state.isCreatingBooking = false;
              state.error = error instanceof Error ? error.message : 'Failed to create booking';
            });
            return null;
          }
        },

        createDeepBooking: async (
          projectId,
          performerId,
          shotId,
          durationSeconds = 60,
          requirements
        ) => {
          set((state) => {
            state.isCreatingBooking = true;
            state.error = null;
          });

          try {
            const booking = await api.createDeepBooking({
              project_id: projectId,
              shot_id: shotId,
              performer_id: performerId,
              duration_seconds: durationSeconds,
              emotion_markers: requirements?.emotion_markers,
              special_instructions: requirements?.special_instructions,
            });
            set((state) => {
              state.activeBookings.push(booking);
              state.isCreatingBooking = false;
              state.showBookingModal = false;
            });
            return booking;
          } catch (error) {
            console.error('Failed to create DEEP booking:', error);
            set((state) => {
              state.isCreatingBooking = false;
              state.error = error instanceof Error ? error.message : 'Failed to create booking';
            });
            return null;
          }
        },

        createEpicBooking: async (
          projectId,
          performerId,
          shotId,
          durationSeconds = 300,
          requirements
        ) => {
          set((state) => {
            state.isCreatingBooking = true;
            state.error = null;
          });

          try {
            const booking = await api.createEpicBooking({
              project_id: projectId,
              shot_id: shotId,
              performer_id: performerId,
              duration_seconds: durationSeconds,
              emotion_markers: requirements?.emotion_markers,
              special_instructions: requirements?.special_instructions,
            });
            set((state) => {
              state.activeBookings.push(booking);
              state.isCreatingBooking = false;
              state.showBookingModal = false;
            });
            return booking;
          } catch (error) {
            console.error('Failed to create EPIC booking:', error);
            set((state) => {
              state.isCreatingBooking = false;
              state.error = error instanceof Error ? error.message : 'Failed to create booking';
            });
            return null;
          }
        },

        acceptBooking: async (bookingId) => {
          try {
            const updated = await api.acceptBooking(bookingId);
            set((state) => {
              const index = state.activeBookings.findIndex((b) => b.id === bookingId);
              if (index !== -1) {
                state.activeBookings[index] = updated;
              }
              if (state.selectedBooking?.id === bookingId) {
                state.selectedBooking = updated;
              }
            });
            return true;
          } catch (error) {
            console.error('Failed to accept booking:', error);
            return false;
          }
        },

        deliverBooking: async (bookingId, deliveryUrl, notes) => {
          try {
            const updated = await api.deliverBooking(bookingId, deliveryUrl, notes);
            set((state) => {
              const index = state.activeBookings.findIndex((b) => b.id === bookingId);
              if (index !== -1) {
                state.activeBookings[index] = updated;
              }
              if (state.selectedBooking?.id === bookingId) {
                state.selectedBooking = updated;
              }
            });
            return true;
          } catch (error) {
            console.error('Failed to deliver booking:', error);
            return false;
          }
        },

        approveBooking: async (bookingId) => {
          try {
            const updated = await api.approveBooking(bookingId);
            set((state) => {
              const index = state.activeBookings.findIndex((b) => b.id === bookingId);
              if (index !== -1) {
                state.activeBookings[index] = updated;
              }
              if (state.selectedBooking?.id === bookingId) {
                state.selectedBooking = updated;
              }
            });
            return true;
          } catch (error) {
            console.error('Failed to approve booking:', error);
            return false;
          }
        },

        disputeBooking: async (bookingId, reason) => {
          try {
            const updated = await api.disputeBooking(bookingId, reason);
            set((state) => {
              const index = state.activeBookings.findIndex((b) => b.id === bookingId);
              if (index !== -1) {
                state.activeBookings[index] = updated;
              }
              if (state.selectedBooking?.id === bookingId) {
                state.selectedBooking = updated;
              }
            });
            return true;
          } catch (error) {
            console.error('Failed to dispute booking:', error);
            return false;
          }
        },

        rateBooking: async (bookingId, rating, review, wouldRehire) => {
          try {
            const updated = await api.rateBooking(bookingId, rating, review, wouldRehire);
            set((state) => {
              const index = state.activeBookings.findIndex((b) => b.id === bookingId);
              if (index !== -1) {
                state.activeBookings[index] = updated;
              }
              if (state.selectedBooking?.id === bookingId) {
                state.selectedBooking = updated;
              }
            });
            return true;
          } catch (error) {
            console.error('Failed to rate booking:', error);
            return false;
          }
        },

        selectBooking: (booking) => {
          set((state) => {
            state.selectedBooking = booking;
          });
        },

        // ============ Payout Calculator ============

        calculatePayout: async (bookingPriceUsd, lifetimeEarningsUsd) => {
          try {
            const payout = await api.calculatePayout(bookingPriceUsd, lifetimeEarningsUsd);
            set((state) => {
              state.payoutEstimate = payout;
            });
          } catch (error) {
            console.error('Failed to calculate payout:', error);
          }
        },

        // ============ UI Actions ============

        setBookingMode: (mode) => {
          set((state) => {
            state.bookingMode = mode;
          });
        },

        openBookingModal: (mode) => {
          set((state) => {
            state.bookingMode = mode;
            state.showBookingModal = true;
          });
        },

        closeBookingModal: () => {
          set((state) => {
            state.showBookingModal = false;
            state.bookingMode = null;
          });
        },

        clearError: () => {
          set((state) => {
            state.error = null;
          });
        },

        // ============ Computed Helpers ============

        getPerformerById: (id: string) => {
          return get().performers.find((p) => p.id === id);
        },

        getBookingsByStatus: (status: BookingStatus) => {
          return get().activeBookings.filter((b) => b.status === status);
        },
      })),
      {
        name: 'scenemachine-actforge-store',
        partialize: (state) => ({
          // Only persist search preferences
          searchParams: {
            sort_by: state.searchParams.sort_by,
            sort_order: state.searchParams.sort_order,
          },
        }),
      }
    ),
    { name: 'ActForgeStore' }
  )
);

/**
 * Hook to get ACI tier badge color.
 */
export function useACIBadgeColor(aciScore: number): string {
  if (aciScore >= 90) return 'text-yellow-400'; // Gold
  if (aciScore >= 75) return 'text-purple-400'; // Elite
  if (aciScore >= 60) return 'text-blue-400'; // Pro
  if (aciScore >= 40) return 'text-green-400'; // Established
  return 'text-gray-400'; // Emerging
}

/**
 * Hook to get revenue tier label.
 */
export function useRevenueTierLabel(tier: number): string {
  const labels: Record<number, string> = {
    1: 'Emerging (50/50)',
    2: 'Rising (60/40)',
    3: 'Established (70/30)',
    4: 'Professional (80/20)',
    5: 'Elite (90/10)',
    6: 'Legend (99/1)',
  };
  return labels[tier] ?? 'Unknown';
}

/**
 * Hook to get booking mode info.
 */
export function useBookingModeInfo(mode: BookingMode): {
  label: string;
  description: string;
  maxDuration: number;
  icon: string;
} {
  const modes = {
    BLINK: {
      label: 'Blink',
      description: '10-second quick generation with auto-matched performer',
      maxDuration: 10,
      icon: 'zap',
    },
    DEEP: {
      label: 'Deep',
      description: 'Method acting up to 120 seconds with emotion markers',
      maxDuration: 120,
      icon: 'heart',
    },
    EPIC: {
      label: 'Epic',
      description: 'Long-form 5-20 minute dedicated session',
      maxDuration: 1200,
      icon: 'crown',
    },
    AUCTION: {
      label: 'Auction',
      description: 'Competitive bidding for premium talent',
      maxDuration: 600,
      icon: 'gavel',
    },
  };
  return modes[mode];
}
