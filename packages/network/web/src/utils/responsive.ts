/**
 * Responsive design utilities for SceneMachine Network.
 *
 * Mobile-first approach with breakpoints optimized for video viewing.
 */

/**
 * Breakpoint definitions (mobile-first)
 */
export const breakpoints = {
  xs: 0,      // Mobile portrait
  sm: 480,    // Mobile landscape
  md: 768,    // Tablet portrait
  lg: 1024,   // Tablet landscape / Small desktop
  xl: 1280,   // Desktop
  '2xl': 1536 // Large desktop
} as const;

export type Breakpoint = keyof typeof breakpoints;

/**
 * Media query strings for CSS-in-JS
 */
export const mediaQueries = {
  xs: `@media (min-width: ${breakpoints.xs}px)`,
  sm: `@media (min-width: ${breakpoints.sm}px)`,
  md: `@media (min-width: ${breakpoints.md}px)`,
  lg: `@media (min-width: ${breakpoints.lg}px)`,
  xl: `@media (min-width: ${breakpoints.xl}px)`,
  '2xl': `@media (min-width: ${breakpoints['2xl']}px)`,
  // Special queries
  touch: '@media (hover: none) and (pointer: coarse)',
  mouse: '@media (hover: hover) and (pointer: fine)',
  reducedMotion: '@media (prefers-reduced-motion: reduce)',
  darkMode: '@media (prefers-color-scheme: dark)',
  landscape: '@media (orientation: landscape)',
  portrait: '@media (orientation: portrait)',
} as const;

/**
 * Check if current viewport matches a breakpoint
 */
export function matchesBreakpoint(breakpoint: Breakpoint): boolean {
  if (typeof window === 'undefined') return false;
  return window.matchMedia(`(min-width: ${breakpoints[breakpoint]}px)`).matches;
}

/**
 * Get current breakpoint
 */
export function getCurrentBreakpoint(): Breakpoint {
  if (typeof window === 'undefined') return 'xs';

  const width = window.innerWidth;

  if (width >= breakpoints['2xl']) return '2xl';
  if (width >= breakpoints.xl) return 'xl';
  if (width >= breakpoints.lg) return 'lg';
  if (width >= breakpoints.md) return 'md';
  if (width >= breakpoints.sm) return 'sm';
  return 'xs';
}

/**
 * Check if device has touch capability
 */
export function isTouchDevice(): boolean {
  if (typeof window === 'undefined') return false;
  return (
    'ontouchstart' in window ||
    navigator.maxTouchPoints > 0 ||
    window.matchMedia('(hover: none) and (pointer: coarse)').matches
  );
}

/**
 * Check if device prefers reduced motion
 */
export function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined') return false;
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/**
 * Check if device is in landscape orientation
 */
export function isLandscape(): boolean {
  if (typeof window === 'undefined') return false;
  return window.matchMedia('(orientation: landscape)').matches;
}

/**
 * Check if device is mobile (touch + small screen)
 */
export function isMobile(): boolean {
  return isTouchDevice() && !matchesBreakpoint('md');
}

/**
 * Check if device is tablet
 */
export function isTablet(): boolean {
  return isTouchDevice() && matchesBreakpoint('md') && !matchesBreakpoint('lg');
}

/**
 * Check if device is desktop
 */
export function isDesktop(): boolean {
  return !isTouchDevice() || matchesBreakpoint('lg');
}

/**
 * Container max-widths for different breakpoints
 */
export const containerMaxWidths = {
  xs: '100%',
  sm: '100%',
  md: '720px',
  lg: '960px',
  xl: '1140px',
  '2xl': '1320px',
} as const;

/**
 * Video player aspect ratios
 */
export const aspectRatios = {
  '16:9': 16 / 9,
  '4:3': 4 / 3,
  '21:9': 21 / 9,
  '1:1': 1,
  '9:16': 9 / 16, // Vertical video
} as const;

/**
 * Calculate video player height for a given width and aspect ratio
 */
export function getVideoHeight(
  width: number,
  ratio: keyof typeof aspectRatios = '16:9'
): number {
  return width / aspectRatios[ratio];
}

/**
 * Calculate optimal video quality based on viewport and connection
 */
export function getOptimalVideoQuality(): '360p' | '480p' | '720p' | '1080p' | '4k' {
  if (typeof window === 'undefined') return '720p';

  const width = window.innerWidth;
  const dpr = window.devicePixelRatio || 1;
  const effectiveWidth = width * dpr;

  // Check connection speed if available
  const connection = (navigator as any).connection;
  const isSlowConnection = connection && (
    connection.effectiveType === 'slow-2g' ||
    connection.effectiveType === '2g' ||
    connection.saveData
  );

  if (isSlowConnection) {
    return effectiveWidth > 720 ? '480p' : '360p';
  }

  if (effectiveWidth >= 3840) return '4k';
  if (effectiveWidth >= 1920) return '1080p';
  if (effectiveWidth >= 1280) return '720p';
  if (effectiveWidth >= 720) return '480p';
  return '360p';
}

/**
 * Safe area insets for notched devices
 */
export function getSafeAreaInsets(): {
  top: number;
  right: number;
  bottom: number;
  left: number;
} {
  if (typeof window === 'undefined' || !CSS.supports('padding-top: env(safe-area-inset-top)')) {
    return { top: 0, right: 0, bottom: 0, left: 0 };
  }

  const style = getComputedStyle(document.documentElement);
  return {
    top: parseInt(style.getPropertyValue('--sat') || '0', 10),
    right: parseInt(style.getPropertyValue('--sar') || '0', 10),
    bottom: parseInt(style.getPropertyValue('--sab') || '0', 10),
    left: parseInt(style.getPropertyValue('--sal') || '0', 10),
  };
}

/**
 * CSS custom properties for safe area insets
 * Add to :root in global CSS
 */
export const safeAreaCSSVars = `
  :root {
    --sat: env(safe-area-inset-top);
    --sar: env(safe-area-inset-right);
    --sab: env(safe-area-inset-bottom);
    --sal: env(safe-area-inset-left);
  }
`;
