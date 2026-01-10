/**
 * Collaborator Cursor Component
 *
 * Displays a cursor pointer with the collaborator's name label.
 * Features smooth animation and automatic fade-out after inactivity.
 */

import { useState, useEffect, memo } from 'react';
import { cn } from '../../lib/utils';

interface CursorProps {
  x: number;
  y: number;
  name: string;
  color: string;
  lastUpdate: number;
  className?: string;
}

// Fade out cursor after 3 seconds of inactivity
const INACTIVITY_FADE_MS = 3000;

function CursorComponent({ x, y, name, color, lastUpdate, className }: CursorProps) {
  const [opacity, setOpacity] = useState(1);

  // Fade out after inactivity
  useEffect(() => {
    const now = Date.now();
    const timeSinceUpdate = now - lastUpdate;

    if (timeSinceUpdate >= INACTIVITY_FADE_MS) {
      setOpacity(0.3);
    } else {
      setOpacity(1);

      // Schedule fade
      const fadeTimer = setTimeout(() => {
        setOpacity(0.3);
      }, INACTIVITY_FADE_MS - timeSinceUpdate);

      return () => clearTimeout(fadeTimer);
    }
  }, [lastUpdate]);

  // Truncate name to 10 characters
  const displayName = name.length > 10 ? `${name.substring(0, 10)}…` : name;

  return (
    <div
      className={cn(
        "absolute pointer-events-none z-[9999]",
        "transition-all duration-50 ease-out",
        className
      )}
      style={{
        left: x,
        top: y,
        opacity,
        transform: 'translate(-2px, -2px)',
      }}
      aria-hidden="true"
    >
      {/* Cursor arrow SVG */}
      <svg
        width="20"
        height="20"
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="drop-shadow-md"
      >
        {/* Cursor arrow shape */}
        <path
          d="M5.5 3.21V20.8C5.5 21.51 6.28 21.93 6.87 21.54L10.71 18.87L13.02 23.8C13.22 24.26 13.78 24.46 14.24 24.26L16.47 23.27C16.93 23.07 17.13 22.51 16.93 22.05L14.62 17.12L19.28 16.42C19.97 16.32 20.28 15.5 19.81 15L6.76 2.72C6.3 2.3 5.5 2.58 5.5 3.21Z"
          fill={color}
          stroke="white"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>

      {/* Name label */}
      <div
        className={cn(
          "absolute left-4 top-4",
          "px-2 py-0.5 rounded-md text-xs font-medium",
          "whitespace-nowrap shadow-md",
          "border border-white/20"
        )}
        style={{
          backgroundColor: color,
          color: getContrastColor(color),
        }}
      >
        {displayName}
      </div>
    </div>
  );
}

/**
 * Determine if text should be white or black based on background color
 */
function getContrastColor(hexColor: string): string {
  // Remove # if present
  const hex = hexColor.replace('#', '');

  // Parse RGB values
  const r = parseInt(hex.substring(0, 2), 16);
  const g = parseInt(hex.substring(2, 4), 16);
  const b = parseInt(hex.substring(4, 6), 16);

  // Calculate relative luminance
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;

  // Return white for dark backgrounds, black for light
  return luminance > 0.5 ? '#000000' : '#FFFFFF';
}

// Memoize to prevent unnecessary re-renders
export const Cursor = memo(CursorComponent);

export default Cursor;
