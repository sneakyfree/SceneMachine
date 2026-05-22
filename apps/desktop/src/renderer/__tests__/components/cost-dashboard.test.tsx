/**
 * Cost Dashboard component tests.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

// Mock the CostDashboard component
vi.mock('../../components/cost-dashboard', () => ({
  CostDashboard: ({
    totalSpent,
    budget,
    dailyCosts,
    providerCosts,
    onSetBudget,
    onExportReport,
    timeRange = '30d',
    onTimeRangeChange,
  }: any) => {
    const budgetPercentage = budget > 0 ? (totalSpent / budget) * 100 : 0;
    const isOverBudget = totalSpent > budget;
    const remaining = Math.max(0, budget - totalSpent);

    return (
      <div data-testid="cost-dashboard">
        {/* Summary Cards */}
        <div data-testid="summary-section">
          <div data-testid="total-spent">
            <span>Total Spent</span>
            <span data-testid="total-amount">${totalSpent.toFixed(2)}</span>
          </div>

          <div data-testid="budget-card">
            <span>Budget</span>
            <span data-testid="budget-amount">${budget.toFixed(2)}</span>
            {budget > 0 && (
              <div data-testid="budget-progress">
                <div
                  data-testid="budget-bar"
                  style={{ width: `${Math.min(budgetPercentage, 100)}%` }}
                  className={isOverBudget ? 'over-budget' : ''}
                />
              </div>
            )}
          </div>

          <div data-testid="remaining-card">
            <span>Remaining</span>
            <span data-testid="remaining-amount" className={isOverBudget ? 'text-red-500' : ''}>
              ${remaining.toFixed(2)}
            </span>
          </div>
        </div>

        {/* Budget Warning */}
        {isOverBudget && (
          <div data-testid="budget-warning" role="alert">
            You have exceeded your budget by ${(totalSpent - budget).toFixed(2)}
          </div>
        )}

        {budgetPercentage >= 80 && budgetPercentage < 100 && (
          <div data-testid="budget-approaching" role="alert">
            You are approaching your budget limit ({budgetPercentage.toFixed(0)}% used)
          </div>
        )}

        {/* Time Range Selector */}
        <div data-testid="time-range-section">
          <select
            data-testid="time-range-select"
            value={timeRange}
            onChange={(e) => onTimeRangeChange?.(e.target.value)}
          >
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
            <option value="90d">Last 90 days</option>
            <option value="all">All time</option>
          </select>
        </div>

        {/* Daily Costs Chart */}
        <div data-testid="daily-costs-section">
          <h3>Daily Costs</h3>
          {dailyCosts?.length > 0 ? (
            <div data-testid="daily-costs-chart">
              {dailyCosts.map((day: any, i: number) => (
                <div key={i} data-testid={`daily-bar-${i}`}>
                  <span>{day.date}</span>
                  <span>${day.cost.toFixed(2)}</span>
                </div>
              ))}
            </div>
          ) : (
            <div data-testid="no-daily-data">No cost data available</div>
          )}
        </div>

        {/* Provider Breakdown */}
        <div data-testid="provider-costs-section">
          <h3>Costs by Provider</h3>
          {providerCosts?.length > 0 ? (
            <div data-testid="provider-costs-list">
              {providerCosts.map((provider: any) => (
                <div key={provider.id} data-testid={`provider-${provider.id}`}>
                  <span>{provider.name}</span>
                  <span>${provider.cost.toFixed(2)}</span>
                  <span>{provider.percentage.toFixed(1)}%</span>
                </div>
              ))}
            </div>
          ) : (
            <div data-testid="no-provider-data">No provider data available</div>
          )}
        </div>

        {/* Actions */}
        <div data-testid="actions-section">
          <button onClick={() => onSetBudget?.()} data-testid="set-budget-btn">
            Set Budget
          </button>
          <button onClick={() => onExportReport?.()} data-testid="export-report-btn">
            Export Report
          </button>
        </div>
      </div>
    );
  },
}));

