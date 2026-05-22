/**
 * Monetization Components
 * Stripe integration, subscription management, billing dashboard
 */

import React from 'react';
import {
  CreditCard,
  Check,
  X,
  Loader2,
  Star,
  Zap,
  Crown,
  DollarSign,
  TrendingUp,
  Calendar,
  Download,
  AlertCircle,
  ChevronRight,
  Shield,
} from 'lucide-react';
import { cn } from '../../lib/utils';

// Plan types
export interface Plan {
  id: string;
  name: string;
  price: number;
  interval: 'month' | 'year';
  features: string[];
  highlighted?: boolean;
  badge?: string;
}

// Subscription status
export type SubscriptionStatus = 'active' | 'canceled' | 'past_due' | 'trialing';

// Subscription interface
export interface Subscription {
  id: string;
  planId: string;
  status: SubscriptionStatus;
  currentPeriodEnd: Date;
  cancelAtPeriodEnd: boolean;
}

// Invoice interface
export interface Invoice {
  id: string;
  amount: number;
  status: 'paid' | 'open' | 'void';
  date: Date;
  pdfUrl?: string;
}

// Payout interface
export interface Payout {
  id: string;
  amount: number;
  status: 'pending' | 'in_transit' | 'paid' | 'failed';
  date: Date;
}

// Default plans
export const DEFAULT_PLANS: Plan[] = [
  {
    id: 'free',
    name: 'Free',
    price: 0,
    interval: 'month',
    features: ['5 projects', '720p export', 'Basic lip sync', 'Community support'],
  },
  {
    id: 'pro',
    name: 'Pro',
    price: 19,
    interval: 'month',
    features: [
      'Unlimited projects',
      '4K export',
      'Advanced lip sync (LatentSync)',
      'Priority rendering',
      'Remove watermark',
      'Email support',
    ],
    highlighted: true,
    badge: 'Most Popular',
  },
  {
    id: 'team',
    name: 'Team',
    price: 49,
    interval: 'month',
    features: [
      'Everything in Pro',
      'Team collaboration',
      'Shared asset library',
      'Admin controls',
      'API access',
      'Dedicated support',
    ],
  },
];

// Plan card component
const PlanCard: React.FC<{
  plan: Plan;
  isCurrentPlan?: boolean;
  onSelect: () => void;
  isLoading?: boolean;
}> = ({ plan, isCurrentPlan, onSelect, isLoading }) => {
  const PlanIcon = plan.id === 'free' ? Star : plan.id === 'pro' ? Zap : Crown;

  return (
    <div
      className={cn(
        'relative flex flex-col p-6 rounded-xl border-2 transition-all',
        plan.highlighted
          ? 'border-brand-500 bg-brand-500/5'
          : 'border-surface-700 hover:border-surface-600'
      )}
    >
      {/* Badge */}
      {plan.badge && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-brand-500 text-white text-xs font-medium rounded-full">
          {plan.badge}
        </div>
      )}

      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div
          className={cn(
            'w-10 h-10 rounded-lg flex items-center justify-center',
            plan.id === 'free'
              ? 'bg-surface-700'
              : plan.id === 'pro'
                ? 'bg-brand-500'
                : 'bg-yellow-500'
          )}
        >
          <PlanIcon className="w-5 h-5 text-white" />
        </div>
        <div>
          <h3 className="font-bold text-lg">{plan.name}</h3>
          <div className="flex items-baseline gap-1">
            <span className="text-2xl font-bold">${plan.price}</span>
            <span className="text-surface-400 text-sm">/{plan.interval}</span>
          </div>
        </div>
      </div>

      {/* Features */}
      <ul className="flex-1 space-y-2 mb-6">
        {plan.features.map((feature, i) => (
          <li key={i} className="flex items-center gap-2 text-sm">
            <Check className="w-4 h-4 text-green-500 flex-shrink-0" />
            {feature}
          </li>
        ))}
      </ul>

      {/* Action button */}
      <button
        onClick={onSelect}
        disabled={isCurrentPlan || isLoading}
        className={cn(
          'w-full py-2.5 rounded-lg font-medium transition-colors flex items-center justify-center gap-2',
          isCurrentPlan
            ? 'bg-surface-700 text-surface-400 cursor-not-allowed'
            : plan.highlighted
              ? 'bg-brand-500 hover:bg-brand-600 text-white'
              : 'bg-surface-800 hover:bg-surface-700'
        )}
      >
        {isLoading ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : isCurrentPlan ? (
          'Current Plan'
        ) : plan.price === 0 ? (
          'Downgrade'
        ) : (
          <>
            Upgrade
            <ChevronRight className="w-4 h-4" />
          </>
        )}
      </button>
    </div>
  );
};

// Pricing table
export const PricingTable: React.FC<{
  plans?: Plan[];
  currentPlanId?: string;
  onSelectPlan: (planId: string) => void;
  isLoading?: boolean;
  className?: string;
}> = ({ plans = DEFAULT_PLANS, currentPlanId, onSelectPlan, isLoading, className }) => (
  <div className={cn('grid md:grid-cols-3 gap-6', className)}>
    {plans.map((plan) => (
      <PlanCard
        key={plan.id}
        plan={plan}
        isCurrentPlan={currentPlanId === plan.id}
        onSelect={() => onSelectPlan(plan.id)}
        isLoading={isLoading}
      />
    ))}
  </div>
);

