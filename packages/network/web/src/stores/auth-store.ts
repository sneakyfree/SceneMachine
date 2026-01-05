/**
 * Authentication Store
 *
 * Manages user authentication state with Zustand.
 * Handles login, logout, token refresh, and user data.
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { api, User, AuthResponse, ApiError } from '../lib/api-client';

// =============================================================================
// TYPES
// =============================================================================

interface AuthState {
  // State
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  login: (email: string, password: string) => Promise<void>;
  register: (data: {
    email: string;
    password: string;
    username: string;
    display_name?: string;
  }) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  updateProfile: (data: Partial<{
    display_name: string;
    bio: string;
    avatar_url: string;
  }>) => Promise<void>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
  requestPasswordReset: (email: string) => Promise<void>;
  resetPassword: (token: string, newPassword: string) => Promise<void>;
  uploadAvatar: (file: File) => Promise<string>;
  uploadBanner: (file: File) => Promise<string>;
  clearError: () => void;
  checkAuth: () => Promise<boolean>;
  // Dev/testing: Set mock user without API call
  setMockUser: (user: User, role?: string) => void;
}

// =============================================================================
// STORE
// =============================================================================

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      // Login
      login: async (email: string, password: string) => {
        set({ isLoading: true, error: null });

        try {
          const auth = await api.login(email, password);
          set({
            user: auth.user,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });
        } catch (error) {
          const apiError = error as ApiError;
          set({
            user: null,
            isAuthenticated: false,
            isLoading: false,
            error: apiError.message || 'Login failed',
          });
          throw error;
        }
      },

      // Register
      register: async (data) => {
        set({ isLoading: true, error: null });

        try {
          const auth = await api.register(data);
          set({
            user: auth.user,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });
        } catch (error) {
          const apiError = error as ApiError;
          set({
            user: null,
            isAuthenticated: false,
            isLoading: false,
            error: apiError.message || 'Registration failed',
          });
          throw error;
        }
      },

      // Logout
      logout: async () => {
        set({ isLoading: true });

        try {
          await api.logout();
        } catch {
          // Ignore logout errors - we're logging out anyway
        } finally {
          set({
            user: null,
            isAuthenticated: false,
            isLoading: false,
            error: null,
          });
        }
      },

      // Refresh user data
      refreshUser: async () => {
        if (!get().isAuthenticated) return;

        try {
          const user = await api.getCurrentUser();
          set({ user });
        } catch (error) {
          const apiError = error as ApiError;
          if (apiError.status === 401) {
            // Token expired or invalid
            set({
              user: null,
              isAuthenticated: false,
              error: null,
            });
          }
        }
      },

      // Update profile
      updateProfile: async (data) => {
        set({ isLoading: true, error: null });

        try {
          const user = await api.updateProfile(data);
          set({ user, isLoading: false });
        } catch (error) {
          const apiError = error as ApiError;
          set({
            isLoading: false,
            error: apiError.message || 'Profile update failed',
          });
          throw error;
        }
      },

      // Change password
      changePassword: async (currentPassword: string, newPassword: string) => {
        set({ isLoading: true, error: null });

        try {
          await api.changePassword(currentPassword, newPassword);
          set({ isLoading: false });
        } catch (error) {
          const apiError = error as ApiError;
          set({
            isLoading: false,
            error: apiError.message || 'Failed to change password',
          });
          throw error;
        }
      },

      // Request password reset
      requestPasswordReset: async (email: string) => {
        set({ isLoading: true, error: null });

        try {
          await api.requestPasswordReset(email);
          set({ isLoading: false });
        } catch (error) {
          const apiError = error as ApiError;
          set({
            isLoading: false,
            error: apiError.message || 'Failed to send reset email',
          });
          throw error;
        }
      },

      // Reset password with token
      resetPassword: async (token: string, newPassword: string) => {
        set({ isLoading: true, error: null });

        try {
          await api.resetPassword(token, newPassword);
          set({ isLoading: false });
        } catch (error) {
          const apiError = error as ApiError;
          set({
            isLoading: false,
            error: apiError.message || 'Failed to reset password',
          });
          throw error;
        }
      },

      // Upload avatar
      uploadAvatar: async (file: File) => {
        set({ isLoading: true, error: null });

        try {
          const { avatar_url } = await api.uploadAvatar(file);
          // Update user with new avatar
          set((state) => ({
            user: state.user ? { ...state.user, avatar_url } : null,
            isLoading: false,
          }));
          return avatar_url;
        } catch (error) {
          const apiError = error as ApiError;
          set({
            isLoading: false,
            error: apiError.message || 'Failed to upload avatar',
          });
          throw error;
        }
      },

      // Upload banner
      uploadBanner: async (file: File) => {
        set({ isLoading: true, error: null });

        try {
          const { banner_url } = await api.uploadBanner(file);
          set({ isLoading: false });
          return banner_url;
        } catch (error) {
          const apiError = error as ApiError;
          set({
            isLoading: false,
            error: apiError.message || 'Failed to upload banner',
          });
          throw error;
        }
      },

      // Clear error
      clearError: () => {
        set({ error: null });
      },

      // Check if user is still authenticated (validate token)
      checkAuth: async () => {
        if (!api.isAuthenticated()) {
          set({ user: null, isAuthenticated: false });
          return false;
        }

        try {
          const user = await api.getCurrentUser();
          set({ user, isAuthenticated: true });
          return true;
        } catch {
          set({ user: null, isAuthenticated: false });
          return false;
        }
      },

      // Dev/testing: Set mock user without API call
      setMockUser: (user: User, role?: string) => {
        set({
          user,
          isAuthenticated: true,
          isLoading: false,
          error: null,
        });
        // Store in localStorage for persistence
        if (typeof window !== 'undefined') {
          localStorage.setItem('mock_user_role', role || 'user');
        }
      },
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        // Only persist user data, not loading/error state
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);

// =============================================================================
// SELECTORS
// =============================================================================

export const selectUser = (state: AuthState) => state.user;
export const selectIsAuthenticated = (state: AuthState) => state.isAuthenticated;
export const selectIsLoading = (state: AuthState) => state.isLoading;
export const selectError = (state: AuthState) => state.error;

// =============================================================================
// HOOKS
// =============================================================================

/**
 * Hook to check if user is a creator
 */
export function useIsCreator(): boolean {
  return useAuthStore((state) => state.user?.is_creator ?? false);
}

/**
 * Hook to check if user is verified
 */
export function useIsVerified(): boolean {
  return useAuthStore((state) => state.user?.is_verified ?? false);
}

/**
 * Hook to require authentication
 * Returns true if authenticated, false if redirect needed
 */
export function useRequireAuth(): {
  isAuthenticated: boolean;
  isLoading: boolean;
} {
  const isAuthenticated = useAuthStore(selectIsAuthenticated);
  const isLoading = useAuthStore(selectIsLoading);

  return { isAuthenticated, isLoading };
}

export default useAuthStore;
