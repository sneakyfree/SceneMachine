/**
 * Settings Page
 *
 * User account settings, channel customization, and preferences.
 */

'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuthStore } from '../../stores';
import { apiClient } from '../../lib/api-client';

type SettingsTab = 'account' | 'channel' | 'notifications' | 'privacy' | 'billing';

interface UserSettings {
  email: string;
  username: string;
  display_name: string;
  bio: string;
  avatar_url: string;
  banner_url: string;
  notification_preferences: {
    email_comments: boolean;
    email_followers: boolean;
    email_earnings: boolean;
    push_comments: boolean;
    push_followers: boolean;
  };
  privacy_settings: {
    show_subscribers: boolean;
    show_watch_history: boolean;
    allow_recommendations: boolean;
  };
}

export default function SettingsPage() {
  const router = useRouter();
  const { user, isAuthenticated, refreshUser } = useAuthStore();
  const avatarInputRef = useRef<HTMLInputElement>(null);
  const bannerInputRef = useRef<HTMLInputElement>(null);

  const [activeTab, setActiveTab] = useState<SettingsTab>('account');
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [settings, setSettings] = useState<UserSettings>({
    email: '',
    username: '',
    display_name: '',
    bio: '',
    avatar_url: '',
    banner_url: '',
    notification_preferences: {
      email_comments: true,
      email_followers: true,
      email_earnings: true,
      push_comments: true,
      push_followers: true,
    },
    privacy_settings: {
      show_subscribers: true,
      show_watch_history: false,
      allow_recommendations: true,
    },
  });

  const [avatarPreview, setAvatarPreview] = useState<string | null>(null);
  const [bannerPreview, setBannerPreview] = useState<string | null>(null);
  const [newAvatar, setNewAvatar] = useState<File | null>(null);
  const [newBanner, setNewBanner] = useState<File | null>(null);

  // Password change
  const [passwordData, setPasswordData] = useState({
    current: '',
    new: '',
    confirm: '',
  });
  const [passwordError, setPasswordError] = useState<string | null>(null);

  // Redirect if not authenticated
  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login?redirect=/settings');
    }
  }, [isAuthenticated, router]);

  // Load settings
  useEffect(() => {
    if (!isAuthenticated || !user) return;

    setSettings({
      email: user.email || '',
      username: user.username || '',
      display_name: user.display_name || '',
      bio: user.bio || '',
      avatar_url: user.avatar_url || '',
      banner_url: user.banner_url || '',
      notification_preferences: user.notification_preferences || {
        email_comments: true,
        email_followers: true,
        email_earnings: true,
        push_comments: true,
        push_followers: true,
      },
      privacy_settings: user.privacy_settings || {
        show_subscribers: true,
        show_watch_history: false,
        allow_recommendations: true,
      },
    });
  }, [isAuthenticated, user]);

  const handleAvatarSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setNewAvatar(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setAvatarPreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleBannerSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setNewBanner(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setBannerPreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    setError(null);
    setSaveSuccess(false);

    try {
      // Upload new avatar if selected
      if (newAvatar) {
        const result = await apiClient.uploadAvatar(newAvatar);
        settings.avatar_url = result.avatar_url;
      }

      // Upload new banner if selected
      if (newBanner) {
        const result = await apiClient.uploadBanner(newBanner);
        settings.banner_url = result.banner_url;
      }

      // Update profile
      await apiClient.updateProfile({
        display_name: settings.display_name,
        bio: settings.bio,
        notification_preferences: settings.notification_preferences,
        privacy_settings: settings.privacy_settings,
      });

      // Update local state
      await refreshUser();

      setSaveSuccess(true);
      setNewAvatar(null);
      setNewBanner(null);
      setAvatarPreview(null);
      setBannerPreview(null);

      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save settings');
    } finally {
      setIsSaving(false);
    }
  };

  const handlePasswordChange = async () => {
    setPasswordError(null);

    if (passwordData.new !== passwordData.confirm) {
      setPasswordError('New passwords do not match');
      return;
    }

    if (passwordData.new.length < 8) {
      setPasswordError('Password must be at least 8 characters');
      return;
    }

    setIsSaving(true);
    try {
      await apiClient.changePassword(passwordData.current, passwordData.new);
      setPasswordData({ current: '', new: '', confirm: '' });
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      setPasswordError(err instanceof Error ? err.message : 'Failed to change password');
    } finally {
      setIsSaving(false);
    }
  };

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="settings-page">
      {/* Sidebar */}
      <aside className="sidebar">
        <Link href="/" className="logo">
          <span className="logo-icon">SM</span>
          <span className="logo-text">Network</span>
        </Link>

        <nav className="nav">
          <button
            className={`nav-item ${activeTab === 'account' ? 'active' : ''}`}
            onClick={() => setActiveTab('account')}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
            Account
          </button>
          <button
            className={`nav-item ${activeTab === 'channel' ? 'active' : ''}`}
            onClick={() => setActiveTab('channel')}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polygon points="23 7 16 12 23 17 23 7" />
              <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
            </svg>
            Channel
          </button>
          <button
            className={`nav-item ${activeTab === 'notifications' ? 'active' : ''}`}
            onClick={() => setActiveTab('notifications')}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
              <path d="M13.73 21a2 2 0 0 1-3.46 0" />
            </svg>
            Notifications
          </button>
          <button
            className={`nav-item ${activeTab === 'privacy' ? 'active' : ''}`}
            onClick={() => setActiveTab('privacy')}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
            Privacy
          </button>
          <button
            className={`nav-item ${activeTab === 'billing' ? 'active' : ''}`}
            onClick={() => setActiveTab('billing')}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="1" y="4" width="22" height="16" rx="2" ry="2" />
              <line x1="1" y1="10" x2="23" y2="10" />
            </svg>
            Billing
          </button>
        </nav>

        <div className="sidebar-footer">
          <Link href="/dashboard" className="nav-item">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="7" height="7" />
              <rect x="14" y="3" width="7" height="7" />
              <rect x="14" y="14" width="7" height="7" />
              <rect x="3" y="14" width="7" height="7" />
            </svg>
            Dashboard
          </Link>
          <Link href={`/channel/${user?.id}`} className="nav-item">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
              <polyline points="10 17 15 12 10 7" />
              <line x1="15" y1="12" x2="3" y2="12" />
            </svg>
            View Channel
          </Link>
        </div>
      </aside>

      {/* Main Content */}
      <main className="main">
        <header className="header">
          <h1>Settings</h1>
          {saveSuccess && (
            <span className="save-success">Changes saved successfully!</span>
          )}
        </header>

        {error && (
          <div className="error-message" role="alert">
            {error}
          </div>
        )}

        {/* Account Tab */}
        {activeTab === 'account' && (
          <div className="settings-section">
            <h2>Account Information</h2>

            <div className="form-group">
              <label>Email</label>
              <input
                type="email"
                value={settings.email}
                disabled
                className="disabled"
              />
              <span className="hint">Contact support to change your email</span>
            </div>

            <div className="form-group">
              <label>Username</label>
              <div className="input-with-prefix">
                <span className="prefix">@</span>
                <input
                  type="text"
                  value={settings.username}
                  disabled
                  className="disabled"
                />
              </div>
              <span className="hint">Username cannot be changed</span>
            </div>

            <div className="form-group">
              <label htmlFor="display_name">Display Name</label>
              <input
                type="text"
                id="display_name"
                value={settings.display_name}
                onChange={(e) => setSettings(s => ({ ...s, display_name: e.target.value }))}
                placeholder="Your public display name"
                maxLength={50}
              />
            </div>

            <div className="divider" />

            <h2>Change Password</h2>

            {passwordError && (
              <div className="error-message small">{passwordError}</div>
            )}

            <div className="form-group">
              <label htmlFor="current_password">Current Password</label>
              <input
                type="password"
                id="current_password"
                value={passwordData.current}
                onChange={(e) => setPasswordData(p => ({ ...p, current: e.target.value }))}
                placeholder="Enter current password"
              />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="new_password">New Password</label>
                <input
                  type="password"
                  id="new_password"
                  value={passwordData.new}
                  onChange={(e) => setPasswordData(p => ({ ...p, new: e.target.value }))}
                  placeholder="Enter new password"
                />
              </div>
              <div className="form-group">
                <label htmlFor="confirm_password">Confirm Password</label>
                <input
                  type="password"
                  id="confirm_password"
                  value={passwordData.confirm}
                  onChange={(e) => setPasswordData(p => ({ ...p, confirm: e.target.value }))}
                  placeholder="Confirm new password"
                />
              </div>
            </div>

            <button
              className="btn-secondary"
              onClick={handlePasswordChange}
              disabled={!passwordData.current || !passwordData.new || !passwordData.confirm || isSaving}
            >
              Change Password
            </button>
          </div>
        )}

        {/* Channel Tab */}
        {activeTab === 'channel' && (
          <div className="settings-section">
            <h2>Channel Customization</h2>

            {/* Banner */}
            <div className="form-group">
              <label>Channel Banner</label>
              <div
                className="banner-preview"
                style={{
                  backgroundImage: bannerPreview || settings.banner_url
                    ? `url(${bannerPreview || settings.banner_url})`
                    : undefined,
                }}
                onClick={() => bannerInputRef.current?.click()}
              >
                {!bannerPreview && !settings.banner_url && (
                  <div className="upload-placeholder">
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                      <circle cx="8.5" cy="8.5" r="1.5" />
                      <polyline points="21 15 16 10 5 21" />
                    </svg>
                    <span>Upload banner (2048 x 512)</span>
                  </div>
                )}
                <input
                  ref={bannerInputRef}
                  type="file"
                  accept="image/*"
                  onChange={handleBannerSelect}
                  hidden
                />
              </div>
            </div>

            {/* Avatar */}
            <div className="form-group">
              <label>Profile Picture</label>
              <div className="avatar-section">
                <div
                  className="avatar-preview"
                  onClick={() => avatarInputRef.current?.click()}
                >
                  <img
                    src={avatarPreview || settings.avatar_url || '/default-avatar.jpg'}
                    alt="Avatar"
                  />
                  <div className="avatar-overlay">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12" />
                    </svg>
                  </div>
                  <input
                    ref={avatarInputRef}
                    type="file"
                    accept="image/*"
                    onChange={handleAvatarSelect}
                    hidden
                  />
                </div>
                <span className="hint">Click to upload (recommended: 400 x 400)</span>
              </div>
            </div>

            {/* Bio */}
            <div className="form-group">
              <label htmlFor="bio">Channel Description</label>
              <textarea
                id="bio"
                value={settings.bio}
                onChange={(e) => setSettings(s => ({ ...s, bio: e.target.value }))}
                placeholder="Tell viewers about your channel..."
                rows={5}
                maxLength={1000}
              />
              <span className="char-count">{settings.bio.length}/1000</span>
            </div>

            <button
              className="btn-primary"
              onClick={handleSave}
              disabled={isSaving}
            >
              {isSaving ? <span className="spinner" /> : 'Save Changes'}
            </button>
          </div>
        )}

        {/* Notifications Tab */}
        {activeTab === 'notifications' && (
          <div className="settings-section">
            <h2>Email Notifications</h2>

            <div className="toggle-group">
              <label className="toggle-item">
                <div className="toggle-info">
                  <span className="toggle-label">Comments</span>
                  <span className="toggle-description">Get notified when someone comments on your videos</span>
                </div>
                <input
                  type="checkbox"
                  checked={settings.notification_preferences.email_comments}
                  onChange={(e) => setSettings(s => ({
                    ...s,
                    notification_preferences: { ...s.notification_preferences, email_comments: e.target.checked },
                  }))}
                />
              </label>

              <label className="toggle-item">
                <div className="toggle-info">
                  <span className="toggle-label">New Followers</span>
                  <span className="toggle-description">Get notified when you gain new followers</span>
                </div>
                <input
                  type="checkbox"
                  checked={settings.notification_preferences.email_followers}
                  onChange={(e) => setSettings(s => ({
                    ...s,
                    notification_preferences: { ...s.notification_preferences, email_followers: e.target.checked },
                  }))}
                />
              </label>

              <label className="toggle-item">
                <div className="toggle-info">
                  <span className="toggle-label">Earnings Updates</span>
                  <span className="toggle-description">Weekly summary of your earnings and payouts</span>
                </div>
                <input
                  type="checkbox"
                  checked={settings.notification_preferences.email_earnings}
                  onChange={(e) => setSettings(s => ({
                    ...s,
                    notification_preferences: { ...s.notification_preferences, email_earnings: e.target.checked },
                  }))}
                />
              </label>
            </div>

            <div className="divider" />

            <h2>Push Notifications</h2>

            <div className="toggle-group">
              <label className="toggle-item">
                <div className="toggle-info">
                  <span className="toggle-label">Comments</span>
                  <span className="toggle-description">Instant notifications for new comments</span>
                </div>
                <input
                  type="checkbox"
                  checked={settings.notification_preferences.push_comments}
                  onChange={(e) => setSettings(s => ({
                    ...s,
                    notification_preferences: { ...s.notification_preferences, push_comments: e.target.checked },
                  }))}
                />
              </label>

              <label className="toggle-item">
                <div className="toggle-info">
                  <span className="toggle-label">New Followers</span>
                  <span className="toggle-description">Instant notifications for new followers</span>
                </div>
                <input
                  type="checkbox"
                  checked={settings.notification_preferences.push_followers}
                  onChange={(e) => setSettings(s => ({
                    ...s,
                    notification_preferences: { ...s.notification_preferences, push_followers: e.target.checked },
                  }))}
                />
              </label>
            </div>

            <button
              className="btn-primary"
              onClick={handleSave}
              disabled={isSaving}
            >
              {isSaving ? <span className="spinner" /> : 'Save Changes'}
            </button>
          </div>
        )}

        {/* Privacy Tab */}
        {activeTab === 'privacy' && (
          <div className="settings-section">
            <h2>Privacy Settings</h2>

            <div className="toggle-group">
              <label className="toggle-item">
                <div className="toggle-info">
                  <span className="toggle-label">Show Subscriber Count</span>
                  <span className="toggle-description">Display your subscriber count on your channel</span>
                </div>
                <input
                  type="checkbox"
                  checked={settings.privacy_settings.show_subscribers}
                  onChange={(e) => setSettings(s => ({
                    ...s,
                    privacy_settings: { ...s.privacy_settings, show_subscribers: e.target.checked },
                  }))}
                />
              </label>

              <label className="toggle-item">
                <div className="toggle-info">
                  <span className="toggle-label">Show Watch History</span>
                  <span className="toggle-description">Allow others to see videos you've watched</span>
                </div>
                <input
                  type="checkbox"
                  checked={settings.privacy_settings.show_watch_history}
                  onChange={(e) => setSettings(s => ({
                    ...s,
                    privacy_settings: { ...s.privacy_settings, show_watch_history: e.target.checked },
                  }))}
                />
              </label>

              <label className="toggle-item">
                <div className="toggle-info">
                  <span className="toggle-label">Personalized Recommendations</span>
                  <span className="toggle-description">Use your watch history for better recommendations</span>
                </div>
                <input
                  type="checkbox"
                  checked={settings.privacy_settings.allow_recommendations}
                  onChange={(e) => setSettings(s => ({
                    ...s,
                    privacy_settings: { ...s.privacy_settings, allow_recommendations: e.target.checked },
                  }))}
                />
              </label>
            </div>

            <div className="divider" />

            <h2>Data & Account</h2>

            <div className="action-group">
              <button className="btn-secondary">Download My Data</button>
              <button className="btn-danger">Delete Account</button>
            </div>

            <button
              className="btn-primary"
              onClick={handleSave}
              disabled={isSaving}
            >
              {isSaving ? <span className="spinner" /> : 'Save Changes'}
            </button>
          </div>
        )}

        {/* Billing Tab */}
        {activeTab === 'billing' && (
          <div className="settings-section">
            <h2>Payment Methods</h2>

            <div className="empty-state">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <rect x="1" y="4" width="22" height="16" rx="2" ry="2" />
                <line x1="1" y1="10" x2="23" y2="10" />
              </svg>
              <p>No payment methods added</p>
              <button className="btn-primary">Add Payment Method</button>
            </div>

            <div className="divider" />

            <h2>Payout Settings</h2>

            <div className="payout-info">
              <p>Configure how you receive your earnings from SceneMachine Network.</p>
              <Link href="/dashboard/earnings" className="link">
                Manage payouts in Earnings Dashboard →
              </Link>
            </div>
          </div>
        )}
      </main>

      <style jsx>{`
        .settings-page {
          display: flex;
          min-height: 100vh;
          background: var(--color-bg-primary);
        }

        /* Sidebar */
        .sidebar {
          width: 260px;
          background: var(--color-bg-secondary);
          border-right: 1px solid var(--color-border);
          display: flex;
          flex-direction: column;
          position: fixed;
          top: 0;
          left: 0;
          bottom: 0;
          z-index: 100;
        }

        .logo {
          display: flex;
          align-items: center;
          gap: var(--space-2);
          padding: var(--space-4);
          text-decoration: none;
        }

        .logo-icon {
          width: 32px;
          height: 32px;
          background: var(--gradient-primary);
          border-radius: var(--radius-md);
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          font-weight: 700;
          font-size: var(--text-sm);
        }

        .logo-text {
          font-weight: 700;
          font-size: var(--text-lg);
          color: var(--color-text-primary);
        }

        .nav {
          flex: 1;
          padding: var(--space-4);
          display: flex;
          flex-direction: column;
          gap: var(--space-1);
        }

        .nav-item {
          display: flex;
          align-items: center;
          gap: var(--space-3);
          padding: var(--space-3);
          border-radius: var(--radius-md);
          color: var(--color-text-secondary);
          text-decoration: none;
          font-weight: 500;
          transition: all var(--transition-fast);
          width: 100%;
          text-align: left;
        }

        .nav-item:hover {
          background: var(--color-bg-tertiary);
          color: var(--color-text-primary);
        }

        .nav-item.active {
          background: var(--color-accent-light);
          color: var(--color-accent);
        }

        .sidebar-footer {
          padding: var(--space-4);
          border-top: 1px solid var(--color-border);
          display: flex;
          flex-direction: column;
          gap: var(--space-1);
        }

        /* Main */
        .main {
          flex: 1;
          margin-left: 260px;
          padding: var(--space-6);
          max-width: 800px;
        }

        .header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: var(--space-6);
        }

        .header h1 {
          font-size: var(--text-2xl);
        }

        .save-success {
          color: var(--color-success);
          font-size: var(--text-sm);
          font-weight: 500;
        }

        .error-message {
          padding: var(--space-4);
          background: rgba(239, 68, 68, 0.1);
          border: 1px solid var(--color-error);
          border-radius: var(--radius-lg);
          color: var(--color-error);
          margin-bottom: var(--space-6);
        }

        .error-message.small {
          padding: var(--space-3);
          font-size: var(--text-sm);
          margin-bottom: var(--space-4);
        }

        /* Settings Section */
        .settings-section {
          background: var(--color-bg-secondary);
          border: 1px solid var(--color-border);
          border-radius: var(--radius-xl);
          padding: var(--space-6);
        }

        .settings-section h2 {
          font-size: var(--text-lg);
          margin-bottom: var(--space-4);
        }

        .divider {
          height: 1px;
          background: var(--color-border);
          margin: var(--space-6) 0;
        }

        /* Form */
        .form-group {
          margin-bottom: var(--space-4);
        }

        .form-group label {
          display: block;
          font-size: var(--text-sm);
          font-weight: 500;
          color: var(--color-text-secondary);
          margin-bottom: var(--space-2);
        }

        .form-group input,
        .form-group textarea {
          width: 100%;
          padding: var(--space-3) var(--space-4);
          background: var(--color-bg-tertiary);
          border: 1px solid var(--color-border);
          border-radius: var(--radius-md);
          color: var(--color-text-primary);
          font-size: var(--text-base);
        }

        .form-group input:focus,
        .form-group textarea:focus {
          border-color: var(--color-accent);
          outline: none;
        }

        .form-group input.disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .form-group textarea {
          resize: vertical;
        }

        .hint {
          display: block;
          font-size: var(--text-xs);
          color: var(--color-text-muted);
          margin-top: var(--space-1);
        }

        .char-count {
          display: block;
          font-size: var(--text-xs);
          color: var(--color-text-muted);
          text-align: right;
          margin-top: var(--space-1);
        }

        .input-with-prefix {
          display: flex;
          align-items: center;
          background: var(--color-bg-tertiary);
          border: 1px solid var(--color-border);
          border-radius: var(--radius-md);
        }

        .prefix {
          padding: var(--space-3) var(--space-3) var(--space-3) var(--space-4);
          color: var(--color-text-tertiary);
        }

        .input-with-prefix input {
          border: none;
          background: transparent;
          padding-left: 0;
        }

        .form-row {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: var(--space-4);
        }

        /* Banner & Avatar */
        .banner-preview {
          width: 100%;
          height: 128px;
          background: var(--color-bg-tertiary);
          background-size: cover;
          background-position: center;
          border-radius: var(--radius-lg);
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          border: 2px dashed var(--color-border);
          transition: border-color var(--transition-fast);
        }

        .banner-preview:hover {
          border-color: var(--color-accent);
        }

        .upload-placeholder {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: var(--space-2);
          color: var(--color-text-tertiary);
          font-size: var(--text-sm);
        }

        .avatar-section {
          display: flex;
          align-items: center;
          gap: var(--space-4);
        }

        .avatar-preview {
          position: relative;
          width: 100px;
          height: 100px;
          border-radius: 50%;
          overflow: hidden;
          cursor: pointer;
        }

        .avatar-preview img {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }

        .avatar-overlay {
          position: absolute;
          inset: 0;
          background: rgba(0, 0, 0, 0.5);
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          opacity: 0;
          transition: opacity var(--transition-fast);
        }

        .avatar-preview:hover .avatar-overlay {
          opacity: 1;
        }

        /* Toggle Group */
        .toggle-group {
          display: flex;
          flex-direction: column;
          gap: var(--space-2);
        }

        .toggle-item {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: var(--space-4);
          background: var(--color-bg-tertiary);
          border-radius: var(--radius-md);
          cursor: pointer;
        }

        .toggle-info {
          flex: 1;
        }

        .toggle-label {
          display: block;
          font-weight: 500;
          margin-bottom: var(--space-1);
        }

        .toggle-description {
          display: block;
          font-size: var(--text-sm);
          color: var(--color-text-tertiary);
        }

        .toggle-item input[type="checkbox"] {
          width: 44px;
          height: 24px;
          accent-color: var(--color-accent);
        }

        /* Buttons */
        .btn-primary,
        .btn-secondary,
        .btn-danger {
          padding: var(--space-3) var(--space-4);
          border-radius: var(--radius-md);
          font-weight: 600;
          font-size: var(--text-sm);
          transition: all var(--transition-fast);
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: var(--space-2);
        }

        .btn-primary {
          background: var(--gradient-primary);
          color: white;
          margin-top: var(--space-4);
        }

        .btn-secondary {
          background: var(--color-bg-tertiary);
          border: 1px solid var(--color-border);
          color: var(--color-text-primary);
        }

        .btn-danger {
          background: rgba(239, 68, 68, 0.1);
          border: 1px solid var(--color-error);
          color: var(--color-error);
        }

        .btn-primary:disabled,
        .btn-secondary:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .action-group {
          display: flex;
          gap: var(--space-3);
          margin-bottom: var(--space-4);
        }

        /* Empty State */
        .empty-state {
          text-align: center;
          padding: var(--space-8);
          color: var(--color-text-tertiary);
        }

        .empty-state svg {
          margin-bottom: var(--space-4);
        }

        .empty-state p {
          margin-bottom: var(--space-4);
        }

        .payout-info {
          padding: var(--space-4);
          background: var(--color-bg-tertiary);
          border-radius: var(--radius-md);
        }

        .payout-info p {
          margin-bottom: var(--space-2);
          color: var(--color-text-secondary);
        }

        .link {
          color: var(--color-accent);
          font-weight: 500;
        }

        .spinner {
          width: 16px;
          height: 16px;
          border: 2px solid rgba(255, 255, 255, 0.3);
          border-top-color: white;
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }

        @media (max-width: 900px) {
          .sidebar { display: none; }
          .main { margin-left: 0; max-width: 100%; }
        }

        @media (max-width: 640px) {
          .main { padding: var(--space-4); }
          .form-row { grid-template-columns: 1fr; }
          .action-group { flex-direction: column; }
        }
      `}</style>
    </div>
  );
}
