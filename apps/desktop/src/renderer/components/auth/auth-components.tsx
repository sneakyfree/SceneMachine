/**
 * Authentication Components
 * OAuth flow, login/signup UI, session management
 */

import React from 'react';
import {
  User,
  Mail,
  Lock,
  Eye,
  EyeOff,
  LogIn,
  LogOut,
  Loader2,
  AlertCircle,
  CheckCircle,
  ArrowRight,
  Github,
  Chrome,
} from 'lucide-react';
import { cn } from '../../lib/utils';

// User interface
export interface AuthUser {
  id: string;
  email: string;
  name: string;
  avatarUrl?: string;
  subscription?: 'free' | 'pro' | 'team';
}

// Auth state
export interface AuthState {
  user: AuthUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  error: string | null;
}

// Login form component
export const LoginForm: React.FC<{
  onSubmit: (email: string, password: string) => Promise<void>;
  onForgotPassword?: () => void;
  onSignupClick?: () => void;
  onOAuthLogin?: (provider: 'google' | 'github') => void;
  isLoading?: boolean;
  error?: string | null;
  className?: string;
}> = ({
  onSubmit,
  onForgotPassword,
  onSignupClick,
  onOAuthLogin,
  isLoading = false,
  error,
  className,
}) => {
  const [email, setEmail] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [showPassword, setShowPassword] = React.useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onSubmit(email, password);
  };

  return (
    <div className={cn('w-full max-w-sm mx-auto', className)}>
      <div className="text-center mb-8">
        <h1 className="text-2xl font-bold">Welcome back</h1>
        <p className="text-surface-400 mt-1">Sign in to your account</p>
      </div>

      {/* OAuth buttons */}
      {onOAuthLogin && (
        <>
          <div className="space-y-2 mb-6">
            <button
              onClick={() => onOAuthLogin('google')}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-surface-800 hover:bg-surface-700 border border-surface-700 rounded-lg transition-colors"
            >
              <Chrome className="w-5 h-5 text-blue-400" />
              Continue with Google
            </button>
            <button
              onClick={() => onOAuthLogin('github')}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-surface-800 hover:bg-surface-700 border border-surface-700 rounded-lg transition-colors"
            >
              <Github className="w-5 h-5" />
              Continue with GitHub
            </button>
          </div>

          <div className="relative mb-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-surface-700" />
            </div>
            <div className="relative flex justify-center text-xs">
              <span className="px-2 bg-surface-900 text-surface-500">or continue with email</span>
            </div>
          </div>
        </>
      )}

      {/* Error message */}
      {error && (
        <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg flex items-center gap-2 text-red-400 text-sm">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Email */}
        <div>
          <label className="block text-sm font-medium mb-1.5">Email</label>
          <div className="relative">
            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-500" />
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              className="w-full pl-10 pr-3 py-2.5 bg-surface-800 border border-surface-700 rounded-lg focus:border-brand-500 focus:outline-none"
            />
          </div>
        </div>

        {/* Password */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className="text-sm font-medium">Password</label>
            {onForgotPassword && (
              <button
                type="button"
                onClick={onForgotPassword}
                className="text-xs text-brand-400 hover:text-brand-300"
              >
                Forgot password?
              </button>
            )}
          </div>
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-500" />
            <input
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              className="w-full pl-10 pr-10 py-2.5 bg-surface-800 border border-surface-700 rounded-lg focus:border-brand-500 focus:outline-none"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-surface-500 hover:text-surface-300"
            >
              {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={isLoading}
          className={cn(
            'w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-brand-500 hover:bg-brand-600 text-white font-medium rounded-lg transition-colors',
            isLoading && 'opacity-50 cursor-not-allowed'
          )}
        >
          {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <LogIn className="w-4 h-4" />}
          Sign in
        </button>
      </form>

      {/* Signup link */}
      {onSignupClick && (
        <p className="text-center mt-6 text-sm text-surface-400">
          Don't have an account?{' '}
          <button onClick={onSignupClick} className="text-brand-400 hover:text-brand-300">
            Sign up
          </button>
        </p>
      )}
    </div>
  );
};

// Signup form component
export const SignupForm: React.FC<{
  onSubmit: (name: string, email: string, password: string) => Promise<void>;
  onLoginClick?: () => void;
  onOAuthLogin?: (provider: 'google' | 'github') => void;
  isLoading?: boolean;
  error?: string | null;
  className?: string;
}> = ({ onSubmit, onLoginClick, onOAuthLogin, isLoading = false, error, className }) => {
  const [name, setName] = React.useState('');
  const [email, setEmail] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [showPassword, setShowPassword] = React.useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onSubmit(name, email, password);
  };

  const passwordStrength = React.useMemo(() => {
    if (!password) return 0;
    let strength = 0;
    if (password.length >= 8) strength++;
    if (/[A-Z]/.test(password)) strength++;
    if (/[0-9]/.test(password)) strength++;
    if (/[^A-Za-z0-9]/.test(password)) strength++;
    return strength;
  }, [password]);

  return (
    <div className={cn('w-full max-w-sm mx-auto', className)}>
      <div className="text-center mb-8">
        <h1 className="text-2xl font-bold">Create an account</h1>
        <p className="text-surface-400 mt-1">Get started with SceneMachine</p>
      </div>

      {/* OAuth buttons */}
      {onOAuthLogin && (
        <>
          <div className="space-y-2 mb-6">
            <button
              onClick={() => onOAuthLogin('google')}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-surface-800 hover:bg-surface-700 border border-surface-700 rounded-lg transition-colors"
            >
              <Chrome className="w-5 h-5 text-blue-400" />
              Sign up with Google
            </button>
            <button
              onClick={() => onOAuthLogin('github')}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-surface-800 hover:bg-surface-700 border border-surface-700 rounded-lg transition-colors"
            >
              <Github className="w-5 h-5" />
              Sign up with GitHub
            </button>
          </div>

          <div className="relative mb-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-surface-700" />
            </div>
            <div className="relative flex justify-center text-xs">
              <span className="px-2 bg-surface-900 text-surface-500">or continue with email</span>
            </div>
          </div>
        </>
      )}

      {/* Error message */}
      {error && (
        <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg flex items-center gap-2 text-red-400 text-sm">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Name */}
        <div>
          <label className="block text-sm font-medium mb-1.5">Full name</label>
          <div className="relative">
            <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-500" />
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="John Doe"
              required
              className="w-full pl-10 pr-3 py-2.5 bg-surface-800 border border-surface-700 rounded-lg focus:border-brand-500 focus:outline-none"
            />
          </div>
        </div>

        {/* Email */}
        <div>
          <label className="block text-sm font-medium mb-1.5">Email</label>
          <div className="relative">
            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-500" />
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              className="w-full pl-10 pr-3 py-2.5 bg-surface-800 border border-surface-700 rounded-lg focus:border-brand-500 focus:outline-none"
            />
          </div>
        </div>

        {/* Password */}
        <div>
          <label className="block text-sm font-medium mb-1.5">Password</label>
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-500" />
            <input
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              minLength={8}
              className="w-full pl-10 pr-10 py-2.5 bg-surface-800 border border-surface-700 rounded-lg focus:border-brand-500 focus:outline-none"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-surface-500 hover:text-surface-300"
            >
              {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
          {/* Password strength indicator */}
          <div className="flex gap-1 mt-2">
            {[1, 2, 3, 4].map((level) => (
              <div
                key={level}
                className={cn(
                  'h-1 flex-1 rounded',
                  passwordStrength >= level
                    ? passwordStrength >= 3
                      ? 'bg-green-500'
                      : passwordStrength >= 2
                        ? 'bg-yellow-500'
                        : 'bg-red-500'
                    : 'bg-surface-700'
                )}
              />
            ))}
          </div>
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={isLoading}
          className={cn(
            'w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-brand-500 hover:bg-brand-600 text-white font-medium rounded-lg transition-colors',
            isLoading && 'opacity-50 cursor-not-allowed'
          )}
        >
          {isLoading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <>
              Create account
              <ArrowRight className="w-4 h-4" />
            </>
          )}
        </button>
      </form>

      {/* Login link */}
      {onLoginClick && (
        <p className="text-center mt-6 text-sm text-surface-400">
          Already have an account?{' '}
          <button onClick={onLoginClick} className="text-brand-400 hover:text-brand-300">
            Sign in
          </button>
        </p>
      )}
    </div>
  );
};

// User menu component
export const UserMenu: React.FC<{
  user: AuthUser;
  onProfile?: () => void;
  onSettings?: () => void;
  onLogout: () => void;
  className?: string;
}> = ({ user, onProfile, onSettings, onLogout, className }) => {
  const [isOpen, setIsOpen] = React.useState(false);

  return (
    <div className={cn('relative', className)}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-surface-800 transition-colors"
      >
        {user.avatarUrl ? (
          <img src={user.avatarUrl} alt={user.name} className="w-8 h-8 rounded-full" />
        ) : (
          <div className="w-8 h-8 rounded-full bg-brand-500 flex items-center justify-center text-white font-medium">
            {user.name.charAt(0).toUpperCase()}
          </div>
        )}
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setIsOpen(false)} />
          <div className="absolute right-0 top-full mt-2 w-56 bg-surface-800 border border-surface-700 rounded-lg shadow-xl z-20">
            <div className="p-3 border-b border-surface-700">
              <p className="font-medium">{user.name}</p>
              <p className="text-sm text-surface-400">{user.email}</p>
            </div>
            <div className="p-1">
              {onProfile && (
                <button
                  onClick={() => {
                    onProfile();
                    setIsOpen(false);
                  }}
                  className="w-full px-3 py-2 text-left text-sm hover:bg-surface-700 rounded"
                >
                  Profile
                </button>
              )}
              {onSettings && (
                <button
                  onClick={() => {
                    onSettings();
                    setIsOpen(false);
                  }}
                  className="w-full px-3 py-2 text-left text-sm hover:bg-surface-700 rounded"
                >
                  Settings
                </button>
              )}
              <button
                onClick={() => {
                  onLogout();
                  setIsOpen(false);
                }}
                className="w-full px-3 py-2 text-left text-sm text-red-400 hover:bg-surface-700 rounded flex items-center gap-2"
              >
                <LogOut className="w-4 h-4" />
                Sign out
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

// Auth context and provider
const AuthContext = React.createContext<{
  state: AuthState;
  login: (email: string, password: string) => Promise<void>;
  signup: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  oauthLogin: (provider: 'google' | 'github') => void;
} | null>(null);

export const AuthProvider: React.FC<{
  children: React.ReactNode;
  onLogin?: (user: AuthUser) => void;
  onLogout?: () => void;
}> = ({ children, onLogin, onLogout }) => {
  const [state, setState] = React.useState<AuthState>({
    user: null,
    isLoading: true,
    isAuthenticated: false,
    error: null,
  });

  // Check for existing session on mount
  React.useEffect(() => {
    const checkSession = async () => {
      try {
        const stored = localStorage.getItem('auth_user');
        if (stored) {
          const user = JSON.parse(stored);
          setState({ user, isLoading: false, isAuthenticated: true, error: null });
        } else {
          setState((s) => ({ ...s, isLoading: false }));
        }
      } catch {
        setState((s) => ({ ...s, isLoading: false }));
      }
    };
    checkSession();
  }, []);

  const login = async (email: string, password: string) => {
    setState((s) => ({ ...s, isLoading: true, error: null }));
    try {
      // Simulate API call
      await new Promise((r) => setTimeout(r, 1000));
      const user: AuthUser = { id: '1', email, name: email.split('@')[0] };
      localStorage.setItem('auth_user', JSON.stringify(user));
      setState({ user, isLoading: false, isAuthenticated: true, error: null });
      onLogin?.(user);
    } catch (error) {
      setState((s) => ({ ...s, isLoading: false, error: 'Invalid credentials' }));
    }
  };

  const signup = async (name: string, email: string, password: string) => {
    setState((s) => ({ ...s, isLoading: true, error: null }));
    try {
      await new Promise((r) => setTimeout(r, 1000));
      const user: AuthUser = { id: '1', email, name };
      localStorage.setItem('auth_user', JSON.stringify(user));
      setState({ user, isLoading: false, isAuthenticated: true, error: null });
      onLogin?.(user);
    } catch (error) {
      setState((s) => ({ ...s, isLoading: false, error: 'Signup failed' }));
    }
  };

  const logout = () => {
    localStorage.removeItem('auth_user');
    setState({ user: null, isLoading: false, isAuthenticated: false, error: null });
    onLogout?.();
  };

  const oauthLogin = (provider: 'google' | 'github') => {
    console.log(`OAuth login with ${provider}`);
    // In production, redirect to OAuth provider
  };

  return (
    <AuthContext.Provider value={{ state, login, signup, logout, oauthLogin }}>
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth() {
  const context = React.useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
}
