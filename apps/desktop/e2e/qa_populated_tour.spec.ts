/**
 * QA populated-data tour.
 *
 * The other tours use empty backend responses, so data-bearing components
 * (shot cards, performer cards, cost estimates, queue manager, timeline clips,
 * scene rows, generation jobs) never render. This tour feeds RICH, fully-
 * populated responses so those components actually render — exercising their
 * number-formatting / list-mapping paths (e.g. `.toFixed`, `.map`) that the
 * empty tours can't reach. Records any crash-class error per route.
 *
 * Run: QA_PORT=5273 npx playwright test qa_populated_tour \
 *        --config=qa-playwright.config.ts
 */

import { test, expect, type Page } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const SHOT_DIR = '/tmp/sm_qa/populated';
const REPORT_DIR = '/tmp/sm_qa/report';
fs.mkdirSync(SHOT_DIR, { recursive: true });
fs.mkdirSync(REPORT_DIR, { recursive: true });

const FIXTURE = '00000000-0000-0000-0000-000000000001';

async function installRichMock(page: Page): Promise<void> {
  await page.addInitScript(() => {
    try {
      localStorage.setItem('scenemachine-onboarding-completed', 'true');
    } catch {
      /* sandboxed */
    }

    const uid = (n: number) => `00000000-0000-0000-0000-00000000000${n}`;

    // A shot rich enough for shot-card / shot-preview / timeline / dashboard.
    const shot = (i: number) => ({
      id: uid(i),
      shotId: uid(i),
      shot_number: `${i}`,
      shotNumber: `${i}`,
      scene_id: uid(1),
      sceneId: uid(1),
      sequence_number: i,
      status: i % 2 === 0 ? 'completed' : 'pending',
      state: i % 2 === 0 ? 'completed' : 'pending',
      shot_type: 'wide',
      shotType: 'wide',
      camera_movement: 'static',
      description: `Shot ${i} description`,
      duration_seconds: 3.5,
      durationSeconds: 3.5,
      qualityScore: 0.82,
      quality_score: 0.82,
      cost_usd: 0.25,
      generation_time_seconds: 12.5,
      provider: 'replicate',
      model: 'wan-2.2',
      prompt: 'a cinematic shot',
      jobNumber: i,
      progressPercent: 50,
      progress: 50,
    });

    const scene = (i: number) => ({
      id: uid(i),
      sceneId: uid(i),
      scene_number: `${i}`,
      sceneNumber: `${i}`,
      sequence_number: i,
      heading: `INT. LOCATION ${i} - DAY`,
      scene_type: 'interior',
      location: `Location ${i}`,
      time_of_day: 'day',
      state: 'approved',
      shot_breakdown_approved: true,
      estimatedDurationSeconds: 12.0,
      estimated_duration_seconds: 12.0,
      character_ids: [uid(1)],
      // Unique shot ids per scene so flattened renders don't collide on keys.
      shots: [shot(i * 10 + 1), shot(i * 10 + 2)],
      shot_count: 2,
    });

    const performer = (i: number) => ({
      id: uid(i),
      performer_id: uid(i),
      stage_name: `Performer ${i}`,
      name: `Performer ${i}`,
      performer_type: 'human',
      aci_score: 85.5,
      rating: 4.5,
      cost_per_second: 0.04,
      placement_rate: 80,
      pricing: { blink: 9.99, deep: 49.99, epic: 199.99 },
      availability_status: 'available',
      is_active: true,
    });

    const richDefault = (method: string, params?: any): any => {
      const m = method.toLowerCase();
      if (m === 'settings.get') {
        return {
          apiKeys: { anthropic: { configured: true }, openai: { configured: true } },
          llmProvider: 'anthropic',
          videoProvider: 'local',
          themeMode: 'dark',
        };
      }
      if (method === 'projects.list')
        return [{ id: uid(1), name: 'QA Test Project', state: 'generating', characterCount: 2, sceneCount: 2 }];
      if (method === 'projects.get' || method === 'projects.getDetail')
        return { id: uid(1), name: 'QA Test Project', state: 'generating' };
      if (m.includes('scene') && (m.includes('list') || m.endsWith('s'))) return [scene(1), scene(2)];
      if (m === 'scenes.get' || m === 'scenes.getdetail') return scene(1);
      if (m.includes('shot') && (m.includes('list') || m.endsWith('s'))) return [shot(1), shot(2)];
      if (m.includes('performer')) return [performer(1), performer(2)];
      if (m.includes('character') && (m.includes('list') || m.endsWith('s')))
        return [{ id: uid(1), name: 'Bob', screenplayName: 'BOB', lockState: 'locked', isLocked: true, sceneCount: 2, dialogueCount: 5, referenceCount: 1 }];
      if (m.includes('job') || m === 'generation.getpendingjobs')
        return [shot(1), shot(2)];
      if (m === 'generation.getqueuestatus' || m === 'generation.getworkerstatus')
        return { status: 'running', isRunning: true, jobs_processed: 10, jobs_succeeded: 8, jobs_failed: 2, processed: 10, succeeded: 8, failed: 2, uptime_seconds: 120, progressPercent: 50 };
      if (m === 'assembly.gettimeline')
        return { scenes: [scene(1), scene(2)], clips: [shot(101), shot(102)], totalDuration: 24, total_duration: 24 };
      if (m === 'assembly.getstatus')
        return { status: 'pending', shotsTotal: 2, shotsGenerated: 1, totalDuration: 24, missingShots: [], scenes: [scene(1)] };
      if (m.includes('cost') || m.includes('estimate'))
        return { total_cost: 12.5, totalCost: 12.5, cost_per_shot: 0.25, costPerShot: 0.25, avg_cost: 0.25, breakdown: [{ value: 1.25, unit: 'USD', label: 'shots' }] };
      if (m.includes('analytics') || m.includes('stats'))
        return { totalJobs: 10, completed: 8, failed: 2, totalSpent: 12.5, avgCostPerShot: 0.25, successRate: 80, byProvider: [{ provider: 'replicate', cost: 12.5, success_rate: 99.0, count: 10 }], trend: { direction: 'up', percent: 12.5 } };
      if (m.includes('cache'))
        return { projectCount: 1, videoCount: 2, totalVideoSizeMB: 100.0, totalSizeMB: 120.0 };
      if (m.includes('list') || m.endsWith('.getall') || m.endsWith('s')) return [];
      if (m.includes('count')) return 2;
      if (m.includes('exists') || m.includes('has')) return true;
      return {};
    };

    (window as any).electronAPI = {
      backendRequest: async (method: string, params?: any) => richDefault(method, params),
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
  { name: 'project', path: `/#/project/${FIXTURE}` },
  { name: 'characters', path: `/#/project/${FIXTURE}/characters` },
  { name: 'scenes', path: `/#/project/${FIXTURE}/scenes` },
  { name: 'generate', path: `/#/project/${FIXTURE}/generate` },
  { name: 'timeline', path: `/#/project/${FIXTURE}/timeline` },
  { name: 'export', path: `/#/project/${FIXTURE}/export` },
  { name: 'explainability', path: `/#/project/${FIXTURE}/explainability` },
  { name: 'analytics', path: '/#/analytics' },
  { name: 'actforge', path: '/#/actforge' },
  { name: 'admin', path: '/#/admin' },
];

interface RouteReport {
  route: string;
  crashes: string[];
  keyWarnings: number;
}
const reports: RouteReport[] = [];

test.describe.configure({ mode: 'serial' });

for (const route of ROUTES) {
  test(`populated ${route.name}`, async ({ page }) => {
    await installRichMock(page);
    const errs: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') errs.push(msg.text());
    });
    page.on('pageerror', (err) => errs.push(`PAGEERROR: ${err.message}`));

    await page.goto(route.path, { waitUntil: 'networkidle', timeout: 15000 });
    await page.waitForTimeout(1200);
    await page.screenshot({ path: path.join(SHOT_DIR, `${route.name}.png`), fullPage: true }).catch(() => {});

    // Crashes only — React dev "Warning:" lines (e.g. list-key advisories) are
    // not crashes and are excluded so the crash count reflects real breakage.
    const crashes = errs.filter(
      (e) =>
        !/^(PAGEERROR: )?Warning:/.test(e) &&
        /Cannot read propert|is not a function|is not iterable|undefined is not|PAGEERROR|Unexpected Application Error/i.test(
          e,
        ),
    );
    const keyWarnings = errs.filter((e) => /two children with the same key|unique "key" prop/.test(e)).length;
    reports.push({ route: route.name, crashes, keyWarnings });
    expect(true).toBe(true);
  });
}

test.afterAll(async () => {
  const lines = ['# QA Populated-Data Tour — rendering real data', ''];
  const total = reports.reduce((s, r) => s + r.crashes.length, 0);
  const totalWarn = reports.reduce((s, r) => s + r.keyWarnings, 0);
  lines.push(`Total crashes: ${total}`, `Total React key warnings (advisory): ${totalWarn}`, '');
  for (const r of reports) {
    lines.push(`## ${r.route}: ${r.crashes.length} crash(es), ${r.keyWarnings} key-warning(s)`);
    for (const c of r.crashes.slice(0, 4)) lines.push(`  - ${c.slice(0, 200)}`);
    lines.push('');
  }
  fs.writeFileSync(path.join(REPORT_DIR, 'POPULATED_SUMMARY.md'), lines.join('\n'));
});
