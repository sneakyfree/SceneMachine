/**
 * QA screenshot tour: every page, every nav link.
 *
 * Captures full-page screenshots + console errors + every IPC call the
 * renderer attempts. Mocks window.electronAPI so pages render against
 * sensible defaults instead of undefined-access crashes.
 *
 * Output: screenshots in /tmp/sm_qa/screenshots/, structured JSON of
 * IPC calls + errors in /tmp/sm_qa/report/.
 *
 * Run: PLAYWRIGHT_BASE_URL=http://localhost:5273 npx playwright test
 *      qa_screenshot_tour --config=qa-playwright.config.ts
 */

import { test, expect, type Page } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const SCREENSHOT_DIR = '/tmp/sm_qa/screenshots';
const REPORT_DIR = '/tmp/sm_qa/report';

fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
fs.mkdirSync(REPORT_DIR, { recursive: true });

interface PageReport {
  route: string;
  title: string;
  consoleErrors: string[];
  pageErrors: string[];
  ipcCalls: { method: string; params: any }[];
  visibleTextSample: string;
  domNodeCount: number;
}

/**
 * Install a window.electronAPI mock that:
 *  - Logs every backendRequest call (method + params)
 *  - Returns an empty array / object based on method-name heuristics so
 *    the page renders something instead of crashing on .then() of undefined
 */
async function installElectronAPIMock(page: Page): Promise<void> {
  await page.addInitScript(() => {
    (window as any).__ipcCalls__ = [];

    // Bypass first-run onboarding gate (App.tsx uses this localStorage key
    // to decide whether to render the Onboarding wizard instead of routes).
    try {
      localStorage.setItem('scenemachine-onboarding-completed', 'true');
    } catch {
      // localStorage may not be available in some sandboxed contexts
    }

    const defaultFor = (method: string, params?: any): any => {
      const m = method.toLowerCase();
      // Special-cases for handlers the renderer assumes a specific shape from
      if (m === 'settings.get') {
        return {
          apiKeys: {
            anthropic: { configured: true },
            openai: { configured: true },
          },
          llmProvider: 'anthropic',
          videoProvider: 'local',
          themeMode: 'dark',
          fontSizeScale: 'medium',
          highContrastEnabled: false,
          reduceMotionEnabled: false,
          largeClickTargetsEnabled: false,
        };
      }
      if (method === 'projects.list') {
        return [
          {
            id: '00000000-0000-0000-0000-000000000001',
            name: 'QA Test Project',
            description: 'Synthetic project for the screenshot tour',
            state: 'planning',
            screenplayTitle: 'Test Screenplay',
            characterCount: 3,
            sceneCount: 5,
            createdAt: '2026-05-24T00:00:00Z',
            updatedAt: '2026-05-24T00:00:00Z',
          },
        ];
      }
      if (method === 'projects.get' || method.endsWith('.get')) {
        return {
          id: params?.id || '00000000-0000-0000-0000-000000000001',
          name: 'QA Test Project',
          state: 'planning',
        };
      }
      if (m.includes('list') || m.endsWith('.getall') || m.endsWith('s')) return [];
      if (m.includes('count')) return 0;
      if (m.includes('exists') || m.includes('has')) return false;
      if (m === 'ping') return { status: 'pong' };
      if (m === 'version') return { version: '0.1.0-qa', environment: 'qa' };
      return {};
    };

    (window as any).electronAPI = {
      backendRequest: async (method: string, params?: any) => {
        (window as any).__ipcCalls__.push({ method, params });
        return defaultFor(method, params);
      },
      onBackendNotification: () => () => {},
      openFileDialog: async () => ({ canceled: true, filePaths: [] }),
      saveFileDialog: async () => ({ canceled: true, filePath: undefined }),
      showItemInFolder: async () => {},
      platform: 'qa-mock',
    };
  });
}

