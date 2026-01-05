/**
 * Avatar Component
 *
 * User avatar with fallback to initials.
 */

import React from 'react';
import clsx from 'clsx';

export interface AvatarProps {
  src?: string | null;
  alt?: string;
  name?: string;
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
  onClick?: () => void;
}

function getInitials(name?: string): string {
  if (!name) return '?';
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) {
    return parts[0].charAt(0).toUpperCase();
  }
  return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
}

function getColorFromName(name?: string): string {
  if (!name) return 'hsl(260, 70%, 50%)';
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  const hue = hash % 360;
  return `hsl(${hue}, 70%, 50%)`;
}

export function Avatar({
  src,
  alt,
  name,
  size = 'md',
  className,
  onClick,
}: AvatarProps) {
  const [imageError, setImageError] = React.useState(false);
  const showImage = src && !imageError;
  const initials = getInitials(name);
  const bgColor = getColorFromName(name);

  return (
    <>
      <div
        className={clsx('avatar', `avatar-${size}`, className)}
        onClick={onClick}
        role={onClick ? 'button' : undefined}
        tabIndex={onClick ? 0 : undefined}
        style={{ backgroundColor: !showImage ? bgColor : undefined }}
      >
        {showImage ? (
          <img
            src={src}
            alt={alt || name || 'Avatar'}
            className="avatar-image"
            onError={() => setImageError(true)}
          />
        ) : (
          <span className="avatar-initials">{initials}</span>
        )}
      </div>

      <style jsx>{`
        .avatar {
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: 50%;
          overflow: hidden;
          flex-shrink: 0;
          user-select: none;
        }

        .avatar[role='button'] {
          cursor: pointer;
          transition: opacity var(--transition-fast);
        }

        .avatar[role='button']:hover {
          opacity: 0.8;
        }

        .avatar-image {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }

        .avatar-initials {
          color: white;
          font-weight: 600;
          text-transform: uppercase;
        }

        /* Sizes */
        .avatar-xs {
          width: 1.5rem;
          height: 1.5rem;
          font-size: 0.625rem;
        }

        .avatar-sm {
          width: 2rem;
          height: 2rem;
          font-size: 0.75rem;
        }

        .avatar-md {
          width: 2.5rem;
          height: 2.5rem;
          font-size: 1rem;
        }

        .avatar-lg {
          width: 3.5rem;
          height: 3.5rem;
          font-size: 1.25rem;
        }

        .avatar-xl {
          width: 5rem;
          height: 5rem;
          font-size: 1.75rem;
        }
      `}</style>
    </>
  );
}

export default Avatar;
