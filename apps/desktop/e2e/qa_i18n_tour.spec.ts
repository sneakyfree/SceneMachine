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

// Page BODY content (not just nav chrome) must render Spanish on each route.
// Each entry asserts a Spanish string that lives in the page body, proving the
// content migration — switching to ES localizes content, not just navigation.
const BODY_ROUTES: { name: string; path: string; es: string }[] = [
  { name: 'home', path: '/', es: 'Crea y gestiona' }, // home subtitle prefix
  { name: 'analytics', path: '/#/analytics', es: 'Analíticas' },
  { name: 'archive', path: '/#/archive', es: 'Archivo' },
  { name: 'help', path: '/#/help', es: 'Ayuda' },
  { name: 'settings', path: '/#/settings', es: 'Configuración' },
  { name: 'admin', path: '/#/admin', es: 'Estado del Sistema' },
];

for (const r of BODY_ROUTES) {
  test(`i18n body content is Spanish — ${r.name}`, async ({ page }) => {
    // Pre-seed locale=es so the very first render is Spanish.
    await installMock(page);
    await page.addInitScript(() => {
      try {
        const raw = localStorage.getItem('scenemachine-experience-store');
        const parsed = raw ? JSON.parse(raw) : { state: {}, version: 0 };
        parsed.state = { ...(parsed.state || {}), locale: 'es' };
        localStorage.setItem('scenemachine-experience-store', JSON.stringify(parsed));
      } catch {
        /* sandboxed */
      }
    });

    const errs: string[] = [];
    page.on('console', (m) => {
      if (m.type() === 'error') errs.push(m.text());
    });
    page.on('pageerror', (e) => errs.push(`PAGEERROR: ${e.message}`));

    await page.goto(r.path, { waitUntil: 'networkidle', timeout: 15000 });
    await page.waitForTimeout(900);
    await page.screenshot({ path: path.join(SHOT_DIR, `body_${r.name}_es.png`), fullPage: true });

    // The page body (excluding the nav sidebar) must contain the Spanish string.
    await expect(page.locator('#main-content').getByText(r.es, { exact: false }).first()).toBeVisible();

    const crashes = errs.filter(
      (e) =>
        !/^(PAGEERROR: )?Warning:/.test(e) &&
        /Cannot read propert|is not a function|is not iterable|undefined is not|PAGEERROR|Unexpected Application Error/i.test(e),
    );
    expect(crashes, `crashes on ${r.name}: ${crashes.join('; ')}`).toHaveLength(0);
  });
}

// Shared components (not just pages) must localize too. The command palette is
// reachable from the sidebar footer "Buscar" button on every route — opening it
// under locale=es must show Spanish chrome (placeholder + footer hints).
test('i18n shared component (command palette) renders Spanish', async ({ page }) => {
  await installMock(page);
  await page.addInitScript(() => {
    try {
      const raw = localStorage.getItem('scenemachine-experience-store');
      const parsed = raw ? JSON.parse(raw) : { state: {}, version: 0 };
      parsed.state = { ...(parsed.state || {}), locale: 'es' };
      localStorage.setItem('scenemachine-experience-store', JSON.stringify(parsed));
    } catch {
      /* sandboxed */
    }
  });

  await page.goto('/', { waitUntil: 'networkidle', timeout: 15000 });
  await page.waitForTimeout(700);

  // Open the command palette via the keyboard shortcut.
  await page.keyboard.press('Control+k');
  await page.waitForTimeout(400);

  // Spanish placeholder + footer hint prove the component (not just nav) is localized.
  await expect(page.getByPlaceholder('Buscar comandos...')).toBeVisible();
  await expect(page.getByText('para navegar', { exact: false }).first()).toBeVisible();
  await page.screenshot({ path: path.join(SHOT_DIR, 'command_palette_es.png') });
});

// French + German locales: switching must re-render the nav in that language
// and persist. Asserts hand-authored nav strings unique to each locale.
const EXTRA_LOCALES: { code: string; nav: string[]; gone: string }[] = [
  { code: 'FR', nav: ['Projets', 'Paramètres', 'Aide'], gone: 'Projects' },
  { code: 'DE', nav: ['Projekte', 'Einstellungen', 'Hilfe'], gone: 'Projects' },
];

for (const loc of EXTRA_LOCALES) {
  test(`i18n locale switch re-renders nav in ${loc.code}`, async ({ page }) => {
    await installMock(page);
    await page.goto('/', { waitUntil: 'networkidle', timeout: 15000 });
    await page.waitForTimeout(700);

    const nav = page.getByRole('navigation', { name: 'Main navigation' });
    await expect(nav.getByText('Projects', { exact: true })).toBeVisible();

    await page.getByRole('button', { name: loc.code, exact: true }).click();
    await page.waitForTimeout(400);

    for (const label of loc.nav) {
      await expect(nav.getByText(label, { exact: true })).toBeVisible();
    }
    await expect(nav.getByText(loc.gone, { exact: true })).toHaveCount(0);
    await page.screenshot({ path: path.join(SHOT_DIR, `nav_${loc.code.toLowerCase()}.png`) });

    // Persist across reload.
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(700);
    await expect(nav.getByText(loc.nav[0], { exact: true })).toBeVisible();
  });
}
