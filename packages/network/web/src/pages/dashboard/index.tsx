/**
 * Creator Dashboard
 *
 * Analytics overview, video management, and quick actions for creators.
 */

'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuthStore } from '../../stores';
import { apiClient, Video } from '../../lib/api-client';

interface LocalDashboardStats {
  total_views: number;
  total_watch_time_minutes: number;
  total_subscribers: number;
  total_revenue: number;
  views_change: number;
  subscribers_change: number;
  revenue_change: number;
}

interface DailyStats {
  date: string;
  views: number;
  watch_time: number;
  revenue: number;
}

interface TopVideo {
  video: Video;
  views: number;
  watch_time: number;
  revenue: number;
}

type TimeRange = '7d' | '30d' | '90d' | 'all';

export default function CreatorDashboard() {
  const router = useRouter();
  const { user, isAuthenticated } = useAuthStore();

  const [stats, setStats] = useState<LocalDashboardStats | null>(null);
  const [dailyStats, setDailyStats] = useState<DailyStats[]>([]);
  const [topVideos, setTopVideos] = useState<TopVideo[]>([]);
  const [recentVideos, setRecentVideos] = useState<Video[]>([]);
  const [timeRange, setTimeRange] = useState<TimeRange>('30d');
  const [isLoading, setIsLoading] = useState(true);

  // Redirect if not authenticated
  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login?redirect=/dashboard');
    }
  }, [isAuthenticated, router]);

  // Load dashboard data
  useEffect(() => {
    if (!isAuthenticated) return;

    const loadDashboard = async () => {
      setIsLoading(true);
      try {
        const [dashboardData, videosRes] = await Promise.all([
          apiClient.getCreatorDashboard(timeRange),
          apiClient.getVideosByCreator(user!.id),
        ]);

        // Transform API stats to local format
        const apiStats = dashboardData.stats;
        setStats({
          total_views: apiStats?.total_views || 0,
          total_watch_time_minutes: (apiStats?.total_watch_time_hours || 0) * 60,
          total_subscribers: apiStats?.subscriber_count || 0,
          total_revenue: apiStats?.total_earnings || 0,
          views_change: apiStats?.views_change_percent || 0,
          subscribers_change: 0, // Not in API response
          revenue_change: apiStats?.earnings_change_percent || 0,
        });
        setDailyStats(dashboardData.daily_stats || []);
        setTopVideos(dashboardData.top_videos || []);
        setRecentVideos(videosRes.items.slice(0, 5));
      } catch (err) {
        console.error('Failed to load dashboard:', err);
      } finally {
        setIsLoading(false);
      }
    };

    loadDashboard();
  }, [isAuthenticated, user, timeRange]);

  const formatNumber = (num: number): string => {
    if (num >= 1000000) {
      return `${(num / 1000000).toFixed(1)}M`;
    }
    if (num >= 1000) {
      return `${(num / 1000).toFixed(1)}K`;
    }
    return num.toLocaleString();
  };

  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const formatDuration = (minutes: number): string => {
    if (minutes >= 60) {
      const hours = Math.floor(minutes / 60);
      const mins = minutes % 60;
      return `${hours}h ${mins}m`;
    }
    return `${minutes}m`;
  };

  const formatChange = (change: number): { text: string; isPositive: boolean } => {
    const isPositive = change >= 0;
    const text = `${isPositive ? '+' : ''}${change.toFixed(1)}%`;
    return { text, isPositive };
  };

  const formatVideoDuration = (seconds: number): string => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    if (hrs > 0) {
      return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Calculate chart dimensions
  const maxViews = Math.max(...dailyStats.map(d => d.views), 1);

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="dashboard-page">
      {/* Sidebar */}
      <aside className="sidebar">
        <Link href="/" className="logo">
          <span className="logo-icon">SM</span>
          <span className="logo-text">Studio</span>
        </Link>

        <nav className="nav">
          <Link href="/dashboard" className="nav-item active">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="7" height="7" />
              <rect x="14" y="3" width="7" height="7" />
              <rect x="14" y="14" width="7" height="7" />
              <rect x="3" y="14" width="7" height="7" />
            </svg>
            Dashboard
          </Link>
          <Link href="/dashboard/content" className="nav-item">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polygon points="23 7 16 12 23 17 23 7" />
              <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
            </svg>
            Content
          </Link>
          <Link href="/dashboard/analytics" className="nav-item">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="20" x2="18" y2="10" />
              <line x1="12" y1="20" x2="12" y2="4" />
              <line x1="6" y1="20" x2="6" y2="14" />
            </svg>
            Analytics
          </Link>
          <Link href="/dashboard/earnings" className="nav-item">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="12" y1="1" x2="12" y2="23" />
              <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
            </svg>
            Earnings
          </Link>
          <Link href="/dashboard/comments" className="nav-item">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
            Comments
          </Link>
        </nav>

        <div className="sidebar-footer">
          <Link href="/settings" className="nav-item">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
            </svg>
            Settings
          </Link>
          <Link href={`/channel/${user?.id}`} className="nav-item">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
            View Channel
          </Link>
        </div>
      </aside>

      {/* Main Content */}
      <main className="main">
        {/* Header */}
        <header className="header">
          <div className="header-left">
            <h1>Channel Dashboard</h1>
            <p>Welcome back, {user?.display_name || user?.username}</p>
          </div>

          <div className="header-right">
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value as TimeRange)}
              className="time-select"
            >
              <option value="7d">Last 7 days</option>
              <option value="30d">Last 30 days</option>
              <option value="90d">Last 90 days</option>
              <option value="all">All time</option>
            </select>

            <Link href="/upload" className="upload-btn">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12" />
              </svg>
              Upload
            </Link>
          </div>
        </header>

        {isLoading ? (
          <div className="loading-state">
            <div className="stats-grid">
              {[1, 2, 3, 4].map(i => (
                <div key={i} className="skeleton stat-card" />
              ))}
            </div>
            <div className="skeleton chart-card" />
          </div>
        ) : (
          <>
            {/* Stats Cards */}
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-icon views">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                </div>
                <div className="stat-content">
                  <span className="stat-label">Views</span>
                  <span className="stat-value">{formatNumber(stats?.total_views || 0)}</span>
                  {stats && (
                    <span className={`stat-change ${formatChange(stats.views_change).isPositive ? 'positive' : 'negative'}`}>
                      {formatChange(stats.views_change).text}
                    </span>
                  )}
                </div>
              </div>

              <div className="stat-card">
                <div className="stat-icon time">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10" />
                    <polyline points="12 6 12 12 16 14" />
                  </svg>
                </div>
                <div className="stat-content">
                  <span className="stat-label">Watch Time</span>
                  <span className="stat-value">{formatDuration(stats?.total_watch_time_minutes || 0)}</span>
                </div>
              </div>

              <div className="stat-card">
                <div className="stat-icon subscribers">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                    <circle cx="9" cy="7" r="4" />
                    <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
                  </svg>
                </div>
                <div className="stat-content">
                  <span className="stat-label">Subscribers</span>
                  <span className="stat-value">{formatNumber(stats?.total_subscribers || 0)}</span>
                  {stats && (
                    <span className={`stat-change ${formatChange(stats.subscribers_change).isPositive ? 'positive' : 'negative'}`}>
                      {formatChange(stats.subscribers_change).text}
                    </span>
                  )}
                </div>
              </div>

              <div className="stat-card">
                <div className="stat-icon revenue">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="12" y1="1" x2="12" y2="23" />
                    <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
                  </svg>
                </div>
                <div className="stat-content">
                  <span className="stat-label">Revenue</span>
                  <span className="stat-value">{formatCurrency(stats?.total_revenue || 0)}</span>
                  {stats && (
                    <span className={`stat-change ${formatChange(stats.revenue_change).isPositive ? 'positive' : 'negative'}`}>
                      {formatChange(stats.revenue_change).text}
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Chart */}
            <div className="chart-card">
              <h2>Views Over Time</h2>
              <div className="chart">
                <div className="chart-bars">
                  {dailyStats.map((day, index) => (
                    <div
                      key={day.date}
                      className="chart-bar"
                      style={{ height: `${(day.views / maxViews) * 100}%` }}
                      title={`${day.date}: ${formatNumber(day.views)} views`}
                    />
                  ))}
                </div>
                <div className="chart-labels">
                  {dailyStats.filter((_, i) => i % Math.ceil(dailyStats.length / 7) === 0).map(day => (
                    <span key={day.date}>{new Date(day.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
                  ))}
                </div>
              </div>
            </div>

            {/* Two Column Layout */}
            <div className="two-col">
              {/* Top Videos */}
              <div className="card">
                <div className="card-header">
                  <h2>Top Videos</h2>
                  <Link href="/dashboard/analytics" className="see-more">See All</Link>
                </div>
                <div className="video-list">
                  {topVideos.length === 0 ? (
                    <p className="empty-text">No video data yet</p>
                  ) : (
                    topVideos.slice(0, 5).map((item, index) => (
                      <div key={item.video.id} className="video-item">
                        <span className="rank">{index + 1}</span>
                        <Link href={`/watch/${item.video.id}`} className="video-thumb">
                          <img src={item.video.thumbnail_url || '/placeholder-thumbnail.jpg'} alt={item.video.title} />
                        </Link>
                        <div className="video-info">
                          <Link href={`/watch/${item.video.id}`} className="video-title">
                            {item.video.title}
                          </Link>
                          <span className="video-stats">{formatNumber(item.views)} views</span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Recent Videos */}
              <div className="card">
                <div className="card-header">
                  <h2>Recent Uploads</h2>
                  <Link href="/dashboard/content" className="see-more">See All</Link>
                </div>
                <div className="video-list">
                  {recentVideos.length === 0 ? (
                    <div className="empty-state">
                      <p>No videos uploaded yet</p>
                      <Link href="/upload" className="upload-link">Upload your first video</Link>
                    </div>
                  ) : (
                    recentVideos.map(video => (
                      <div key={video.id} className="video-item">
                        <Link href={`/watch/${video.id}`} className="video-thumb">
                          <img src={video.thumbnail_url || '/placeholder-thumbnail.jpg'} alt={video.title} />
                          <span className="duration">{formatVideoDuration(video.duration_seconds)}</span>
                        </Link>
                        <div className="video-info">
                          <Link href={`/watch/${video.id}`} className="video-title">
                            {video.title}
                          </Link>
                          <span className="video-stats">
                            {video.status === 'PUBLISHED' ? (
                              <>{formatNumber(video.view_count)} views</>
                            ) : (
                              <span className="status-badge">{video.status}</span>
                            )}
                          </span>
                        </div>
                        <Link href={`/dashboard/video/${video.id}`} className="edit-btn">
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                          </svg>
                        </Link>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="quick-actions">
              <h2>Quick Actions</h2>
              <div className="actions-grid">
                <Link href="/upload" className="action-card">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12" />
                  </svg>
                  <span>Upload Video</span>
                </Link>
                <Link href="/dashboard/analytics" className="action-card">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="18" y1="20" x2="18" y2="10" />
                    <line x1="12" y1="20" x2="12" y2="4" />
                    <line x1="6" y1="20" x2="6" y2="14" />
                  </svg>
                  <span>View Analytics</span>
                </Link>
                <Link href="/dashboard/earnings" className="action-card">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="12" y1="1" x2="12" y2="23" />
                    <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
                  </svg>
                  <span>Manage Earnings</span>
                </Link>
                <Link href="/settings/channel" className="action-card">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="3" />
                    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
                  </svg>
                  <span>Channel Settings</span>
                </Link>
              </div>
            </div>
          </>
        )}
      </main>

      <style jsx>{`
        .dashboard-page {
          display: flex;
          min-height: 100vh;
          background: var(--color-bg-primary);
        }

        /* Sidebar */
        .sidebar {
          width: 240px;
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

        /* Main Content */
        .main {
          flex: 1;
          margin-left: 240px;
          padding: var(--space-6);
        }

        .header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: var(--space-6);
        }

        .header h1 {
          font-size: var(--text-2xl);
          margin-bottom: var(--space-1);
        }

        .header p {
          color: var(--color-text-secondary);
        }

        .header-right {
          display: flex;
          align-items: center;
          gap: var(--space-3);
        }

        .time-select {
          padding: var(--space-2) var(--space-3);
          background: var(--color-bg-secondary);
          border: 1px solid var(--color-border);
          border-radius: var(--radius-md);
          color: var(--color-text-primary);
          font-size: var(--text-sm);
        }

        .upload-btn {
          display: flex;
          align-items: center;
          gap: var(--space-2);
          padding: var(--space-2) var(--space-4);
          background: var(--gradient-primary);
          color: white;
          border-radius: var(--radius-md);
          font-weight: 600;
          text-decoration: none;
        }

        /* Stats Grid */
        .stats-grid {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: var(--space-4);
          margin-bottom: var(--space-6);
        }

        .stat-card {
          display: flex;
          align-items: center;
          gap: var(--space-4);
          padding: var(--space-4);
          background: var(--color-bg-secondary);
          border: 1px solid var(--color-border);
          border-radius: var(--radius-lg);
        }

        .stat-icon {
          width: 48px;
          height: 48px;
          border-radius: var(--radius-md);
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .stat-icon.views { background: rgba(99, 102, 241, 0.2); color: #6366f1; }
        .stat-icon.time { background: rgba(236, 72, 153, 0.2); color: #ec4899; }
        .stat-icon.subscribers { background: rgba(16, 185, 129, 0.2); color: #10b981; }
        .stat-icon.revenue { background: rgba(245, 158, 11, 0.2); color: #f59e0b; }

        .stat-content {
          display: flex;
          flex-direction: column;
        }

        .stat-label {
          font-size: var(--text-sm);
          color: var(--color-text-secondary);
        }

        .stat-value {
          font-size: var(--text-2xl);
          font-weight: 700;
        }

        .stat-change {
          font-size: var(--text-sm);
          font-weight: 500;
        }

        .stat-change.positive { color: var(--color-success); }
        .stat-change.negative { color: var(--color-error); }

        /* Chart */
        .chart-card {
          background: var(--color-bg-secondary);
          border: 1px solid var(--color-border);
          border-radius: var(--radius-lg);
          padding: var(--space-4);
          margin-bottom: var(--space-6);
        }

        .chart-card h2 {
          font-size: var(--text-lg);
          margin-bottom: var(--space-4);
        }

        .chart {
          height: 200px;
        }

        .chart-bars {
          display: flex;
          align-items: flex-end;
          gap: 2px;
          height: 160px;
        }

        .chart-bar {
          flex: 1;
          background: var(--gradient-primary);
          border-radius: var(--radius-sm) var(--radius-sm) 0 0;
          min-height: 4px;
          transition: opacity var(--transition-fast);
        }

        .chart-bar:hover {
          opacity: 0.8;
        }

        .chart-labels {
          display: flex;
          justify-content: space-between;
          padding-top: var(--space-2);
          font-size: var(--text-xs);
          color: var(--color-text-tertiary);
        }

        /* Two Column */
        .two-col {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: var(--space-6);
          margin-bottom: var(--space-6);
        }

        .card {
          background: var(--color-bg-secondary);
          border: 1px solid var(--color-border);
          border-radius: var(--radius-lg);
          padding: var(--space-4);
        }

        .card-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: var(--space-4);
        }

        .card-header h2 {
          font-size: var(--text-lg);
        }

        .see-more {
          font-size: var(--text-sm);
          color: var(--color-accent);
        }

        .video-list {
          display: flex;
          flex-direction: column;
          gap: var(--space-3);
        }

        .video-item {
          display: flex;
          align-items: center;
          gap: var(--space-3);
        }

        .rank {
          width: 24px;
          font-weight: 700;
          color: var(--color-text-tertiary);
          text-align: center;
        }

        .video-thumb {
          position: relative;
          width: 80px;
          aspect-ratio: 16/9;
          border-radius: var(--radius-sm);
          overflow: hidden;
          flex-shrink: 0;
        }

        .video-thumb img {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }

        .video-thumb .duration {
          position: absolute;
          bottom: 2px;
          right: 2px;
          background: rgba(0,0,0,0.8);
          color: white;
          font-size: 10px;
          padding: 1px 4px;
          border-radius: 2px;
        }

        .video-info {
          flex: 1;
          min-width: 0;
        }

        .video-title {
          display: block;
          font-weight: 500;
          color: var(--color-text-primary);
          text-decoration: none;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          margin-bottom: var(--space-1);
        }

        .video-title:hover {
          color: var(--color-accent);
        }

        .video-stats {
          font-size: var(--text-sm);
          color: var(--color-text-tertiary);
        }

        .status-badge {
          padding: 2px 6px;
          background: var(--color-bg-tertiary);
          border-radius: var(--radius-sm);
          font-size: var(--text-xs);
          text-transform: capitalize;
        }

        .edit-btn {
          padding: var(--space-2);
          color: var(--color-text-tertiary);
          border-radius: var(--radius-sm);
        }

        .edit-btn:hover {
          background: var(--color-bg-tertiary);
          color: var(--color-text-primary);
        }

        .empty-text {
          color: var(--color-text-tertiary);
          text-align: center;
          padding: var(--space-6);
        }

        .empty-state {
          text-align: center;
          padding: var(--space-6);
        }

        .empty-state p {
          color: var(--color-text-tertiary);
          margin-bottom: var(--space-3);
        }

        .upload-link {
          color: var(--color-accent);
        }

        /* Quick Actions */
        .quick-actions h2 {
          font-size: var(--text-lg);
          margin-bottom: var(--space-4);
        }

        .actions-grid {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: var(--space-4);
        }

        .action-card {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: var(--space-2);
          padding: var(--space-4);
          background: var(--color-bg-secondary);
          border: 1px solid var(--color-border);
          border-radius: var(--radius-lg);
          text-decoration: none;
          color: var(--color-text-secondary);
          transition: all var(--transition-fast);
        }

        .action-card:hover {
          border-color: var(--color-accent);
          color: var(--color-accent);
        }

        .action-card span {
          font-weight: 500;
          font-size: var(--text-sm);
        }

        /* Loading */
        .loading-state .skeleton {
          background: linear-gradient(
            90deg,
            var(--color-bg-tertiary) 25%,
            var(--color-bg-elevated) 50%,
            var(--color-bg-tertiary) 75%
          );
          background-size: 200% 100%;
          animation: skeleton-pulse 1.5s ease-in-out infinite;
          border-radius: var(--radius-lg);
        }

        .skeleton.stat-card {
          height: 96px;
        }

        .skeleton.chart-card {
          height: 280px;
          margin-bottom: var(--space-6);
        }

        @keyframes skeleton-pulse {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }

        /* Responsive */
        @media (max-width: 1200px) {
          .stats-grid {
            grid-template-columns: repeat(2, 1fr);
          }
          .actions-grid {
            grid-template-columns: repeat(2, 1fr);
          }
        }

        @media (max-width: 900px) {
          .sidebar {
            display: none;
          }
          .main {
            margin-left: 0;
          }
          .two-col {
            grid-template-columns: 1fr;
          }
        }

        @media (max-width: 640px) {
          .main {
            padding: var(--space-4);
          }
          .stats-grid {
            grid-template-columns: 1fr;
          }
          .header {
            flex-direction: column;
            align-items: flex-start;
            gap: var(--space-4);
          }
          .header-right {
            width: 100%;
          }
          .actions-grid {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </div>
  );
}
