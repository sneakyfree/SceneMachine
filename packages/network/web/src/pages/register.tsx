/**
 * Register Page
 *
 * New user registration page.
 */

'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuthStore } from '../stores';

export default function RegisterPage() {
  const router = useRouter();
  const { register, isAuthenticated, isLoading, error, clearError } = useAuthStore();

  const [formData, setFormData] = useState({
    email: '',
    username: '',
    display_name: '',
    password: '',
    confirmPassword: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [agreedToTerms, setAgreedToTerms] = useState(false);

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

  // Validate password match
  useEffect(() => {
    if (formData.confirmPassword && formData.password !== formData.confirmPassword) {
      setPasswordError('Passwords do not match');
    } else {
      setPasswordError(null);
    }
  }, [formData.password, formData.confirmPassword]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const isFormValid = () => {
    return (
      formData.email &&
      formData.username &&
      formData.password &&
      formData.password === formData.confirmPassword &&
      formData.password.length >= 8 &&
      agreedToTerms
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!isFormValid()) return;

    try {
      await register({
        email: formData.email,
        username: formData.username,
        password: formData.password,
        display_name: formData.display_name || undefined,
      });
      router.push('/');
    } catch {
      // Error is handled by store
    }
  };

  return (
    <div className="register-page">
      <div className="register-container">
        {/* Logo */}
        <div className="logo">
          <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
            <rect width="48" height="48" rx="12" fill="url(#logo-gradient)" />
            <path
              d="M16 18L24 14L32 18V30L24 34L16 30V18Z"
              stroke="white"
              strokeWidth="2"
              fill="none"
            />
            <path
              d="M24 14V34M16 18L32 30M32 18L16 30"
              stroke="white"
              strokeWidth="2"
            />
            <defs>
              <linearGradient id="logo-gradient" x1="0" y1="0" x2="48" y2="48">
                <stop stopColor="#6366f1" />
                <stop offset="1" stopColor="#8b5cf6" />
              </linearGradient>
            </defs>
          </svg>
          <h1>SceneMachine</h1>
          <p className="tagline">Network</p>
        </div>

        {/* Register Form */}
        <form onSubmit={handleSubmit} className="register-form">
          <h2>Create your account</h2>
          <p className="subtitle">Join the indie film community</p>

          {error && (
            <div className="error-message" role="alert">
              {error}
            </div>
          )}

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="email">Email *</label>
              <input
                type="email"
                id="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                placeholder="you@example.com"
                required
                autoComplete="email"
                disabled={isLoading}
              />
            </div>
          </div>

          <div className="form-row two-col">
            <div className="form-group">
              <label htmlFor="username">Username *</label>
              <input
                type="text"
                id="username"
                name="username"
                value={formData.username}
                onChange={handleChange}
                placeholder="yourname"
                required
                pattern="[a-zA-Z0-9_]+"
                minLength={3}
                maxLength={30}
                autoComplete="username"
                disabled={isLoading}
              />
              <span className="hint">Letters, numbers, underscores only</span>
            </div>

            <div className="form-group">
              <label htmlFor="display_name">Display Name</label>
              <input
                type="text"
                id="display_name"
                name="display_name"
                value={formData.display_name}
                onChange={handleChange}
                placeholder="Your Name"
                maxLength={50}
                autoComplete="name"
                disabled={isLoading}
              />
            </div>
          </div>

          <div className="form-row two-col">
            <div className="form-group">
              <label htmlFor="password">Password *</label>
              <div className="password-input">
                <input
                  type={showPassword ? 'text' : 'password'}
                  id="password"
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  placeholder="••••••••"
                  required
                  minLength={8}
                  autoComplete="new-password"
                  disabled={isLoading}
                />
                <button
                  type="button"
                  className="toggle-password"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? '👁️' : '👁️‍🗨️'}
                </button>
              </div>
              <span className="hint">At least 8 characters</span>
            </div>

            <div className="form-group">
              <label htmlFor="confirmPassword">Confirm Password *</label>
              <input
                type={showPassword ? 'text' : 'password'}
                id="confirmPassword"
                name="confirmPassword"
                value={formData.confirmPassword}
                onChange={handleChange}
                placeholder="••••••••"
                required
                autoComplete="new-password"
                disabled={isLoading}
                className={passwordError ? 'error' : ''}
              />
              {passwordError && <span className="error-hint">{passwordError}</span>}
            </div>
          </div>

          <div className="terms-checkbox">
            <label>
              <input
                type="checkbox"
                checked={agreedToTerms}
                onChange={(e) => setAgreedToTerms(e.target.checked)}
                disabled={isLoading}
              />
              <span>
                I agree to the{' '}
                <Link href="/terms" target="_blank">Terms of Service</Link>
                {' '}and{' '}
                <Link href="/privacy" target="_blank">Privacy Policy</Link>
              </span>
            </label>
          </div>

          <button
            type="submit"
            className="submit-button"
            disabled={isLoading || !isFormValid()}
          >
            {isLoading ? (
              <>
                <span className="spinner" />
                Creating account...
              </>
            ) : (
              'Create account'
            )}
          </button>

          <div className="creator-note">
            <span className="icon">🎬</span>
            <p>
              Want to publish your films? You can enable creator mode after signing up.
            </p>
          </div>
        </form>

        {/* Login link */}
        <p className="login-link">
          Already have an account?{' '}
          <Link href="/login">Sign in</Link>
        </p>
      </div>

      <style jsx>{`
        .register-page {
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: var(--space-4);
          background: var(--gradient-bg);
        }

        .register-container {
          width: 100%;
          max-width: 520px;
        }

        .logo {
          text-align: center;
          margin-bottom: var(--space-6);
        }

        .logo svg {
          margin-bottom: var(--space-3);
        }

        .logo h1 {
          font-size: var(--text-2xl);
          margin-bottom: var(--space-1);
        }

        .logo .tagline {
          color: var(--color-accent);
          font-size: var(--text-sm);
          font-weight: 500;
          letter-spacing: 0.1em;
          text-transform: uppercase;
        }

        .register-form {
          background: var(--color-bg-secondary);
          border-radius: var(--radius-xl);
          padding: var(--space-6);
          border: 1px solid var(--color-border);
        }

        .register-form h2 {
          font-size: var(--text-xl);
          margin-bottom: var(--space-1);
        }

        .register-form .subtitle {
          color: var(--color-text-secondary);
          font-size: var(--text-sm);
          margin-bottom: var(--space-6);
        }

        .error-message {
          background: rgba(239, 68, 68, 0.1);
          border: 1px solid var(--color-error);
          color: var(--color-error);
          padding: var(--space-3);
          border-radius: var(--radius-md);
          font-size: var(--text-sm);
          margin-bottom: var(--space-4);
        }

        .form-row {
          margin-bottom: var(--space-4);
        }

        .form-row.two-col {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: var(--space-4);
        }

        @media (max-width: 520px) {
          .form-row.two-col {
            grid-template-columns: 1fr;
          }
        }

        .form-group label {
          display: block;
          font-size: var(--text-sm);
          font-weight: 500;
          margin-bottom: var(--space-2);
          color: var(--color-text-secondary);
        }

        .form-group input {
          width: 100%;
          padding: var(--space-3) var(--space-4);
          background: var(--color-bg-tertiary);
          border: 1px solid var(--color-border);
          border-radius: var(--radius-md);
          color: var(--color-text-primary);
          font-size: var(--text-base);
          transition: border-color var(--transition-fast);
        }

        .form-group input:focus {
          border-color: var(--color-accent);
          outline: none;
        }

        .form-group input.error {
          border-color: var(--color-error);
        }

        .form-group input::placeholder {
          color: var(--color-text-muted);
        }

        .form-group .hint {
          display: block;
          font-size: var(--text-xs);
          color: var(--color-text-muted);
          margin-top: var(--space-1);
        }

        .form-group .error-hint {
          display: block;
          font-size: var(--text-xs);
          color: var(--color-error);
          margin-top: var(--space-1);
        }

        .password-input {
          position: relative;
        }

        .password-input input {
          padding-right: 48px;
        }

        .toggle-password {
          position: absolute;
          right: var(--space-3);
          top: 50%;
          transform: translateY(-50%);
          padding: var(--space-1);
          color: var(--color-text-secondary);
        }

        .terms-checkbox {
          margin-bottom: var(--space-6);
        }

        .terms-checkbox label {
          display: flex;
          align-items: flex-start;
          gap: var(--space-2);
          cursor: pointer;
          font-size: var(--text-sm);
          color: var(--color-text-secondary);
        }

        .terms-checkbox input {
          width: 16px;
          height: 16px;
          margin-top: 2px;
          accent-color: var(--color-accent);
        }

        .terms-checkbox a {
          color: var(--color-accent);
        }

        .submit-button {
          width: 100%;
          padding: var(--space-3) var(--space-4);
          background: var(--gradient-primary);
          color: white;
          font-weight: 600;
          border-radius: var(--radius-md);
          display: flex;
          align-items: center;
          justify-content: center;
          gap: var(--space-2);
          transition: opacity var(--transition-fast), transform var(--transition-fast);
        }

        .submit-button:hover:not(:disabled) {
          opacity: 0.9;
        }

        .submit-button:active:not(:disabled) {
          transform: scale(0.98);
        }

        .submit-button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .submit-button .spinner {
          width: 16px;
          height: 16px;
          border-width: 2px;
          border-color: rgba(255, 255, 255, 0.3);
          border-top-color: white;
        }

        .creator-note {
          display: flex;
          align-items: flex-start;
          gap: var(--space-3);
          margin-top: var(--space-6);
          padding: var(--space-4);
          background: var(--color-accent-light);
          border-radius: var(--radius-md);
        }

        .creator-note .icon {
          font-size: var(--text-xl);
        }

        .creator-note p {
          margin: 0;
          font-size: var(--text-sm);
          color: var(--color-text-secondary);
        }

        .login-link {
          text-align: center;
          margin-top: var(--space-6);
          color: var(--color-text-secondary);
          font-size: var(--text-sm);
        }

        .login-link a {
          color: var(--color-accent);
          font-weight: 500;
        }
      `}</style>
    </div>
  );
}
