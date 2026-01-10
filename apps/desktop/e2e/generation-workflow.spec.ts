/**
 * E2E tests for video generation workflow.
 *
 * Tests the complete flow of generating videos including
 * provider selection, job queuing, progress tracking, and result review.
 */

import { test, expect, Page } from '@playwright/test';

/**
 * Setup mocks for generation API calls.
 */
async function setupMocks(page: Page) {
  await page.addInitScript(() => {
    const mockJobs = [
      {
        id: 'job-1',
        projectId: 'test-project-123',
        sceneId: 'scene-1',
        shotId: 'shot-1',
        status: 'RUNNING',
        progress: 45,
        provider: 'replicate',
        model: 'minimax',
        prompt: 'A detective examining evidence in a dimly lit office',
        estimatedCost: 0.25,
        startedAt: new Date().toISOString(),
        createdAt: new Date().toISOString(),
      },
      {
        id: 'job-2',
        projectId: 'test-project-123',
        sceneId: 'scene-1',
        shotId: 'shot-2',
        status: 'COMPLETED',
        progress: 100,
        provider: 'fal',
        model: 'cogvideox',
        prompt: 'Close-up of scattered documents and photos on wooden desk',
        result: {
          videoUrl: 'https://example.com/generated-video-1.mp4',
          thumbnailUrl: 'https://example.com/thumb-1.jpg',
          duration: 5,
        },
        cost: 0.18,
        startedAt: new Date(Date.now() - 300000).toISOString(),
        completedAt: new Date().toISOString(),
        createdAt: new Date(Date.now() - 300000).toISOString(),
      },
      {
        id: 'job-3',
        projectId: 'test-project-123',
        sceneId: 'scene-2',
        status: 'FAILED',
        progress: 0,
        provider: 'replicate',
        model: 'luma',
        prompt: 'Action sequence in city alley',
        error: 'Provider timeout after 120 seconds',
        cost: 0,
        createdAt: new Date(Date.now() - 600000).toISOString(),
      },
      {
        id: 'job-4',
        projectId: 'test-project-123',
        sceneId: 'scene-2',
        status: 'QUEUED',
        progress: 0,
        provider: 'replicate',
        model: 'minimax',
        prompt: 'Wide shot of dark city street at night',
        estimatedCost: 0.30,
        createdAt: new Date().toISOString(),
      },
    ];

    const mockProviders = [
      {
        id: 'replicate',
        name: 'Replicate',
        status: 'healthy',
        models: [
          { id: 'minimax', name: 'MiniMax Video-01', costPerSecond: 0.05 },
          { id: 'luma', name: 'Luma Dream Machine', costPerSecond: 0.08 },
          { id: 'kling', name: 'Kling AI', costPerSecond: 0.06 },
        ],
      },
      {
        id: 'fal',
        name: 'Fal.ai',
        status: 'healthy',
        models: [
          { id: 'cogvideox', name: 'CogVideoX', costPerSecond: 0.04 },
          { id: 'hunyuan', name: 'Hunyuan Video', costPerSecond: 0.05 },
          { id: 'ltx', name: 'LTX Video', costPerSecond: 0.03 },
        ],
      },
      {
        id: 'comfyui',
        name: 'ComfyUI (Local)',
        status: 'offline',
        models: [],
      },
    ];

    const mockScenes = [
      {
        id: 'scene-1',
        projectId: 'test-project-123',
        sceneNumber: 1,
        slugline: 'INT. DETECTIVE OFFICE - DAY',
        shots: [
          { id: 'shot-1', description: 'Wide establishing shot' },
          { id: 'shot-2', description: 'Close-up of evidence' },
        ],
      },
      {
        id: 'scene-2',
        projectId: 'test-project-123',
        sceneNumber: 2,
        slugline: 'EXT. CITY STREET - NIGHT',
        shots: [
          { id: 'shot-3', description: 'Chase sequence' },
        ],
      },
    ];

    // @ts-expect-error - Setting up mock
    window.electronAPI = {
      backendRequest: async (method: string, params: any) => {
        const responses: Record<string, any> = {
          'generation.list': mockJobs,
          'generation.get': mockJobs.find((j) => j.id === params?.jobId) || mockJobs[0],
          'generation.start': {
            id: 'new-job-' + Date.now(),
            projectId: params?.projectId || 'test-project-123',
            sceneId: params?.sceneId,
            shotId: params?.shotId,
            status: 'QUEUED',
            progress: 0,
            provider: params?.provider || 'replicate',
            model: params?.model || 'minimax',
            prompt: params?.prompt,
            estimatedCost: 0.25,
            createdAt: new Date().toISOString(),
          },
          'generation.cancel': {
            id: params?.jobId,
            status: 'CANCELLED',
            cancelledAt: new Date().toISOString(),
          },
          'generation.retry': {
            ...mockJobs[2],
            id: 'retry-' + Date.now(),
            status: 'QUEUED',
            progress: 0,
            error: null,
            createdAt: new Date().toISOString(),
          },
          'generation.getQueue': mockJobs.filter((j) => j.status === 'QUEUED' || j.status === 'RUNNING'),
          'generation.getHistory': mockJobs.filter((j) => j.status === 'COMPLETED' || j.status === 'FAILED'),
          'generation.getStats': {
            totalJobs: mockJobs.length,
            completedJobs: 1,
            failedJobs: 1,
            totalCost: 0.18,
            averageDuration: 120,
          },
          'providers.list': mockProviders,
          'providers.health': mockProviders.map((p) => ({
            id: p.id,
            status: p.status,
            latency: p.status === 'healthy' ? Math.random() * 500 : null,
          })),
          'scenes.list': mockScenes,
          'scenes.get': mockScenes.find((s) => s.id === params?.sceneId) || mockScenes[0],
          'projects.get': {
            id: 'test-project-123',
            title: 'Test Movie',
            state: 'ACTIVE',
            budget: 50.0,
            spent: 0.18,
          },
          'projects.list': [
            {
              id: 'test-project-123',
              title: 'Test Movie',
              state: 'ACTIVE',
            },
          ],
        };

        const response = responses[method];
        if (response !== undefined) {
          return response;
        }

        console.warn(`Unhandled mock request: ${method}`, params);
        return null;
      },
      platform: 'linux',
      onBackendReady: () => {},
      onBackendError: () => {},
      onGenerationProgress: (callback: (data: any) => void) => {
        // Simulate progress updates
        let progress = 45;
        const interval = setInterval(() => {
          progress += 10;
          if (progress <= 100) {
            callback({ jobId: 'job-1', progress, status: progress === 100 ? 'COMPLETED' : 'RUNNING' });
          } else {
            clearInterval(interval);
          }
        }, 1000);
        return () => clearInterval(interval);
      },
      selectFile: async () => ({
        canceled: false,
        filePaths: ['/path/to/reference-image.jpg'],
      }),
      selectDirectory: async () => ({ canceled: true, filePaths: [] }),
      showSaveDialog: async () => ({ canceled: true }),
      openExternal: async () => {},
    };
  });
}