const ROUTES: { name: string; path: string }[] = [
  { name: 'home', path: '/' },
  { name: 'home-projects', path: '/#/' },
  { name: 'settings', path: '/#/settings' },
  { name: 'help', path: '/#/help' },
  { name: 'archive', path: '/#/archive' },
  { name: 'admin', path: '/#/admin' },
  { name: 'analytics', path: '/#/analytics' },
  { name: 'actforge', path: '/#/actforge' },
  // Real route is `dna-strand-demo`, not `dna-strand` (the latter 404'd in
  // prior tours — a tour-spec typo, not a platform bug).
  { name: 'dna-strand', path: '/#/dna-strand-demo' },
  // Deliberate unmatched URL — must render the friendly NotFoundPage (catch-all
  // `path: '*'` route), NOT React Router's raw "Hey developer 👋 404" screen.
  // Regression guard for the 404 gap fixed 2026-05-28.
  { name: 'not-found-404', path: '/#/this-route-definitely-does-not-exist' },
  // The project-scoped routes need a project ID. Use a fixture UUID;
  // the renderer will hit our mocked backend.
  { name: 'project-detail', path: '/#/project/00000000-0000-0000-0000-000000000001' },
  {
    name: 'character-lab',
    path: '/#/project/00000000-0000-0000-0000-000000000001/characters',
  },
  {
    name: 'scene-planning',
    path: '/#/project/00000000-0000-0000-0000-000000000001/scenes',
  },
  {
    name: 'generation',
    path: '/#/project/00000000-0000-0000-0000-000000000001/generate',
  },
  {
    name: 'timeline',
    path: '/#/project/00000000-0000-0000-0000-000000000001/timeline',
  },
  {
    name: 'export',
    path: '/#/project/00000000-0000-0000-0000-000000000001/export',
  },
  {
    name: 'explainability',
    path: '/#/project/00000000-0000-0000-0000-000000000001/explainability',
  },
];

const allReports: PageReport[] = [];

test.describe.configure({ mode: 'serial' });

for (const route of ROUTES) {
  test(`screenshot ${route.name}`, async ({ page }) => {
    await installElectronAPIMock(page);

    const consoleErrors: string[] = [];
    const pageErrors: string[] = [];

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });
    page.on('pageerror', (err) => {
      pageErrors.push(err.message);
    });

    await page.goto(route.path, { waitUntil: 'networkidle', timeout: 15000 });
    // Give the page a moment to fire IPC calls + render
    await page.waitForTimeout(1500);

    const title = await page.title();
    const visibleText = (await page.locator('body').innerText().catch(() => '')).slice(0, 600);
    const domNodeCount = await page.evaluate(() => document.querySelectorAll('*').length);
    const ipcCalls = await page.evaluate(() => (window as any).__ipcCalls__ || []);

    const screenshotPath = path.join(SCREENSHOT_DIR, `${route.name}.png`);
    await page.screenshot({ path: screenshotPath, fullPage: true });

    const report: PageReport = {
      route: route.path,
      title,
      consoleErrors,
      pageErrors,
      ipcCalls,
      visibleTextSample: visibleText,
      domNodeCount,
    };
    allReports.push(report);

    fs.writeFileSync(
      path.join(REPORT_DIR, `${route.name}.json`),
      JSON.stringify(report, null, 2),
    );

    // Soft assertions — we want the test to PASS so all pages get captured.
    // Real failures get surfaced in the final report.
    expect(title).toBeTruthy();

    // Hard assertion for the catch-all route: an unmatched URL must render the
    // friendly NotFoundPage, never React Router's raw developer error screen.
    if (route.name === 'not-found-404') {
      expect(visibleText).not.toContain('Unexpected Application Error');
      expect(visibleText).not.toContain('Hey developer');
      expect(visibleText.toLowerCase()).toContain('wrong turn');
    }
  });
}

test.afterAll(async () => {
  fs.writeFileSync(
    path.join(REPORT_DIR, 'all_reports.json'),
    JSON.stringify(allReports, null, 2),
  );

  // Human-readable summary
  const lines: string[] = [];
  lines.push('# QA Tour Summary');
  lines.push('');
  lines.push(`Total pages: ${allReports.length}`);
  const totalErrors = allReports.reduce(
    (sum, r) => sum + r.consoleErrors.length + r.pageErrors.length,
    0,
  );
  lines.push(`Total console+page errors: ${totalErrors}`);
  lines.push('');
  for (const r of allReports) {
    lines.push(`## ${r.route}`);
    lines.push(`- title: ${r.title}`);
    lines.push(`- DOM nodes: ${r.domNodeCount}`);
    lines.push(`- IPC calls (${r.ipcCalls.length}): ${r.ipcCalls.map((c) => c.method).join(', ') || '(none)'}`);
    if (r.consoleErrors.length) {
      lines.push(`- **console errors (${r.consoleErrors.length})**:`);
      for (const e of r.consoleErrors.slice(0, 5)) lines.push(`  - ${e.slice(0, 200)}`);
    }
    if (r.pageErrors.length) {
      lines.push(`- **page errors (${r.pageErrors.length})**:`);
      for (const e of r.pageErrors.slice(0, 5)) lines.push(`  - ${e.slice(0, 200)}`);
    }
    lines.push('');
  }
  fs.writeFileSync(path.join(REPORT_DIR, 'SUMMARY.md'), lines.join('\n'));
});
