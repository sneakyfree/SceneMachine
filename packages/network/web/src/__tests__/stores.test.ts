/**
 * Stores Tests
 *
 * Tests for Zustand stores.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { act } from '@testing-library/react';

// Mock the API client
vi.mock('../lib/api-client', () => ({
  api: {
    login: vi.fn(),
    logout: vi.fn(),
    register: vi.fn(),
    getCurrentUser: vi.fn(),
    updateProfile: vi.fn(),
    isAuthenticated: vi.fn(() => false),
    changePassword: vi.fn(),
    requestPasswordReset: vi.fn(),
    resetPassword: vi.fn(),
    uploadAvatar: vi.fn(),
    uploadBanner: vi.fn(),
  },
  apiClient: {
    getCreatorDashboard: vi.fn(),
    getMyVideos: vi.fn(),
    getEarnings: vi.fn(),
    getTransactions: vi.fn(),
    getPayoutHistory: vi.fn(),
    deleteVideo: vi.fn(),
    requestPayout: vi.fn(),
  },
}));

import { useAuthStore } from '../stores/auth-store';
import { useCreatorStore } from '../stores/creator-store';
import { api } from '../lib/api-client';
import { apiClient } from '../lib/api-client';

describe('useAuthStore', () => {
  beforeEach(() => {
    // Reset store state
    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
    });
    vi.clearAllMocks();
  });

  describe('login', () => {
    it('should set user and authenticated state on successful login', async () => {
      const mockUser = {
        id: '123',
        email: 'test@example.com',
        username: 'testuser',
        display_name: 'Test User',
        avatar_url: null,
        bio: null,
        is_verified: false,
        is_creator: false,
        follower_count: 0,
        following_count: 0,
        created_at: new Date().toISOString(),
      };

      vi.mocked(api.login).mockResolvedValueOnce({
        access_token: 'token',
        refresh_token: 'refresh',
        token_type: 'bearer',
        expires_in: 3600,
        user: mockUser,
      });

      await act(async () => {
        await useAuthStore.getState().login('test@example.com', 'password');
      });

      const state = useAuthStore.getState();
      expect(state.user).toEqual(mockUser);
      expect(state.isAuthenticated).toBe(true);
      expect(state.isLoading).toBe(false);
      expect(state.error).toBeNull();
    });

    it('should set error on failed login', async () => {
      vi.mocked(api.login).mockRejectedValueOnce({
        message: 'Invalid credentials',
        status: 401,
      });

      await expect(
        useAuthStore.getState().login('test@example.com', 'wrong')
      ).rejects.toBeDefined();

      const state = useAuthStore.getState();
      expect(state.user).toBeNull();
      expect(state.isAuthenticated).toBe(false);
      expect(state.error).toBe('Invalid credentials');
    });
  });

  describe('logout', () => {
    it('should clear user state on logout', async () => {
      useAuthStore.setState({
        user: { id: '123' } as any,
        isAuthenticated: true,
      });

      vi.mocked(api.logout).mockResolvedValueOnce(undefined);

      await act(async () => {
        await useAuthStore.getState().logout();
      });

      const state = useAuthStore.getState();
      expect(state.user).toBeNull();
      expect(state.isAuthenticated).toBe(false);
    });

    it('should clear state even if logout API fails', async () => {
      useAuthStore.setState({
        user: { id: '123' } as any,
        isAuthenticated: true,
      });

      vi.mocked(api.logout).mockRejectedValueOnce(new Error('API error'));

      await act(async () => {
        await useAuthStore.getState().logout();
      });

      const state = useAuthStore.getState();
      expect(state.user).toBeNull();
      expect(state.isAuthenticated).toBe(false);
    });
  });

  describe('clearError', () => {
    it('should clear the error state', () => {
      useAuthStore.setState({ error: 'Some error' });

      act(() => {
        useAuthStore.getState().clearError();
      });

      expect(useAuthStore.getState().error).toBeNull();
    });
  });
});

describe('useCreatorStore', () => {
  beforeEach(() => {
    // Reset store state
    useCreatorStore.setState({
      stats: null,
      dailyStats: [],
      topVideos: [],
      timeRange: '28d',
      isLoadingDashboard: false,
      videos: [],
      isLoadingVideos: false,
      selectedVideos: [],
      earnings: null,
      transactions: [],
      payouts: [],
      isLoadingEarnings: false,
    });
    vi.clearAllMocks();
  });

  describe('loadDashboard', () => {
    it('should load dashboard data', async () => {
      const mockData = {
        stats: {
          total_views: 1000,
          total_watch_time_hours: 50,
          total_earnings: 100,
          subscriber_count: 10,
          video_count: 5,
          views_change_percent: 10,
          earnings_change_percent: 5,
        },
        daily_stats: [{ date: '2024-01-01', views: 100, watch_time: 5, revenue: 10 }],
        top_videos: [],
      };

      vi.mocked(apiClient.getCreatorDashboard).mockResolvedValueOnce(mockData);

      await act(async () => {
        await useCreatorStore.getState().loadDashboard();
      });

      const state = useCreatorStore.getState();
      expect(state.stats).toEqual(mockData.stats);
      expect(state.dailyStats).toEqual(mockData.daily_stats);
      expect(state.isLoadingDashboard).toBe(false);
    });
  });

  describe('loadVideos', () => {
    it('should load creator videos', async () => {
      const mockVideos = {
        items: [
          { id: '1', title: 'Video 1' },
          { id: '2', title: 'Video 2' },
        ],
        total: 2,
        page: 1,
        page_size: 20,
        has_more: false,
      };

      vi.mocked(apiClient.getMyVideos).mockResolvedValueOnce(mockVideos);

      await act(async () => {
        await useCreatorStore.getState().loadVideos();
      });

      const state = useCreatorStore.getState();
      expect(state.videos).toEqual(mockVideos.items);
      expect(state.isLoadingVideos).toBe(false);
    });
  });

  describe('video selection', () => {
    it('should select and deselect videos', () => {
      useCreatorStore.setState({
        videos: [{ id: '1' }, { id: '2' }, { id: '3' }] as any[],
      });

      act(() => {
        useCreatorStore.getState().selectVideo('1');
      });
      expect(useCreatorStore.getState().selectedVideos).toContain('1');

      act(() => {
        useCreatorStore.getState().selectVideo('2');
      });
      expect(useCreatorStore.getState().selectedVideos).toEqual(['1', '2']);

      act(() => {
        useCreatorStore.getState().deselectVideo('1');
      });
      expect(useCreatorStore.getState().selectedVideos).toEqual(['2']);
    });

    it('should select and deselect all videos', () => {
      useCreatorStore.setState({
        videos: [{ id: '1' }, { id: '2' }, { id: '3' }] as any[],
      });

      act(() => {
        useCreatorStore.getState().selectAllVideos();
      });
      expect(useCreatorStore.getState().selectedVideos).toEqual(['1', '2', '3']);

      act(() => {
        useCreatorStore.getState().deselectAllVideos();
      });
      expect(useCreatorStore.getState().selectedVideos).toEqual([]);
    });
  });

  describe('setTimeRange', () => {
    it('should update time range', () => {
      // Mock the API calls that setTimeRange triggers
      vi.mocked(apiClient.getCreatorDashboard).mockResolvedValue({
        stats: { total_views: 0, total_watch_time_hours: 0, total_earnings: 0, subscriber_count: 0, video_count: 0, views_change_percent: 0, earnings_change_percent: 0 },
        daily_stats: [],
        top_videos: [],
      });
      vi.mocked(apiClient.getEarnings).mockResolvedValue({
        total_earnings: 0,
        pending_payout: 0,
        last_payout_amount: 0,
        last_payout_date: null,
        earnings_by_source: { ad_revenue: 0, ticket_sales: 0, tips: 0, subscriptions: 0 },
      });
      vi.mocked(apiClient.getTransactions).mockResolvedValue({
        transactions: [],
        total: 0,
        page: 1,
        page_size: 20,
      });
      vi.mocked(apiClient.getPayoutHistory).mockResolvedValue({
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
        has_more: false,
      });

      act(() => {
        useCreatorStore.getState().setTimeRange('7d');
      });

      expect(useCreatorStore.getState().timeRange).toBe('7d');
    });
  });
});