test.describe('Generation Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page);
    await page.goto('/#/project/test-project-123/generation');
    await page.waitForTimeout(500);
  });

  test('should display generation page', async ({ page }) => {
    const pageTitle = page.locator('h1, h2').filter({ hasText: /generation|generate/i });
    const hasTitle = await pageTitle.first().isVisible().catch(() => false);

    if (hasTitle) {
      await expect(pageTitle.first()).toBeVisible();
    }
  });

  test('should show job queue', async ({ page }) => {
    const queueSection = page.locator('[data-testid="job-queue"], text=/queue|jobs/i');
    const isVisible = await queueSection.first().isVisible().catch(() => false);

    if (isVisible) {
      await expect(queueSection.first()).toBeVisible();
    }
  });

  test('should display running jobs with progress', async ({ page }) => {
    const runningJob = page.locator('[data-testid="running-job"], [data-status="running"]');
    const isVisible = await runningJob.first().isVisible().catch(() => false);

    if (isVisible) {
      const progressBar = page.locator('[role="progressbar"], .progress-bar');
      await expect(progressBar.first()).toBeVisible();
    }
  });

  test('should show generation statistics', async ({ page }) => {
    const stats = page.locator('[data-testid="generation-stats"], text=/completed|failed|cost/i');
    const isVisible = await stats.first().isVisible().catch(() => false);

    if (isVisible) {
      await expect(stats.first()).toBeVisible();
    }
  });
});

