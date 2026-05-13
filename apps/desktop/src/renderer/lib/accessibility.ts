/**
 * Accessibility utilities for SceneMachine
 * Provides focus management and screen reader announcements
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import type React from 'react';

let announcerElement: HTMLDivElement | null = null;

/**
 * Initialize the screen reader announcer element (live region)
 */
export function initializeAnnouncer(): void {
    if (announcerElement) return;

    announcerElement = document.createElement('div');
    announcerElement.setAttribute('role', 'status');
    announcerElement.setAttribute('aria-live', 'polite');
    announcerElement.setAttribute('aria-atomic', 'true');
    announcerElement.className = 'sr-only';
    announcerElement.id = 'a11y-announcer';
    document.body.appendChild(announcerElement);
}

/**
 * Announce a message to screen readers
 */
export function announce(message: string, priority: 'polite' | 'assertive' = 'polite'): void {
    if (!announcerElement) {
        initializeAnnouncer();
    }

    if (announcerElement) {
        announcerElement.setAttribute('aria-live', priority);
        // Clear and set to trigger announcement
        announcerElement.textContent = '';
        requestAnimationFrame(() => {
            if (announcerElement) {
                announcerElement.textContent = message;
            }
        });
    }
}

/**
 * Initialize focus-visible polyfill behavior
 * Adds 'focus-visible' class when focus is from keyboard navigation
 */
export function initializeFocusVisible(): void {
    let hadKeyboardEvent = false;

    // Track keyboard events
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Tab' || e.key === 'Escape' || e.key === 'Enter' || e.key === ' ') {
            hadKeyboardEvent = true;
        }
    });

    // Reset on mouse/touch
    document.addEventListener('mousedown', () => {
        hadKeyboardEvent = false;
    });

    document.addEventListener('touchstart', () => {
        hadKeyboardEvent = false;
    });

    // Apply focus-visible class based on input method
    document.addEventListener('focusin', (e) => {
        const target = e.target as HTMLElement;
        if (hadKeyboardEvent) {
            target.classList.add('focus-visible');
            document.body.classList.add('keyboard-navigation');
        }
    });

    document.addEventListener('focusout', (e) => {
        const target = e.target as HTMLElement;
        target.classList.remove('focus-visible');
        document.body.classList.remove('keyboard-navigation');
    });
}

// ============================================================================
// React hooks + components
// Used by components/accessible-modal.tsx and components/skip-links.tsx
// ============================================================================

/**
 * Definition for a single skip-link entry. A "skip link" is an
 * accessibility shortcut that lets keyboard users jump directly to
 * a major landmark in the page (e.g. main content, primary nav).
 */
export interface SkipLink {
    id: string;
    label: string;
    targetId: string;
}

const DEFAULT_SKIP_LINKS: SkipLink[] = [
    { id: 'skip-main', label: 'Skip to main content', targetId: 'main-content' },
    { id: 'skip-nav', label: 'Skip to navigation', targetId: 'primary-nav' },
];

/**
 * Returns the active skip-links + a click/keydown handler that focuses
 * the corresponding landmark. Renderer calls this from <SkipLinks/>.
 */
export function useSkipLinks(custom?: SkipLink[]): {
    links: SkipLink[];
    handleSkipClick: (
        targetId: string,
        event: React.MouseEvent | React.KeyboardEvent,
    ) => void;
} {
    const links = custom && custom.length > 0 ? custom : DEFAULT_SKIP_LINKS;
    const handleSkipClick = useCallback(
        (targetId: string, event: React.MouseEvent | React.KeyboardEvent) => {
            event.preventDefault();
            const target = document.getElementById(targetId);
            if (!target) return;
            // tabIndex = -1 so the element can receive programmatic focus.
            if (!target.hasAttribute('tabindex')) {
                target.setAttribute('tabindex', '-1');
            }
            target.focus({ preventScroll: false });
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        },
        [],
    );
    return { links, handleSkipClick };
}

/**
 * React hook variant of createFocusTrap. Returns a ref that the caller
 * attaches to the modal/dialog container; when `active` is true, focus
 * is trapped within that container.
 */
export function useFocusTrap<T extends HTMLElement = HTMLElement>(options: {
    active: boolean;
    returnFocusOnDeactivate?: boolean;
}): React.RefObject<T> {
    const containerRef = useRef<T>(null);
    useEffect(() => {
        if (!options.active || !containerRef.current) return;
        const trap = createFocusTrap(containerRef.current);
        trap.activate();
        return () => {
            trap.deactivate();
        };
    }, [options.active]);
    return containerRef;
}

/**
 * React hook reporting whether the user has opted in to reduced motion
 * via the OS/browser. Components should disable animation when this
 * returns true.
 */
export function usePrefersReducedMotion(): boolean {
    const [reduced, setReduced] = useState<boolean>(() => {
        if (typeof window === 'undefined' || !window.matchMedia) return false;
        return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    });
    useEffect(() => {
        if (typeof window === 'undefined' || !window.matchMedia) return;
        const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
        const handler = (e: MediaQueryListEvent) => setReduced(e.matches);
        mq.addEventListener('change', handler);
        return () => mq.removeEventListener('change', handler);
    }, []);
    return reduced;
}

/**
 * Build the ARIA attribute object for a dialog/modal element. Spread the
 * return value onto the dialog root: `<div {...ariaDialog({ labelledBy })}>`.
 */
export function ariaDialog(options: {
    labelledBy?: string;
    describedBy?: string;
} = {}): Record<string, string> {
    const attrs: Record<string, string> = {
        role: 'dialog',
        'aria-modal': 'true',
    };
    if (options.labelledBy) attrs['aria-labelledby'] = options.labelledBy;
    if (options.describedBy) attrs['aria-describedby'] = options.describedBy;
    return attrs;
}

/**
 * Focus trap utility for modals and dialogs
 */
export function createFocusTrap(container: HTMLElement): {
    activate: () => void;
    deactivate: () => void;
} {
    const focusableSelectors = [
        'button:not([disabled])',
        'input:not([disabled])',
        'select:not([disabled])',
        'textarea:not([disabled])',
        'a[href]',
        '[tabindex]:not([tabindex="-1"])',
    ].join(', ');

    let previousActiveElement: Element | null = null;

    function getFocusableElements(): HTMLElement[] {
        return Array.from(container.querySelectorAll(focusableSelectors));
    }

    function handleKeyDown(e: KeyboardEvent): void {
        if (e.key !== 'Tab') return;

        const focusableElements = getFocusableElements();
        if (focusableElements.length === 0) return;

        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        if (e.shiftKey && document.activeElement === firstElement) {
            e.preventDefault();
            lastElement.focus();
        } else if (!e.shiftKey && document.activeElement === lastElement) {
            e.preventDefault();
            firstElement.focus();
        }
    }

    return {
        activate() {
            previousActiveElement = document.activeElement;
            container.addEventListener('keydown', handleKeyDown);

            // Focus first focusable element
            const focusableElements = getFocusableElements();
            if (focusableElements.length > 0) {
                focusableElements[0].focus();
            }
        },
        deactivate() {
            container.removeEventListener('keydown', handleKeyDown);

            // Restore previous focus
            if (previousActiveElement instanceof HTMLElement) {
                previousActiveElement.focus();
            }
        },
    };
}
