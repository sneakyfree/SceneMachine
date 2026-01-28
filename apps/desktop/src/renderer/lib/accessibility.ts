/**
 * Accessibility utilities for SceneMachine
 * Provides focus management and screen reader announcements
 */

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