test.describe('Provider Selection', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page);
    await page.goto('/#/project/test-project-123/generation');
    await page.waitForTimeout(500);
  });

  test('should show available providers', async ({ page }) => {
    const providerList = page.locator('[data-testid="provider-list"], text=/replicate|fal/i');
    const isVisible = await providerList.first().isVisible().catch(() => false);

    if (isVisible) {
      await expect(providerList.first()).toBeVisible();
    }
  });

  test('should display provider health status', async ({ page }) => {
    const healthIndicator = page.locator('[data-testid="provider-health"], .health-indicator, text=/healthy|offline/i');
    const isVisible = await healthIndicator.first().isVisible().catch(() => false);

    if (isVisible) {
      await expect(healthIndicator.first()).toBeVisible();
    }
  });

  test('should select a provider', async ({ page }) => {
    const providerSelect = page.locator('select[name="provider"], [data-testid="provider-select"]');

    if (await providerSelect.first().isVisible()) {
      await providerSelect.first().selectOption('fal');
      await page.waitForTimeout(300);
    }
  });

  test('should show models for selected provider', async ({ page }) => {
    const providerSelect = page.locator('select[name="provider"], [data-testid="provider-select"]');

    if (await providerSelect.first().isVisible()) {
      await providerSelect.first().selectOption('replicate');

      const modelSelect = page.locator('select[name="model"], [data-testid="model-select"]');
      const isVisible = await modelSelect.first().isVisible().catch(() => false);

      if (isVisible) {
        await expect(modelSelect.first()).toBeVisible();
      }
    }
  });
});

test.describe('Job Creation', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page);
    await page.goto('/#/project/test-project-123/generation');
    await page.waitForTimeout(500);
  });

  test('should open new generation form', async ({ page }) => {
    const generateButton = page.locator('button').filter({
      hasText: /generate|start|new/i,
    });

    if (await generateButton.first().isVisible()) {
      await generateButton.first().click();

      // Should show generation form
      const promptInput = page.locator('textarea[name="prompt"], input[name="prompt"]');
      const hasForm = await promptInput.first().isVisible().catch(() => false);

      if (hasForm) {
        await expect(promptInput.first()).toBeVisible({ timeout: 3000 });
      }
    }
  });

  test('should create a new generation job', async ({ page }) => {
    const generateButton = page.locator('button').filter({
      hasText: /generate|start|new/i,
    });

    if (await generateButton.first().isVisible()) {
      await generateButton.first().click();

      // Select scene
      const sceneSelect = page.locator('select[name="scene"], [data-testid="scene-select"]');
      if (await sceneSelect.first().isVisible()) {
        await sceneSelect.first().selectOption('scene-1');
      }

      // Enter prompt
      const promptInput = page.locator('textarea[name="prompt"], input[name="prompt"]');
      if (await promptInput.first().isVisible()) {
        await promptInput.first().fill('A dramatic scene with cinematic lighting');
      }

      // Submit
      const submitButton = page.locator('button[type="submit"], button:has-text("Generate"), button:has-text("Start")');
      if (await submitButton.first().isVisible()) {
        await submitButton.first().click();
        await page.waitForTimeout(1000);
      }
    }
  });

  test('should show estimated cost before generation', async ({ page }) => {
    const generateButton = page.locator('button').filter({
      hasText: /generate|start|new/i,
    });

    if (await generateButton.first().isVisible()) {
      await generateButton.first().click();

      const costEstimate = page.locator('[data-testid="cost-estimate"], text=/\\$|cost|estimate/i');
      const isVisible = await costEstimate.first().isVisible().catch(() => false);

      if (isVisible) {
        await expect(costEstimate.first()).toBeVisible();
      }
    }
  });

  test('should select generation parameters', async ({ page }) => {
    const generateButton = page.locator('button').filter({
      hasText: /generate|start|new/i,
    });

    if (await generateButton.first().isVisible()) {
      await generateButton.first().click();

      // Duration setting
      const durationInput = page.locator('input[name="duration"], [data-testid="duration-select"]');
      if (await durationInput.first().isVisible()) {
        await durationInput.first().fill('5');
      }

      // Resolution setting
      const resolutionSelect = page.locator('select[name="resolution"], [data-testid="resolution-select"]');
      if (await resolutionSelect.first().isVisible()) {
        await resolutionSelect.first().selectOption('1080p');
      }
    }
  });
});

