/**
 * Lock Indicator Component
 *
 * Shows when an element is being edited by another collaborator.
 * Displays a lock icon with the user's name and a visual border.
 */

import { useState, useEffect, useCallback } from 'react';
import { Lock } from 'lucide-react';
import { useCollaborationStore, CURSOR_COLORS } from '../../stores/collaboration-store';
import { cn } from '../../lib/utils';

interface LockIndicatorProps {
  /**
   * ID of the element to check for locks
   */
  elementId: string;

  /**
   * Children to wrap with lock indicator
   */
  children: React.ReactNode;

  /**
   * Called when attempting to edit a locked element
   */
  onLockAttempt?: (lockedBy: string) => void;

  /**
   * Called when lock is acquired
   */
  onLockAcquired?: () => void;

  /**
   * Called when lock is released
   */
  onLockReleased?: () => void;

  /**
   * CSS class name for the wrapper
   */
  className?: string;
}

export function LockIndicator({
  elementId,
  children,
  onLockAttempt,
  onLockAcquired,
  onLockReleased,
  className,
}: LockIndicatorProps) {
  const { isConnected, currentUserId, getElementLock, requestLock, releaseLock, collaborators } =
    useCollaborationStore();

  const [showTooltip, setShowTooltip] = useState(false);
  const [isHovering, setIsHovering] = useState(false);

  const lock = getElementLock(elementId);
  const isLocked = lock !== null && lock.userId !== currentUserId;
  const isOwnLock = lock !== null && lock.userId === currentUserId;

  // Get the collaborator color for the lock
  const lockColor = lock
    ? collaborators[lock.userId]?.color ||
      CURSOR_COLORS[Object.keys(collaborators).indexOf(lock.userId) % CURSOR_COLORS.length]
    : undefined;

  // Handle click on locked element
  const handleClick = useCallback(
    async (e: React.MouseEvent) => {
      if (!isConnected) return;

      if (isLocked && lock) {
        e.preventDefault();
        e.stopPropagation();
        onLockAttempt?.(lock.userName);
        setShowTooltip(true);
        setTimeout(() => setShowTooltip(false), 3000);
        return;
      }

      // Request lock if not already locked
      if (!isOwnLock) {
        const acquired = await requestLock(elementId);
        if (acquired) {
          onLockAcquired?.();
        }
      }
    },
    [isConnected, isLocked, lock, isOwnLock, elementId, requestLock, onLockAttempt, onLockAcquired]
  );

  // Release lock when focus is lost or component unmounts
  useEffect(() => {
    return () => {
      if (isOwnLock) {
        releaseLock(elementId);
        onLockReleased?.();
      }
    };
  }, [elementId, isOwnLock, releaseLock, onLockReleased]);

  // Release lock on blur
  const handleBlur = useCallback(() => {
    if (isOwnLock) {
      // Delay release to allow for clicks on child elements
      setTimeout(() => {
        releaseLock(elementId);
        onLockReleased?.();
      }, 100);
    }
  }, [elementId, isOwnLock, releaseLock, onLockReleased]);

  return (
    <div
      className={cn('relative', isLocked && 'cursor-not-allowed', className)}
      onClick={handleClick}
      onBlur={handleBlur}
      onMouseEnter={() => setIsHovering(true)}
      onMouseLeave={() => setIsHovering(false)}
    >
      {/* Lock border overlay */}
      {isLocked && (
        <div
          className={cn(
            'absolute inset-0 pointer-events-none z-10',
            'rounded-lg border-2 transition-opacity',
            isHovering ? 'opacity-100' : 'opacity-70'
          )}
          style={{
            borderColor: lockColor,
            boxShadow: isHovering ? `0 0 8px ${lockColor}40` : undefined,
          }}
        />
      )}

      {/* Lock indicator badge */}
      {isLocked && lock && (
        <div
          className={cn(
            'absolute -top-2 -right-2 z-20',
            'flex items-center gap-1 px-2 py-0.5',
            'rounded-full text-xs font-medium shadow-lg',
            'transition-all duration-200',
            isHovering ? 'scale-110' : 'scale-100'
          )}
          style={{
            backgroundColor: lockColor,
            color: getContrastColor(lockColor || '#000'),
          }}
        >
          <Lock className="w-3 h-3" />
          <span>{lock.userName.split(' ')[0]}</span>
        </div>
      )}

      {/* Tooltip when clicking locked element */}
      {showTooltip && lock && (
        <div
          className={cn(
            'absolute left-1/2 -translate-x-1/2 -top-12 z-30',
            'px-3 py-2 rounded-lg shadow-lg',
            'bg-surface-900 text-white text-sm',
            'whitespace-nowrap animate-in fade-in-0 slide-in-from-bottom-2'
          )}
        >
          Being edited by {lock.userName}
          <div
            className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-2 h-2 rotate-45"
            style={{ backgroundColor: 'rgb(15 23 42)' }}
          />
        </div>
      )}

      {/* Own lock indicator */}
      {isOwnLock && (
        <div
          className={cn(
            'absolute -top-2 -right-2 z-20',
            'flex items-center gap-1 px-2 py-0.5',
            'rounded-full text-xs font-medium shadow-lg',
            'bg-primary-500 text-white'
          )}
        >
          <Lock className="w-3 h-3" />
          <span>Editing</span>
        </div>
      )}

      {/* Children */}
      <div className={cn(isLocked && 'pointer-events-none opacity-75')}>{children}</div>
    </div>
  );
}

/**
 * Determine if text should be white or black based on background color
 */
function getContrastColor(hexColor: string): string {
  const hex = hexColor.replace('#', '');
  const r = parseInt(hex.substring(0, 2), 16);
  const g = parseInt(hex.substring(2, 4), 16);
  const b = parseInt(hex.substring(4, 6), 16);
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance > 0.5 ? '#000000' : '#FFFFFF';
}

export default LockIndicator;
