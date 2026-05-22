/**
 * Optimized Image Component
 *
 * Provides lazy loading, placeholder support, and progressive loading
 * for images with performance optimizations.
 */

import { memo, useState, useEffect, useRef } from 'react';
import { cn } from '../lib/utils';
import { Skeleton } from './skeleton';

// =============================================================================
// Types
// =============================================================================

interface OptimizedImageProps {
  /**
   * Image source URL
   */
  src: string;

  /**
   * Alt text for accessibility
   */
  alt: string;

  /**
   * Optional placeholder image (low-res or blur)
   */
  placeholder?: string;

  /**
   * Optional fallback image on error
   */
  fallback?: string;

  /**
   * Width of the image
   */
  width?: number | string;

  /**
   * Height of the image
   */
  height?: number | string;

  /**
   * Aspect ratio (e.g., "16/9", "4/3", "1/1")
   */
  aspectRatio?: string;

  /**
   * Whether to lazy load the image
   */
  lazy?: boolean;

  /**
   * Root margin for intersection observer
   */
  rootMargin?: string;

  /**
   * Object fit mode
   */
  objectFit?: 'contain' | 'cover' | 'fill' | 'none' | 'scale-down';

  /**
   * Object position
   */
  objectPosition?: string;

  /**
   * Called when image loads successfully
   */
  onLoad?: () => void;

  /**
   * Called when image fails to load
   */
  onError?: (error: Error) => void;

  /**
   * Additional CSS classes
   */
  className?: string;

  /**
   * Container CSS classes
   */
  containerClassName?: string;
}

// =============================================================================
// Component
// =============================================================================

/**
 * Performance-optimized image component with lazy loading and placeholders.
 */
export const OptimizedImage = memo(function OptimizedImage({
  src,
  alt,
  placeholder,
  fallback,
  width,
  height,
  aspectRatio,
  lazy = true,
  rootMargin = '200px',
  objectFit = 'cover',
  objectPosition = 'center',
  onLoad,
  onError,
  className,
  containerClassName,
}: OptimizedImageProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isInView, setIsInView] = useState(!lazy);
  const [isLoaded, setIsLoaded] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [currentSrc, setCurrentSrc] = useState<string>(placeholder || '');

  // Intersection Observer for lazy loading
  useEffect(() => {
    if (!lazy) return;

    const element = containerRef.current;
    if (!element) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setIsInView(true);
            observer.unobserve(element);
          }
        });
      },
      { rootMargin }
    );

    observer.observe(element);

    return () => {
      observer.disconnect();
    };
  }, [lazy, rootMargin]);

  // Load the main image when in view
  useEffect(() => {
    if (!isInView || !src || hasError) return;

    const img = new Image();
    img.src = src;

    img.onload = () => {
      setCurrentSrc(src);
      setIsLoaded(true);
      onLoad?.();
    };

    img.onerror = () => {
      setHasError(true);
      if (fallback) {
        setCurrentSrc(fallback);
      }
      onError?.(new Error(`Failed to load image: ${src}`));
    };

    return () => {
      img.onload = null;
      img.onerror = null;
    };
  }, [isInView, src, fallback, hasError, onLoad, onError]);

  // Compute container styles
  const containerStyle: React.CSSProperties = {
    position: 'relative',
    overflow: 'hidden',
  };

  if (aspectRatio) {
    containerStyle.aspectRatio = aspectRatio;
  }

  if (width) {
    containerStyle.width = typeof width === 'number' ? `${width}px` : width;
  }

  if (height) {
    containerStyle.height = typeof height === 'number' ? `${height}px` : height;
  }

  // Compute image styles
  const imageStyle: React.CSSProperties = {
    objectFit,
    objectPosition,
    width: '100%',
    height: '100%',
    transition: 'opacity 0.3s ease, filter 0.3s ease',
  };

  return (
    <div
      ref={containerRef}
      className={cn('bg-surface-800 rounded-lg', containerClassName)}
      style={containerStyle}
    >
      {/* Skeleton placeholder */}
      {!isLoaded && !currentSrc && <Skeleton className="absolute inset-0 rounded-none" />}

      {/* Blur placeholder */}
      {placeholder && !isLoaded && currentSrc === placeholder && (
        <img
          src={placeholder}
          alt=""
          aria-hidden="true"
          className={cn('absolute inset-0', className)}
          style={{
            ...imageStyle,
            filter: 'blur(10px)',
            transform: 'scale(1.1)',
          }}
        />
      )}

      {/* Main image */}
      {currentSrc && currentSrc !== placeholder && (
        <img
          src={currentSrc}
          alt={alt}
          className={className}
          style={{
            ...imageStyle,
            opacity: isLoaded ? 1 : 0,
          }}
          loading={lazy ? 'lazy' : 'eager'}
          decoding="async"
        />
      )}

      {/* Error state */}
      {hasError && !fallback && (
        <div className="absolute inset-0 flex items-center justify-center bg-surface-800">
          <div className="text-center p-4">
            <div className="w-12 h-12 mx-auto mb-2 rounded-full bg-surface-700 flex items-center justify-center">
              <svg
                className="w-6 h-6 text-surface-500"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                />
              </svg>
            </div>
            <p className="text-xs text-surface-500">Failed to load</p>
          </div>
        </div>
      )}
    </div>
  );
});

