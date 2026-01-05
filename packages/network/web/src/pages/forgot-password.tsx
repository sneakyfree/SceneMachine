/**
 * Forgot Password Page
 *
 * Password reset request flow.
 */

'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { apiClient } from '../lib/api-client';

type Step = 'request' | 'sent' | 'reset' | 'success';

export default function ForgotPasswordPage() {
  const [step, setStep] = useState<Step>('request');
  const [email, setEmail] = useState('');
  const [token, setToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRequestReset = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      await apiClient.requestPasswordReset(email);
      setStep('sent');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send reset email');
    } finally {
      setIsLoading(false);
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    setIsLoading(true);

    try {
      await apiClient.resetPassword(token, newPassword);
      setStep('success');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reset password');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="forgot-page">
      <div className="forgot-container">
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

        {/* Step 1: Request Reset */}
        {step === 'request' && (
          <form onSubmit={handleRequestReset} className="forgot-form">
            <h2>Reset your password</h2>
            <p className="subtitle">
              Enter your email address and we'll send you a link to reset your password.
            </p>

            {error && (
              <div className="error-message" role="alert">
                {error}
              </div>
            )}

            <div className="form-group">
              <label htmlFor="email">Email address</label>
              <input
                type="email"
                id="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                autoComplete="email"
                autoFocus
                disabled={isLoading}
              />
            </div>

            <button
              type="submit"
              className="submit-button"
              disabled={isLoading || !email}
            >
              {isLoading ? (
                <>
                  <span className="spinner" />
                  Sending...
                </>
              ) : (
                'Send reset link'
              )}
            </button>
          </form>
        )}

        {/* Step 2: Email Sent */}
        {step === 'sent' && (
          <div className="forgot-form">
            <div className="success-icon">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                <polyline points="22 4 12 14.01 9 11.01" />
              </svg>
            </div>
            <h2>Check your email</h2>
            <p className="subtitle">
              We've sent a password reset link to <strong>{email}</strong>
            </p>
            <p className="hint">
              Didn't receive the email? Check your spam folder or{' '}
              <button
                type="button"
                className="link-button"
                onClick={() => setStep('request')}
              >
                try again
              </button>
            </p>

            <div className="divider">
              <span>or</span>
            </div>

            <button
              type="button"
              className="secondary-button"
              onClick={() => setStep('reset')}
            >
              I have a reset code
            </button>
          </div>
        )}

        {/* Step 3: Enter New Password */}
        {step === 'reset' && (
          <form onSubmit={handleResetPassword} className="forgot-form">
            <h2>Create new password</h2>
            <p className="subtitle">
              Enter the reset code from your email and create a new password.
            </p>

            {error && (
              <div className="error-message" role="alert">
                {error}
              </div>
            )}

            <div className="form-group">
              <label htmlFor="token">Reset code</label>
              <input
                type="text"
                id="token"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder="Enter code from email"
                required
                autoFocus
                disabled={isLoading}
              />
            </div>

            <div className="form-group">
              <label htmlFor="newPassword">New password</label>
              <input
                type="password"
                id="newPassword"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="At least 8 characters"
                required
                minLength={8}
                autoComplete="new-password"
                disabled={isLoading}
              />
            </div>

            <div className="form-group">
              <label htmlFor="confirmPassword">Confirm password</label>
              <input
                type="password"
                id="confirmPassword"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Confirm your password"
                required
                autoComplete="new-password"
                disabled={isLoading}
              />
            </div>

            <button
              type="submit"
              className="submit-button"
              disabled={isLoading || !token || !newPassword || !confirmPassword}
            >
              {isLoading ? (
                <>
                  <span className="spinner" />
                  Resetting...
                </>
              ) : (
                'Reset password'
              )}
            </button>

            <button
              type="button"
              className="back-button"
              onClick={() => setStep('sent')}
            >
              Back
            </button>
          </form>
        )}

        {/* Step 4: Success */}
        {step === 'success' && (
          <div className="forgot-form">
            <div className="success-icon">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                <polyline points="22 4 12 14.01 9 11.01" />
              </svg>
            </div>
            <h2>Password reset successful</h2>
            <p className="subtitle">
              Your password has been reset. You can now sign in with your new password.
            </p>

            <Link href="/login" className="submit-button">
              Sign in
            </Link>
          </div>
        )}

        {/* Back to login */}
        <p className="login-link">
          Remember your password?{' '}
          <Link href="/login">Sign in</Link>
        </p>
      </div>

      <style jsx>{`
        .forgot-page {
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: var(--space-4);
          background: var(--gradient-bg);
        }

        .forgot-container {
          width: 100%;
          max-width: 400px;
        }

        .logo {
          text-align: center;
          margin-bottom: var(--space-8);
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

        .forgot-form {
          background: var(--color-bg-secondary);
          border-radius: var(--radius-xl);
          padding: var(--space-6);
          border: 1px solid var(--color-border);
        }

        .forgot-form h2 {
          font-size: var(--text-xl);
          margin-bottom: var(--space-2);
          text-align: center;
        }

        .forgot-form .subtitle {
          color: var(--color-text-secondary);
          font-size: var(--text-sm);
          margin-bottom: var(--space-6);
          text-align: center;
        }

        .success-icon {
          display: flex;
          justify-content: center;
          margin-bottom: var(--space-4);
          color: var(--color-success);
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

        .form-group {
          margin-bottom: var(--space-4);
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

        .form-group input::placeholder {
          color: var(--color-text-muted);
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
          transition: opacity var(--transition-fast);
          text-decoration: none;
        }

        .submit-button:hover:not(:disabled) {
          opacity: 0.9;
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

        .secondary-button {
          width: 100%;
          padding: var(--space-3) var(--space-4);
          background: var(--color-bg-tertiary);
          border: 1px solid var(--color-border);
          color: var(--color-text-primary);
          font-weight: 500;
          border-radius: var(--radius-md);
          transition: border-color var(--transition-fast);
        }

        .secondary-button:hover {
          border-color: var(--color-accent);
        }

        .back-button {
          width: 100%;
          padding: var(--space-3);
          color: var(--color-text-secondary);
          font-weight: 500;
          margin-top: var(--space-2);
        }

        .back-button:hover {
          color: var(--color-text-primary);
        }

        .hint {
          font-size: var(--text-sm);
          color: var(--color-text-tertiary);
          text-align: center;
          margin-bottom: var(--space-4);
        }

        .link-button {
          color: var(--color-accent);
          font-weight: 500;
        }

        .divider {
          display: flex;
          align-items: center;
          gap: var(--space-4);
          margin: var(--space-4) 0;
          color: var(--color-text-muted);
          font-size: var(--text-sm);
        }

        .divider::before,
        .divider::after {
          content: '';
          flex: 1;
          height: 1px;
          background: var(--color-border);
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

        .spinner {
          width: 24px;
          height: 24px;
          border: 2px solid var(--color-border);
          border-top-color: var(--color-accent);
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
