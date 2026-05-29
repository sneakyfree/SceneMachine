/**
 * Performer Card component for ActForge marketplace.
 * Displays performer information with booking actions.
 */

import React from 'react';
import { Star, Verified, PlayCircle, Calendar, TrendingUp, Clock, User } from 'lucide-react';
import type { Performer, BookingMode } from '../api/client';
import { cn } from '../lib/utils';
import { useTranslation } from '../i18n/use-translation';

interface PerformerCardProps {
  performer: Performer;
  onSelect: (performer: Performer) => void;
  onBook: (performer: Performer, mode: BookingMode) => void;
}

/**
 * Format currency for display.
 */
function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

/**
 * Get ACI score color based on value.
 */
function getACIColor(score: number): string {
  if (score >= 80) return 'text-green-400';
  if (score >= 60) return 'text-yellow-400';
  if (score >= 40) return 'text-orange-400';
  return 'text-red-400';
}

/**
 * Get ACI badge color based on value.
 */
function getACIBadgeColor(score: number): string {
  if (score >= 80) return 'bg-green-500/20 border-green-500/30';
  if (score >= 60) return 'bg-yellow-500/20 border-yellow-500/30';
  if (score >= 40) return 'bg-orange-500/20 border-orange-500/30';
  return 'bg-red-500/20 border-red-500/30';
}

export function PerformerCard({ performer, onSelect, onBook }: PerformerCardProps): JSX.Element {
  const { t } = useTranslation();
  const isHuman = performer.performer_type === 'HUMAN';
  const hasProfileImage = !!performer.profile_image_url;

  return (
    <div
      className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden hover:border-gray-700 transition-colors group cursor-pointer"
      onClick={() => onSelect(performer)}
    >
      {/* Profile Image / Avatar */}
      <div className="relative aspect-[4/3] bg-gray-800">
        {hasProfileImage ? (
          <img
            src={performer.profile_image_url}
            alt={performer.stage_name}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <span className="text-5xl font-bold text-gray-600">
              {performer.stage_name?.charAt(0)?.toUpperCase() || '?'}
            </span>
          </div>
        )}

        {/* ACI Score Badge */}
        <div
          className={cn(
            'absolute top-3 right-3 px-2 py-1 rounded-lg border text-sm font-bold',
            getACIBadgeColor(performer.aci_score),
            getACIColor(performer.aci_score)
          )}
        >
          ACI {performer.aci_score.toFixed(0)}
        </div>

        {/* Performer Type Badge */}
        <div
          className={cn(
            'absolute top-3 left-3 px-2 py-1 rounded-lg text-xs font-medium',
            isHuman
              ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
              : 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
          )}
        >
          {isHuman ? t('performerCard.human', 'Human') : t('performerCard.synthetic', 'Synthetic')}
        </div>

        {/* Demo Reel Indicator */}
        {performer.demo_reel_url && (
          <div className="absolute bottom-3 left-3">
            <button
              onClick={(e) => {
                e.stopPropagation();
                window.open(performer.demo_reel_url, '_blank');
              }}
              className="flex items-center gap-1 px-2 py-1 bg-black/60 hover:bg-black/80 rounded-lg text-xs text-white transition-colors"
            >
              <PlayCircle className="w-3 h-3" />
              {t('performerCard.demoReel', 'Demo Reel')}
            </button>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="p-4">
        {/* Name and Verified */}
        <div className="flex items-center gap-2 mb-2">
          <h3 className="text-lg font-semibold text-white truncate">{performer.stage_name}</h3>
          {performer.is_verified && <Verified className="w-4 h-4 text-blue-400 flex-shrink-0" />}
        </div>

        {/* Specialties */}
        {performer.specialties && performer.specialties.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-3">
            {performer.specialties.slice(0, 3).map((specialty) => (
              <span
                key={specialty}
                className="px-2 py-0.5 bg-gray-800 text-gray-300 text-xs rounded"
              >
                {specialty}
              </span>
            ))}
            {performer.specialties.length > 3 && (
              <span className="px-2 py-0.5 text-gray-400 text-xs">
                +{performer.specialties.length - 3}
              </span>
            )}
          </div>
        )}

        {/* Stats Row */}
        <div className="grid grid-cols-3 gap-2 mb-4 text-center">
          <div className="bg-gray-800 rounded-lg py-2">
            <div className="flex items-center justify-center gap-1 text-yellow-400 mb-0.5">
              <Star className="w-3 h-3" />
              <span className="text-sm font-bold">{performer.rating.toFixed(1)}</span>
            </div>
            <span className="text-xs text-gray-500">{t('performerCard.rating', 'Rating')}</span>
          </div>
          <div className="bg-gray-800 rounded-lg py-2">
            <div className="flex items-center justify-center gap-1 text-blue-400 mb-0.5">
              <Calendar className="w-3 h-3" />
              <span className="text-sm font-bold">{performer.total_bookings}</span>
            </div>
            <span className="text-xs text-gray-500">{t('performerCard.bookings', 'Bookings')}</span>
          </div>
          <div className="bg-gray-800 rounded-lg py-2">
            <div className="flex items-center justify-center gap-1 text-green-400 mb-0.5">
              <TrendingUp className="w-3 h-3" />
              <span className="text-sm font-bold">
                {(performer.completion_rate * 100).toFixed(0)}%
              </span>
            </div>
            <span className="text-xs text-gray-500">{t('performerCard.complete', 'Complete')}</span>
          </div>
        </div>

        {/* Pricing */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <span className="text-xs text-gray-500 block">{t('performerCard.startingAt', 'Starting at')}</span>
            <span className="text-lg font-bold text-white">
              {formatCurrency(performer.base_price_usd)}
            </span>
            <span className="text-xs text-gray-500">/10s</span>
          </div>
          <div className="text-right">
            <span className="text-xs text-gray-500 block">{t('performerCard.avgDelivery', 'Avg. Delivery')}</span>
            <span className="flex items-center gap-1 text-sm text-gray-300">
              <Clock className="w-3 h-3" />
              {performer.avg_delivery_hours || 24}h
            </span>
          </div>
        </div>

        {/* Booking Buttons */}
        <div className="flex gap-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onBook(performer, 'BLINK');
            }}
            className="flex-1 px-3 py-2 bg-yellow-500 hover:bg-yellow-400 text-black font-medium rounded-lg transition-colors text-sm"
          >
            {t('performerCard.blink10s', 'Blink (10s)')}
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onBook(performer, 'FULL');
            }}
            className="flex-1 px-3 py-2 bg-blue-500 hover:bg-blue-400 text-white font-medium rounded-lg transition-colors text-sm"
          >
            {t('performerCard.fullBooking', 'Full Booking')}
          </button>
        </div>
      </div>
    </div>
  );
}

export default PerformerCard;
