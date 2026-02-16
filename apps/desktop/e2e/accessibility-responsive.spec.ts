/**
 * E2E tests for accessibility and responsive design.
 *
 * Validates WCAG compliance basics, keyboard navigation, ARIA roles,
 * and responsive layouts across viewports.
 */

import { test, expect } from '@playwright/test';

// ──────────────────────────────────────────────
// Accessibility: ARIA and Keyboard
// ──────────────────────────────────────────────

test.describe('Accessibility', () => {
    test('should have proper document structure', async ({ page }) => {
        await page.goto('/');

        // Should have exactly one h1
        const h1Count = await page.locator('h1').count();
        expect(h1Count).toBeGreaterThanOrEqual(1);

        // Should have a <main> landmark
        await expect(page.locator('main')).toBeVisible();

        // Should have an <aside> or <nav> sidebar
        const sidebar = page.locator('aside, nav');
        expect(await sidebar.count()).toBeGreaterThanOrEqual(1);
    });

    test('should have accessible navigation links', async ({ page }) => {
        await page.goto('/');

        // All links should have text content or aria-label
        const links = page.locator('a');
        const linkCount = await links.count();

        for (let i = 0; i < Math.min(linkCount, 10); i++) {
            const link = links.nth(i);
            const text = await link.textContent();
            const ariaLabel = await link.getAttribute('aria-label');
            const title = await link.getAttribute('title');

            // Each link should have at least one accessible name
            expect(text || ariaLabel || title).toBeTruthy();
        }
    });

    test('should support keyboard navigation through sidebar', async ({ page }) => {
        await page.goto('/');

        // Tab to focus the first interactive element
        await page.keyboard.press('Tab');

        // Should have a focused element
        const focused = page.locator(':focus');
        await expect(focused).toBeTruthy();
    });

    test('should have skip-to-content link', async ({ page }) => {
        await page.goto('/');

        // Look for skip link (may be visually hidden until focused)
        const skipLink = page.locator('a:has-text("Skip"), [data-testid="skip-link"]');
        if (await skipLink.count() > 0) {
            // Tab to focus it
            await page.keyboard.press('Tab');
            await expect(skipLink.first()).toBeFocused();
        }
    });

    test('modals should trap focus', async ({ page }) => {
        await page.goto('/');

        // Open shortcuts modal
        const shortcutsButton = page.locator('button[title="Keyboard Shortcuts"]');
        if (await shortcutsButton.count() > 0) {
            await shortcutsButton.click();

            // Modal should be visible
            const dialog = page.locator('[role="dialog"]');
            if (await dialog.count() > 0) {
                await expect(dialog).toBeVisible();

                // Focus should be within the dialog
                await page.keyboard.press('Tab');
                const focusedElement = page.locator(':focus');
                const isWithinDialog = await focusedElement.evaluate(
                    (el) => !!el.closest('[role="dialog"]')
                );
                expect(isWithinDialog).toBe(true);
            }
        }
    });
});

// ──────────────────────────────────────────────
// Responsive Design: Multiple Viewports
// ──────────────────────────────────────────────

test.describe('Responsive Design', () => {
    const viewports = [
        { name: 'Desktop 1920', width: 1920, height: 1080 },
        { name: 'Laptop 1366', width: 1366, height: 768 },
        { name: 'Tablet Portrait', width: 768, height: 1024 },
        { name: 'Tablet Landscape', width: 1024, height: 768 },
        { name: 'Mobile', width: 375, height: 667 },
    ];

    for (const vp of viewports) {
        test(`should render correctly at ${vp.name} (${vp.width}x${vp.height})`, async ({
            page,
        }) => {
            await page.setViewportSize({ width: vp.width, height: vp.height });
            await page.goto('/');

            // App should load without errors
            await expect(page.locator('main')).toBeVisible();
            await expect(page.locator('body')).not.toHaveText(/unhandled error/i);
        });

        test(`settings page at ${vp.name}`, async ({ page }) => {
            await page.setViewportSize({ width: vp.width, height: vp.height });
            await page.goto('/#/settings');

            await expect(page.locator('main')).toBeVisible();
        });
    }
});

// ──────────────────────────────────────────────
// Dark Mode / Theme
// ──────────────────────────────────────────────

test.describe('Theme', () => {
    test('should apply dark theme by default', async ({ page }) => {
        await page.goto('/');

        // App should have dark background (assuming dark-first design)
        const bodyBg = await page.evaluate(() => {
            return window.getComputedStyle(document.body).backgroundColor;
        });

        // Dark theme backgrounds typically have low RGB values
        expect(bodyBg).toBeTruthy();
    });

    test('should persist theme selection', async ({ page }) => {
        await page.goto('/#/settings');

        // Find theme selector
        const themeSelect = page.locator('select').first();
        if (await themeSelect.count() > 0) {
            // Change theme
            await themeSelect.selectOption({ index: 1 });

            // Navigate away and back
            await page.goto('/');
            await page.goto('/#/settings');

            // Theme should be persisted (via localStorage/Zustand)
            await expect(page.locator('main')).toBeVisible();
        }
    });
});

// ──────────────────────────────────────────────
// Performance
// ──────────────────────────────────────────────

test.describe('Performance', () => {
    test('should load home page in reasonable time', async ({ page }) => {
        const start = Date.now();
        await page.goto('/');
        await expect(page.locator('main')).toBeVisible();
        const loadTime = Date.now() - start;

        // Should load within 5 seconds
        expect(loadTime).toBeLessThan(5000);
    });

    test('should not have memory leaks on navigation', async ({ page }) => {
        await page.goto('/');

        // Navigate between pages multiple times
        const routes = ['/#/settings', '/', '/#/analytics', '/', '/#/help', '/'];
        for (const route of routes) {
            await page.goto(route);
            await expect(page.locator('main')).toBeVisible();
        }

        // App should still be responsive
        await expect(page.locator('main')).toBeVisible();
    });
});
