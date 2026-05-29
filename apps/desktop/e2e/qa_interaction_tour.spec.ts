/**
 * QA interaction tour: skeptically exercise every interactive control.
 *
 * The screenshot + tab tours only *render* pages. This tour clicks every
 * visible button on each route (one at a time, re-loading between clicks so
 * each is tested from a clean state) and records any console/page error the
 * click triggers — surfacing crashes in modals, panels, and dialogs that only
 * appear when a user actually interacts. All backend calls are mocked, so
 * clicks (including destructive ones) have no real effect.
 *
 * Run: QA_PORT=5273 npx playwright test qa_interaction_tour \
 *        --config=qa-playwright.config.ts
 */

import { test, expect, type Page } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const SHOT_DIR = '/tmp/sm_qa/interaction';
const REPORT_DIR = '/tmp/sm_qa/report';
fs.mkdirSync(SHOT_DIR, { recursive: true });
fs.mkdirSync(REPORT_DIR, { recursive: true });

const FIXTURE = '00000000-0000-0000-0000-000000000001';

async function installMock(page: Page): Promise<void> {
  await page.addInitScript(() => {
    try {
      localStorage.setItem('scenemachine-onboarding-completed', 'true');
    } catch {
      /* sandboxed */
    }
    const defaultFor = (method: string, params?: any): any => {
      const m = method.toLowerCase();
      if (m === 'settings.get') {
        return {
          apiKeys: { anthropic: { configured: true }, openai: { configured: true } },
          llmProvider: 'anthropic',
          videoProvider: 'local',
          themeMode: 'dark',
          fontSizeScale: 'medium',
        };
      }
      if (method === 'projects.list') {
        return [{ id: '00000000-0000-0000-0000-000000000001', name: 'QA Test Project', state: 'planning' }];
      }
      if (method === 'projects.get' || method.endsWith('.get')) {
        return { id: params?.id || '00000000-0000-0000-0000-000000000001', name: 'QA Test Project', state: 'planning' };
      }
      if (m.includes('list') || m.endsWith('.getall') || m.endsWith('s')) return [];
      if (m.includes('count')) return 0;
      if (m.includes('exists') || m.includes('has')) return false;
      return {};
    };
    (window as any).electronAPI = {
      backendRequest: async (method: string, params?: any) => defaultFor(method, params),
      onBackendNotification: () => () => {},
      openFileDialog: async () => ({ canceled: true, filePaths: [] }),
      saveFileDialog: async () => ({ canceled: true, filePath: undefined }),
      openFile: async () => ({ canceled: true, filePaths: [] }),
      showItemInFolder: async () => {},
      platform: 'qa-mock',
    };
  });
}

const ROUTES: { name: string; path: string }[] = [
  { name: 'home', path: '/' },
  { name: 'settings', path: '/#/settings' },
  { name: 'admin', path: '/#/admin' },
  { name: 'analytics', path: '/#/analytics' },
  { name: 'actforge', path: '/#/actforge' },
  { name: 'archive', path: '/#/archive' },
  { name: 'help', path: '/#/help' },
  { name: 'dna-strand', path: '/#/dna-strand-demo' },
  { name: 'project', path: `/#/project/${FIXTURE}` },
  { name: 'characters', path: `/#/project/${FIXTURE}/characters` },
  { name: 'scenes', path: `/#/project/${FIXTURE}/scenes` },
  { name: 'generate', path: `/#/project/${FIXTURE}/generate` },
  { name: 'timeline', path: `/#/project/${FIXTURE}/timeline` },
  { name: 'export', path: `/#/project/${FIXTURE}/export` },
  { name: 'explainability', path: `/#/project/${FIXTURE}/explainability` },
];

interface ClickError {
  route: string;
  buttonLabel: string;
  index: number;
  errors: string[];
}

const allErrors: ClickError[] = [];

test.describe.configure({ mode: 'serial' });

for (const route of ROUTES) {
  test(`interact ${route.name}`, async ({ page }) => {
    await installMock(page);
    const pageErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') pageErrors.push(msg.text());
    });
    page.on('pageerror', (err) => pageErrors.push(`PAGEERROR: ${err.message}`));

    await page.goto(route.path, { waitUntil: 'networkidle', timeout: 15000 });
    await page.waitForTimeout(600);

    // Count buttons once (stable list from the initial render).
    const count = await page.getByRole('button').count();

    for (let i = 0; i < count; i++) {
      const before = pageErrors.length;
      // Re-resolve the button each iteration; if a prior click navigated/opened
      // a modal, re-goto to restore a clean, comparable state.
      const btn = page.getByRole('button').nth(i);
      let label = '';
      try {
        label = (await btn.innerText({ timeout: 500 })).slice(0, 40) || `[icon-btn ${i}]`;
      } catch {
        label = `[btn ${i}]`;
      }
      try {
        await btn.click({ timeout: 1500, trial: false });
        await page.waitForTimeout(250);
      } catch {
        /* not clickable / detached — skip */
      }
      const newErrs = pageErrors.slice(before);
      // Only flag real crashes, not benign console noise.
      const crashes = newErrs.filter((e) =>
        /Cannot read propert|is not a function|is not iterable|undefined is not|PAGEERROR|Unexpected Application Error/i.test(e),
      );
      if (crashes.length) {
        allErrors.push({ route: route.name, buttonLabel: label, index: i, errors: crashes });
        await page
          .screenshot({ path: path.join(SHOT_DIR, `${route.name}-btn${i}.png`), fullPage: true })
          .catch(() => {});
      }
      // Restore clean state for the next button (close modals / undo nav).
      await page.goto(route.path, { waitUntil: 'networkidle', timeout: 15000 }).catch(() => {});
      await page.waitForTimeout(200);
    }

    expect(true).toBe(true);
  });
}

test.afterAll(async () => {
  const lines = ['# QA Interaction Tour — button-click crashes', ''];
  lines.push(`Total crashing clicks: ${allErrors.length}`, '');
  for (const e of allErrors) {
    lines.push(`## ${e.route} — "${e.buttonLabel}" (button #${e.index})`);
    for (const msg of e.errors.slice(0, 3)) lines.push(`  - ${msg.slice(0, 200)}`);
    lines.push('');
  }
  fs.writeFileSync(path.join(REPORT_DIR, 'INTERACTION_SUMMARY.md'), lines.join('\n'));
});