// Payment method display
export const PaymentMethod: React.FC<{
  brand: string;
  last4: string;
  expiryMonth: number;
  expiryYear: number;
  isDefault?: boolean;
  onRemove?: () => void;
  onSetDefault?: () => void;
  className?: string;
}> = ({ brand, last4, expiryMonth, expiryYear, isDefault, onRemove, onSetDefault, className }) => (
  <div
    className={cn(
      'flex items-center gap-4 p-4 bg-surface-800 rounded-lg border',
      isDefault ? 'border-brand-500' : 'border-surface-700',
      className
    )}
  >
    <CreditCard className="w-8 h-8 text-surface-400" />
    <div className="flex-1">
      <div className="font-medium capitalize">
        {brand} •••• {last4}
      </div>
      <div className="text-sm text-surface-400">
        Expires {String(expiryMonth).padStart(2, '0')}/{expiryYear}
      </div>
    </div>
    {isDefault && (
      <span className="px-2 py-1 bg-brand-500/20 text-brand-400 text-xs rounded">Default</span>
    )}
    <div className="flex gap-2">
      {!isDefault && onSetDefault && (
        <button onClick={onSetDefault} className="text-xs text-surface-400 hover:text-white">
          Set default
        </button>
      )}
      {onRemove && (
        <button onClick={onRemove} className="text-xs text-red-400 hover:text-red-300">
          Remove
        </button>
      )}
    </div>
  </div>
);

