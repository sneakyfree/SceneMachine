/**
 * Earnings Page
 *
 * Revenue tracking, payout management, and financial analytics for creators.
 */

'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuthStore } from '../../stores';
import { apiClient } from '../../lib/api-client';

interface LocalEarningsData {
  balance: number;
  pending_balance: number;
  lifetime_earnings: number;
  current_tier: number;
  current_rate: number;
  next_tier_threshold: number;
  progress_to_next_tier: number;
}

interface Transaction {
  id: string;
  type: 'AD_REVENUE' | 'TICKET_SALE' | 'TIP' | 'SUBSCRIPTION';
  amount: number;
  video_title?: string;
  created_at: string;
}

interface Payout {
  id: string;
  amount: number;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  created_at: string;
  processed_at?: string;
}

interface PaymentMethod {
  id: string;
  type: 'stripe' | 'paypal' | 'bank';
  name: string;
  last4?: string;
  email?: string;
  is_default: boolean;
  created_at: string;
}

interface RevenueBreakdown {
  ad_revenue: number;
  ticket_sales: number;
  tips: number;
  subscriptions: number;
}

type TimeRange = '7d' | '30d' | '90d' | 'all';

const REVENUE_TIERS = [
  { tier: 1, threshold: 0, rate: 50, label: '$0 - $1,000' },
  { tier: 2, threshold: 1000, rate: 60, label: '$1,001 - $10,000' },
  { tier: 3, threshold: 10000, rate: 70, label: '$10,001 - $100,000' },
  { tier: 4, threshold: 100000, rate: 80, label: '$100,001 - $1M' },
  { tier: 5, threshold: 1000000, rate: 90, label: '$1M - $10M' },
  { tier: 6, threshold: 10000000, rate: 99, label: '$10M+' },
];

