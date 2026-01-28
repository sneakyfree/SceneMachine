/**
 * Auth Store
 * Zustand store for authentication state management
 * Wired to backend API at /api/auth/*
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// API base URL
const API_BASE = 'http://localhost:8000/api';

// Types
export interface User {
    id: string;
    email: string;
    username: string;
    full_name: string | null;
    avatar_url: string | null;
    bio: string | null;
    is_active: boolean;
    is_verified: boolean;
    role: 'user' | 'admin' | 'superadmin';
    created_at: string;
}

interface AuthTokens {
    access_token: string;
    refresh_token: string;
    expires_in: number;
}

interface AuthState {
    user: User | null;
    accessToken: string | null;
    refreshToken: string | null;
    isLoading: boolean;
    error: string | null;
    isAuthenticated: boolean;
}

interface AuthActions {
    login: (email: string, password: string) => Promise<boolean>;
    signup: (email: string, username: string, password: string, fullName?: string) => Promise<boolean>;
    logout: () => Promise<void>;
    refreshTokens: () => Promise<boolean>;
    checkSession: () => Promise<void>;
    updateProfile: (data: { full_name?: string; bio?: string; avatar_url?: string }) => Promise<boolean>;
    changePassword: (currentPassword: string, newPassword: string) => Promise<boolean>;
    clearError: () => void;
}

type AuthStore = AuthState & AuthActions;

// Helper to make authenticated requests
const authFetch = async (
    url: string,
    options: RequestInit = {},
    token?: string | null
): Promise<Response> => {
    const headers: HeadersInit = {
        'Content-Type': 'application/json',
        ...options.headers,
    };

    if (token) {
        (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
    }

    return fetch(`${API_BASE}${url}`, {
        ...options,
        headers,
    });
};

export const useAuthStore = create<AuthStore>()(
    persist(
        (set, get) => ({
            // Initial state
            user: null,
            accessToken: null,
            refreshToken: null,
            isLoading: false,
            error: null,
            isAuthenticated: false,

            // Login
            login: async (email: string, password: string): Promise<boolean> => {
                set({ isLoading: true, error: null });

                try {
                    const response = await authFetch('/auth/login', {
                        method: 'POST',
                        body: JSON.stringify({ email, password }),
                    });

                    if (!response.ok) {
                        const data = await response.json();
                        set({ isLoading: false, error: data.detail || 'Login failed' });
                        return false;
                    }

                    const tokens: AuthTokens = await response.json();

                    // Get user profile
                    const userResponse = await authFetch('/auth/me', {}, tokens.access_token);
                    if (!userResponse.ok) {
                        set({ isLoading: false, error: 'Failed to get user profile' });
                        return false;
                    }

                    const user: User = await userResponse.json();

                    set({
                        user,
                        accessToken: tokens.access_token,
                        refreshToken: tokens.refresh_token,
                        isLoading: false,
                        isAuthenticated: true,
                        error: null,
                    });

                    return true;
                } catch (err) {
                    set({
                        isLoading: false,
                        error: err instanceof Error ? err.message : 'Network error',
                    });
                    return false;
                }
            },

            // Signup
            signup: async (
                email: string,
                username: string,
                password: string,
                fullName?: string
            ): Promise<boolean> => {
                set({ isLoading: true, error: null });

                try {
                    const response = await authFetch('/auth/register', {
                        method: 'POST',
                        body: JSON.stringify({
                            email,
                            username,
                            password,
                            full_name: fullName,
                        }),
                    });

                    if (!response.ok) {
                        const data = await response.json();
                        set({ isLoading: false, error: data.detail || 'Registration failed' });
                        return false;
                    }

                    // Auto-login after signup
                    set({ isLoading: false });
                    return get().login(email, password);
                } catch (err) {
                    set({
                        isLoading: false,
                        error: err instanceof Error ? err.message : 'Network error',
                    });
                    return false;
                }
            },

            // Logout
            logout: async (): Promise<void> => {
                const { accessToken, refreshToken } = get();

                try {
                    if (accessToken) {
                        await authFetch(
                            '/auth/logout',
                            {
                                method: 'POST',
                                body: refreshToken ? JSON.stringify({ refresh_token: refreshToken }) : undefined,
                            },
                            accessToken
                        );
                    }
                } catch {
                    // Ignore errors on logout
                }

                set({
                    user: null,
                    accessToken: null,
                    refreshToken: null,
                    isAuthenticated: false,
                    error: null,
                });
            },

            // Refresh tokens
            refreshTokens: async (): Promise<boolean> => {
                const { refreshToken } = get();

                if (!refreshToken) {
                    return false;
                }

                try {
                    const response = await authFetch('/auth/refresh', {
                        method: 'POST',
                        body: JSON.stringify({ refresh_token: refreshToken }),
                    });

                    if (!response.ok) {
                        // Token expired, logout
                        await get().logout();
                        return false;
                    }

                    const tokens: AuthTokens = await response.json();

                    set({
                        accessToken: tokens.access_token,
                        refreshToken: tokens.refresh_token,
                    });

                    return true;
                } catch {
                    await get().logout();
                    return false;
                }
            },

            // Check session on app start
            checkSession: async (): Promise<void> => {
                const { accessToken, refreshToken } = get();

                if (!accessToken) {
                    return;
                }

                set({ isLoading: true });

                try {
                    // Try to get user profile
                    const response = await authFetch('/auth/me', {}, accessToken);

                    if (response.ok) {
                        const user: User = await response.json();
                        set({ user, isAuthenticated: true, isLoading: false });
                        return;
                    }

                    // Token expired, try refresh
                    if (response.status === 401 && refreshToken) {
                        const refreshed = await get().refreshTokens();
                        if (refreshed) {
                            const retryResponse = await authFetch('/auth/me', {}, get().accessToken);
                            if (retryResponse.ok) {
                                const user: User = await retryResponse.json();
                                set({ user, isAuthenticated: true, isLoading: false });
                                return;
                            }
                        }
                    }

                    // Could not restore session
                    await get().logout();
                } catch {
                    set({ isLoading: false });
                }
            },

            // Update profile
            updateProfile: async (data): Promise<boolean> => {
                const { accessToken } = get();

                if (!accessToken) {
                    set({ error: 'Not authenticated' });
                    return false;
                }

                set({ isLoading: true, error: null });

                try {
                    const response = await authFetch(
                        '/auth/me',
                        {
                            method: 'PATCH',
                            body: JSON.stringify(data),
                        },
                        accessToken
                    );

                    if (!response.ok) {
                        const errorData = await response.json();
                        set({ isLoading: false, error: errorData.detail || 'Update failed' });
                        return false;
                    }

                    const user: User = await response.json();
                    set({ user, isLoading: false });
                    return true;
                } catch (err) {
                    set({
                        isLoading: false,
                        error: err instanceof Error ? err.message : 'Network error',
                    });
                    return false;
                }
            },

            // Change password
            changePassword: async (currentPassword: string, newPassword: string): Promise<boolean> => {
                const { accessToken } = get();

                if (!accessToken) {
                    set({ error: 'Not authenticated' });
                    return false;
                }

                set({ isLoading: true, error: null });

                try {
                    const response = await authFetch(
                        '/auth/change-password',
                        {
                            method: 'POST',
                            body: JSON.stringify({
                                current_password: currentPassword,
                                new_password: newPassword,
                            }),
                        },
                        accessToken
                    );

                    if (!response.ok) {
                        const errorData = await response.json();
                        set({ isLoading: false, error: errorData.detail || 'Password change failed' });
                        return false;
                    }

                    // Logout after password change (all sessions invalidated)
                    await get().logout();
                    return true;
                } catch (err) {
                    set({
                        isLoading: false,
                        error: err instanceof Error ? err.message : 'Network error',
                    });
                    return false;
                }
            },

            // Clear error
            clearError: () => set({ error: null }),
        }),
        {
            name: 'scenemachine-auth',
            partialize: (state) => ({
                accessToken: state.accessToken,
                refreshToken: state.refreshToken,
            }),
        }
    )
);

// Selector hooks for convenience
export const useUser = () => useAuthStore((state) => state.user);
export const useIsAuthenticated = () => useAuthStore((state) => state.isAuthenticated);
export const useAuthLoading = () => useAuthStore((state) => state.isLoading);
export const useAuthError = () => useAuthStore((state) => state.error);
