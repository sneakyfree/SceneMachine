/**
 * Skip Links Component
 *
 * Provides keyboard navigation shortcuts to main content areas.
 * Essential for screen reader users and keyboard-only navigation.
 */

import { memo } from 'react';
import { useSkipLinks, SkipLink } from '../lib/accessibility';

// =============================================================================
// Types
// =============================================================================

interface SkipLinksProps {
  /**
   * Custom skip links (overrides defaults)
   */
  links?: SkipLink[];

  /**
   * Additional CSS classes
   */
  className?: string;
}

// =============================================================================
// Component
// =============================================================================

/**
 * Skip links for keyboard navigation.
 * Links are hidden until focused with Tab key.
 */
export const SkipLinks = memo(function SkipLinks({
  links: customLinks,
  className,
}: SkipLinksProps) {
  const { links, handleSkipClick } = useSkipLinks(customLinks);

  return (
    <nav className={`skip-links ${className || ''}`} aria-label="Skip navigation">
      {links.map((link, index) => (
        <a
          key={link.id}
          href={`#${link.targetId}`}
          className="skip-link"
          onClick={(e) => {
            e.preventDefault();
            handleSkipClick(link.targetId);
          }}
          style={{
            // Offset each link slightly
            left: index === 0 ? 0 : undefined,
          }}
        >
          {link.label}
        </a>
      ))}
    </nav>
  );
});

// =============================================================================
// Focus Target Component
// =============================================================================

interface FocusTargetProps {
  /**
   * The ID that skip links will target
   */
  id: string;

  /**
   * Element type to render
   */
  as?: 'main' | 'nav' | 'section' | 'div';

  /**
   * Children elements
   */
  children: React.ReactNode;

  /**
   * Additional CSS classes
   */
  className?: string;

  /**
   * ARIA label for the region
   */
  'aria-label'?: string;
}

/**
 * A focusable target for skip links.
 * Wraps content with proper tabindex for skip link navigation.
 */
export const FocusTarget = memo(function FocusTarget({
  id,
  as: Element = 'div',
  children,
  className,
  'aria-label': ariaLabel,
}: FocusTargetProps) {
  return (
    <Element
      id={id}
      className={className}
      tabIndex={-1}
      aria-label={ariaLabel}
      style={{ outline: 'none' }}
    >
      {children}
    </Element>
  );
});

export default SkipLinks;