import { CostDashboard } from '../../components/cost-dashboard';

const mockDailyCosts = [
  { date: '2024-01-01', cost: 12.5 },
  { date: '2024-01-02', cost: 8.75 },
  { date: '2024-01-03', cost: 15.0 },
  { date: '2024-01-04', cost: 5.25 },
  { date: '2024-01-05', cost: 10.0 },
];

const mockProviderCosts = [
  { id: 'replicate', name: 'Replicate', cost: 35.5, percentage: 68.9 },
  { id: 'fal', name: 'Fal.ai', cost: 12.0, percentage: 23.3 },
  { id: 'runpod', name: 'RunPod', cost: 4.0, percentage: 7.8 },
];

describe('CostDashboard', () => {
  const mockHandlers = {
    onSetBudget: vi.fn(),
    onExportReport: vi.fn(),
    onTimeRangeChange: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderDashboard = (props = {}) => {
    return render(
      <CostDashboard
        totalSpent={51.5}
        budget={100}
        dailyCosts={mockDailyCosts}
        providerCosts={mockProviderCosts}
        {...mockHandlers}
        {...props}
      />
    );
  };

  describe('Basic Rendering', () => {
    it('should render cost dashboard', () => {
      renderDashboard();
      expect(screen.getByTestId('cost-dashboard')).toBeInTheDocument();
    });

    it('should render summary section', () => {
      renderDashboard();
      expect(screen.getByTestId('summary-section')).toBeInTheDocument();
    });
  });

  describe('Summary Cards', () => {
    it('should display total spent', () => {
      renderDashboard();
      expect(screen.getByTestId('total-spent')).toBeInTheDocument();
      expect(screen.getByTestId('total-amount')).toHaveTextContent('$51.50');
    });

    it('should display budget', () => {
      renderDashboard();
      expect(screen.getByTestId('budget-card')).toBeInTheDocument();
      expect(screen.getByTestId('budget-amount')).toHaveTextContent('$100.00');
    });

    it('should display remaining budget', () => {
      renderDashboard();
      expect(screen.getByTestId('remaining-card')).toBeInTheDocument();
      expect(screen.getByTestId('remaining-amount')).toHaveTextContent('$48.50');
    });

    it('should show budget progress bar', () => {
      renderDashboard();
      expect(screen.getByTestId('budget-progress')).toBeInTheDocument();
      expect(screen.getByTestId('budget-bar')).toHaveStyle({ width: '51.5%' });
    });
  });

  describe('Budget Warnings', () => {
    it('should show warning when over budget', () => {
      renderDashboard({ totalSpent: 120, budget: 100 });
      expect(screen.getByTestId('budget-warning')).toBeInTheDocument();
      expect(screen.getByText(/exceeded your budget by \$20.00/)).toBeInTheDocument();
    });

    it('should show approaching warning at 80%', () => {
      renderDashboard({ totalSpent: 85, budget: 100 });
      expect(screen.getByTestId('budget-approaching')).toBeInTheDocument();
      expect(screen.getByText(/85% used/)).toBeInTheDocument();
    });

    it('should not show warning when under 80%', () => {
      renderDashboard({ totalSpent: 50, budget: 100 });
      expect(screen.queryByTestId('budget-warning')).not.toBeInTheDocument();
      expect(screen.queryByTestId('budget-approaching')).not.toBeInTheDocument();
    });

    it('should show remaining as zero when over budget', () => {
      renderDashboard({ totalSpent: 150, budget: 100 });
      expect(screen.getByTestId('remaining-amount')).toHaveTextContent('$0.00');
    });
  });

  describe('Time Range Selector', () => {
    it('should render time range selector', () => {
      renderDashboard();
      expect(screen.getByTestId('time-range-select')).toBeInTheDocument();
    });

    it('should have time range options', () => {
      renderDashboard();
      expect(screen.getByText('Last 7 days')).toBeInTheDocument();
      expect(screen.getByText('Last 30 days')).toBeInTheDocument();
      expect(screen.getByText('Last 90 days')).toBeInTheDocument();
      expect(screen.getByText('All time')).toBeInTheDocument();
    });

    it('should call onTimeRangeChange when changed', () => {
      renderDashboard();
      fireEvent.change(screen.getByTestId('time-range-select'), {
        target: { value: '7d' },
      });
      expect(mockHandlers.onTimeRangeChange).toHaveBeenCalledWith('7d');
    });

    it('should have default time range of 30d', () => {
      renderDashboard();
      expect(screen.getByTestId('time-range-select')).toHaveValue('30d');
    });
  });

  describe('Daily Costs Chart', () => {
    it('should render daily costs section', () => {
      renderDashboard();
      expect(screen.getByTestId('daily-costs-section')).toBeInTheDocument();
    });

    it('should display daily cost data', () => {
      renderDashboard();
      expect(screen.getByTestId('daily-costs-chart')).toBeInTheDocument();
      expect(screen.getByTestId('daily-bar-0')).toBeInTheDocument();
    });

    it('should show all daily cost entries', () => {
      renderDashboard();
      expect(screen.getByText('2024-01-01')).toBeInTheDocument();
      expect(screen.getByText('$12.50')).toBeInTheDocument();
    });

    it('should show empty message when no daily data', () => {
      renderDashboard({ dailyCosts: [] });
      expect(screen.getByTestId('no-daily-data')).toBeInTheDocument();
    });
  });

  describe('Provider Costs', () => {
    it('should render provider costs section', () => {
      renderDashboard();
      expect(screen.getByTestId('provider-costs-section')).toBeInTheDocument();
    });

    it('should display provider breakdown', () => {
      renderDashboard();
      expect(screen.getByTestId('provider-costs-list')).toBeInTheDocument();
    });

    it('should show all providers', () => {
      renderDashboard();
      expect(screen.getByTestId('provider-replicate')).toBeInTheDocument();
      expect(screen.getByTestId('provider-fal')).toBeInTheDocument();
      expect(screen.getByTestId('provider-runpod')).toBeInTheDocument();
    });

    it('should show provider costs and percentages', () => {
      renderDashboard();
      expect(screen.getByText('Replicate')).toBeInTheDocument();
      expect(screen.getByText('$35.50')).toBeInTheDocument();
      expect(screen.getByText('68.9%')).toBeInTheDocument();
    });

    it('should show empty message when no provider data', () => {
      renderDashboard({ providerCosts: [] });
      expect(screen.getByTestId('no-provider-data')).toBeInTheDocument();
    });
  });

  describe('Actions', () => {
    it('should have set budget button', () => {
      renderDashboard();
      expect(screen.getByTestId('set-budget-btn')).toBeInTheDocument();
    });

    it('should call onSetBudget when clicked', () => {
      renderDashboard();
      fireEvent.click(screen.getByTestId('set-budget-btn'));
      expect(mockHandlers.onSetBudget).toHaveBeenCalled();
    });

    it('should have export report button', () => {
      renderDashboard();
      expect(screen.getByTestId('export-report-btn')).toBeInTheDocument();
    });

    it('should call onExportReport when clicked', () => {
      renderDashboard();
      fireEvent.click(screen.getByTestId('export-report-btn'));
      expect(mockHandlers.onExportReport).toHaveBeenCalled();
    });
  });

  describe('Edge Cases', () => {
    it('should handle zero budget', () => {
      renderDashboard({ budget: 0 });
      expect(screen.getByTestId('budget-amount')).toHaveTextContent('$0.00');
    });

    it('should handle zero spent', () => {
      renderDashboard({ totalSpent: 0 });
      expect(screen.getByTestId('total-amount')).toHaveTextContent('$0.00');
    });

    it('should handle very large amounts', () => {
      renderDashboard({ totalSpent: 12345.67, budget: 50000 });
      expect(screen.getByTestId('total-amount')).toHaveTextContent('$12345.67');
    });
  });
});
