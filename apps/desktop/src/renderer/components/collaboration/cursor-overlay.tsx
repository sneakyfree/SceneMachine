/**
 * Cursor Overlay Component
 *
 * Renders all collaborator cursors as an overlay on top of the application.
 * Handles cursor tracking and broadcasts local cursor position.
 */

import { useEffect, useCallback, useRef } from 'react';
import { Cursor } from './cursor';
import { useCollaborationStore, CURSOR_COLORS } from '../../stores/collaboration-store';
import { cn } from '../../lib/utils';

interface CursorOverlayProps {
  /**
   * Whether to track and broadcast local cursor position
   */
  trackLocalCursor?: boolean;

  /**
   * CSS class name for the overlay container
   */
  className?: string;
}

// Throttle cursor updates to 20 per second (50ms minimum between updates)
const CURSOR_UPDATE_INTERVAL_MS = 50;

export function CursorOverlay({ trackLocalCursor = true, className }: CursorOverlayProps) {
  const {
    isConnected,
    currentUserId,
    collaborators,
    cursors,
    setLocalCursor,
  } = useCollaborationStore();

  const lastUpdateRef = useRef<number>(0);
  const rafRef = useRef<number | null>(null);
  const pendingCursorRef = useRef<{ x: number; y: number } | null>(null);

  // Throttled cursor update
  const updateCursor = useCallback(
    (x: number, y: number) => {
      const now = Date.now();
      pendingCursorRef.current = { x, y };

      if (now - lastUpdateRef.current >= CURSOR_UPDATE_INTERVAL_MS) {
        lastUpdateRef.current = now;
        setLocalCursor(x, y);
        pendingCursorRef.current = null;
      } else if (!rafRef.current) {
        // Schedule update
        rafRef.current = window.requestAnimationFrame(() => {
          if (pendingCursorRef.current) {
            setLocalCursor(pendingCursorRef.current.x, pendingCursorRef.current.y);
            pendingCursorRef.current = null;
          }
          rafRef.current = null;
        });
      }
    },
    [setLocalCursor]
  );

  // Track mouse movement
  useEffect(() => {
    if (!trackLocalCursor || !isConnected) return;

    const handleMouseMove = (e: MouseEvent) => {
      updateCursor(e.clientX, e.clientY);
    };

    window.addEventListener('mousemove', handleMouseMove, { passive: true });

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      if (rafRef.current) {
        window.cancelAnimationFrame(rafRef.current);
      }
    };
  }, [trackLocalCursor, isConnected, updateCursor]);

  // Don't render if not connected
  if (!isConnected) {
    return null;
  }

  // Filter out current user's cursor and get cursor data
  const otherCursors = Object.entries(cursors)
    .filter(([userId]) => userId !== currentUserId)
    .map(([userId, position]) => {
      const collaborator = collaborators[userId];
      const colorIndex = Object.keys(collaborators).indexOf(userId);
      const color = collaborator?.color || CURSOR_COLORS[colorIndex % CURSOR_COLORS.length];

      return {
        userId,
        x: position.x,
        y: position.y,
        name: collaborator?.name || 'Unknown',
        color,
        lastUpdate: position.timestamp,
      };
    });

  return (
    <div
      className={cn(
        "fixed inset-0 pointer-events-none z-[9999]",
        className
      )}
      aria-hidden="true"
    >
      {otherCursors.map((cursor) => (
        <Cursor
          key={cursor.userId}
          x={cursor.x}
          y={cursor.y}
          name={cursor.name}
          color={cursor.color}
          lastUpdate={cursor.lastUpdate}
        />
      ))}
    </div>
  );
}

export default CursorOverlay;
