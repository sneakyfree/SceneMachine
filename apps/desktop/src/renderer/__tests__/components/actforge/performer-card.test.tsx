/**
 * Tests for PerformerCard component.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { PerformerCard } from '../../../components/performer-card';
import type { Performer } from '../../../api/client';

// Mock performer data matching API format
const mockPerformer: Performer = {
  id: 'perf-1',
  stage_name: 'Alex Thunder',
  bio: 'Action star specialist with 10 years of experience',
  performer_type: 'SYNTHETIC',
  aci_score: 92.5,
  revenue_tier: 4,
  revenue_split_percent: 70,
  is_verified: true,
  is_available: true,
  is_featured: true,
  total_bookings: 150,
  completed_bookings: 145,
  average_rating: 4.8,
  total_ratings: 140,
  lifetime_earnings_usd: 45000,
  pricing_blink_usd: 15.0,
  pricing_deep_usd: 75.0,
  pricing_epic_usd: 25.0,
  motion_capabilities: {
    live_portrait: true,
    roop_gs_anim: true,
    emotion_range: ['neutral', 'happy', 'sad', 'angry'],
    body_types: ['standard', 'athletic'],
  },
  avatar_url: 'https://example.com/avatar.jpg',
  demo_video_url: 'https://example.com/demo.mp4',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-15T00:00:00Z',
  // Extended fields for frontend compatibility
  specialties: ['action', 'stunts', 'dramatic'],
  profile_image_url: 'https://example.com/avatar.jpg',
  rating: 4.8,
  completion_rate: 0.97,
  base_price_usd: 15.0,
  demo_reel_url: 'https://example.com/demo.mp4',
  avg_delivery_hours: 24,
} as Performer;

describe('PerformerCard', () => {
  const defaultProps = {
    performer: mockPerformer,
    onSelect: vi.fn(),
    onBook: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should render performer stage name', () => {
      render(<PerformerCard {...defaultProps} />);
      expect(screen.getByText('Alex Thunder')).toBeInTheDocument();
    });

    it('should render ACI score badge', () => {
      render(<PerformerCard {...defaultProps} />);
      expect(screen.getByText('ACI 93')).toBeInTheDocument();
    });

    it('should render performer type badge for synthetic', () => {
      render(<PerformerCard {...defaultProps} />);
      expect(screen.getByText('Synthetic')).toBeInTheDocument();
    });

    it('should render performer type badge for human', () => {
      const humanPerformer = { ...mockPerformer, performer_type: 'HUMAN' as const };
      render(<PerformerCard {...defaultProps} performer={humanPerformer} />);
      expect(screen.getByText('Human')).toBeInTheDocument();
    });

    it('should render verified badge when performer is verified', () => {
      render(<PerformerCard {...defaultProps} />);
      // Verified icon should be present
      const verifiedIcon = document.querySelector('[class*="text-blue-400"]');
      expect(verifiedIcon).toBeInTheDocument();
    });

    it('should render specialties tags', () => {
      render(<PerformerCard {...defaultProps} />);
      expect(screen.getByText('action')).toBeInTheDocument();
      expect(screen.getByText('stunts')).toBeInTheDocument();
      expect(screen.getByText('dramatic')).toBeInTheDocument();
    });

    it('should render rating', () => {
      render(<PerformerCard {...defaultProps} />);
      expect(screen.getByText('4.8')).toBeInTheDocument();
    });

    it('should render total bookings', () => {
      render(<PerformerCard {...defaultProps} />);
      expect(screen.getByText('150')).toBeInTheDocument();
    });

    it('should render completion rate', () => {
      render(<PerformerCard {...defaultProps} />);
      expect(screen.getByText('97%')).toBeInTheDocument();
    });

    it('should render base price', () => {
      render(<PerformerCard {...defaultProps} />);
      expect(screen.getByText('$15.00')).toBeInTheDocument();
    });

    it('should render booking buttons', () => {
      render(<PerformerCard {...defaultProps} />);
      expect(screen.getByText('Blink (10s)')).toBeInTheDocument();
      expect(screen.getByText('Full Booking')).toBeInTheDocument();
    });

    it('should render demo reel button when available', () => {
      render(<PerformerCard {...defaultProps} />);
      expect(screen.getByText('Demo Reel')).toBeInTheDocument();
    });

    it('should not render demo reel button when not available', () => {
      const noDemo = { ...mockPerformer, demo_reel_url: null };
      render(<PerformerCard {...defaultProps} performer={noDemo} />);
      expect(screen.queryByText('Demo Reel')).not.toBeInTheDocument();
    });
  });

  describe('Interactions', () => {
    it('should call onSelect when card is clicked', () => {
      render(<PerformerCard {...defaultProps} />);
      const card = screen.getByText('Alex Thunder').closest('div[class*="cursor-pointer"]');
      if (card) {
        fireEvent.click(card);
        expect(defaultProps.onSelect).toHaveBeenCalledWith(mockPerformer);
      }
    });

    it('should call onBook with BLINK mode when Blink button is clicked', () => {
      render(<PerformerCard {...defaultProps} />);
      fireEvent.click(screen.getByText('Blink (10s)'));
      expect(defaultProps.onBook).toHaveBeenCalledWith(mockPerformer, 'BLINK');
    });

    it('should call onBook with FULL mode when Full Booking button is clicked', () => {
      render(<PerformerCard {...defaultProps} />);
      fireEvent.click(screen.getByText('Full Booking'));
      expect(defaultProps.onBook).toHaveBeenCalledWith(mockPerformer, 'FULL');
    });

    it('should not trigger onSelect when booking buttons are clicked', () => {
      render(<PerformerCard {...defaultProps} />);
      fireEvent.click(screen.getByText('Blink (10s)'));
      expect(defaultProps.onSelect).not.toHaveBeenCalled();
    });
  });

  describe('ACI Score Colors', () => {
    it('should show green color for high ACI (80+)', () => {
      render(<PerformerCard {...defaultProps} />);
      const aciBadge = screen.getByText('ACI 93');
      expect(aciBadge).toHaveClass('text-green-400');
    });

    it('should show yellow color for medium ACI (60-79)', () => {
      const mediumACI = { ...mockPerformer, aci_score: 70 };
      render(<PerformerCard {...defaultProps} performer={mediumACI} />);
      const aciBadge = screen.getByText('ACI 70');
      expect(aciBadge).toHaveClass('text-yellow-400');
    });

    it('should show orange color for low ACI (40-59)', () => {
      const lowACI = { ...mockPerformer, aci_score: 50 };
      render(<PerformerCard {...defaultProps} performer={lowACI} />);
      const aciBadge = screen.getByText('ACI 50');
      expect(aciBadge).toHaveClass('text-orange-400');
    });

    it('should show red color for very low ACI (<40)', () => {
      const veryLowACI = { ...mockPerformer, aci_score: 30 };
      render(<PerformerCard {...defaultProps} performer={veryLowACI} />);
      const aciBadge = screen.getByText('ACI 30');
      expect(aciBadge).toHaveClass('text-red-400');
    });
  });

  describe('Profile Image', () => {
    it('should render profile image when available', () => {
      render(<PerformerCard {...defaultProps} />);
      const img = screen.getByAltText('Alex Thunder');
      expect(img).toBeInTheDocument();
      expect(img).toHaveAttribute('src', 'https://example.com/avatar.jpg');
    });

    it('should render initial when no profile image', () => {
      const noImage = { ...mockPerformer, profile_image_url: null };
      render(<PerformerCard {...defaultProps} performer={noImage} />);
      expect(screen.getByText('A')).toBeInTheDocument();
    });
  });

  describe('Empty States', () => {
    it('should handle missing specialties', () => {
      const noSpecialties = { ...mockPerformer, specialties: [] };
      render(<PerformerCard {...defaultProps} performer={noSpecialties} />);
      expect(screen.queryByText('action')).not.toBeInTheDocument();
    });

    it('should limit displayed specialties to 3', () => {
      const manySpecialties = {
        ...mockPerformer,
        specialties: ['action', 'stunts', 'dramatic', 'comedy', 'horror'],
      };
      render(<PerformerCard {...defaultProps} performer={manySpecialties} />);
      expect(screen.getByText('+2')).toBeInTheDocument();
    });
  });
});
