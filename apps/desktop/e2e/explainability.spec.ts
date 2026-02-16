/**
 * E2E spec: Explainability Dashboard
 *
 * Tests navigation, tab switching, data rendering, and snapshot comparison
 * for the 4-layer explainability page.
 */

import { test, expect } from '@playwright/test';

// ──────────────────────────────────────────────
// Navigation
// ──────────────────────────────────────────────

test.describe('Explainability Page Navigation', () => {
    test('should navigate to explainability page from sidebar', async ({ page }) => {
        await page.goto('/');
        await page.click('a[href="/explainability"]');
        await expect(page).toHaveURL(/explainability/);
        await expect(page.locator('text=Explainability Dashboard')).toBeVisible();
    });

    test('should navigate to project-scoped explainability', async ({ page }) => {
        await page.goto('/project/test-project/explainability');
        await expect(page.locator('text=Explainability Dashboard')).toBeVisible();
    });
});

// ──────────────────────────────────────────────
// Tab Switching
// ──────────────────────────────────────────────

test.describe('Explainability Tabs', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/explainability');
    });

    test('should display all 4 tabs', async ({ page }) => {
        await expect(page.locator('button:has-text("Client")')).toBeVisible();
        await expect(page.locator('button:has-text("Operator")')).toBeVisible();
        await expect(page.locator('button:has-text("Technical")')).toBeVisible();
        await expect(page.locator('button:has-text("Audit")')).toBeVisible();
    });

    test('should default to Client tab', async ({ page }) => {
        await expect(page.locator('text=Project Summary')).toBeVisible();
    });

    test('should switch to Operator tab', async ({ page }) => {
        await page.click('button:has-text("Operator")');
        await expect(page.locator('text=Shot Breakdown')).toBeVisible();
    });

    test('should switch to Technical tab', async ({ page }) => {
        await page.click('button:has-text("Technical")');
        await expect(page.locator('text=Agent Actions')).toBeVisible();
    });

    test('should switch to Audit tab', async ({ page }) => {
        await page.click('button:has-text("Audit")');
        await expect(page.locator('text=Immutable Snapshots')).toBeVisible();
    });
});

// ──────────────────────────────────────────────
// Client View
// ──────────────────────────────────────────────

test.describe('Client View', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/explainability');
    });

    test('should display project stats cards', async ({ page }) => {
        // There should be stat cards (Scenes, Shots, Characters, Cost)
        const cards = page.locator('[class*="rounded-lg"][class*="border"]');
        await expect(cards).toHaveCount({ minimum: 4 });
    });

    test('should show estimated completion', async ({ page }) => {
        await expect(page.locator('text=Estimated Completion')).toBeVisible();
    });
});

// ──────────────────────────────────────────────
// Audit View – Snapshot Comparison
// ──────────────────────────────────────────────

test.describe('Audit View Snapshots', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/explainability');
        await page.click('button:has-text("Audit")');
    });

    test('should display snapshot list', async ({ page }) => {
        await expect(page.locator('text=Immutable Snapshots')).toBeVisible();
    });

    test('should allow selecting two snapshots for comparison', async ({ page }) => {
        // Attempt to click two snapshot entries if available
        const snapshots = page.locator('[class*="snapshot"], button:has-text("Compare")');
        const count = await snapshots.count();

        if (count >= 2) {
            await snapshots.nth(0).click();
            await snapshots.nth(1).click();
            // Delta viewer should appear
            await expect(page.locator('text=Delta Comparison')).toBeVisible();
        }
    });
});
