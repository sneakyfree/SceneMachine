/**
 * QA i18n tour — proves the international-launch locale switch works end-to-end.
 *
 * Loads the app (EN default), screenshots the sidebar nav, clicks the "ES"
 * language button, then asserts the nav labels actually re-render in Spanish
 * (Projects→Proyectos, Settings→Configuración, Help→Ayuda). A locale switch
 * that doesn't change visible text is a silent no-op, so we assert on the DOM.
 *
 * Run: QA_PORT=5273 npx playwright test qa_i18n_tour \
 *        --config=qa-playwright.config.ts
 */

import { test, expect, type Page } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const SHOT_DIR = '/tmp/sm_qa/i18n';
fs.mkdirSync(SHOT_DIR, { recursive: true });

async function installMock(page: Page): Promise<void> {
  await page.addInitScript(() => {
    try {
      localStorage.setItem('scenemachine-onboarding-completed', 'true');
    } catch {
      /* sandboxed */
    }
    (window as any).electronAPI = {
      backendRequest: async (method: string) => {
        const m = method.toLowerCase();
        if (m === 'settings.get') return { apiKeys: {}, themeMode: 'dark' };
        if (m === 'projects.list') return [];
        if (m.includes('list') || m.endsWith('s')) return [];
        if (m.includes('count')) return 0;
        return {};
      },
      onBackendNotification: () => () => {},
      openFileDialog: async () => ({ canceled: true, filePaths: [] }),
      saveFileDialog: async () => ({ canceled: true, filePath: undefined }),
      platform: 'qa-mock',
    };
  });
}

test('i18n locale switch re-renders nav in Spanish', async ({ page }) => {
  await installMock(page);
  await page.goto('/', { waitUntil: 'networkidle', timeout: 15000 });
  await page.waitForTimeout(800);

  const nav = page.getByRole('navigation', { name: 'Main navigation' });

  // English default.
  await expect(nav.getByText('Projects', { exact: true })).toBeVisible();
  await expect(nav.getByText('Settings', { exact: true })).toBeVisible();
  await expect(nav.getByText('Help', { exact: true })).toBeVisible();
  await page.screenshot({ path: path.join(SHOT_DIR, 'nav_en.png') });

  // Switch to Spanish via the language selector (accessible name is the code "ES").
  await page.getByRole('button', { name: 'ES', exact: true }).click();
  await page.waitForTimeout(400);

  // Nav must now be Spanish — and the English strings gone.
  await expect(nav.getByText('Proyectos', { exact: true })).toBeVisible();
  await expect(nav.getByText('Configuración', { exact: true })).toBeVisible();
  await expect(nav.getByText('Ayuda', { exact: true })).toBeVisible();
  await expect(nav.getByText('Projects', { exact: true })).toHaveCount(0);
  await page.screenshot({ path: path.join(SHOT_DIR, 'nav_es.png') });

  // Locale must persist across reload (zustand persist).
  await page.reload({ waitUntil: 'networkidle' });
  await page.waitForTimeout(800);
  await expect(nav.getByText('Proyectos', { exact: true })).toBeVisible();
});
