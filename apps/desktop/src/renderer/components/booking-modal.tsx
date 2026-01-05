/**
 * BookingModal - Modal for creating ActForge bookings.
 *
 * Supports BLINK, DEEP, and EPIC booking modes with
 * different options for each.
 */

import React, { useState, useCallback } from 'react';
import { X, Zap, Heart, Crown, Clock, DollarSign, AlertCircle, Loader2 } from 'lucide-react';
import type { Performer, BookingMode } from '../api/client';
import { useActForgeStore, useBookingModeInfo } from '../stores/actforge-store';

interface BookingModalProps {
  isOpen: boolean;
  onClose: () => void;
  performer: Performer | null;
  mode: BookingMode;
  projectId: string;
  shotId?: string;
  onSuccess?: () => void;
}

export function BookingModal({
  isOpen,
  onClose,
  performer,
  mode,
  projectId,
  shotId,
  onSuccess,
}: BookingModalProps): JSX.Element | null {
  const [durationSeconds, setDurationSeconds] = useState<number>(() => {
    switch (mode) {
      case 'BLINK':
        return 10;
      case 'DEEP':
        return 60;
      case 'EPIC':
        return 300;
      default:
        return 10;
    }
  });
  const [emotionMarkers, setEmotionMarkers] = useState<string[]>([]);
  const [specialInstructions, setSpecialInstructions] = useState('');

  const {
    createBlinkBooking,
    createDeepBooking,
    createEpicBooking,
    isCreatingBooking,
    error,
    clearError,
  } = useActForgeStore();

  const modeInfo = useBookingModeInfo(mode);

  const getModeIcon = () => {
    switch (mode) {
      case 'BLINK':
        return <Zap className="w-6 h-6 text-yellow-400" />;
      case 'DEEP':
        return <Heart className="w-6 h-6 text-pink-400" />;
      case 'EPIC':
        return <Crown className="w-6 h-6 text-purple-400" />;
      default:
        return null;
    }
  };

  const getPrice = () => {
    if (!performer) return 0;
    // Calculate price based on duration
    const basePrice =
      mode === 'BLINK'
        ? performer.pricing_blink_usd
        : mode === 'DEEP'
        ? performer.pricing_deep_usd
        : performer.pricing_epic_usd;
    const baseSeconds = mode === 'BLINK' ? 10 : mode === 'DEEP' ? 60 : 300;
    return (basePrice / baseSeconds) * durationSeconds;
  };

  const handleSubmit = useCallback(async () => {
    clearError();

    let booking = null;

    switch (mode) {
      case 'BLINK':
        booking = await createBlinkBooking(projectId, shotId, performer?.id, durationSeconds);
        break;
      case 'DEEP':
        if (!performer) return;
        booking = await createDeepBooking(
          projectId,
          performer.id,
          shotId,
          durationSeconds,
          { emotion_markers: emotionMarkers, special_instructions: specialInstructions }
        );
        break;
      case 'EPIC':
        if (!performer) return;
        booking = await createEpicBooking(
          projectId,
          performer.id,
          shotId,
          durationSeconds,
          { emotion_markers: emotionMarkers, special_instructions: specialInstructions }
        );
        break;
    }

    if (booking) {
      onSuccess?.();
      onClose();
    }
  }, [
    mode,
    projectId,
    shotId,
    performer,
    durationSeconds,
    emotionMarkers,
    specialInstructions,
    createBlinkBooking,
    createDeepBooking,
    createEpicBooking,
    clearError,
    onSuccess,
    onClose,
  ]);

  const toggleEmotion = (emotion: string) => {
    setEmotionMarkers((prev) =>
      prev.includes(emotion) ? prev.filter((e) => e !== emotion) : [...prev, emotion]
    );
  };

  const availableEmotions = [
    'happy',
    'sad',
    'angry',
    'surprised',
    'fearful',
    'disgusted',
    'neutral',
    'contemplative',
    'excited',
    'loving',
  ];

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 rounded-xl border border-gray-800 max-w-md w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-800">
          <div className="flex items-center gap-3">
            {getModeIcon()}
            <div>
              <h2 className="text-lg font-semibold text-white">{modeInfo.label} Booking</h2>
              <p className="text-sm text-gray-400">{modeInfo.description}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="icon-btn p-2 hover:bg-gray-800 rounded-lg transition-colors"
            aria-label="Close booking modal"
          >
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4">
          {/* Error display */}
          {error && (
            <div className="flex items-start gap-2 p-3 bg-red-500/20 border border-red-500/50 rounded-lg">
              <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-300">{error}</p>
            </div>
          )}

          {/* Performer info */}
          {performer && (
            <div className="flex items-center gap-3 p-3 bg-gray-800 rounded-lg">
              <div className="w-12 h-12 rounded-full bg-gray-700 overflow-hidden flex-shrink-0">
                {performer.avatar_url ? (
                  <img
                    src={performer.avatar_url}
                    alt={performer.stage_name}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-gray-400">
                    ?
                  </div>
                )}
              </div>
              <div>
                <div className="font-medium text-white">{performer.stage_name}</div>
                <div className="text-sm text-gray-400">
                  ACI {performer.aci_score.toFixed(0)} | {performer.completed_bookings} bookings
                </div>
              </div>
            </div>
          )}

          {/* Duration selector */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              <Clock className="w-4 h-4 inline mr-1" />
              Duration
            </label>
            <div className="flex items-center gap-3">
              <input
                type="range"
                min={mode === 'BLINK' ? 3 : mode === 'DEEP' ? 10 : 60}
                max={modeInfo.maxDuration}
                value={durationSeconds}
                onChange={(e) => setDurationSeconds(parseInt(e.target.value, 10))}
                className="flex-1 h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
              />
              <span className="text-white font-medium w-16 text-right">
                {durationSeconds < 60
                  ? `${durationSeconds}s`
                  : `${Math.floor(durationSeconds / 60)}:${String(durationSeconds % 60).padStart(
                      2,
                      '0'
                    )}`}
              </span>
            </div>
          </div>

          {/* Emotion markers (DEEP and EPIC only) */}
          {(mode === 'DEEP' || mode === 'EPIC') && (
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Emotion Markers
              </label>
              <div className="flex flex-wrap gap-2">
                {availableEmotions.map((emotion) => (
                  <button
                    key={emotion}
                    onClick={() => toggleEmotion(emotion)}
                    className={`px-3 py-1 rounded-full text-sm transition-colors ${
                      emotionMarkers.includes(emotion)
                        ? 'bg-blue-500 text-white'
                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    }`}
                  >
                    {emotion}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Special instructions (DEEP and EPIC only) */}
          {(mode === 'DEEP' || mode === 'EPIC') && (
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Special Instructions
              </label>
              <textarea
                value={specialInstructions}
                onChange={(e) => setSpecialInstructions(e.target.value)}
                placeholder="Describe any specific actions, expressions, or timing..."
                className="w-full p-3 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none resize-none"
                rows={3}
              />
            </div>
          )}

          {/* Price estimate */}
          <div className="flex items-center justify-between p-3 bg-gray-800 rounded-lg">
            <div className="flex items-center gap-2 text-gray-300">
              <DollarSign className="w-5 h-5" />
              <span>Estimated Cost</span>
            </div>
            <span className="text-xl font-bold text-white">${getPrice().toFixed(2)}</span>
          </div>

          {/* BLINK auto-match note */}
          {mode === 'BLINK' && !performer && (
            <p className="text-sm text-gray-400 text-center">
              A performer will be automatically matched based on availability and your requirements.
            </p>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-800 flex gap-3">
          <button
            onClick={onClose}
            disabled={isCreatingBooking}
            className="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={isCreatingBooking || (mode !== 'BLINK' && !performer)}
            className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors disabled:opacity-50 flex items-center justify-center gap-2 ${
              mode === 'BLINK'
                ? 'bg-yellow-500 hover:bg-yellow-400 text-black'
                : mode === 'DEEP'
                ? 'bg-pink-500 hover:bg-pink-400 text-white'
                : 'bg-purple-500 hover:bg-purple-400 text-white'
            }`}
          >
            {isCreatingBooking ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Creating...
              </>
            ) : (
              <>Book {modeInfo.label}</>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

export default BookingModal;