export default function EarningsPage() {
  const router = useRouter();
  const { user, isAuthenticated } = useAuthStore();

  const [earnings, setEarnings] = useState<LocalEarningsData | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [payouts, setPayouts] = useState<Payout[]>([]);
  const [breakdown, setBreakdown] = useState<RevenueBreakdown | null>(null);
  const [timeRange, setTimeRange] = useState<TimeRange>('30d');
  const [isLoading, setIsLoading] = useState(true);
  const [isRequestingPayout, setIsRequestingPayout] = useState(false);
  const [payoutSuccess, setPayoutSuccess] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'transactions' | 'payouts' | 'payment-methods'>('overview');
  const [paymentMethods, setPaymentMethods] = useState<PaymentMethod[]>([]);
  const [showAddMethodModal, setShowAddMethodModal] = useState(false);
  const [newMethodType, setNewMethodType] = useState<'stripe' | 'paypal' | 'bank'>('stripe');
  const [isAddingMethod, setIsAddingMethod] = useState(false);

  // Redirect if not authenticated
  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login?redirect=/dashboard/earnings');
    }
  }, [isAuthenticated, router]);

  // Load earnings data
  useEffect(() => {
    if (!isAuthenticated) return;

    const loadEarnings = async () => {
      setIsLoading(true);
      try {
        const [apiEarnings, transactionsData, payoutsData] = await Promise.all([
          apiClient.getEarnings(timeRange),
          apiClient.getTransactions(timeRange),
          apiClient.getPayoutHistory(),
        ]);

        // Transform API earnings to local format
        const lifetimeEarnings = apiEarnings.total_earnings || 0;
        const tier = REVENUE_TIERS.find(t => lifetimeEarnings >= t.threshold) || REVENUE_TIERS[0];
        const nextTier = REVENUE_TIERS[Math.min(REVENUE_TIERS.indexOf(tier) + 1, REVENUE_TIERS.length - 1)];

        setEarnings({
          balance: apiEarnings.total_earnings - (apiEarnings.pending_payout || 0),
          pending_balance: apiEarnings.pending_payout || 0,
          lifetime_earnings: lifetimeEarnings,
          current_tier: tier.tier,
          current_rate: tier.rate,
          next_tier_threshold: nextTier.threshold,
          progress_to_next_tier: nextTier.threshold > 0
            ? Math.min((lifetimeEarnings / nextTier.threshold) * 100, 100)
            : 100,
        });
        setTransactions(transactionsData.transactions || []);
        setPayouts(payoutsData.items?.map(p => ({
          ...p,
          status: p.status.toUpperCase() as 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED',
        })) || []);
        setBreakdown({
          ad_revenue: apiEarnings.earnings_by_source?.ads || 0,
          ticket_sales: apiEarnings.earnings_by_source?.tickets || 0,
          tips: apiEarnings.earnings_by_source?.tips || 0,
          subscriptions: apiEarnings.earnings_by_source?.subscriptions || 0,
        });
      } catch (err) {
        console.error('Failed to load earnings:', err);
      } finally {
        setIsLoading(false);
      }
    };

    loadEarnings();
  }, [isAuthenticated, timeRange]);

  const handleAddPaymentMethod = async () => {
    setIsAddingMethod(true);
    try {
      // In production, this would redirect to Stripe Connect or similar
      // For now, simulate adding a payment method
      const newMethod: PaymentMethod = {
        id: `pm_${Date.now()}`,
        type: newMethodType,
        name: newMethodType === 'stripe' ? 'Stripe Connect' :
              newMethodType === 'paypal' ? 'PayPal' : 'Bank Account',
        last4: newMethodType === 'bank' ? '4242' : undefined,
        email: newMethodType === 'paypal' ? 'creator@example.com' : undefined,
        is_default: paymentMethods.length === 0,
        created_at: new Date().toISOString(),
      };
      setPaymentMethods(prev => [...prev, newMethod]);
      setShowAddMethodModal(false);
    } catch (err) {
      console.error('Failed to add payment method:', err);
    } finally {
      setIsAddingMethod(false);
    }
  };

  const handleSetDefaultMethod = (methodId: string) => {
    setPaymentMethods(prev =>
      prev.map(m => ({ ...m, is_default: m.id === methodId }))
    );
  };

  const handleRemoveMethod = (methodId: string) => {
    setPaymentMethods(prev => prev.filter(m => m.id !== methodId));
  };

  const handleRequestPayout = async () => {
    if (!earnings || earnings.balance < 100) return;

    setIsRequestingPayout(true);
    try {
      await apiClient.requestPayout();
      setPayoutSuccess(true);

      // Refresh data
      const [apiEarnings, payoutsData] = await Promise.all([
        apiClient.getEarnings(timeRange),
        apiClient.getPayoutHistory(),
      ]);

      // Transform API earnings to local format
      const lifetimeEarnings = apiEarnings.total_earnings || 0;
      const tier = REVENUE_TIERS.find(t => lifetimeEarnings >= t.threshold) || REVENUE_TIERS[0];
      const nextTier = REVENUE_TIERS[Math.min(REVENUE_TIERS.indexOf(tier) + 1, REVENUE_TIERS.length - 1)];

      setEarnings({
        balance: apiEarnings.total_earnings - (apiEarnings.pending_payout || 0),
        pending_balance: apiEarnings.pending_payout || 0,
        lifetime_earnings: lifetimeEarnings,
        current_tier: tier.tier,
        current_rate: tier.rate,
        next_tier_threshold: nextTier.threshold,
        progress_to_next_tier: nextTier.threshold > 0
          ? Math.min((lifetimeEarnings / nextTier.threshold) * 100, 100)
          : 100,
      });
      setPayouts(payoutsData.items?.map(p => ({
        ...p,
        status: p.status.toUpperCase() as 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED',
      })) || []);

      setTimeout(() => setPayoutSuccess(false), 5000);
    } catch (err) {
      console.error('Payout request failed:', err);
    } finally {
      setIsRequestingPayout(false);
    }
  };

  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const formatDate = (dateStr: string): string => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const getTransactionIcon = (type: Transaction['type']) => {
    switch (type) {
      case 'AD_REVENUE':
        return (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
            <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
          </svg>
        );
      case 'TICKET_SALE':
        return (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M2 9a3 3 0 0 1 0 6v2a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-2a3 3 0 0 1 0-6V7a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z" />
            <path d="M13 5v2M13 17v2M13 11v2" />
          </svg>
        );
      case 'TIP':
        return (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
          </svg>
        );
      case 'SUBSCRIPTION':
        return (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
            <circle cx="9" cy="7" r="4" />
            <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
          </svg>
        );
    }
  };

  const getPayoutStatusColor = (status: Payout['status']) => {
    switch (status) {
      case 'COMPLETED': return 'var(--color-success)';
      case 'PROCESSING': return 'var(--color-warning)';
      case 'PENDING': return 'var(--color-text-tertiary)';
      case 'FAILED': return 'var(--color-error)';
    }
  };

  if (!isAuthenticated) {
    return null;
  }

  const currentTier = REVENUE_TIERS.find(t => t.tier === (earnings?.current_tier || 1));

  return (
    <div className="earnings-page">
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
          <Link href="/dashboard/analytics" className="nav-item">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="20" x2="18" y2="10" />
              <line x1="12" y1="20" x2="12" y2="4" />
              <line x1="6" y1="20" x2="6" y2="14" />
            </svg>
            Analytics
          </Link>
          <Link href="/dashboard/earnings" className="nav-item active">
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
        </div>
      </aside>

      {/* Main Content */}
      <main className="main">
        {/* Header */}
        <header className="header">
          <div className="header-left">
            <h1>Earnings</h1>
            <p>Track your revenue and manage payouts</p>
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

        {/* Success Message */}
        {payoutSuccess && (
          <div className="success-message">
            Payout request submitted successfully! You'll receive your funds within 3-5 business days.
          </div>
        )}

        {isLoading ? (
          <div className="loading-state">
            <div className="skeleton balance-card" />
            <div className="skeleton-grid">
              <div className="skeleton card" />
              <div className="skeleton card" />
            </div>
          </div>
        ) : (
          <>
            {/* Balance Card */}
            <div className="balance-card">
              <div className="balance-main">
                <div className="balance-info">
                  <span className="balance-label">Available Balance</span>
                  <span className="balance-value">{formatCurrency(earnings?.balance || 0)}</span>
                  {earnings && earnings.pending_balance > 0 && (
                    <span className="pending-balance">
                      + {formatCurrency(earnings.pending_balance)} pending
                    </span>
                  )}
                </div>

                <button
                  className="payout-btn"
                  onClick={handleRequestPayout}
                  disabled={!earnings || earnings.balance < 100 || isRequestingPayout}
                >
                  {isRequestingPayout ? (
                    <span className="spinner" />
                  ) : (
                    <>
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <line x1="12" y1="1" x2="12" y2="23" />
                        <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
                      </svg>
                      Request Payout
                    </>
                  )}
                </button>
              </div>

              {earnings && earnings.balance < 100 && (
                <p className="payout-note">
                  Minimum payout amount is $100. You need {formatCurrency(100 - earnings.balance)} more to request a payout.
                </p>
              )}

              <div className="balance-stats">
                <div className="balance-stat">
                  <span className="stat-value">{formatCurrency(earnings?.lifetime_earnings || 0)}</span>
                  <span className="stat-label">Lifetime Earnings</span>
                </div>
                <div className="balance-stat">
                  <span className="stat-value">{currentTier?.rate || 50}%</span>
                  <span className="stat-label">Your Revenue Share</span>
                </div>
                <div className="balance-stat">
                  <span className="stat-value">Tier {earnings?.current_tier || 1}</span>
                  <span className="stat-label">{currentTier?.label}</span>
                </div>
              </div>
            </div>

            {/* Revenue Tier Progress */}
            {earnings && earnings.current_tier < 6 && (
              <div className="tier-progress-card">
                <h3>Revenue Tier Progress</h3>
                <div className="tier-info">
                  <span>Tier {earnings.current_tier}: {currentTier?.rate}% share</span>
                  <span>Next: Tier {earnings.current_tier + 1} ({REVENUE_TIERS[earnings.current_tier]?.rate}% share)</span>
                </div>
                <div className="tier-bar">
                  <div
                    className="tier-fill"
                    style={{ width: `${earnings.progress_to_next_tier}%` }}
                  />
                </div>
                <p className="tier-note">
                  Earn {formatCurrency(earnings.next_tier_threshold - earnings.lifetime_earnings)} more to reach Tier {earnings.current_tier + 1}
                </p>
              </div>
            )}

            {/* Tabs */}
            <div className="tabs">
              <button
                className={`tab ${activeTab === 'overview' ? 'active' : ''}`}
                onClick={() => setActiveTab('overview')}
              >
                Overview
              </button>
              <button
                className={`tab ${activeTab === 'transactions' ? 'active' : ''}`}
                onClick={() => setActiveTab('transactions')}
              >
                Transactions
              </button>
              <button
                className={`tab ${activeTab === 'payouts' ? 'active' : ''}`}
                onClick={() => setActiveTab('payouts')}
              >
                Payouts
              </button>
              <button
                className={`tab ${activeTab === 'payment-methods' ? 'active' : ''}`}
                onClick={() => setActiveTab('payment-methods')}
              >
                Payment Methods
              </button>
            </div>

            {/* Tab Content */}
            {activeTab === 'overview' && breakdown && (
              <div className="overview-grid">
                <div className="breakdown-card">
                  <h3>Revenue Breakdown</h3>
                  <div className="breakdown-list">
                    <div className="breakdown-item">
                      <div className="breakdown-label">
                        <span className="color-dot ads" />
                        Ad Revenue
                      </div>
                      <span className="breakdown-value">{formatCurrency(breakdown.ad_revenue)}</span>
                    </div>
                    <div className="breakdown-item">
                      <div className="breakdown-label">
                        <span className="color-dot tickets" />
                        Ticket Sales
                      </div>
                      <span className="breakdown-value">{formatCurrency(breakdown.ticket_sales)}</span>
                    </div>
                    <div className="breakdown-item">
                      <div className="breakdown-label">
                        <span className="color-dot tips" />
                        Tips
                      </div>
                      <span className="breakdown-value">{formatCurrency(breakdown.tips)}</span>
                    </div>
                    <div className="breakdown-item">
                      <div className="breakdown-label">
                        <span className="color-dot subs" />
                        Subscriptions
                      </div>
                      <span className="breakdown-value">{formatCurrency(breakdown.subscriptions)}</span>
                    </div>
                  </div>
                </div>

                <div className="tier-card">
                  <h3>Revenue Share Tiers</h3>
                  <p className="tier-description">
                    As you earn more, your revenue share increases. We believe in rewarding successful creators.
                  </p>
                  <div className="tier-list">
                    {REVENUE_TIERS.map(tier => (
                      <div
                        key={tier.tier}
                        className={`tier-item ${tier.tier === earnings?.current_tier ? 'current' : ''}`}
                      >
                        <span className="tier-label">{tier.label}</span>
                        <span className="tier-rate">{tier.rate}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'transactions' && (
              <div className="transactions-card">
                {transactions.length === 0 ? (
                  <div className="empty-state">
                    <p>No transactions in this period</p>
                  </div>
                ) : (
                  <div className="transactions-list">
                    {transactions.map(tx => (
                      <div key={tx.id} className="transaction-item">
                        <div className={`tx-icon ${tx.type.toLowerCase()}`}>
                          {getTransactionIcon(tx.type)}
                        </div>
                        <div className="tx-info">
                          <span className="tx-type">
                            {tx.type.replace('_', ' ').toLowerCase().replace(/\b\w/g, c => c.toUpperCase())}
                          </span>
                          {tx.video_title && (
                            <span className="tx-video">{tx.video_title}</span>
                          )}
                        </div>
                        <div className="tx-details">
                          <span className="tx-amount">+{formatCurrency(tx.amount)}</span>
                          <span className="tx-date">{formatDate(tx.created_at)}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === 'payouts' && (
              <div className="payouts-card">
                {payouts.length === 0 ? (
                  <div className="empty-state">
                    <p>No payout history yet</p>
                  </div>
                ) : (
                  <div className="payouts-list">
                    {payouts.map(payout => (
                      <div key={payout.id} className="payout-item">
                        <div className="payout-info">
                          <span className="payout-amount">{formatCurrency(payout.amount)}</span>
                          <span className="payout-date">
                            Requested {formatDate(payout.created_at)}
                          </span>
                        </div>
                        <span
                          className="payout-status"
                          style={{ color: getPayoutStatusColor(payout.status) }}
                        >
                          {payout.status}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === 'payment-methods' && (
              <div className="payment-methods-section">
                <div className="methods-header">
                  <div>
                    <h3>Payment Methods</h3>
                    <p className="methods-description">
                      Manage how you receive your payouts
                    </p>
                  </div>
                  <button
                    className="add-method-btn"
                    onClick={() => setShowAddMethodModal(true)}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <line x1="12" y1="5" x2="12" y2="19" />
                      <line x1="5" y1="12" x2="19" y2="12" />
                    </svg>
                    Add Payment Method
                  </button>
                </div>

                {paymentMethods.length === 0 ? (
                  <div className="no-methods">
                    <div className="no-methods-icon">
                      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                        <rect x="1" y="4" width="22" height="16" rx="2" ry="2" />
                        <line x1="1" y1="10" x2="23" y2="10" />
                      </svg>
                    </div>
                    <h4>No payment methods</h4>
                    <p>Add a payment method to receive your payouts</p>
                    <button
                      className="add-first-method-btn"
                      onClick={() => setShowAddMethodModal(true)}
                    >
                      Add Your First Payment Method
                    </button>
                  </div>
                ) : (
                  <div className="methods-list">
                    {paymentMethods.map(method => (
                      <div key={method.id} className="method-card">
                        <div className="method-icon">
                          {method.type === 'stripe' && (
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                              <path d="M13.976 9.15c-2.172-.806-3.356-1.426-3.356-2.409 0-.831.683-1.305 1.901-1.305 2.227 0 4.515.858 6.09 1.631l.89-5.494C18.252.975 15.697 0 12.165 0 9.667 0 7.589.654 6.104 1.872 4.56 3.147 3.757 4.992 3.757 7.218c0 4.039 2.467 5.76 6.476 7.219 2.585.92 3.445 1.574 3.445 2.583 0 .98-.84 1.545-2.354 1.545-1.875 0-4.965-.921-6.99-2.109l-.9 5.555C5.175 22.99 8.385 24 11.714 24c2.641 0 4.843-.624 6.328-1.813 1.664-1.305 2.525-3.236 2.525-5.732 0-4.128-2.524-5.851-6.591-7.305z"/>
                            </svg>
                          )}
                          {method.type === 'paypal' && (
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                              <path d="M7.076 21.337H2.47a.641.641 0 0 1-.633-.74L4.944.901C5.026.382 5.474 0 5.998 0h7.46c2.57 0 4.578.543 5.69 1.81 1.01 1.15 1.304 2.42 1.012 4.287-.023.143-.047.288-.077.437-.983 5.05-4.349 6.797-8.647 6.797h-2.19c-.524 0-.968.382-1.05.9l-1.12 7.106zm14.146-14.42a3.35 3.35 0 0 0-.607-.541c.013.076.026.175.041.254.93 4.778-2.147 7.93-7.515 7.93h-.583c-.22 0-.405.158-.44.376l-.734 4.645-.207 1.312a.326.326 0 0 0 .32.376h4.312c.215 0 .398-.154.432-.368.016-.1.09-.475.18-.93.09-.462.364-1.848.406-2.073.082-.442.336-.56.56-.56h.353c3.36 0 5.99-1.367 6.762-5.327.32-1.647.168-3.01-.68-3.987l-.6-.607z"/>
                            </svg>
                          )}
                          {method.type === 'bank' && (
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <path d="M3 21h18M3 10h18M5 6l7-3 7 3M4 10v11M20 10v11M8 14v3M12 14v3M16 14v3" />
                            </svg>
                          )}
                        </div>
                        <div className="method-info">
                          <span className="method-name">{method.name}</span>
                          {method.last4 && (
                            <span className="method-detail">••••{method.last4}</span>
                          )}
                          {method.email && (
                            <span className="method-detail">{method.email}</span>
                          )}
                          {method.is_default && (
                            <span className="default-badge">Default</span>
                          )}
                        </div>
                        <div className="method-actions">
                          {!method.is_default && (
                            <button
                              className="method-action-btn"
                              onClick={() => handleSetDefaultMethod(method.id)}
                            >
                              Set as Default
                            </button>
                          )}
                          <button
                            className="method-action-btn danger"
                            onClick={() => handleRemoveMethod(method.id)}
                          >
                            Remove
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </main>

      {/* Add Payment Method Modal */}
      {showAddMethodModal && (
        <div className="modal-overlay" onClick={() => setShowAddMethodModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Add Payment Method</h3>
              <button
                className="modal-close"
                onClick={() => setShowAddMethodModal(false)}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
            <div className="modal-body">
              <p className="modal-description">
                Choose how you'd like to receive your payouts
              </p>
              <div className="method-options">
                <button
                  className={`method-option ${newMethodType === 'stripe' ? 'selected' : ''}`}
                  onClick={() => setNewMethodType('stripe')}
                >
                  <div className="method-option-icon stripe">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M13.976 9.15c-2.172-.806-3.356-1.426-3.356-2.409 0-.831.683-1.305 1.901-1.305 2.227 0 4.515.858 6.09 1.631l.89-5.494C18.252.975 15.697 0 12.165 0 9.667 0 7.589.654 6.104 1.872 4.56 3.147 3.757 4.992 3.757 7.218c0 4.039 2.467 5.76 6.476 7.219 2.585.92 3.445 1.574 3.445 2.583 0 .98-.84 1.545-2.354 1.545-1.875 0-4.965-.921-6.99-2.109l-.9 5.555C5.175 22.99 8.385 24 11.714 24c2.641 0 4.843-.624 6.328-1.813 1.664-1.305 2.525-3.236 2.525-5.732 0-4.128-2.524-5.851-6.591-7.305z"/>
                    </svg>
                  </div>
                  <div className="method-option-info">
                    <span className="method-option-name">Stripe Connect</span>
                    <span className="method-option-desc">Fast payouts, low fees</span>
                  </div>
                </button>
                <button
                  className={`method-option ${newMethodType === 'paypal' ? 'selected' : ''}`}
                  onClick={() => setNewMethodType('paypal')}
                >
                  <div className="method-option-icon paypal">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M7.076 21.337H2.47a.641.641 0 0 1-.633-.74L4.944.901C5.026.382 5.474 0 5.998 0h7.46c2.57 0 4.578.543 5.69 1.81 1.01 1.15 1.304 2.42 1.012 4.287-.023.143-.047.288-.077.437-.983 5.05-4.349 6.797-8.647 6.797h-2.19c-.524 0-.968.382-1.05.9l-1.12 7.106zm14.146-14.42a3.35 3.35 0 0 0-.607-.541c.013.076.026.175.041.254.93 4.778-2.147 7.93-7.515 7.93h-.583c-.22 0-.405.158-.44.376l-.734 4.645-.207 1.312a.326.326 0 0 0 .32.376h4.312c.215 0 .398-.154.432-.368.016-.1.09-.475.18-.93.09-.462.364-1.848.406-2.073.082-.442.336-.56.56-.56h.353c3.36 0 5.99-1.367 6.762-5.327.32-1.647.168-3.01-.68-3.987l-.6-.607z"/>
                    </svg>
                  </div>
                  <div className="method-option-info">
                    <span className="method-option-name">PayPal</span>
                    <span className="method-option-desc">Widely accepted worldwide</span>
                  </div>
                </button>
                <button
                  className={`method-option ${newMethodType === 'bank' ? 'selected' : ''}`}
                  onClick={() => setNewMethodType('bank')}
                >
                  <div className="method-option-icon bank">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M3 21h18M3 10h18M5 6l7-3 7 3M4 10v11M20 10v11M8 14v3M12 14v3M16 14v3" />
                    </svg>
                  </div>
                  <div className="method-option-info">
                    <span className="method-option-name">Bank Account</span>
                    <span className="method-option-desc">Direct deposit (ACH)</span>
                  </div>
                </button>
              </div>
            </div>
            <div className="modal-footer">
              <button
                className="modal-btn secondary"
                onClick={() => setShowAddMethodModal(false)}
              >
                Cancel
              </button>
              <button
                className="modal-btn primary"
                onClick={handleAddPaymentMethod}
                disabled={isAddingMethod}
              >
                {isAddingMethod ? 'Connecting...' : 'Continue'}
              </button>
            </div>
          </div>
        </div>
      )}

      <style jsx>{`
        .earnings-page {
          display: flex;
          min-height: 100vh;
          background: var(--color-bg-primary);
        }

        /* Sidebar - same as dashboard */
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

        .success-message {
          padding: var(--space-4);
          background: rgba(16, 185, 129, 0.1);
          border: 1px solid var(--color-success);
          border-radius: var(--radius-lg);
          color: var(--color-success);
          margin-bottom: var(--space-6);
        }

        /* Balance Card */
        .balance-card {
          background: var(--gradient-primary);
          border-radius: var(--radius-xl);
          padding: var(--space-6);
          margin-bottom: var(--space-6);
          color: white;
        }

        .balance-main {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: var(--space-4);
        }

        .balance-label {
          display: block;
          font-size: var(--text-sm);
          opacity: 0.8;
          margin-bottom: var(--space-1);
        }

        .balance-value {
          display: block;
          font-size: var(--text-4xl);
          font-weight: 700;
        }

        .pending-balance {
          display: block;
          font-size: var(--text-sm);
          opacity: 0.8;
          margin-top: var(--space-1);
        }

        .payout-btn {
          display: flex;
          align-items: center;
          gap: var(--space-2);
          padding: var(--space-3) var(--space-4);
          background: white;
          color: var(--color-accent);
          border-radius: var(--radius-md);
          font-weight: 600;
        }

        .payout-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .payout-note {
          font-size: var(--text-sm);
          opacity: 0.8;
          margin-bottom: var(--space-4);
        }

        .balance-stats {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: var(--space-4);
          padding-top: var(--space-4);
          border-top: 1px solid rgba(255, 255, 255, 0.2);
        }

        .balance-stat {
          text-align: center;
        }

        .balance-stat .stat-value {
          display: block;
          font-size: var(--text-xl);
          font-weight: 600;
        }

        .balance-stat .stat-label {
          font-size: var(--text-sm);
          opacity: 0.8;
        }

        /* Tier Progress */
        .tier-progress-card {
          background: var(--color-bg-secondary);
          border: 1px solid var(--color-border);
          border-radius: var(--radius-lg);
          padding: var(--space-4);
          margin-bottom: var(--space-6);
        }

        .tier-progress-card h3 {
          font-size: var(--text-base);
          margin-bottom: var(--space-3);
        }

        .tier-info {
          display: flex;
          justify-content: space-between;
          font-size: var(--text-sm);
          color: var(--color-text-secondary);
          margin-bottom: var(--space-2);
        }

        .tier-bar {
          height: 8px;
          background: var(--color-bg-tertiary);
          border-radius: var(--radius-full);
          overflow: hidden;
        }

        .tier-fill {
          height: 100%;
          background: var(--gradient-primary);
          transition: width var(--transition-normal);
        }

        .tier-note {
          font-size: var(--text-sm);
          color: var(--color-text-tertiary);
          margin-top: var(--space-2);
        }

        /* Tabs */
        .tabs {
          display: flex;
          gap: var(--space-1);
          margin-bottom: var(--space-4);
          border-bottom: 1px solid var(--color-border);
        }

        .tab {
          padding: var(--space-3) var(--space-4);
          font-weight: 500;
          color: var(--color-text-secondary);
          border-bottom: 2px solid transparent;
          margin-bottom: -1px;
        }

        .tab:hover {
          color: var(--color-text-primary);
        }

        .tab.active {
          color: var(--color-accent);
          border-bottom-color: var(--color-accent);
        }

        /* Overview */
        .overview-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: var(--space-6);
        }

        .breakdown-card,
        .tier-card {
          background: var(--color-bg-secondary);
          border: 1px solid var(--color-border);
          border-radius: var(--radius-lg);
          padding: var(--space-4);
        }

        .breakdown-card h3,
        .tier-card h3 {
          font-size: var(--text-lg);
          margin-bottom: var(--space-4);
        }

        .breakdown-list {
          display: flex;
          flex-direction: column;
          gap: var(--space-3);
        }

        .breakdown-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .breakdown-label {
          display: flex;
          align-items: center;
          gap: var(--space-2);
        }

        .color-dot {
          width: 12px;
          height: 12px;
          border-radius: 50%;
        }

        .color-dot.ads { background: #6366f1; }
        .color-dot.tickets { background: #f59e0b; }
        .color-dot.tips { background: #ec4899; }
        .color-dot.subs { background: #10b981; }

        .breakdown-value {
          font-weight: 600;
        }

        .tier-description {
          font-size: var(--text-sm);
          color: var(--color-text-secondary);
          margin-bottom: var(--space-4);
        }

        .tier-list {
          display: flex;
          flex-direction: column;
          gap: var(--space-2);
        }

        .tier-item {
          display: flex;
          justify-content: space-between;
          padding: var(--space-2) var(--space-3);
          border-radius: var(--radius-md);
          font-size: var(--text-sm);
        }

        .tier-item.current {
          background: var(--color-accent-light);
          color: var(--color-accent);
        }

        .tier-rate {
          font-weight: 600;
        }

        /* Transactions */
        .transactions-card,
        .payouts-card {
          background: var(--color-bg-secondary);
          border: 1px solid var(--color-border);
          border-radius: var(--radius-lg);
          padding: var(--space-4);
        }

        .transactions-list,
        .payouts-list {
          display: flex;
          flex-direction: column;
        }

        .transaction-item {
          display: flex;
          align-items: center;
          gap: var(--space-3);
          padding: var(--space-3) 0;
          border-bottom: 1px solid var(--color-border);
        }

        .transaction-item:last-child {
          border-bottom: none;
        }

        .tx-icon {
          width: 40px;
          height: 40px;
          border-radius: var(--radius-md);
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .tx-icon.ad_revenue { background: rgba(99, 102, 241, 0.2); color: #6366f1; }
        .tx-icon.ticket_sale { background: rgba(245, 158, 11, 0.2); color: #f59e0b; }
        .tx-icon.tip { background: rgba(236, 72, 153, 0.2); color: #ec4899; }
        .tx-icon.subscription { background: rgba(16, 185, 129, 0.2); color: #10b981; }

        .tx-info {
          flex: 1;
        }

        .tx-type {
          display: block;
          font-weight: 500;
        }

        .tx-video {
          display: block;
          font-size: var(--text-sm);
          color: var(--color-text-tertiary);
        }

        .tx-details {
          text-align: right;
        }

        .tx-amount {
          display: block;
          font-weight: 600;
          color: var(--color-success);
        }

        .tx-date {
          font-size: var(--text-sm);
          color: var(--color-text-tertiary);
        }

        /* Payouts */
        .payout-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: var(--space-3) 0;
          border-bottom: 1px solid var(--color-border);
        }

        .payout-item:last-child {
          border-bottom: none;
        }

        .payout-amount {
          display: block;
          font-weight: 600;
          font-size: var(--text-lg);
        }

        .payout-date {
          font-size: var(--text-sm);
          color: var(--color-text-tertiary);
        }

        .payout-status {
          font-weight: 500;
          font-size: var(--text-sm);
          text-transform: capitalize;
        }

        .empty-state {
          text-align: center;
          padding: var(--space-8);
          color: var(--color-text-tertiary);
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

        .skeleton.balance-card {
          height: 200px;
          margin-bottom: var(--space-6);
        }

        .skeleton-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: var(--space-6);
        }

        .skeleton.card {
          height: 300px;
        }

        @keyframes skeleton-pulse {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }

        .spinner {
          width: 20px;
          height: 20px;
          border: 2px solid rgba(99, 102, 241, 0.3);
          border-top-color: var(--color-accent);
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }

        /* Payment Methods */
        .payment-methods-section {
          background: var(--color-bg-secondary);
          border: 1px solid var(--color-border);
          border-radius: var(--radius-lg);
          padding: var(--space-6);
        }

        .methods-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: var(--space-6);
        }

        .methods-header h3 {
          font-size: var(--text-lg);
          margin-bottom: var(--space-1);
        }

        .methods-description {
          font-size: var(--text-sm);
          color: var(--color-text-secondary);
        }

        .add-method-btn {
          display: flex;
          align-items: center;
          gap: var(--space-2);
          padding: var(--space-2) var(--space-4);
          background: var(--color-accent);
          color: white;
          border-radius: var(--radius-md);
          font-weight: 500;
        }

        .add-method-btn:hover {
          background: var(--color-accent-dark);
        }

        .no-methods {
          text-align: center;
          padding: var(--space-10) var(--space-4);
        }

        .no-methods-icon {
          color: var(--color-text-tertiary);
          margin-bottom: var(--space-4);
        }

        .no-methods h4 {
          font-size: var(--text-lg);
          margin-bottom: var(--space-2);
        }

        .no-methods p {
          color: var(--color-text-secondary);
          margin-bottom: var(--space-6);
        }

        .add-first-method-btn {
          padding: var(--space-3) var(--space-6);
          background: var(--gradient-primary);
          color: white;
          border-radius: var(--radius-md);
          font-weight: 600;
        }

        .methods-list {
          display: flex;
          flex-direction: column;
          gap: var(--space-3);
        }

        .method-card {
          display: flex;
          align-items: center;
          gap: var(--space-4);
          padding: var(--space-4);
          background: var(--color-bg-tertiary);
          border: 1px solid var(--color-border);
          border-radius: var(--radius-lg);
        }

        .method-icon {
          width: 48px;
          height: 48px;
          display: flex;
          align-items: center;
          justify-content: center;
          background: var(--color-bg-secondary);
          border-radius: var(--radius-md);
          color: var(--color-text-secondary);
        }

        .method-info {
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: var(--space-1);
        }

        .method-name {
          font-weight: 600;
        }

        .method-detail {
          font-size: var(--text-sm);
          color: var(--color-text-secondary);
        }

        .default-badge {
          display: inline-block;
          padding: 2px var(--space-2);
          background: var(--color-accent-light);
          color: var(--color-accent);
          font-size: var(--text-xs);
          font-weight: 600;
          border-radius: var(--radius-sm);
          width: fit-content;
        }

        .method-actions {
          display: flex;
          gap: var(--space-2);
        }

        .method-action-btn {
          padding: var(--space-2) var(--space-3);
          font-size: var(--text-sm);
          font-weight: 500;
          color: var(--color-text-secondary);
          background: var(--color-bg-secondary);
          border: 1px solid var(--color-border);
          border-radius: var(--radius-md);
        }

        .method-action-btn:hover {
          color: var(--color-text-primary);
          border-color: var(--color-text-tertiary);
        }

        .method-action-btn.danger:hover {
          color: var(--color-error);
          border-color: var(--color-error);
        }

        /* Modal */
        .modal-overlay {
          position: fixed;
          inset: 0;
          background: rgba(0, 0, 0, 0.6);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
        }

        .modal {
          background: var(--color-bg-secondary);
          border: 1px solid var(--color-border);
          border-radius: var(--radius-xl);
          width: 100%;
          max-width: 480px;
          margin: var(--space-4);
        }

        .modal-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: var(--space-4) var(--space-6);
          border-bottom: 1px solid var(--color-border);
        }

        .modal-header h3 {
          font-size: var(--text-lg);
        }

        .modal-close {
          color: var(--color-text-tertiary);
        }

        .modal-close:hover {
          color: var(--color-text-primary);
        }

        .modal-body {
          padding: var(--space-6);
        }

        .modal-description {
          color: var(--color-text-secondary);
          margin-bottom: var(--space-4);
        }

        .method-options {
          display: flex;
          flex-direction: column;
          gap: var(--space-3);
        }

        .method-option {
          display: flex;
          align-items: center;
          gap: var(--space-4);
          padding: var(--space-4);
          background: var(--color-bg-tertiary);
          border: 2px solid var(--color-border);
          border-radius: var(--radius-lg);
          text-align: left;
          transition: all var(--transition-fast);
        }

        .method-option:hover {
          border-color: var(--color-accent);
        }

        .method-option.selected {
          border-color: var(--color-accent);
          background: var(--color-accent-light);
        }

        .method-option-icon {
          width: 48px;
          height: 48px;
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: var(--radius-md);
        }

        .method-option-icon.stripe {
          background: #635bff;
          color: white;
        }

        .method-option-icon.paypal {
          background: #003087;
          color: white;
        }

        .method-option-icon.bank {
          background: var(--color-bg-secondary);
          color: var(--color-text-secondary);
          border: 1px solid var(--color-border);
        }

        .method-option-info {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }

        .method-option-name {
          font-weight: 600;
        }

        .method-option-desc {
          font-size: var(--text-sm);
          color: var(--color-text-secondary);
        }

        .modal-footer {
          display: flex;
          justify-content: flex-end;
          gap: var(--space-3);
          padding: var(--space-4) var(--space-6);
          border-top: 1px solid var(--color-border);
        }

        .modal-btn {
          padding: var(--space-2) var(--space-4);
          font-weight: 500;
          border-radius: var(--radius-md);
        }

        .modal-btn.secondary {
          color: var(--color-text-secondary);
          background: var(--color-bg-tertiary);
          border: 1px solid var(--color-border);
        }

        .modal-btn.secondary:hover {
          color: var(--color-text-primary);
        }

        .modal-btn.primary {
          color: white;
          background: var(--color-accent);
        }

        .modal-btn.primary:hover {
          background: var(--color-accent-dark);
        }

        .modal-btn.primary:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        @media (max-width: 900px) {
          .sidebar { display: none; }
          .main { margin-left: 0; }
          .overview-grid { grid-template-columns: 1fr; }
          .balance-stats { grid-template-columns: 1fr; gap: var(--space-2); }
        }

        @media (max-width: 640px) {
          .main { padding: var(--space-4); }
          .balance-main { flex-direction: column; gap: var(--space-4); align-items: flex-start; }
          .payout-btn { width: 100%; justify-content: center; }
        }
      `}</style>
    </div>
  );
}