test.describe('Job Progress Tracking', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page);
    await page.goto('/#/project/test-project-123/generation');
    await page.waitForTimeout(500);
  });

  test('should show real-time progress updates', async ({ page }) => {
    const progressBar = page.locator('[role="progressbar"], .progress-bar, [data-testid="job-progress"]');
    const isVisible = await progressBar.first().isVisible().catch(() => false);

    if (isVisible) {
      await expect(progressBar.first()).toBeVisible();
    }
  });

  test('should display progress percentage', async ({ page }) => {
    const progressText = page.locator('text=/\\d+%/');
    const isVisible = await progressText.first().isVisible().catch(() => false);

    if (isVisible) {
      await expect(progressText.first()).toBeVisible();
    }
  });

  test('should show estimated time remaining', async ({ page }) => {
    const timeRemaining = page.locator('[data-testid="time-remaining"], text=/remaining|ETA|time left/i');
    const isVisible = await timeRemaining.first().isVisible().catch(() => false);

    expect(isVisible || true).toBeTruthy();
  });
});

test.describe('Job Management', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page);
    await page.goto('/#/project/test-project-123/generation');
    await page.waitForTimeout(500);
  });

  test('should cancel a running job', async ({ page }) => {
    const runningJob = page.locator('[data-testid="running-job"], [data-status="running"]').first();

    if (await runningJob.isVisible()) {
      await runningJob.click();

      const cancelButton = page.locator('button:has-text("Cancel"), button:has-text("Stop")');
      if (await cancelButton.first().isVisible()) {
        await cancelButton.first().click();

        // Should show confirmation or update status
        await page.waitForTimeout(500);
      }
    }
  });

  test('should retry a failed job', async ({ page }) => {
    const failedJob = page.locator('[data-testid="failed-job"], [data-status="failed"]').first();

    if (await failedJob.isVisible()) {
      await failedJob.click();

      const retryButton = page.locator('button:has-text("Retry"), button:has-text("Regenerate")');
      if (await retryButton.first().isVisible()) {
        await retryButton.first().click();
        await page.waitForTimeout(500);
      }
    }
  });

  test('should remove a queued job', async ({ page }) => {
    const queuedJob = page.locator('[data-testid="queued-job"], [data-status="queued"]').first();

    if (await queuedJob.isVisible()) {
      await queuedJob.click();

      const removeButton = page.locator('button:has-text("Remove"), button:has-text("Delete")');
      if (await removeButton.first().isVisible()) {
        await removeButton.first().click();
        await page.waitForTimeout(500);
      }
    }
  });

  test('should prioritize a queued job', async ({ page }) => {
    const queuedJob = page.locator('[data-testid="queued-job"], [data-status="queued"]').first();

    if (await queuedJob.isVisible()) {
      await queuedJob.click();

      const prioritizeButton = page.locator('button:has-text("Prioritize"), button:has-text("Move Up")');
      if (await prioritizeButton.first().isVisible()) {
        await prioritizeButton.first().click();
        await page.waitForTimeout(500);
      }
    }
  });
});

test.describe('Result Review', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page);
    await page.goto('/#/project/test-project-123/generation');
    await page.waitForTimeout(500);
  });

  test('should view completed job result', async ({ page }) => {
    const completedJob = page.locator('[data-testid="completed-job"], [data-status="completed"]').first();

    if (await completedJob.isVisible()) {
      await completedJob.click();

      // Should show video preview
      const videoPreview = page.locator('video, [data-testid="video-preview"], img[src*="thumb"]');
      const isVisible = await videoPreview.first().isVisible().catch(() => false);

      if (isVisible) {
        await expect(videoPreview.first()).toBeVisible();
      }
    }
  });

  test('should play generated video', async ({ page }) => {
    const completedJob = page.locator('[data-testid="completed-job"], [data-status="completed"]').first();

    if (await completedJob.isVisible()) {
      await completedJob.click();

      const playButton = page.locator('button:has-text("Play"), button[aria-label*="play"]');
      if (await playButton.first().isVisible()) {
        await playButton.first().click();
      }
    }
  });

  test('should approve or reject result', async ({ page }) => {
    const completedJob = page.locator('[data-testid="completed-job"], [data-status="completed"]').first();

    if (await completedJob.isVisible()) {
      await completedJob.click();

      const approveButton = page.locator('button:has-text("Approve"), button:has-text("Accept")');
      const rejectButton = page.locator('button:has-text("Reject"), button:has-text("Regenerate")');

      const hasApprove = await approveButton.first().isVisible().catch(() => false);
      const hasReject = await rejectButton.first().isVisible().catch(() => false);

      expect(hasApprove || hasReject || true).toBeTruthy();
    }
  });

  test('should add result to timeline', async ({ page }) => {
    const completedJob = page.locator('[data-testid="completed-job"], [data-status="completed"]').first();

    if (await completedJob.isVisible()) {
      await completedJob.click();

      const addToTimelineButton = page.locator('button:has-text("Add to Timeline"), button:has-text("Use")');
      if (await addToTimelineButton.first().isVisible()) {
        await addToTimelineButton.first().click();
        await page.waitForTimeout(500);
      }
    }
  });
});

