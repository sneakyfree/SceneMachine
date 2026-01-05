/**
 * Login Page - Stunning SceneMachine Network Design
 *
 * Beautiful authentication page with glass morphism and animations.
 */

'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Eye, EyeOff, Mail, Lock, Sparkles, Shield, Crown, User, Clapperboard } from 'lucide-react';
import { useAuthStore } from '../stores';
import { cn } from '../lib/utils';

// Quick login test accounts with mock user data
const TEST_ACCOUNTS = [
  {
    role: 'Super Admin',
    email: 'superadmin@scenemachine.io',
    password: 'SuperAdmin123!',
    icon: Crown,
    gradient: 'from-red-500 to-rose-600',
    mockUser: {
      id: 'mock-super-admin',
      email: 'superadmin@scenemachine.io',
      username: 'superadmin',
      display_name: 'Super Admin',
      avatar_url: 'https://api.dicebear.com/7.x/avataaars/svg?seed=superadmin',
      bio: 'Platform super administrator',
      is_verified: true,
      is_creator: true,
      follower_count: 0,
      following_count: 0,
      created_at: new Date().toISOString(),
    }
  },
  {
    role: 'Admin',
    email: 'admin@scenemachine.io',
    password: 'Admin123!',
    icon: Shield,
    gradient: 'from-amber-500 to-orange-600',
    mockUser: {
      id: 'mock-admin',
      email: 'admin@scenemachine.io',
      username: 'admin',
      display_name: 'Admin User',
      avatar_url: 'https://api.dicebear.com/7.x/avataaars/svg?seed=admin',
      bio: 'Platform administrator',
      is_verified: true,
      is_creator: true,
      follower_count: 0,
      following_count: 0,
      created_at: new Date().toISOString(),
    }
  },
  {
    role: 'Creator',
    email: 'user@scenemachine.io',
    password: 'User123!',
    icon: Sparkles,
    gradient: 'from-emerald-500 to-green-600',
    mockUser: {
      id: 'mock-user',
      email: 'user@scenemachine.io',
      username: 'testuser',
      display_name: 'Test Creator',
      avatar_url: 'https://api.dicebear.com/7.x/avataaars/svg?seed=creator',
      bio: 'Independent filmmaker',
      is_verified: true,
      is_creator: true,
      follower_count: 1250,
      following_count: 89,
      created_at: new Date().toISOString(),
    }
  },
  {
    role: 'Viewer',
    email: 'sales@scenemachine.io',
    password: 'Sales123!',
    icon: User,
    gradient: 'from-blue-500 to-indigo-600',
    mockUser: {
      id: 'mock-viewer',
      email: 'viewer@scenemachine.io',
      username: 'viewer',
      display_name: 'Film Enthusiast',
      avatar_url: 'https://api.dicebear.com/7.x/avataaars/svg?seed=viewer',
      bio: 'Love indie films!',
      is_verified: false,
      is_creator: false,
      follower_count: 12,
      following_count: 156,
      created_at: new Date().toISOString(),
    }
  },
];