// =============================================================================
// Image Gallery Component
// =============================================================================

interface ImageGalleryProps {
  /**
   * Array of image sources
   */
  images: Array<{
    src: string;
    alt: string;
    placeholder?: string;
  }>;

  /**
   * Number of columns
   */
  columns?: 2 | 3 | 4;

  /**
   * Gap between images
   */
  gap?: 'sm' | 'md' | 'lg';

  /**
   * Aspect ratio for all images
   */
  aspectRatio?: string;

  /**
   * Called when an image is clicked
   */
  onImageClick?: (index: number) => void;

  /**
   * Additional CSS classes
   */
  className?: string;
}

/**
 * Performance-optimized image gallery with lazy loading.
 */
export const ImageGallery = memo(function ImageGallery({
  images,
  columns = 3,
  gap = 'md',
  aspectRatio = '16/9',
  onImageClick,
  className,
}: ImageGalleryProps) {
  const columnClasses = {
    2: 'grid-cols-2',
    3: 'grid-cols-3',
    4: 'grid-cols-4',
  };

  const gapClasses = {
    sm: 'gap-2',
    md: 'gap-4',
    lg: 'gap-6',
  };

  return (
    <div className={cn('grid', columnClasses[columns], gapClasses[gap], className)}>
      {images.map((image, index) => (
        <button
          key={`${image.src}-${index}`}
          onClick={() => onImageClick?.(index)}
          className={cn(
            'focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2',
            'focus:ring-offset-surface-900 rounded-lg',
            onImageClick && 'cursor-pointer hover:opacity-90 transition-opacity'
          )}
          disabled={!onImageClick}
          type="button"
        >
          <OptimizedImage
            src={image.src}
            alt={image.alt}
            placeholder={image.placeholder}
            aspectRatio={aspectRatio}
            containerClassName="rounded-lg"
          />
        </button>
      ))}
    </div>
  );
});

// =============================================================================
// Avatar Image Component
// =============================================================================

interface AvatarImageProps {
  /**
   * Image source URL
   */
  src?: string;

  /**
   * Alt text / name for fallback
   */
  name: string;

  /**
   * Size of the avatar
   */
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';

  /**
   * Additional CSS classes
   */
  className?: string;
}

/**
 * Optimized avatar image with initials fallback.
 */
export const AvatarImage = memo(function AvatarImage({
  src,
  name,
  size = 'md',
  className,
}: AvatarImageProps) {
  const [hasError, setHasError] = useState(false);

  const sizeClasses = {
    xs: 'w-6 h-6 text-xs',
    sm: 'w-8 h-8 text-sm',
    md: 'w-10 h-10 text-sm',
    lg: 'w-12 h-12 text-base',
    xl: 'w-16 h-16 text-lg',
  };

  // Generate initials from name
  const initials = name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);

  // Generate a consistent color based on the name
  const colorIndex = name.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0) % 8;
  const colors = [
    'bg-red-500',
    'bg-orange-500',
    'bg-yellow-500',
    'bg-green-500',
    'bg-teal-500',
    'bg-blue-500',
    'bg-indigo-500',
    'bg-purple-500',
  ];

  if (!src || hasError) {
    return (
      <div
        className={cn(
          'flex items-center justify-center rounded-full font-medium text-white',
          sizeClasses[size],
          colors[colorIndex],
          className
        )}
        role="img"
        aria-label={name}
      >
        {initials}
      </div>
    );
  }

  return (
    <div
      className={cn('rounded-full overflow-hidden bg-surface-800', sizeClasses[size], className)}
    >
      <img
        src={src}
        alt={name}
        className="w-full h-full object-cover"
        onError={() => setHasError(true)}
        loading="lazy"
        decoding="async"
      />
    </div>
  );
});

export default OptimizedImage;
