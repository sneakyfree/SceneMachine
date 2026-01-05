/**
 * PerformerCard - Display card for ActForge performer.
 *
 * Shows performer avatar, ACI score, pricing, and booking options.
 */

import React from 'react';
import { Star, Zap, Heart, Crown, CheckCircle, User } from 'lucide-react';
import type { Performer, BookingMode } from '../api/client';

interface PerformerCardProps {
  performer: Performer;
  onSelect?: (performer: Performer) => void;
  onBook?: (performer: Performer, mode: BookingMode) => void;
  compact?: boolean;
}

export function PerformerCard({
  performer,
  onSelect,
  onBook,
  compact = false,
}: PerformerCardProps): JSX.Element {
  const handleSelect = () => {
    onSelect?.(performer);
  };

  const handleBook = (mode: BookingMode, e: React.MouseEvent) => {
    e.stopPropagation();
    onBook?.(performer, mode);
  };

  const getACIBadgeColor = (score: number): string => {
    if (score >= 90) return 'bg-gradient-to-r from-yellow-400 to-amber-500 text-black';
    if (score >= 75) return 'bg-gradient-to-r from-purple-500 to-pink-500 text-white';
    if (score >= 60) return 'bg-gradient-to-r from-blue-500 to-cyan-500 text-white';
    if (score >= 40) return 'bg-gradient-to-r from-green-500 to-emerald-500 text-white';
    return 'bg-gray-600 text-white';
  };

  const getACITierLabel = (score: number): string => {
    if (score >= 90) return 'Legend';
    if (score >= 75) return 'Elite';
    if (score >= 60) return 'Pro';
    if (score >= 40) return 'Rising';
    return 'Emerging';
  };

  if (compact) {
    return (
      <div
        className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-800 cursor-pointer transition-colors"
        onClick={handleSelect}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && handleSelect()}
      >
        {/* Avatar */}
        <div className="relative w-10 h-10 rounded-full overflow-hidden bg-gray-700 flex-shrink-0">
          {performer.avatar_url ? (
            <img
              src={performer.avatar_url}
              alt={performer.stage_name}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <User className="w-5 h-5 text-gray-400" />
            </div>
          )}
          {performer.is_verified && (
            <div className="absolute -bottom-0.5 -right-0.5 bg-blue-500 rounded-full p-0.5">
              <CheckCircle className="w-3 h-3 text-white" />
            </div>
          )}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm text-white truncate">
              {performer.stage_name}
            </span>
            <span
              className={`px-1.5 py-0.5 rounded text-xs font-bold ${getACIBadgeColor(
                performer.aci_score
              )}`}
            >
              {performer.aci_score.toFixed(0)}
            </span>
          </div>
          <div className="text-xs text-gray-400">
            ${performer.pricing_blink_usd.toFixed(0)} BLINK
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden hover:border-gray-700 transition-all cursor-pointer group"
      onClick={handleSelect}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && handleSelect()}
    >
      {/* Header with avatar and ACI */}
      <div className="relative">
        <div className="aspect-[4/3] bg-gray-800 overflow-hidden">
          {performer.avatar_url ? (
            <img
              src={performer.avatar_url}
              alt={performer.stage_name}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <User className="w-16 h-16 text-gray-600" />
            </div>
          )}
        </div>

        {/* ACI Badge */}
        <div
          className={`absolute top-3 right-3 px-2 py-1 rounded-lg font-bold text-sm ${getACIBadgeColor(
            performer.aci_score
          )}`}
        >
          <span className="text-xs opacity-75">ACI </span>
          {performer.aci_score.toFixed(0)}
        </div>

        {/* Verified badge */}
        {performer.is_verified && (
          <div className="absolute top-3 left-3 bg-blue-500 rounded-full p-1">
            <CheckCircle className="w-4 h-4 text-white" />
          </div>
        )}

        {/* Featured badge */}
        {performer.is_featured && (
          <div className="absolute bottom-3 left-3 bg-gradient-to-r from-yellow-500 to-orange-500 px-2 py-0.5 rounded text-xs font-bold text-black">
            Featured
          </div>
        )}

        {/* Type badge */}
        <div className="absolute bottom-3 right-3 bg-gray-900/80 backdrop-blur px-2 py-0.5 rounded text-xs text-gray-300">
          {performer.performer_type === 'HUMAN' ? 'Human' : 'Synthetic'}
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        {/* Name and tier */}
        <div className="flex items-center justify-between mb-2">
          <h3 className="font-semibold text-white text-lg truncate">
            {performer.stage_name}
          </h3>
          <span className="text-xs text-gray-400">{getACITierLabel(performer.aci_score)}</span>
        </div>

        {/* Rating */}
        <div className="flex items-center gap-1 mb-3">
          <Star className="w-4 h-4 text-yellow-400 fill-yellow-400" />
          <span className="text-sm text-white font-medium">
            {performer.average_rating.toFixed(1)}
          </span>
          <span className="text-xs text-gray-400">
            ({performer.total_ratings} reviews)
          </span>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-2 mb-4 text-xs">
          <div className="bg-gray-800 rounded-lg p-2 text-center">
            <div className="text-gray-400">Bookings</div>
            <div className="text-white font-medium">{performer.completed_bookings}</div>
          </div>
          <div className="bg-gray-800 rounded-lg p-2 text-center">
            <div className="text-gray-400">Split</div>
            <div className="text-green-400 font-medium">
              {performer.revenue_split_percent.toFixed(0)}%
            </div>
          </div>
        </div>

        {/* Pricing */}
        <div className="space-y-2 mb-4">
          <button
            onClick={(e) => handleBook('BLINK', e)}
            className="w-full flex items-center justify-between p-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition-colors text-sm"
          >
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-yellow-400" />
              <span className="text-gray-200">Blink</span>
              <span className="text-xs text-gray-400">(10s)</span>
            </div>
            <span className="font-medium text-white">
              ${performer.pricing_blink_usd.toFixed(0)}
            </span>
          </button>

          <button
            onClick={(e) => handleBook('DEEP', e)}
            className="w-full flex items-center justify-between p-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition-colors text-sm"
          >
            <div className="flex items-center gap-2">
              <Heart className="w-4 h-4 text-pink-400" />
              <span className="text-gray-200">Deep</span>
              <span className="text-xs text-gray-400">(120s)</span>
            </div>
            <span className="font-medium text-white">
              ${performer.pricing_deep_usd.toFixed(0)}
            </span>
          </button>

          <button
            onClick={(e) => handleBook('EPIC', e)}
            className="w-full flex items-center justify-between p-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition-colors text-sm"
          >
            <div className="flex items-center gap-2">
              <Crown className="w-4 h-4 text-purple-400" />
              <span className="text-gray-200">Epic</span>
              <span className="text-xs text-gray-400">(5-20min)</span>
            </div>
            <span className="font-medium text-white">
              ${performer.pricing_epic_usd.toFixed(0)}
            </span>
          </button>
        </div>

        {/* Capabilities */}
        <div className="flex flex-wrap gap-1">
          {performer.motion_capabilities.live_portrait && (
            <span className="px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded text-xs">
              LivePortrait
            </span>
          )}
          {performer.motion_capabilities.roop_gs_anim && (
            <span className="px-2 py-0.5 bg-purple-500/20 text-purple-400 rounded text-xs">
              Full-Body
            </span>
          )}
          {performer.motion_capabilities.emotion_range?.slice(0, 2).map((emotion) => (
            <span
              key={emotion}
              className="px-2 py-0.5 bg-gray-700 text-gray-300 rounded text-xs"
            >
              {emotion}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

export default PerformerCard;
