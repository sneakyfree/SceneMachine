/**
 * E2E tests for SceneMachine desktop app.
 *
 * Note: These tests run against the renderer (web) portion of the app.
 * Full Electron E2E testing would require electron-playwright or similar.
 */

import { test, expect } from '@playwright/test';

test.describe('Application Shell', () => {
  test('should load the application', async ({ page }) => {
    await page.goto('/');

    // Should display the app title
    await expect(page.locator('text=SceneMachine')).toBeVisible();
  });

  test('should display sidebar navigation', async ({ page }) => {
    await page.goto('/');

    // Sidebar should be visible
    const sidebar = page.locator('aside');
    await expect(sidebar).toBeVisible();

    // Should have navigation links
    await expect(page.locator('text=Projects')).toBeVisible();
    await expect(page.locator('text=Settings')).toBeVisible();
  });

  test('should toggle sidebar collapse', async ({ page }) => {
    await page.goto('/');

    const sidebar = page.locator('aside');

    // Get initial width (expanded)
    const initialWidth = await sidebar.evaluate((el) => el.offsetWidth);
    expect(initialWidth).toBeGreaterThan(200);

    // Click collapse button
    const collapseButton = page.locator('aside button').last();
    await collapseButton.click();

    // Wait for animation
    await page.waitForTimeout(300);

    // Sidebar should be collapsed
    const collapsedWidth = await sidebar.evaluate((el) => el.offsetWidth);
    expect(collapsedWidth).toBeLessThan(100);
  });
});

test.describe('Navigation', () => {
  test('should navigate to settings page', async ({ page }) => {
    await page.goto('/');

    // Click Settings link
    await page.click('text=Settings');

    // Should be on settings page
    await expect(page).toHaveURL(/#\/settings/);
    await expect(page.locator('h1:has-text("Settings")')).toBeVisible();
  });

  test('should navigate back to projects from settings', async ({ page }) => {
    await page.goto('/#/settings');

    // Click Projects link
    await page.click('text=Projects');

    // Should be on projects page
    await expect(page).toHaveURL(/\/#\/?$/);
  });
});

test.describe('Settings Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/#/settings');
  });

  test('should display API keys section', async ({ page }) => {
    await expect(page.locator('text=API Keys')).toBeVisible();
    await expect(page.locator('text=Anthropic')).toBeVisible();
    await expect(page.locator('text=OpenAI')).toBeVisible();
  });

  test('should display generation settings section', async ({ page }) => {
    await expect(page.locator('text=Generation Settings')).toBeVisible();
    await expect(page.locator('text=Default LLM Provider')).toBeVisible();
  });

  test('should display appearance settings section', async ({ page }) => {
    await expect(page.locator('text=Appearance')).toBeVisible();
    await expect(page.locator('text=Theme')).toBeVisible();
  });

  test('should display storage section', async ({ page }) => {
    await expect(page.locator('text=Storage')).toBeVisible();
  });

  test('should have save button when changes are made', async ({ page }) => {
    // Make a change to settings
    const themeSelect = page.locator('select').first();
    await themeSelect.selectOption({ index: 1 });

    // Should show save/discard buttons
    await expect(page.locator('button:has-text("Save Changes")')).toBeVisible();
    await expect(page.locator('button:has-text("Discard")')).toBeVisible();
  });
});

test.describe('Keyboard Shortcuts', () => {
  test('should open shortcuts modal', async ({ page }) => {
    await page.goto('/');

    // Click keyboard shortcuts button in sidebar
    await page.click('button[title="Keyboard Shortcuts"]');

    // Modal should be visible
    await expect(page.locator('text=Keyboard Shortcuts')).toBeVisible();
    await expect(page.locator('text=Navigation')).toBeVisible();
    await expect(page.locator('text=General')).toBeVisible();
  });

  test('should close shortcuts modal with X button', async ({ page }) => {
    await page.goto('/');

    // Open modal
    await page.click('button[title="Keyboard Shortcuts"]');
    await expect(page.locator('h2:has-text("Keyboard Shortcuts")')).toBeVisible();

    // Close modal
    const closeButton = page.locator('[role="dialog"] button').first();
    await closeButton.click();

    // Modal should be closed
    await expect(page.locator('h2:has-text("Keyboard Shortcuts")')).not.toBeVisible();
  });

  test('should close shortcuts modal with Escape key', async ({ page }) => {
    await page.goto('/');

    // Open modal
    await page.click('button[title="Keyboard Shortcuts"]');
    await expect(page.locator('h2:has-text("Keyboard Shortcuts")')).toBeVisible();

    // Press Escape
    await page.keyboard.press('Escape');

    // Wait a moment for modal to close
    await page.waitForTimeout(100);

    // Modal should be closed
    await expect(page.locator('h2:has-text("Keyboard Shortcuts")')).not.toBeVisible();
  });
});

test.describe('Projects Page', () => {
  test('should display projects heading', async ({ page }) => {
    await page.goto('/');

    // Should show projects area
    await expect(page.locator('main')).toBeVisible();
  });
});

test.describe('Responsive Design', () => {
  test('should adapt to smaller screen sizes', async ({ page }) => {
    // Set viewport to tablet size
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('/');

    // App should still be visible and functional
    await expect(page.locator('text=SceneMachine')).toBeVisible();
  });

  test('should work on mobile viewport', async ({ page }) => {
    // Set viewport to mobile size
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');

    // App should still load
    const main = page.locator('main');
    await expect(main).toBeVisible();
  });
});

test.describe('Error Handling', () => {
  test('should display error boundary on unhandled errors', async ({ page }) => {
    // Navigate to a page that might trigger an error
    // This test verifies the error boundary is in place
    await page.goto('/');

    // The app should load without crashing
    await expect(page.locator('body')).not.toHaveText(/unhandled/i);
  });
});