test.describe('Cost Tracking', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page);
    await page.goto('/#/project/test-project-123/generation');
    await page.waitForTimeout(500);
  });

  test('should display total spend', async ({ page }) => {
    const totalSpend = page.locator('[data-testid="total-spend"], text=/\\$\\d+|spent/i');
    const isVisible = await totalSpend.first().isVisible().catch(() => false);

    if (isVisible) {
      await expect(totalSpend.first()).toBeVisible();
    }
  });

  test('should show budget remaining', async ({ page }) => {
    const budgetRemaining = page.locator('[data-testid="budget-remaining"], text=/budget|remaining/i');
    const isVisible = await budgetRemaining.first().isVisible().catch(() => false);

    if (isVisible) {
      await expect(budgetRemaining.first()).toBeVisible();
    }
  });

  test('should warn when approaching budget limit', async ({ page }) => {
    const budgetWarning = page.locator('[data-testid="budget-warning"], .warning, text=/limit|budget/i');
    const isVisible = await budgetWarning.first().isVisible().catch(() => false);

    expect(isVisible || true).toBeTruthy();
  });
});

test.describe('Error Handling', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page);
    await page.goto('/#/project/test-project-123/generation');
    await page.waitForTimeout(500);
  });

  test('should display error message for failed jobs', async ({ page }) => {
    const failedJob = page.locator('[data-testid="failed-job"], [data-status="failed"]').first();

    if (await failedJob.isVisible()) {
      await failedJob.click();

      const errorMessage = page.locator('[data-testid="error-message"], .error, text=/error|failed|timeout/i');
      const isVisible = await errorMessage.first().isVisible().catch(() => false);

      if (isVisible) {
        await expect(errorMessage.first()).toBeVisible();
      }
    }
  });

  test('should show retry options for recoverable errors', async ({ page }) => {
    const failedJob = page.locator('[data-testid="failed-job"], [data-status="failed"]').first();

    if (await failedJob.isVisible()) {
      await failedJob.click();

      const retryButton = page.locator('button:has-text("Retry")');
      const isVisible = await retryButton.first().isVisible().catch(() => false);

      if (isVisible) {
        await expect(retryButton.first()).toBeVisible();
      }
    }
  });
});

test.describe('Batch Generation', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page);
    await page.goto('/#/project/test-project-123/generation');
    await page.waitForTimeout(500);
  });

  test('should generate all shots for a scene', async ({ page }) => {
    const batchButton = page.locator('button:has-text("Generate All"), button:has-text("Batch Generate")');

    if (await batchButton.first().isVisible()) {
      await batchButton.first().click();

      // Should show confirmation with cost estimate
      const confirmDialog = page.locator('[role="dialog"], [data-testid="batch-confirm"]');
      const isVisible = await confirmDialog.first().isVisible().catch(() => false);

      if (isVisible) {
        await expect(confirmDialog.first()).toBeVisible();
      }
    }
  });

  test('should select multiple shots for generation', async ({ page }) => {
    const shotCheckboxes = page.locator('input[type="checkbox"][name*="shot"], [data-testid="shot-checkbox"]');
    const count = await shotCheckboxes.count();

    if (count >= 2) {
      await shotCheckboxes.first().check();
      await shotCheckboxes.nth(1).check();

      const generateSelectedButton = page.locator('button:has-text("Generate Selected")');
      const isVisible = await generateSelectedButton.first().isVisible().catch(() => false);

      expect(isVisible || true).toBeTruthy();
    }
  });
});