// Billing dashboard
export const BillingDashboard: React.FC<{
  subscription?: Subscription;
  invoices?: Invoice[];
  payouts?: Payout[];
  totalRevenue?: number;
  monthlyRevenue?: number;
  onManageSubscription?: () => void;
  onAddPaymentMethod?: () => void;
  className?: string;
}> = ({
  subscription,
  invoices = [],
  payouts = [],
  totalRevenue = 0,
  monthlyRevenue = 0,
  onManageSubscription,
  onAddPaymentMethod,
  className,
}) => {
  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);

  const formatDate = (date: Date) =>
    new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric' }).format(
      date
    );

  return (
    <div className={cn('space-y-6', className)}>
      {/* Revenue stats */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-surface-800 rounded-lg p-4">
          <div className="flex items-center gap-2 text-surface-400 mb-2">
            <DollarSign className="w-4 h-4" />
            Total Revenue
          </div>
          <div className="text-2xl font-bold">{formatCurrency(totalRevenue)}</div>
        </div>
        <div className="bg-surface-800 rounded-lg p-4">
          <div className="flex items-center gap-2 text-surface-400 mb-2">
            <TrendingUp className="w-4 h-4" />
            This Month
          </div>
          <div className="text-2xl font-bold">{formatCurrency(monthlyRevenue)}</div>
        </div>
      </div>

      {/* Current subscription */}
      {subscription && (
        <div className="bg-surface-800 rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-medium">Current Plan</h3>
            {onManageSubscription && (
              <button
                onClick={onManageSubscription}
                className="text-sm text-brand-400 hover:text-brand-300"
              >
                Manage
              </button>
            )}
          </div>
          <div className="flex items-center gap-2">
            <span
              className={cn(
                'px-2 py-1 rounded text-xs font-medium',
                subscription.status === 'active'
                  ? 'bg-green-500/20 text-green-400'
                  : subscription.status === 'trialing'
                    ? 'bg-blue-500/20 text-blue-400'
                    : subscription.status === 'past_due'
                      ? 'bg-red-500/20 text-red-400'
                      : 'bg-surface-700 text-surface-400'
              )}
            >
              {subscription.status}
            </span>
            {subscription.cancelAtPeriodEnd && (
              <span className="text-xs text-yellow-400">Cancels at period end</span>
            )}
          </div>
          <p className="text-sm text-surface-400 mt-2">
            {subscription.status === 'trialing' ? 'Trial ends' : 'Renews'}{' '}
            {formatDate(subscription.currentPeriodEnd)}
          </p>
        </div>
      )}

      {/* Recent invoices */}
      <div className="bg-surface-800 rounded-lg p-4">
        <h3 className="font-medium mb-3">Recent Invoices</h3>
        {invoices.length > 0 ? (
          <div className="space-y-2">
            {invoices.slice(0, 5).map((invoice) => (
              <div
                key={invoice.id}
                className="flex items-center justify-between py-2 border-b border-surface-700 last:border-b-0"
              >
                <div>
                  <div className="font-medium">{formatCurrency(invoice.amount / 100)}</div>
                  <div className="text-xs text-surface-400">{formatDate(invoice.date)}</div>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={cn(
                      'px-2 py-0.5 rounded text-xs',
                      invoice.status === 'paid'
                        ? 'bg-green-500/20 text-green-400'
                        : invoice.status === 'open'
                          ? 'bg-yellow-500/20 text-yellow-400'
                          : 'bg-surface-700 text-surface-400'
                    )}
                  >
                    {invoice.status}
                  </span>
                  {invoice.pdfUrl && (
                    <a href={invoice.pdfUrl} className="p-1 hover:bg-surface-700 rounded">
                      <Download className="w-4 h-4 text-surface-400" />
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-surface-400">No invoices yet</p>
        )}
      </div>

      {/* Recent payouts */}
      {payouts.length > 0 && (
        <div className="bg-surface-800 rounded-lg p-4">
          <h3 className="font-medium mb-3">Recent Payouts</h3>
          <div className="space-y-2">
            {payouts.slice(0, 5).map((payout) => (
              <div
                key={payout.id}
                className="flex items-center justify-between py-2 border-b border-surface-700 last:border-b-0"
              >
                <div>
                  <div className="font-medium">{formatCurrency(payout.amount / 100)}</div>
                  <div className="text-xs text-surface-400">{formatDate(payout.date)}</div>
                </div>
                <span
                  className={cn(
                    'px-2 py-0.5 rounded text-xs',
                    payout.status === 'paid'
                      ? 'bg-green-500/20 text-green-400'
                      : payout.status === 'in_transit'
                        ? 'bg-blue-500/20 text-blue-400'
                        : payout.status === 'pending'
                          ? 'bg-yellow-500/20 text-yellow-400'
                          : 'bg-red-500/20 text-red-400'
                  )}
                >
                  {payout.status.replace('_', ' ')}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Security note */}
      <div className="flex items-center gap-2 text-xs text-surface-400">
        <Shield className="w-4 h-4" />
        Payments secured by Stripe
      </div>
    </div>
  );
};

// Checkout form
export const CheckoutForm: React.FC<{
  plan: Plan;
  onSubmit: () => Promise<void>;
  onCancel: () => void;
  isLoading?: boolean;
  error?: string | null;
  className?: string;
}> = ({ plan, onSubmit, onCancel, isLoading, error, className }) => {
  const [cardNumber, setCardNumber] = React.useState('');
  const [expiry, setExpiry] = React.useState('');
  const [cvc, setCvc] = React.useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onSubmit();
  };

  return (
    <div className={cn('max-w-md mx-auto', className)}>
      <div className="bg-surface-800 rounded-lg p-4 mb-6">
        <div className="flex justify-between items-center">
          <div>
            <div className="font-medium">{plan.name} Plan</div>
            <div className="text-sm text-surface-400">Billed {plan.interval}ly</div>
          </div>
          <div className="text-2xl font-bold">${plan.price}</div>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg flex items-center gap-2 text-red-400 text-sm">
          <AlertCircle className="w-4 h-4" />
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1.5">Card number</label>
          <input
            type="text"
            value={cardNumber}
            onChange={(e) => setCardNumber(e.target.value.replace(/\D/g, '').slice(0, 16))}
            placeholder="4242 4242 4242 4242"
            className="w-full px-3 py-2.5 bg-surface-900 border border-surface-700 rounded-lg focus:border-brand-500 focus:outline-none"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1.5">Expiry</label>
            <input
              type="text"
              value={expiry}
              onChange={(e) => setExpiry(e.target.value.replace(/\D/g, '').slice(0, 4))}
              placeholder="MM/YY"
              className="w-full px-3 py-2.5 bg-surface-900 border border-surface-700 rounded-lg focus:border-brand-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1.5">CVC</label>
            <input
              type="text"
              value={cvc}
              onChange={(e) => setCvc(e.target.value.replace(/\D/g, '').slice(0, 4))}
              placeholder="123"
              className="w-full px-3 py-2.5 bg-surface-900 border border-surface-700 rounded-lg focus:border-brand-500 focus:outline-none"
            />
          </div>
        </div>

        <div className="flex gap-3 pt-4">
          <button
            type="button"
            onClick={onCancel}
            className="flex-1 py-2.5 bg-surface-800 hover:bg-surface-700 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isLoading}
            className="flex-1 py-2.5 bg-brand-500 hover:bg-brand-600 text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <>
                Subscribe
                <ChevronRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      </form>

      <div className="flex items-center justify-center gap-2 mt-4 text-xs text-surface-400">
        <Shield className="w-4 h-4" />
        Secured by Stripe
      </div>
    </div>
  );
};

// Hook for subscription management
export function useSubscription() {
  const [subscription, setSubscription] = React.useState<Subscription | null>(null);
  const [isLoading, setIsLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const subscribe = React.useCallback(async (planId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      // Simulate API call
      await new Promise((r) => setTimeout(r, 1500));
      setSubscription({
        id: `sub_${Date.now()}`,
        planId,
        status: 'active',
        currentPeriodEnd: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000),
        cancelAtPeriodEnd: false,
      });
    } catch (e) {
      setError('Failed to create subscription');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const cancel = React.useCallback(async () => {
    setIsLoading(true);
    try {
      await new Promise((r) => setTimeout(r, 1000));
      setSubscription((s) => (s ? { ...s, cancelAtPeriodEnd: true } : null));
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { subscription, isLoading, error, subscribe, cancel };
}
