/**
 * API Client Tests
 *
 * Tests for the NetworkAPIClient class.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Import after mocking
import { api } from '../lib/api-client';

describe('NetworkAPIClient', () => {
  beforeEach(() => {
    mockFetch.mockReset();
    // Clear localStorage
    if (typeof window !== 'undefined') {
      localStorage.clear();
    }
    // Ensure api is logged out for clean test state
    api.logout().catch(() => {
      // Ignore logout errors in tests
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('authentication', () => {
    it('should login successfully', async () => {
      const mockResponse = {
        access_token: 'test-token',
        refresh_token: 'test-refresh',
        token_type: 'bearer',
        expires_in: 3600,
        user: {
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
        },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
        text: async () => JSON.stringify(mockResponse),
      });

      const result = await api.login('test@example.com', 'password');

      expect(result).toEqual(mockResponse);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/auth/login'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ email: 'test@example.com', password: 'password' }),
        })
      );
    });

    it('should handle login failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        json: async () => ({ detail: 'Invalid credentials' }),
      });

      await expect(api.login('test@example.com', 'wrong')).rejects.toMatchObject({
        message: 'Invalid credentials',
        status: 401,
      });
    });

    it('should check if authenticated after logout', () => {
      // After logout, should not be authenticated
      expect(api.isAuthenticated()).toBe(false);
    });
  });

  describe('videos', () => {
    it('should fetch a video by ID', async () => {
      const mockVideo = {
        id: 'video-123',
        title: 'Test Video',
        description: 'A test video',
        creator_id: 'user-123',
        status: 'PUBLISHED',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockVideo,
        text: async () => JSON.stringify(mockVideo),
      });

      const result = await api.getVideo('video-123');

      expect(result).toEqual(mockVideo);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/videos/video-123'),
        expect.any(Object)
      );
    });

    it('should search videos', async () => {
      const mockResponse = {
        items: [{ id: '1', title: 'Result 1' }],
        total: 1,
        page: 1,
        page_size: 20,
        has_more: false,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
        text: async () => JSON.stringify(mockResponse),
      });

      const result = await api.search('test query');

      expect(result).toEqual(mockResponse);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/search?q=test+query'),
        expect.any(Object)
      );
    });
  });

  describe('social features', () => {
    it('should follow a user', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: async () => '',
      });

      await api.follow('user-123');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/social/follow/user-123'),
        expect.objectContaining({ method: 'POST' })
      );
    });

    it('should unfollow a user', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: async () => '',
      });

      await api.unfollow('user-123');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/social/follow/user-123'),
        expect.objectContaining({ method: 'DELETE' })
      );
    });

    it('should add a comment', async () => {
      const mockComment = {
        id: 'comment-123',
        content: 'Great video!',
        user_id: 'user-123',
        video_id: 'video-123',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockComment,
        text: async () => JSON.stringify(mockComment),
      });

      const result = await api.addComment('video-123', 'Great video!');

      expect(result).toEqual(mockComment);
    });
  });

  describe('error handling', () => {
    it('should handle network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      await expect(api.getVideo('123')).rejects.toThrow('Network error');
    });

    it('should handle API errors with details', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        json: async () => ({
          detail: 'Validation error',
          code: 'VALIDATION_ERROR',
        }),
      });

      await expect(api.getVideo('123')).rejects.toMatchObject({
        message: 'Validation error',
        code: 'VALIDATION_ERROR',
        status: 400,
      });
    });
  });
});
