/**
 * Creator Store
 *
 * State management for creator dashboard, analytics, and content management.
 */

import { create } from 'zustand';
import { apiClient, Video } from '../lib/api-client';

export interface DashboardStats {
  total_views: number;
  total_watch_time_minutes: number;
  total_subscribers: number;
  total_revenue: number;
  views_change: number;
  subscribers_change: number;
  revenue_change: number;
}

export interface DailyStats {
  date: string;
  views: number;
  watch_time: number;
  revenue: number;
}

export interface TopVideo {
  video: Video;
  views: number;
  watch_time: number;
  revenue: number;
}

export interface EarningsData {
  balance: number;
  pending_balance: number;
  lifetime_earnings: number;
  current_tier: number;
  current_rate: number;
  next_tier_threshold: number;
  progress_to_next_tier: number;
  breakdown: {
    ad_revenue: number;
    ticket_sales: number;
    tips: number;
    subscriptions: number;
  };
}

export interface Transaction {
  id: string;
  type: 'AD_REVENUE' | 'TICKET_SALE' | 'TIP' | 'SUBSCRIPTION';
  amount: number;
  video_title?: string;
  created_at: string;
}

export interface Payout {
  id: string;
  amount: number;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  created_at: string;
  processed_at?: string;
}

export type TimeRange = '7d' | '30d' | '90d' | 'all';

interface CreatorState {
  // Dashboard
  stats: DashboardStats | null;
  dailyStats: DailyStats[];
  topVideos: TopVideo[];
  timeRange: TimeRange;
  isLoadingDashboard: boolean;

  // Content
  videos: Video[];
  isLoadingVideos: boolean;
  selectedVideos: string[];

  // Earnings
  earnings: EarningsData | null;
  transactions: Transaction[];
  payouts: Payout[];
  isLoadingEarnings: boolean;

  // Actions
  setTimeRange: (range: TimeRange) => void;
  loadDashboard: () => Promise<void>;
  loadVideos: () => Promise<void>;
  loadEarnings: () => Promise<void>;
  selectVideo: (videoId: string) => void;
  deselectVideo: (videoId: string) => void;
  selectAllVideos: () => void;
  deselectAllVideos: () => void;
  deleteSelectedVideos: () => Promise<void>;
  requestPayout: () => Promise<boolean>;
  refreshAll: () => Promise<void>;
}

export const useCreatorStore = create<CreatorState>((set, get) => ({
  // Initial state
  stats: null,
  dailyStats: [],
  topVideos: [],
  timeRange: '30d',
  isLoadingDashboard: false,

  videos: [],
  isLoadingVideos: false,
  selectedVideos: [],

  earnings: null,
  transactions: [],
  payouts: [],
  isLoadingEarnings: false,

  // Actions
  setTimeRange: (range) => {
    set({ timeRange: range });
    // Reload data with new time range
    get().loadDashboard();
    get().loadEarnings();
  },

  loadDashboard: async () => {
    set({ isLoadingDashboard: true });
    try {
      const { timeRange } = get();
      const data = await apiClient.getCreatorDashboard(timeRange);

      // Transform API stats to local format
      const apiStats = data.stats;
      const stats: DashboardStats = {
        total_views: apiStats?.total_views || 0,
        total_watch_time_minutes: (apiStats?.total_watch_time_hours || 0) * 60,
        total_subscribers: apiStats?.subscriber_count || 0,
        total_revenue: apiStats?.total_earnings || 0,
        views_change: apiStats?.views_change_percent || 0,
        subscribers_change: 0, // Not in API response
        revenue_change: apiStats?.earnings_change_percent || 0,
      };

      set({
        stats,
        dailyStats: data.daily_stats || [],
        topVideos: data.top_videos || [],
        isLoadingDashboard: false,
      });
    } catch (error) {
      console.error('Failed to load dashboard:', error);
      set({ isLoadingDashboard: false });
    }
  },

  loadVideos: async () => {
    set({ isLoadingVideos: true });
    try {
      const response = await apiClient.getMyVideos();
      set({ videos: response.items, isLoadingVideos: false });
    } catch (error) {
      console.error('Failed to load videos:', error);
      set({ isLoadingVideos: false });
    }
  },

  loadEarnings: async () => {
    set({ isLoadingEarnings: true });
    try {
      const { timeRange } = get();
      const [earningsData, transactionsData, payoutsData] = await Promise.all([
        apiClient.getEarnings(timeRange),
        apiClient.getTransactions(timeRange),
        apiClient.getPayoutHistory(),
      ]);

      // Map API response to store format
      const earnings: EarningsData = {
        balance: earningsData.total_earnings - (earningsData.pending_payout || 0),
        pending_balance: earningsData.pending_payout || 0,
        lifetime_earnings: earningsData.total_earnings,
        current_tier: 1, // Calculate based on earnings
        current_rate: 50, // 50% at tier 1
        next_tier_threshold: 1000,
        progress_to_next_tier: Math.min((earningsData.total_earnings / 1000) * 100, 100),
        breakdown: {
          ad_revenue: earningsData.earnings_by_source?.ads || 0,
          ticket_sales: earningsData.earnings_by_source?.tickets || 0,
          tips: earningsData.earnings_by_source?.tips || 0,
          subscriptions: earningsData.earnings_by_source?.subscriptions || 0,
        },
      };

      set({
        earnings,
        transactions: transactionsData.transactions || [],
        payouts: (payoutsData.items || []).map(p => ({
          ...p,
          status: p.status.toUpperCase() as Payout['status'],
        })),
        isLoadingEarnings: false,
      });
    } catch (error) {
      console.error('Failed to load earnings:', error);
      set({ isLoadingEarnings: false });
    }
  },

  selectVideo: (videoId) => {
    set((state) => ({
      selectedVideos: [...state.selectedVideos, videoId],
    }));
  },

  deselectVideo: (videoId) => {
    set((state) => ({
      selectedVideos: state.selectedVideos.filter((id) => id !== videoId),
    }));
  },

  selectAllVideos: () => {
    set((state) => ({
      selectedVideos: state.videos.map((v) => v.id),
    }));
  },

  deselectAllVideos: () => {
    set({ selectedVideos: [] });
  },

  deleteSelectedVideos: async () => {
    const { selectedVideos } = get();
    try {
      await Promise.all(
        selectedVideos.map((id) => apiClient.deleteVideo(id))
      );
      set((state) => ({
        videos: state.videos.filter((v) => !selectedVideos.includes(v.id)),
        selectedVideos: [],
      }));
    } catch (error) {
      console.error('Failed to delete videos:', error);
      throw error;
    }
  },

  requestPayout: async () => {
    try {
      await apiClient.requestPayout();
      // Refresh earnings data
      await get().loadEarnings();
      return true;
    } catch (error) {
      console.error('Failed to request payout:', error);
      return false;
    }
  },

  refreshAll: async () => {
    await Promise.all([
      get().loadDashboard(),
      get().loadVideos(),
      get().loadEarnings(),
    ]);
  },
}));

export default useCreatorStore;