export default function LoginPage() {
  const router = useRouter();
  const { login, isAuthenticated, isLoading, error, clearError, setMockUser } = useAuthStore();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [focusedField, setFocusedField] = useState<string | null>(null);

  // Quick login handler - directly sets mock user (bypasses API for dev)
  const handleQuickLogin = (account: typeof TEST_ACCOUNTS[0]) => {
    clearError();
    setMockUser(account.mockUser as any, account.role);
    router.push('/');
  };

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      router.push('/');
    }
  }, [isAuthenticated, router]);

  // Clear errors on unmount
  useEffect(() => {
    return () => clearError();
  }, [clearError]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      await login(email, password);
      router.push('/');
    } catch {
      // Error is handled by store
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-background p-4">
      {/* Animated Background */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -left-1/4 -top-1/4 h-[600px] w-[600px] rounded-full bg-primary/20 blur-[120px]" />
        <div className="absolute -bottom-1/4 -right-1/4 h-[600px] w-[600px] rounded-full bg-violet-500/20 blur-[120px]" />
      </div>

      {/* Grid Pattern */}
      <div
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage: `linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)`,
          backgroundSize: '50px 50px',
        }}
      />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative z-10 w-full max-w-md"
      >
        {/* Logo */}
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="mb-8 text-center"
        >
          <Link href="/" className="inline-flex flex-col items-center gap-3">
            <div className="relative">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-violet-500 shadow-2xl shadow-primary/30">
                <Clapperboard className="h-8 w-8 text-white" />
              </div>
              <div className="absolute -right-1 -top-1 h-4 w-4 rounded-full bg-emerald-400 ring-4 ring-background" />
            </div>
            <div>
              <h1 className="bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text text-2xl font-bold text-transparent">
                SceneMachine
              </h1>
              <p className="mt-1 text-sm font-medium tracking-widest text-primary">NETWORK</p>
            </div>
          </Link>
        </motion.div>

        {/* Login Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="glass rounded-2xl p-6 shadow-2xl"
        >
          <div className="mb-6 text-center">
            <h2 className="text-xl font-semibold text-foreground">Welcome back</h2>
            <p className="mt-1 text-sm text-muted-foreground">Sign in to continue to your account</p>
          </div>

          {/* Error Message */}
          {error && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              className="mb-4 rounded-lg border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive"
              role="alert"
            >
              {error}
            </motion.div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Email Field */}
            <div className="space-y-2">
              <label htmlFor="email" className="text-sm font-medium text-foreground">
                Email
              </label>
              <div className={cn(
                'relative flex items-center rounded-lg border bg-secondary/50 transition-all duration-200',
                focusedField === 'email' ? 'border-primary ring-4 ring-primary/10' : 'border-border'
              )}>
                <Mail className="absolute left-3 h-4 w-4 text-muted-foreground" />
                <input
                  type="email"
                  id="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  onFocus={() => setFocusedField('email')}
                  onBlur={() => setFocusedField(null)}
                  placeholder="you@example.com"
                  required
                  autoComplete="email"
                  disabled={isLoading}
                  className="h-11 w-full bg-transparent pl-10 pr-4 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
                />
              </div>
            </div>

            {/* Password Field */}
            <div className="space-y-2">
              <label htmlFor="password" className="text-sm font-medium text-foreground">
                Password
              </label>
              <div className={cn(
                'relative flex items-center rounded-lg border bg-secondary/50 transition-all duration-200',
                focusedField === 'password' ? 'border-primary ring-4 ring-primary/10' : 'border-border'
              )}>
                <Lock className="absolute left-3 h-4 w-4 text-muted-foreground" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  id="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onFocus={() => setFocusedField('password')}
                  onBlur={() => setFocusedField(null)}
                  placeholder="••••••••"
                  required
                  autoComplete="current-password"
                  disabled={isLoading}
                  className="h-11 w-full bg-transparent pl-10 pr-12 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 rounded p-1 text-muted-foreground transition-colors hover:text-foreground"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            {/* Options Row */}
            <div className="flex items-center justify-between text-sm">
              <label className="flex cursor-pointer items-center gap-2 text-muted-foreground">
                <input
                  type="checkbox"
                  className="h-4 w-4 rounded border-border bg-secondary accent-primary"
                />
                <span>Remember me</span>
              </label>
              <Link href="/forgot-password" className="font-medium text-primary hover:underline">
                Forgot password?
              </Link>
            </div>

            {/* Submit Button */}
            <motion.button
              type="submit"
              disabled={isLoading || !email || !password}
              whileHover={{ scale: 1.01 }}
              whileTap={{ scale: 0.99 }}
              className="btn-primary flex h-11 w-full items-center justify-center gap-2 rounded-lg font-semibold disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isLoading ? (
                <>
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                  Signing in...
                </>
              ) : (
                'Sign in'
              )}
            </motion.button>
          </form>

          {/* Divider */}
          <div className="my-6 flex items-center gap-3">
            <div className="h-px flex-1 bg-border" />
            <span className="text-xs text-muted-foreground">or continue with</span>
            <div className="h-px flex-1 bg-border" />
          </div>

          {/* Social Buttons */}
          <div className="grid grid-cols-2 gap-3">
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              type="button"
              disabled
              className="flex h-11 items-center justify-center gap-2 rounded-lg border border-border bg-secondary/50 text-sm font-medium text-foreground transition-colors hover:bg-secondary disabled:cursor-not-allowed disabled:opacity-50"
            >
              <svg width="18" height="18" viewBox="0 0 20 20">
                <path d="M19.8 10.2c0-.7-.1-1.4-.2-2H10v3.8h5.5c-.2 1.2-1 2.3-2 3v2.5h3.2c1.9-1.7 3-4.3 3-7.3z" fill="#4285F4" />
                <path d="M10 20c2.7 0 5-1 6.6-2.5l-3.2-2.5c-.9.6-2 1-3.4 1-2.6 0-4.8-1.8-5.6-4.2H1.1v2.6C2.7 17.8 6.1 20 10 20z" fill="#34A853" />
                <path d="M4.4 11.8c-.2-.6-.3-1.2-.3-1.8s.1-1.2.3-1.8V5.6H1.1C.4 7 0 8.4 0 10s.4 3 1.1 4.4l3.3-2.6z" fill="#FBBC05" />
                <path d="M10 4c1.5 0 2.8.5 3.9 1.5l2.9-2.9C15 1 12.7 0 10 0 6.1 0 2.7 2.2 1.1 5.6l3.3 2.6C5.2 5.8 7.4 4 10 4z" fill="#EA4335" />
              </svg>
              Google
            </motion.button>
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              type="button"
              disabled
              className="flex h-11 items-center justify-center gap-2 rounded-lg border border-border bg-secondary/50 text-sm font-medium text-foreground transition-colors hover:bg-secondary disabled:cursor-not-allowed disabled:opacity-50"
            >
              <svg width="18" height="18" viewBox="0 0 20 20" fill="currentColor">
                <path d="M10 0C4.5 0 0 4.5 0 10c0 4.4 2.9 8.2 6.8 9.5.5.1.7-.2.7-.5v-1.7c-2.8.6-3.4-1.3-3.4-1.3-.4-1.1-1.1-1.4-1.1-1.4-.9-.6.1-.6.1-.6 1 .1 1.5 1 1.5 1 .9 1.5 2.3 1.1 2.9.8.1-.6.3-1.1.6-1.3-2.2-.3-4.5-1.1-4.5-4.9 0-1.1.4-2 1-2.7-.1-.2-.4-1.2.1-2.5 0 0 .8-.3 2.7 1a9.4 9.4 0 015 0c1.9-1.3 2.7-1 2.7-1 .5 1.3.2 2.3.1 2.5.6.7 1 1.6 1 2.7 0 3.8-2.3 4.6-4.5 4.9.4.3.7.9.7 1.9v2.8c0 .3.2.6.7.5 4-1.3 6.8-5.1 6.8-9.5C20 4.5 15.5 0 10 0z" />
              </svg>
              GitHub
            </motion.button>
          </div>
        </motion.div>

        {/* Quick Login Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="mt-6"
        >
          <div className="mb-4 flex items-center gap-3">
            <div className="h-px flex-1 bg-border/50" />
            <span className="text-xs font-medium text-muted-foreground">DEV QUICK LOGIN</span>
            <div className="h-px flex-1 bg-border/50" />
          </div>

          <div className="grid grid-cols-2 gap-3">
            {TEST_ACCOUNTS.map((account, index) => (
              <motion.button
                key={account.role}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 + index * 0.1 }}
                whileHover={{ scale: 1.02, y: -2 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => handleQuickLogin(account)}
                className={cn(
                  'group relative flex items-center gap-3 overflow-hidden rounded-xl border border-border/50 bg-card/50 p-3 text-left backdrop-blur-sm transition-all hover:border-border hover:shadow-lg'
                )}
              >
                <div className={cn(
                  'flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-gradient-to-br shadow-lg',
                  account.gradient
                )}>
                  <account.icon className="h-5 w-5 text-white" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold text-foreground">{account.role}</p>
                  <p className="truncate text-xs text-muted-foreground">{account.email}</p>
                </div>
                <div className={cn(
                  'absolute inset-0 bg-gradient-to-r opacity-0 transition-opacity group-hover:opacity-5',
                  account.gradient
                )} />
              </motion.button>
            ))}
          </div>
        </motion.div>

        {/* Sign Up Link */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="mt-6 text-center text-sm text-muted-foreground"
        >
          Don't have an account?{' '}
          <Link href="/register" className="font-semibold text-primary hover:underline">
            Create one
          </Link>
        </motion.p>
      </motion.div>
    </div>
  );
}
