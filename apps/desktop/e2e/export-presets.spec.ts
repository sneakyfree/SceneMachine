/**
 * E2E spec: Export Page — Platform Presets
 *
 * Tests the platform preset quick-select cards and their effect
 * on export settings.
 */

import { test, expect } from '@playwright/test';

// ──────────────────────────────────────────────
// Platform Preset Cards
// ──────────────────────────────────────────────

test.describe('Export Platform Presets', () => {
    test.beforeEach(async ({ page }) => {
        // Need a project context for the export page
        await page.goto('/project/test-project/export');
    });

    test('should display 6 platform preset cards', async ({ page }) => {
        const presets = page.locator('button:has-text("YouTube 4K"), button:has-text("YouTube HD"), button:has-text("Instagram"), button:has-text("TikTok"), button:has-text("Vimeo"), button:has-text("Archive")');
        await expect(presets).toHaveCount(6);
    });

    test('should select YouTube 4K preset', async ({ page }) => {
        await page.click('button:has-text("YouTube 4K")');
        // Verify the card gets the active styling
        const card = page.locator('button:has-text("YouTube 4K")');
        await expect(card).toHaveClass(/border-brand-500/);
    });

    test('should select Instagram Reels preset', async ({ page }) => {
        await page.click('button:has-text("Instagram")');
        const card = page.locator('button:has-text("Instagram")');
        await expect(card).toHaveClass(/border-brand-500/);
    });

    test('should select Archive preset', async ({ page }) => {
        await page.click('button:has-text("Archive")');
        const card = page.locator('button:has-text("Archive")');
        await expect(card).toHaveClass(/border-brand-500/);
    });

    test('preset selection should update format dropdown', async ({ page }) => {
        // Click YouTube 4K (mp4_h264, 3840x2160)
        await page.click('button:has-text("YouTube 4K")');

        // The format select should now show MP4 (H.264)
        const formatSelect = page.locator('select').first();
        await expect(formatSelect).toHaveValue('mp4_h264');
    });

    test('switching presets should change the active card', async ({ page }) => {
        await page.click('button:has-text("YouTube 4K")');
        let activeCard = page.locator('button:has-text("YouTube 4K")');
        await expect(activeCard).toHaveClass(/border-brand-500/);

        await page.click('button:has-text("TikTok")');
        activeCard = page.locator('button:has-text("TikTok")');
        await expect(activeCard).toHaveClass(/border-brand-500/);

        // YouTube 4K should no longer be active
        const oldCard = page.locator('button:has-text("YouTube 4K")');
        await expect(oldCard).not.toHaveClass(/border-brand-500/);
    });
});

// ──────────────────────────────────────────────
// Export History
// ──────────────────────────────────────────────

test.describe('Export History', () => {
    test('should display export history section', async ({ page }) => {
        await page.goto('/project/test-project/export');
        await expect(page.locator('text=Export History')).toBeVisible();
    });
});
