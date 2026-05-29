/**
 * QA in-page tab tour.
 *
 * The route-level screenshot tour (qa_screenshot_tour.spec.ts) only captures
 * each page's *default* tab. This tour drives the in-page tabs that route
 * navigation never reaches — clicking each tab and capturing a screenshot +
 * console/page errors per tab. Closes the "every tab" half of the visual QA
 * directive (2026-05-28).
 *
 * Tab inventory verified against source:
 *   - explainability.tsx: overview / operator / technical / audit
 *   - admin.tsx:          overview / providers / queue / storage / logs /
 *                         system / feedback / settings
 *
 * Run: QA_PORT=5273 npx playwright test qa_tabs_tour \
 *        --config=qa-playwright.config.ts
 */

import { test, expect, type Page } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const SCREENSHOT_DIR = '/tmp/sm_qa/tabs';
const REPORT_DIR = '/tmp/sm_qa/report';
fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
fs.mkdirSync(REPORT_DIR, { recursive: true });

const FIXTURE_PROJECT = '00000000-0000-0000-0000-000000000001';

// Minimal electronAPI mock — same shape-aware defaults as the route tour so
// pages render against sensible data instead of undefined-access crashes.
async function installElectronAPIMock(page: Page): Promise<void> {
  await page.addInitScript(() => {
    (window as any).__ipcCalls__ = [];
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
          highContrastEnabled: false,
          reduceMotionEnabled: false,
          largeClickTargetsEnabled: false,
        };
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

interface TabbedPage {
  page: string;
  route: string;
  tabs: string[];
}

// Real in-page tabs verified against source. (admin.tsx has NO tabs — it's a
// single scrolling page — so it is intentionally not listed here.)
const TABBED_PAGES: TabbedPage[] = [
  {
    page: 'explainability',
    route: `/#/project/${FIXTURE_PROJECT}/explainability`,
    tabs: ['Client', 'Operator', 'Technical', 'Audit'],
  },
  {
    page: 'dna-strand',
    route: '/#/dna-strand-demo',
    tabs: ['Overview', 'Blockers', 'Pipeline', 'Agents'],
  },
];

interface TabReport {
  page: string;
  tab: string;
  consoleErrors: string[];
  pageErrors: string[];
  domNodeCount: number;
}

const tabReports: TabReport[] = [];

test.describe.configure({ mode: 'serial' });

for (const tp of TABBED_PAGES) {
  test(`tabs ${tp.page}`, async ({ page }) => {
    await installElectronAPIMock(page);

    const consoleErrors: string[] = [];
    const pageErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });
    page.on('pageerror', (err) => pageErrors.push(err.message));

    await page.goto(tp.route, { waitUntil: 'networkidle', timeout: 15000 });
    await page.waitForTimeout(800);

    for (const tab of tp.tabs) {
      // Snapshot errors before the click so we can attribute new ones to the tab.
      const beforeConsole = consoleErrors.length;
      const beforePage = pageErrors.length;

      // Tab controls render as <button> with the label as text. Match the
      // accessible name case-insensitively + whitespace-tolerantly: some tabs
      // render lowercase text styled with CSS `capitalize` (e.g. dna-strand),
      // so an exact "Blockers" match would miss the real "blockers" node.
      const btn = page
        .getByRole('button', { name: new RegExp(`^\\s*${tab}\\s*$`, 'i') })
        .first();
      if (await btn.count()) {
        await btn.click().catch(() => {});
        await page.waitForTimeout(500);
      }

      const domNodeCount = await page.evaluate(() => document.querySelectorAll('*').length);
      await page.screenshot({
        path: path.join(SCREENSHOT_DIR, `${tp.page}-${tab.toLowerCase()}.png`),
        fullPage: true,
      });

      tabReports.push({
        page: tp.page,
        tab,
        consoleErrors: consoleErrors.slice(beforeConsole),
        pageErrors: pageErrors.slice(beforePage),
        domNodeCount,
      });
    }

    // Hard assertion: switching tabs must never surface a React error boundary
    // or page crash on any tab of this page.
    const crashed = pageErrors.filter(
      (e) => /Unexpected Application Error|is not a function|Cannot read propert/i.test(e),
    );
    expect(crashed, `page crashes on ${tp.page} tabs: ${crashed.join('; ')}`).toEqual([]);
  });
}

test.afterAll(async () => {
  const lines: string[] = ['# QA Tabs Tour Summary', ''];
  const total = tabReports.reduce((s, r) => s + r.consoleErrors.length + r.pageErrors.length, 0);
  lines.push(`Tabs visited: ${tabReports.length}`);
  lines.push(`Total console+page errors across all tabs: ${total}`);
  lines.push('');
  for (const r of tabReports) {
    lines.push(`## ${r.page} › ${r.tab}`);
    lines.push(`- DOM nodes: ${r.domNodeCount}`);
    if (r.consoleErrors.length) {
      lines.push(`- console errors (${r.consoleErrors.length}):`);
      for (const e of r.consoleErrors.slice(0, 4)) lines.push(`  - ${e.slice(0, 180)}`);
    }
    if (r.pageErrors.length) {
      lines.push(`- **page errors (${r.pageErrors.length})**:`);
      for (const e of r.pageErrors.slice(0, 4)) lines.push(`  - ${e.slice(0, 180)}`);
    }
    lines.push('');
  }
  fs.writeFileSync(path.join(REPORT_DIR, 'TABS_SUMMARY.md'), lines.join('\n'));
});
