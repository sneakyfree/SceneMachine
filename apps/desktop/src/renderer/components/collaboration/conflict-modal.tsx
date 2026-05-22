/**
 * Conflict Resolution Modal Component
 *
 * Displays when simultaneous edits create a conflict.
 * Allows users to choose between their changes, the other user's changes,
 * or merge if possible.
 */

import { useState, useCallback } from 'react';
import { AlertTriangle, Check, X, GitMerge, User, Users } from 'lucide-react';
import { cn } from '../../lib/utils';

export interface ConflictData<T = unknown> {
  elementId: string;
  elementType: string;
  elementName: string;
  yourChanges: T;
  theirChanges: T;
  theirUserId: string;
  theirUserName: string;
  baseVersion: T;
  canAutoMerge: boolean;
  mergedVersion?: T;
}

interface ConflictModalProps<T = unknown> {
  conflict: ConflictData<T>;
  onResolve: (resolution: 'mine' | 'theirs' | 'merge', resolvedData?: T) => void;
  onCancel: () => void;
  renderPreview?: (data: T, label: string) => React.ReactNode;
}

export function ConflictModal<T = unknown>({
  conflict,
  onResolve,
  onCancel,
  renderPreview,
}: ConflictModalProps<T>) {
  const [selectedOption, setSelectedOption] = useState<'mine' | 'theirs' | 'merge' | null>(null);
  const [isResolving, setIsResolving] = useState(false);

  const handleResolve = useCallback(async () => {
    if (!selectedOption) return;

    setIsResolving(true);

    try {
      if (selectedOption === 'merge' && conflict.mergedVersion) {
        onResolve('merge', conflict.mergedVersion);
      } else {
        onResolve(selectedOption);
      }
    } finally {
      setIsResolving(false);
    }
  }, [selectedOption, conflict.mergedVersion, onResolve]);

  // Default preview renderer
  const defaultRenderPreview = (data: T, label: string) => (
    <div className="p-3 bg-surface-800 rounded-lg">
      <div className="text-sm text-surface-400 mb-2">{label}</div>
      <pre className="text-xs text-surface-200 whitespace-pre-wrap overflow-auto max-h-48">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );

  const preview = renderPreview || defaultRenderPreview;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onCancel} />

      {/* Modal */}
      <div
        className={cn(
          'relative w-full max-w-2xl mx-4',
          'bg-surface-900 rounded-xl shadow-2xl',
          'border border-surface-700',
          'animate-in fade-in-0 zoom-in-95 duration-200'
        )}
      >
        {/* Header */}
        <div className="flex items-center gap-3 px-6 py-4 border-b border-surface-700">
          <div className="p-2 rounded-full bg-yellow-500/20">
            <AlertTriangle className="w-5 h-5 text-yellow-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">Conflict Detected</h2>
            <p className="text-sm text-surface-400">
              Changes conflict with {conflict.theirUserName}&apos;s edits to{' '}
              <span className="text-surface-200">{conflict.elementName}</span>
            </p>
          </div>
        </div>

        {/* Body */}
        <div className="p-6 space-y-4">
          {/* Preview comparison */}
          <div className="grid grid-cols-2 gap-4">
            {/* Your changes */}
            <div
              className={cn(
                'rounded-lg border-2 cursor-pointer transition-all',
                selectedOption === 'mine'
                  ? 'border-primary-500 bg-primary-500/10'
                  : 'border-surface-700 hover:border-surface-600'
              )}
              onClick={() => setSelectedOption('mine')}
            >
              <div className="flex items-center gap-2 px-4 py-3 border-b border-surface-700">
                <User className="w-4 h-4 text-primary-400" />
                <span className="font-medium text-white">Your Changes</span>
                {selectedOption === 'mine' && (
                  <Check className="w-4 h-4 text-primary-400 ml-auto" />
                )}
              </div>
              <div className="p-4">{preview(conflict.yourChanges, 'Your version')}</div>
            </div>

            {/* Their changes */}
            <div
              className={cn(
                'rounded-lg border-2 cursor-pointer transition-all',
                selectedOption === 'theirs'
                  ? 'border-orange-500 bg-orange-500/10'
                  : 'border-surface-700 hover:border-surface-600'
              )}
              onClick={() => setSelectedOption('theirs')}
            >
              <div className="flex items-center gap-2 px-4 py-3 border-b border-surface-700">
                <Users className="w-4 h-4 text-orange-400" />
                <span className="font-medium text-white">
                  {conflict.theirUserName}&apos;s Changes
                </span>
                {selectedOption === 'theirs' && (
                  <Check className="w-4 h-4 text-orange-400 ml-auto" />
                )}
              </div>
              <div className="p-4">
                {preview(conflict.theirChanges, `${conflict.theirUserName}'s version`)}
              </div>
            </div>
          </div>

          {/* Merge option (if available) */}
          {conflict.canAutoMerge && conflict.mergedVersion && (
            <div
              className={cn(
                'rounded-lg border-2 cursor-pointer transition-all',
                selectedOption === 'merge'
                  ? 'border-green-500 bg-green-500/10'
                  : 'border-surface-700 hover:border-surface-600'
              )}
              onClick={() => setSelectedOption('merge')}
            >
              <div className="flex items-center gap-2 px-4 py-3 border-b border-surface-700">
                <GitMerge className="w-4 h-4 text-green-400" />
                <span className="font-medium text-white">Auto-Merge</span>
                <span className="text-xs text-surface-400 px-2 py-0.5 bg-green-500/20 rounded">
                  Recommended
                </span>
                {selectedOption === 'merge' && <Check className="w-4 h-4 text-green-400 ml-auto" />}
              </div>
              <div className="p-4">{preview(conflict.mergedVersion, 'Combined changes')}</div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-surface-700">
          <button
            onClick={onCancel}
            className={cn(
              'px-4 py-2 rounded-lg text-sm font-medium',
              'bg-surface-800 text-surface-200',
              'hover:bg-surface-700 transition-colors',
              'focus:outline-none focus:ring-2 focus:ring-surface-500'
            )}
          >
            <X className="w-4 h-4 inline mr-2" />
            Cancel
          </button>

          <button
            onClick={handleResolve}
            disabled={!selectedOption || isResolving}
            className={cn(
              'px-4 py-2 rounded-lg text-sm font-medium',
              'bg-primary-500 text-white',
              'hover:bg-primary-600 transition-colors',
              'focus:outline-none focus:ring-2 focus:ring-primary-500',
              'disabled:opacity-50 disabled:cursor-not-allowed'
            )}
          >
            {isResolving ? (
              <>
                <span className="inline-block w-4 h-4 mr-2 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Resolving...
              </>
            ) : (
              <>
                <Check className="w-4 h-4 inline mr-2" />
                Apply {selectedOption === 'merge' ? 'Merge' : 'Selection'}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

export default ConflictModal;
