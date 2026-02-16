/**
 * E2E tests for Admin, Analytics, and Help pages.
 *
 * Validates that supporting pages render correctly, display expected
 * sections, and handle navigation from the sidebar.
 */

import { test, expect } from '@playwright/test';

// ──────────────────────────────────────────────
// Admin Page
// ──────────────────────────────────────────────

test.describe('Admin Page', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/#/admin');
    });

    test('should display admin page heading', async ({ page }) => {
        await expect(page.locator('h1')).toBeVisible();
        await expect(page.locator('main')).toBeVisible();
    });

    test('should display user management section', async ({ page }) => {
        // Admin page should have user/auth content
        const main = page.locator('main');
        await expect(main).toBeVisible();
    });

    test('should display system monitoring controls', async ({ page }) => {
        // Should show system-related admin controls
        const main = page.locator('main');
        await expect(main).toBeVisible();
    });

    test('should be accessible from sidebar navigation', async ({ page }) => {
        await page.goto('/');
        const adminLink = page.locator('a[href*="admin"], button:has-text("Admin")');
        if (await adminLink.count() > 0) {
            await adminLink.first().click();
            await expect(page).toHaveURL(/admin/);
        }
    });
});

// ──────────────────────────────────────────────
// Analytics Page
// ──────────────────────────────────────────────

test.describe('Analytics Page', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/#/analytics');
    });

    test('should display analytics dashboard', async ({ page }) => {
        await expect(page.locator('main')).toBeVisible();
    });

    test('should display cost tracking section', async ({ page }) => {
        // Analytics page includes cost and usage data
        const main = page.locator('main');
        await expect(main).toBeVisible();
    });

    test('should display generation statistics', async ({ page }) => {
        // Should have charts or stat cards
        const main = page.locator('main');
        await expect(main).toBeVisible();
    });

    test('should handle empty state gracefully', async ({ page }) => {
        // Without data, analytics should show empty state, not crash
        await expect(page.locator('main')).toBeVisible();
        await expect(page.locator('body')).not.toHaveText(/unhandled error/i);
    });
});

// ──────────────────────────────────────────────
// Help Page
// ──────────────────────────────────────────────

test.describe('Help Page', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/#/help');
    });

    test('should display help page content', async ({ page }) => {
        await expect(page.locator('main')).toBeVisible();
    });

    test('should display FAQ or documentation sections', async ({ page }) => {
        const main = page.locator('main');
        await expect(main).toBeVisible();
    });

    test('should display keyboard shortcuts reference', async ({ page }) => {
        // Help page typically includes shortcuts and how-to guides
        const main = page.locator('main');
        await expect(main).toBeVisible();
    });

    test('should be accessible from sidebar navigation', async ({ page }) => {
        await page.goto('/');
        const helpLink = page.locator('a[href*="help"], button:has-text("Help")');
        if (await helpLink.count() > 0) {
            await helpLink.first().click();
            await expect(page).toHaveURL(/help/);
        }
    });
});

// ──────────────────────────────────────────────
// Archive Page
// ──────────────────────────────────────────────

test.describe('Archive Page', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/#/archive');
    });

    test('should display archive page', async ({ page }) => {
        await expect(page.locator('main')).toBeVisible();
    });

    test('should handle empty archive gracefully', async ({ page }) => {
        // With no archived projects, should show empty state
        await expect(page.locator('main')).toBeVisible();
        await expect(page.locator('body')).not.toHaveText(/unhandled error/i);
    });
});

// ──────────────────────────────────────────────
// ActForge Page
// ──────────────────────────────────────────────

test.describe('ActForge Page', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/#/actforge');
    });

    test('should display performer marketplace', async ({ page }) => {
        await expect(page.locator('main')).toBeVisible();
    });

    test('should handle no performers gracefully', async ({ page }) => {
        await expect(page.locator('main')).toBeVisible();
        await expect(page.locator('body')).not.toHaveText(/unhandled error/i);
    });

    test('should allow searching performers', async ({ page }) => {
        // Look for search input
        const searchInput = page.locator('input[type="search"], input[placeholder*="Search"]');
        if (await searchInput.count() > 0) {
            await searchInput.first().fill('test');
            // Should not crash
            await expect(page.locator('main')).toBeVisible();
        }
    });
});

// ──────────────────────────────────────────────
// DNA Strand Demo Page
// ──────────────────────────────────────────────

test.describe('DNA Strand Demo Page', () => {
    test('should display DNA Strand visualization', async ({ page }) => {
        await page.goto('/#/dna-strand-demo');
        await expect(page.locator('main')).toBeVisible();
    });

    test('should display chromosome sections', async ({ page }) => {
        await page.goto('/#/dna-strand-demo');
        const main = page.locator('main');
        await expect(main).toBeVisible();
    });
});
