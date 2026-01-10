/**
 * ActForge store unit tests.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { act } from '@testing-library/react';
import { useActForgeStore, useACIBadgeColor, useRevenueTierLabel, useBookingModeInfo } from '../../stores/actforge-store';

// Mock the API client
vi.mock('../../api/client', () => ({
  api: {
    searchPerformers: vi.fn(),
    getFeaturedPerformers: vi.fn(),
    getPerformerLeaderboard: vi.fn(),
    getPerformer: vi.fn(),
    getPerformerACI: vi.fn(),
    listProjectBookings: vi.fn(),
    createBlinkBooking: vi.fn(),
    createDeepBooking: vi.fn(),
    createEpicBooking: vi.fn(),
    acceptBooking: vi.fn(),
    deliverBooking: vi.fn(),
    approveBooking: vi.fn(),
    disputeBooking: vi.fn(),
    rateBooking: vi.fn(),
    calculatePayout: vi.fn(),
  },
}));

const mockPerformer = {
  id: 'performer-1',
  display_name: 'Test Performer',
  bio: 'A test performer',
  aci_score: 75,
  total_bookings: 10,
  rating: 4.5,
  created_at: new Date().toISOString(),
};

const mockBooking = {
  id: 'booking-1',
  project_id: 'project-1',
  performer_id: 'performer-1',
  mode: 'BLINK' as const,
  status: 'pending' as const,
  duration_seconds: 10,
  price_usd: 5.0,
  created_at: new Date().toISOString(),
};

describe('ActForgeStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useActForgeStore.setState({
      performers: [],
      featuredPerformers: [],
      leaderboard: [],
      selectedPerformer: null,
      selectedPerformerACI: null,
      searchParams: {
        limit: 20,
        offset: 0,
        sort_by: 'aci_score',
        sort_order: 'desc',
      },
      searchTotal: 0,
      searchHasMore: false,
      activeBookings: [],
      selectedBooking: null,
      payoutEstimate: null,
      isLoadingPerformers: false,
      isLoadingBookings: false,
      isCreatingBooking: false,
      bookingMode: null,
      showBookingModal: false,
      error: null,
    });
    vi.clearAllMocks();
  });

  describe('clearSelectedPerformer', () => {
    it('should clear the selected performer', () => {
      useActForgeStore.setState({
        selectedPerformer: mockPerformer,
        selectedPerformerACI: { total_score: 75, components: {} },
      });

      const { clearSelectedPerformer } = useActForgeStore.getState();

      act(() => {
        clearSelectedPerformer();
      });

      const state = useActForgeStore.getState();
      expect(state.selectedPerformer).toBeNull();
      expect(state.selectedPerformerACI).toBeNull();
    });
  });

  describe('selectBooking', () => {
    it('should set the selected booking', () => {
      const { selectBooking } = useActForgeStore.getState();

      act(() => {
        selectBooking(mockBooking);
      });

      expect(useActForgeStore.getState().selectedBooking).toEqual(mockBooking);
    });

    it('should allow clearing the selection', () => {
      useActForgeStore.setState({ selectedBooking: mockBooking });

      const { selectBooking } = useActForgeStore.getState();

      act(() => {
        selectBooking(null);
      });

      expect(useActForgeStore.getState().selectedBooking).toBeNull();
    });
  });

  describe('setBookingMode', () => {
    it('should set the booking mode', () => {
      const { setBookingMode } = useActForgeStore.getState();

      act(() => {
        setBookingMode('DEEP');
      });

      expect(useActForgeStore.getState().bookingMode).toBe('DEEP');
    });
  });

  describe('openBookingModal', () => {
    it('should open the booking modal with mode', () => {
      const { openBookingModal } = useActForgeStore.getState();

      act(() => {
        openBookingModal('EPIC');
      });

      const state = useActForgeStore.getState();
      expect(state.showBookingModal).toBe(true);
      expect(state.bookingMode).toBe('EPIC');
    });
  });

  describe('closeBookingModal', () => {
    it('should close the booking modal', () => {
      useActForgeStore.setState({ showBookingModal: true, bookingMode: 'BLINK' });

      const { closeBookingModal } = useActForgeStore.getState();

      act(() => {
        closeBookingModal();
      });

      const state = useActForgeStore.getState();
      expect(state.showBookingModal).toBe(false);
      expect(state.bookingMode).toBeNull();
    });
  });

  describe('clearError', () => {
    it('should clear the error state', () => {
      useActForgeStore.setState({ error: 'Test error' });

      const { clearError } = useActForgeStore.getState();

      act(() => {
        clearError();
      });

      expect(useActForgeStore.getState().error).toBeNull();
    });
  });

  describe('getPerformerById', () => {
    it('should find performer by ID', () => {
      useActForgeStore.setState({ performers: [mockPerformer] });

      const { getPerformerById } = useActForgeStore.getState();
      const found = getPerformerById('performer-1');

      expect(found).toEqual(mockPerformer);
    });

    it('should return undefined for non-existent ID', () => {
      useActForgeStore.setState({ performers: [mockPerformer] });

      const { getPerformerById } = useActForgeStore.getState();
      const found = getPerformerById('nonexistent');

      expect(found).toBeUndefined();
    });
  });

  describe('getBookingsByStatus', () => {
    it('should filter bookings by status', () => {
      const bookings = [
        { ...mockBooking, id: 'b1', status: 'pending' as const },
        { ...mockBooking, id: 'b2', status: 'accepted' as const },
        { ...mockBooking, id: 'b3', status: 'pending' as const },
      ];
      useActForgeStore.setState({ activeBookings: bookings });

      const { getBookingsByStatus } = useActForgeStore.getState();
      const pending = getBookingsByStatus('pending');

      expect(pending).toHaveLength(2);
      expect(pending.every((b) => b.status === 'pending')).toBe(true);
    });
  });
});

describe('useACIBadgeColor', () => {
  it('should return gold for score >= 90', () => {
    expect(useACIBadgeColor(90)).toBe('text-yellow-400');
    expect(useACIBadgeColor(95)).toBe('text-yellow-400');
  });

  it('should return purple for score >= 75', () => {
    expect(useACIBadgeColor(75)).toBe('text-purple-400');
    expect(useACIBadgeColor(89)).toBe('text-purple-400');
  });

  it('should return blue for score >= 60', () => {
    expect(useACIBadgeColor(60)).toBe('text-blue-400');
    expect(useACIBadgeColor(74)).toBe('text-blue-400');
  });

  it('should return green for score >= 40', () => {
    expect(useACIBadgeColor(40)).toBe('text-green-400');
    expect(useACIBadgeColor(59)).toBe('text-green-400');
  });

  it('should return gray for score < 40', () => {
    expect(useACIBadgeColor(39)).toBe('text-gray-400');
    expect(useACIBadgeColor(0)).toBe('text-gray-400');
  });
});

describe('useRevenueTierLabel', () => {
  it('should return correct tier labels', () => {
    expect(useRevenueTierLabel(1)).toBe('Emerging (50/50)');
    expect(useRevenueTierLabel(2)).toBe('Rising (60/40)');
    expect(useRevenueTierLabel(3)).toBe('Established (70/30)');
    expect(useRevenueTierLabel(4)).toBe('Professional (80/20)');
    expect(useRevenueTierLabel(5)).toBe('Elite (90/10)');
    expect(useRevenueTierLabel(6)).toBe('Legend (99/1)');
  });

  it('should return Unknown for invalid tier', () => {
    expect(useRevenueTierLabel(0)).toBe('Unknown');
    expect(useRevenueTierLabel(7)).toBe('Unknown');
  });
});

describe('useBookingModeInfo', () => {
  it('should return correct info for BLINK mode', () => {
    const info = useBookingModeInfo('BLINK');
    expect(info.label).toBe('Blink');
    expect(info.maxDuration).toBe(10);
    expect(info.icon).toBe('zap');
  });

  it('should return correct info for DEEP mode', () => {
    const info = useBookingModeInfo('DEEP');
    expect(info.label).toBe('Deep');
    expect(info.maxDuration).toBe(120);
    expect(info.icon).toBe('heart');
  });

  it('should return correct info for EPIC mode', () => {
    const info = useBookingModeInfo('EPIC');
    expect(info.label).toBe('Epic');
    expect(info.maxDuration).toBe(1200);
    expect(info.icon).toBe('crown');
  });

  it('should return correct info for AUCTION mode', () => {
    const info = useBookingModeInfo('AUCTION');
    expect(info.label).toBe('Auction');
    expect(info.maxDuration).toBe(600);
    expect(info.icon).toBe('gavel');
  });
});
