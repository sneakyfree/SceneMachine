/**
 * Booking Modal component for ActForge performer bookings.
 * Handles BLINK (quick) and FULL (custom) booking modes.
 */

import React, { useState, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import {
  X,
  Zap,
  Clock,
  AlertCircle,
  CheckCircle,
  Loader2,
  User,
  Video,
  FileText,
  Calendar,
} from 'lucide-react';
import type { Performer, BookingMode, BookingRequest } from '../api/client';
import { api } from '../api/client';
import { cn } from '../lib/utils';

interface BookingModalProps {
  isOpen: boolean;
  onClose: () => void;
  performer: Performer | null;
  mode: BookingMode;
  projectId: string;
  onSuccess: () => void;
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

export function BookingModal({
  isOpen,
  onClose,
  performer,
  mode,
  projectId,
  onSuccess,
}: BookingModalProps): JSX.Element | null {
  // Form state
  const [duration, setDuration] = useState(mode === 'BLINK' ? 10 : 30);
  const [promptText, setPromptText] = useState('');
  const [referenceStyle, setReferenceStyle] = useState('');
  const [notes, setNotes] = useState('');
  const [urgency, setUrgency] = useState<'STANDARD' | 'RUSH' | 'PRIORITY'>('STANDARD');
  const [agreedToTerms, setAgreedToTerms] = useState(false);

  // Calculate estimated cost
  const baseCost = performer?.base_price_usd || 0;
  const durationMultiplier = duration / 10;
  const urgencyMultiplier = urgency === 'RUSH' ? 1.5 : urgency === 'PRIORITY' ? 2.0 : 1.0;
  const estimatedCost = baseCost * durationMultiplier * urgencyMultiplier;

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      setDuration(mode === 'BLINK' ? 10 : 30);
      setPromptText('');
      setReferenceStyle('');
      setNotes('');
      setUrgency('STANDARD');
      setAgreedToTerms(false);
    }
  }, [isOpen, mode]);

  // Booking mutation
  const bookingMutation = useMutation({
    mutationFn: async (request: BookingRequest) => {
      return api.createBooking(request);
    },
    onSuccess: () => {
      onSuccess();
      onClose();
    },
  });

  const handleSubmit = () => {
    if (!performer || !agreedToTerms) return;

    const request: BookingRequest = {
      performer_id: performer.id,
      project_id: projectId || undefined,
      mode,
      duration_seconds: duration,
      prompt: promptText || undefined,
      reference_style: referenceStyle || undefined,
      notes: notes || undefined,
      urgency,
    };

    bookingMutation.mutate(request);
  };

  if (!isOpen) return null;

  const isBlink = mode === 'BLINK';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative bg-gray-900 rounded-xl border border-gray-800 shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-800">
          <div className="flex items-center gap-3">
            {isBlink ? (
              <div className="p-2 bg-yellow-500/20 rounded-lg">
                <Zap className="w-5 h-5 text-yellow-400" />
              </div>
            ) : (
              <div className="p-2 bg-blue-500/20 rounded-lg">
                <Calendar className="w-5 h-5 text-blue-400" />
              </div>
            )}
            <div>
              <h2 className="text-lg font-semibold text-white">
                {isBlink ? 'Quick Blink Booking' : 'Full Booking Request'}
              </h2>
              <p className="text-sm text-gray-400">
                {isBlink ? '10-second auto-matched clip' : 'Custom performance request'}
              </p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-800 rounded-lg transition-colors">
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4">
          {/* Performer Info (if selected) */}
          {performer && (
            <div className="flex items-center gap-3 p-3 bg-gray-800 rounded-lg">
              <div className="w-12 h-12 rounded-full bg-gray-700 overflow-hidden flex-shrink-0">
                {performer.profile_image_url ? (
                  <img
                    src={performer.profile_image_url}
                    alt={performer.stage_name}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-gray-500">
                    <User className="w-6 h-6" />
                  </div>
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-medium text-white truncate">{performer.stage_name}</div>
                <div className="text-sm text-gray-400">
                  ACI Score: {performer.aci_score.toFixed(0)} | Rating:{' '}
                  {performer.rating.toFixed(1)}
                </div>
              </div>
              <div className="text-right">
                <div className="text-sm text-gray-400">Base Price</div>
                <div className="font-bold text-white">
                  {formatCurrency(performer.base_price_usd)}/10s
                </div>
              </div>
            </div>
          )}

          {/* Duration Selection (only for full booking) */}
          {!isBlink && (
            <div>
              <label className="block text-sm text-gray-400 mb-2">
                <Video className="w-4 h-4 inline mr-1" />
                Duration (seconds)
              </label>
              <div className="flex gap-2">
                {[10, 30, 60, 120].map((d) => (
                  <button
                    key={d}
                    onClick={() => setDuration(d)}
                    className={cn(
                      'flex-1 py-2 rounded-lg border transition-colors',
                      duration === d
                        ? 'bg-blue-500 border-blue-500 text-white'
                        : 'bg-gray-800 border-gray-700 text-gray-300 hover:bg-gray-700'
                    )}
                  >
                    {d}s
                  </button>
                ))}
              </div>
              <input
                type="range"
                min={10}
                max={300}
                step={10}
                value={duration}
                onChange={(e) => setDuration(parseInt(e.target.value))}
                className="w-full mt-2"
              />
            </div>
          )}

          {/* Prompt */}
          <div>
            <label className="block text-sm text-gray-400 mb-2">
              <FileText className="w-4 h-4 inline mr-1" />
              {isBlink ? 'Quick prompt (optional)' : 'Performance prompt'}
            </label>
            <textarea
              value={promptText}
              onChange={(e) => setPromptText(e.target.value)}
              placeholder={
                isBlink
                  ? 'Brief description of desired action...'
                  : 'Describe the performance in detail: setting, emotion, actions...'
              }
              rows={isBlink ? 2 : 4}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none resize-none"
            />
          </div>

          {/* Reference Style (only for full booking) */}
          {!isBlink && (
            <div>
              <label className="block text-sm text-gray-400 mb-2">Reference style (optional)</label>
              <input
                type="text"
                value={referenceStyle}
                onChange={(e) => setReferenceStyle(e.target.value)}
                placeholder="e.g., Film noir, cyberpunk, documentary..."
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none"
              />
            </div>
          )}

          {/* Urgency Selection (only for full booking) */}
          {!isBlink && (
            <div>
              <label className="block text-sm text-gray-400 mb-2">
                <Clock className="w-4 h-4 inline mr-1" />
                Delivery urgency
              </label>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { value: 'STANDARD', label: 'Standard', time: '24-48h', multiplier: '1x' },
                  { value: 'RUSH', label: 'Rush', time: '12-24h', multiplier: '1.5x' },
                  { value: 'PRIORITY', label: 'Priority', time: '< 12h', multiplier: '2x' },
                ].map((option) => (
                  <button
                    key={option.value}
                    onClick={() => setUrgency(option.value as typeof urgency)}
                    className={cn(
                      'p-3 rounded-lg border transition-colors text-center',
                      urgency === option.value
                        ? 'bg-blue-500/20 border-blue-500/50 text-blue-400'
                        : 'bg-gray-800 border-gray-700 text-gray-300 hover:bg-gray-700'
                    )}
                  >
                    <div className="font-medium">{option.label}</div>
                    <div className="text-xs text-gray-500">{option.time}</div>
                    <div className="text-xs text-gray-500">{option.multiplier}</div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Notes (only for full booking) */}
          {!isBlink && (
            <div>
              <label className="block text-sm text-gray-400 mb-2">
                Additional notes (optional)
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Any special requirements or instructions..."
                rows={2}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none resize-none"
              />
            </div>
          )}

          {/* Cost Summary */}
          <div className="p-4 bg-gray-800 rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <span className="text-gray-400">Duration</span>
              <span className="text-white">{duration} seconds</span>
            </div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-gray-400">Base rate</span>
              <span className="text-white">{formatCurrency(baseCost)}/10s</span>
            </div>
            {!isBlink && urgency !== 'STANDARD' && (
              <div className="flex items-center justify-between mb-2">
                <span className="text-gray-400">Urgency multiplier</span>
                <span className="text-yellow-400">{urgency === 'RUSH' ? '1.5x' : '2x'}</span>
              </div>
            )}
            <div className="border-t border-gray-700 pt-2 mt-2">
              <div className="flex items-center justify-between">
                <span className="font-medium text-white">Estimated Total</span>
                <span className="text-xl font-bold text-green-400">
                  {formatCurrency(estimatedCost)}
                </span>
              </div>
            </div>
          </div>

          {/* Terms Agreement */}
          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={agreedToTerms}
              onChange={(e) => setAgreedToTerms(e.target.checked)}
              className="mt-1 w-4 h-4 rounded border-gray-700 bg-gray-800 text-blue-500 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-400">
              I agree to the{' '}
              <a href="#" className="text-blue-400 hover:underline">
                booking terms
              </a>{' '}
              and understand that final delivery may vary from the estimated timeline.
            </span>
          </label>

          {/* Error Message */}
          {bookingMutation.error && (
            <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <span className="text-sm">
                {bookingMutation.error instanceof Error
                  ? bookingMutation.error.message
                  : 'Failed to create booking'}
              </span>
            </div>
          )}

          {/* Success Message */}
          {bookingMutation.isSuccess && (
            <div className="flex items-center gap-2 p-3 bg-green-500/10 border border-green-500/30 rounded-lg text-green-400">
              <CheckCircle className="w-5 h-5 flex-shrink-0" />
              <span className="text-sm">Booking created successfully!</span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-4 border-t border-gray-800 bg-gray-900/50">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-400 hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!agreedToTerms || (!isBlink && !promptText) || bookingMutation.isPending}
            className={cn(
              'px-6 py-2 rounded-lg font-medium transition-colors flex items-center gap-2',
              isBlink
                ? 'bg-yellow-500 hover:bg-yellow-400 text-black disabled:opacity-50 disabled:cursor-not-allowed'
                : 'bg-blue-500 hover:bg-blue-400 text-white disabled:opacity-50 disabled:cursor-not-allowed'
            )}
          >
            {bookingMutation.isPending ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Processing...
              </>
            ) : (
              <>
                {isBlink ? <Zap className="w-4 h-4" /> : <Calendar className="w-4 h-4" />}
                {isBlink ? 'Book Blink' : 'Submit Booking'}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

export default BookingModal;
