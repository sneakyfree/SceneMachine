/**
 * Creator Analytics Dashboard
 *
 * Detailed analytics with views, watch time, audience demographics,
 * and video performance metrics.
 */

'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuthStore } from '../../stores';
import { apiClient, Video } from '../../lib/api-client';

interface VideoAnalytics {
  video: Video;
  views: number;
  watch_time_minutes: number;
  avg_view_duration: number;
  likes: number;
  comments: number;
  shares: number;
  click_through_rate: number;
  avg_view_percentage: number;
}

interface DemographicData {
  age_groups: { range: string; percentage: number }[];
  gender: { type: string; percentage: number }[];
  countries: { country: string; views: number; percentage: number }[];
  devices: { type: string; percentage: number }[];
}

interface TrafficSource {
  source: string;
  views: number;
  percentage: number;
}

interface DailyMetric {
  date: string;
  views: number;
  watch_time: number;
  subscribers_gained: number;
  subscribers_lost: number;
}

type TimeRange = '7d' | '30d' | '90d' | 'all';
type MetricType = 'views' | 'watch_time' | 'subscribers';

export default function AnalyticsDashboard() {
  const router = useRouter();
  const { user, isAuthenticated } = useAuthStore();

  const [timeRange, setTimeRange] = useState<TimeRange>('30d');
  const [metricType, setMetricType] = useState<MetricType>('views');
  const [isLoading, setIsLoading] = useState(true);

  // Analytics data
  const [dailyMetrics, setDailyMetrics] = useState<DailyMetric[]>([]);
  const [videoAnalytics, setVideoAnalytics] = useState<VideoAnalytics[]>([]);
  const [demographics, setDemographics] = useState<DemographicData | null>(null);
  const [trafficSources, setTrafficSources] = useState<TrafficSource[]>([]);

  // Summary stats
  const [totalViews, setTotalViews] = useState(0);
  const [totalWatchTime, setTotalWatchTime] = useState(0);
  const [subscribersGained, setSubscribersGained] = useState(0);
  const [viewsChange, setViewsChange] = useState(0);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login?redirect=/dashboard/analytics');
    }
  }, [isAuthenticated, router]);

  useEffect(() => {
    if (!isAuthenticated || !user) return;

    const loadAnalytics = async () => {
      setIsLoading(true);
      try {
        // Load all analytics data
        const [dashboard, videosRes] = await Promise.all([
          apiClient.getCreatorDashboard(timeRange),
          apiClient.getVideosByCreator(user.id),
        ]);
        const videos = videosRes.items;

        // Process dashboard data
        if (dashboard.daily_stats) {
          setDailyMetrics(dashboard.daily_stats.map((d: any) => ({
            date: d.date,
            views: d.views || 0,
            watch_time: d.watch_time || 0,
            subscribers_gained: d.subscribers_gained || 0,
            subscribers_lost: d.subscribers_lost || 0,
          })));
        }

        // Set summary stats
        setTotalViews(dashboard.stats?.total_views || 0);
        setTotalWatchTime((dashboard.stats?.total_watch_time_hours || 0) * 60); // Convert hours to minutes
        setSubscribersGained(dashboard.stats?.subscriber_count || 0);
        setViewsChange(dashboard.stats?.views_change_percent || 0);

        // Create video analytics from videos
        if (dashboard.top_videos) {
          setVideoAnalytics(dashboard.top_videos.map((tv: any) => ({
            video: tv.video,
            views: tv.views || 0,
            watch_time_minutes: tv.watch_time || 0,
            avg_view_duration: Math.round((tv.watch_time || 0) / Math.max(tv.views || 1, 1)),
            likes: tv.video?.like_count || 0,
            comments: tv.video?.comment_count || 0,
            shares: 0,
            click_through_rate: Math.random() * 10 + 2, // Mock CTR
            avg_view_percentage: Math.random() * 40 + 40, // Mock avg view %
          })));
        }

        // Mock demographics data
        setDemographics({
          age_groups: [
            { range: '18-24', percentage: 28 },
            { range: '25-34', percentage: 35 },
            { range: '35-44', percentage: 22 },
            { range: '45-54', percentage: 10 },
            { range: '55+', percentage: 5 },
          ],
          gender: [
            { type: 'Male', percentage: 62 },
            { type: 'Female', percentage: 35 },
            { type: 'Other', percentage: 3 },
          ],
          countries: [
            { country: 'United States', views: Math.round(totalViews * 0.45), percentage: 45 },
            { country: 'United Kingdom', views: Math.round(totalViews * 0.12), percentage: 12 },
            { country: 'Canada', views: Math.round(totalViews * 0.08), percentage: 8 },
            { country: 'Australia', views: Math.round(totalViews * 0.06), percentage: 6 },
            { country: 'Germany', views: Math.round(totalViews * 0.05), percentage: 5 },
          ],
          devices: [
            { type: 'Mobile', percentage: 58 },
            { type: 'Desktop', percentage: 32 },
            { type: 'Tablet', percentage: 7 },
            { type: 'TV', percentage: 3 },
          ],
        });

        // Mock traffic sources
        setTrafficSources([
          { source: 'Search', views: Math.round(totalViews * 0.35), percentage: 35 },
          { source: 'Suggested', views: Math.round(totalViews * 0.28), percentage: 28 },
          { source: 'Browse', views: Math.round(totalViews * 0.18), percentage: 18 },
          { source: 'External', views: Math.round(totalViews * 0.12), percentage: 12 },
          { source: 'Direct', views: Math.round(totalViews * 0.07), percentage: 7 },
        ]);

      } catch (err) {
        console.error('Failed to load analytics:', err);
      } finally {
        setIsLoading(false);
      }
    };

    loadAnalytics();
  }, [isAuthenticated, user, timeRange]);

  const formatNumber = (num: number): string => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toLocaleString();
  };

  const formatDuration = (minutes: number): string => {
    if (minutes >= 1440) {
      const days = Math.floor(minutes / 1440);
      return `${days}d`;
    }
    if (minutes >= 60) {
      const hours = Math.floor(minutes / 60);
      return `${hours}h`;
    }
    return `${minutes}m`;
  };

  const formatChange = (change: number) => {
    const isPositive = change >= 0;
    return { text: `${isPositive ? '+' : ''}${change.toFixed(1)}%`, isPositive };
  };

  // Calculate chart data
  const getChartData = () => {
    return dailyMetrics.map(d => {
      switch (metricType) {
        case 'views': return d.views;
        case 'watch_time': return d.watch_time;
        case 'subscribers': return d.subscribers_gained - d.subscribers_lost;
        default: return d.views;
      }
    });
  };

  const chartData = getChartData();
  const maxChartValue = Math.max(...chartData, 1);

  if (!isAuthenticated) return null;

  return (
    <div className="analytics-page">
      {/* Sidebar */}
      <aside className="sidebar">
        <Link href="/" className="logo">
          <span className="logo-icon">SM</span>
          <span className="logo-text">Studio</span>
        </Link>

        <nav className="nav">
          <Link href="/dashboard" className="nav-item">
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
          <Link href="/dashboard/analytics" className="nav-item active">
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
      </aside>

      {/* Main Content */}
      <main className="main">
        <header className="header">
          <div className="header-left">
            <h1>Channel Analytics</h1>
            <p>Track your channel performance and audience insights</p>
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
          </div>
        </header>

        {isLoading ? (
          <div className="loading-state">
            <div className="stats-grid">
              {[1, 2, 3, 4].map(i => (
                <div key={i} className="skeleton stat-card" />
              ))}
            </div>
            <div className="skeleton chart-section" />
          </div>
        ) : (
          <>
            {/* Summary Stats */}
            <div className="stats-grid">
              <div className="stat-card">
                <span className="stat-label">Total Views</span>
                <span className="stat-value">{formatNumber(totalViews)}</span>
                <span className={`stat-change ${formatChange(viewsChange).isPositive ? 'positive' : 'negative'}`}>
                  {formatChange(viewsChange).text} vs previous period
                </span>
              </div>
              <div className="stat-card">
                <span className="stat-label">Watch Time</span>
                <span className="stat-value">{formatDuration(totalWatchTime)}</span>
                <span className="stat-subtitle">{totalWatchTime.toLocaleString()} minutes</span>
              </div>
              <div className="stat-card">
                <span className="stat-label">Subscribers</span>
                <span className="stat-value">{subscribersGained >= 0 ? '+' : ''}{formatNumber(subscribersGained)}</span>
                <span className="stat-subtitle">Net change this period</span>
              </div>
              <div className="stat-card">
                <span className="stat-label">Avg. View Duration</span>
                <span className="stat-value">{formatDuration(Math.round(totalWatchTime / Math.max(totalViews, 1)))}</span>
                <span className="stat-subtitle">Per view</span>
              </div>
            </div>

            {/* Main Chart */}
            <div className="chart-section">
              <div className="chart-header">
                <h2>Performance Over Time</h2>
                <div className="metric-tabs">
                  <button
                    className={`metric-tab ${metricType === 'views' ? 'active' : ''}`}
                    onClick={() => setMetricType('views')}
                  >
                    Views
                  </button>
                  <button
                    className={`metric-tab ${metricType === 'watch_time' ? 'active' : ''}`}
                    onClick={() => setMetricType('watch_time')}
                  >
                    Watch Time
                  </button>
                  <button
                    className={`metric-tab ${metricType === 'subscribers' ? 'active' : ''}`}
                    onClick={() => setMetricType('subscribers')}
                  >
                    Subscribers
                  </button>
                </div>
              </div>
              <div className="chart">
                <div className="chart-bars">
                  {chartData.map((value, index) => (
                    <div
                      key={index}
                      className="chart-bar"
                      style={{ height: `${Math.max((value / maxChartValue) * 100, 2)}%` }}
                      title={`${dailyMetrics[index]?.date}: ${formatNumber(value)}`}
                    />
                  ))}
                </div>
                <div className="chart-labels">
                  {dailyMetrics
                    .filter((_, i) => i % Math.ceil(dailyMetrics.length / 7) === 0)
                    .map((d) => (
                      <span key={d.date}>
                        {new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                      </span>
                    ))}
                </div>
              </div>
            </div>

            {/* Two Column Layout */}
            <div className="two-col">
              {/* Top Videos */}
              <div className="card">
                <h2>Top Videos</h2>
                <div className="video-analytics-list">
                  {videoAnalytics.length === 0 ? (
                    <p className="empty-text">No video data available</p>
                  ) : (
                    videoAnalytics.slice(0, 10).map((va, index) => (
                      <div key={va.video.id} className="video-analytics-item">
                        <span className="rank">{index + 1}</span>
                        <div className="video-thumb">
                          <img
                            src={va.video.thumbnail_url || '/placeholder-thumbnail.svg'}
                            alt={va.video.title}
                          />
                        </div>
                        <div className="video-info">
                          <Link href={`/watch/${va.video.id}`} className="video-title">
                            {va.video.title}
                          </Link>
                          <div className="video-metrics">
                            <span>{formatNumber(va.views)} views</span>
                            <span>{formatDuration(va.watch_time_minutes)} watch time</span>
                            <span>{va.avg_view_percentage.toFixed(0)}% avg viewed</span>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Traffic Sources */}
              <div className="card">
                <h2>Traffic Sources</h2>
                <div className="traffic-list">
                  {trafficSources.map((source) => (
                    <div key={source.source} className="traffic-item">
                      <div className="traffic-info">
                        <span className="traffic-name">{source.source}</span>
                        <span className="traffic-views">{formatNumber(source.views)} views</span>
                      </div>
                      <div className="traffic-bar-bg">
                        <div
                          className="traffic-bar"
                          style={{ width: `${source.percentage}%` }}
                        />
                      </div>
                      <span className="traffic-percent">{source.percentage}%</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Audience Demographics */}
            {demographics && (
              <div className="demographics-section">
                <h2>Audience Demographics</h2>
                <div className="demographics-grid">
                  {/* Age Groups */}
                  <div className="demo-card">
                    <h3>Age</h3>
                    <div className="demo-bars">
                      {demographics.age_groups.map((ag) => (
                        <div key={ag.range} className="demo-bar-item">
                          <span className="demo-label">{ag.range}</span>
                          <div className="demo-bar-bg">
                            <div className="demo-bar" style={{ width: `${ag.percentage}%` }} />
                          </div>
                          <span className="demo-percent">{ag.percentage}%</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Gender */}
                  <div className="demo-card">
                    <h3>Gender</h3>
                    <div className="demo-bars">
                      {demographics.gender.map((g) => (
                        <div key={g.type} className="demo-bar-item">
                          <span className="demo-label">{g.type}</span>
                          <div className="demo-bar-bg">
                            <div className="demo-bar" style={{ width: `${g.percentage}%` }} />
                          </div>
                          <span className="demo-percent">{g.percentage}%</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Top Countries */}
                  <div className="demo-card">
                    <h3>Top Countries</h3>
                    <div className="demo-bars">
                      {demographics.countries.map((c) => (
                        <div key={c.country} className="demo-bar-item">
                          <span className="demo-label">{c.country}</span>
                          <div className="demo-bar-bg">
                            <div className="demo-bar" style={{ width: `${c.percentage}%` }} />
                          </div>
                          <span className="demo-percent">{c.percentage}%</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Devices */}
                  <div className="demo-card">
                    <h3>Devices</h3>
                    <div className="demo-bars">
                      {demographics.devices.map((d) => (
                        <div key={d.type} className="demo-bar-item">
                          <span className="demo-label">{d.type}</span>
                          <div className="demo-bar-bg">
                            <div className="demo-bar" style={{ width: `${d.percentage}%` }} />
                          </div>
                          <span className="demo-percent">{d.percentage}%</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </main>

      <style jsx>{`
        .analytics-page {
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

        /* Main */
        .main {
          flex: 1;
          margin-left: 240px;
          padding: var(--space-6);
        }

        .header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: var(--space-6);
        }

        .header h1 {
          font-size: var(--text-2xl);
          margin-bottom: var(--space-1);
        }

        .header p {
          color: var(--color-text-secondary);
        }

        .time-select {
          padding: var(--space-2) var(--space-3);
          background: var(--color-bg-secondary);
          border: 1px solid var(--color-border);
          border-radius: var(--radius-md);
          color: var(--color-text-primary);
        }

        /* Stats Grid */
        .stats-grid {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: var(--space-4);
          margin-bottom: var(--space-6);
        }

        .stat-card {
          background: var(--color-bg-secondary);
          border: 1px solid var(--color-border);
          border-radius: var(--radius-lg);
          padding: var(--space-4);
          display: flex;
          flex-direction: column;
        }

        .stat-label {
          font-size: var(--text-sm);
          color: var(--color-text-secondary);
          margin-bottom: var(--space-1);
        }

        .stat-value {
          font-size: var(--text-3xl);
          font-weight: 700;
          margin-bottom: var(--space-1);
        }

        .stat-change {
          font-size: var(--text-sm);
        }

        .stat-change.positive { color: var(--color-success); }
        .stat-change.negative { color: var(--color-error); }

        .stat-subtitle {
          font-size: var(--text-sm);
          color: var(--color-text-tertiary);
        }

        /* Chart Section */
        .chart-section {
          background: var(--color-bg-secondary);
          border: 1px solid var(--color-border);
          border-radius: var(--radius-lg);
          padding: var(--space-4);
          margin-bottom: var(--space-6);
        }

        .chart-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: var(--space-4);
        }

        .chart-header h2 {
          font-size: var(--text-lg);
        }

        .metric-tabs {
          display: flex;
          gap: var(--space-1);
          background: var(--color-bg-tertiary);
          padding: var(--space-1);
          border-radius: var(--radius-md);
        }

        .metric-tab {
          padding: var(--space-2) var(--space-3);
          border: none;
          background: none;
          color: var(--color-text-secondary);
          font-weight: 500;
          border-radius: var(--radius-sm);
          cursor: pointer;
          transition: all var(--transition-fast);
        }

        .metric-tab:hover {
          color: var(--color-text-primary);
        }

        .metric-tab.active {
          background: var(--color-bg-secondary);
          color: var(--color-text-primary);
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
          min-height: 2px;
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

        .card h2 {
          font-size: var(--text-lg);
          margin-bottom: var(--space-4);
        }

        /* Video Analytics */
        .video-analytics-list {
          display: flex;
          flex-direction: column;
          gap: var(--space-3);
        }

        .video-analytics-item {
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

        .video-metrics {
          display: flex;
          gap: var(--space-3);
          font-size: var(--text-xs);
          color: var(--color-text-tertiary);
        }

        /* Traffic Sources */
        .traffic-list {
          display: flex;
          flex-direction: column;
          gap: var(--space-3);
        }

        .traffic-item {
          display: flex;
          align-items: center;
          gap: var(--space-3);
        }

        .traffic-info {
          width: 100px;
          display: flex;
          flex-direction: column;
        }

        .traffic-name {
          font-weight: 500;
        }

        .traffic-views {
          font-size: var(--text-xs);
          color: var(--color-text-tertiary);
        }

        .traffic-bar-bg {
          flex: 1;
          height: 8px;
          background: var(--color-bg-tertiary);
          border-radius: var(--radius-sm);
          overflow: hidden;
        }

        .traffic-bar {
          height: 100%;
          background: var(--gradient-primary);
          border-radius: var(--radius-sm);
        }

        .traffic-percent {
          width: 40px;
          text-align: right;
          font-weight: 500;
        }

        /* Demographics */
        .demographics-section h2 {
          font-size: var(--text-lg);
          margin-bottom: var(--space-4);
        }

        .demographics-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: var(--space-4);
        }

        .demo-card {
          background: var(--color-bg-secondary);
          border: 1px solid var(--color-border);
          border-radius: var(--radius-lg);
          padding: var(--space-4);
        }

        .demo-card h3 {
          font-size: var(--text-base);
          margin-bottom: var(--space-3);
        }

        .demo-bars {
          display: flex;
          flex-direction: column;
          gap: var(--space-2);
        }

        .demo-bar-item {
          display: flex;
          align-items: center;
          gap: var(--space-2);
        }

        .demo-label {
          width: 80px;
          font-size: var(--text-sm);
          color: var(--color-text-secondary);
        }

        .demo-bar-bg {
          flex: 1;
          height: 8px;
          background: var(--color-bg-tertiary);
          border-radius: var(--radius-sm);
          overflow: hidden;
        }

        .demo-bar {
          height: 100%;
          background: var(--gradient-primary);
          border-radius: var(--radius-sm);
        }

        .demo-percent {
          width: 40px;
          text-align: right;
          font-size: var(--text-sm);
          font-weight: 500;
        }

        .empty-text {
          color: var(--color-text-tertiary);
          text-align: center;
          padding: var(--space-6);
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
          height: 120px;
        }

        .skeleton.chart-section {
          height: 300px;
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
          .demographics-grid {
            grid-template-columns: 1fr;
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
        }
      `}</style>
    </div>
  );
}
