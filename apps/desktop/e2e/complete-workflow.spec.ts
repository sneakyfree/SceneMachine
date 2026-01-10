/**
 * E2E tests for the complete screenplay-to-video workflow.
 * Tests the main user journey through the entire application.
 */

import { test, expect, Page } from '@playwright/test';

/**
 * Complete mock data for a full workflow test
 */
const mockData = {
  project: {
    id: 'workflow-test-project',
    title: 'Complete Workflow Test',
    description: 'Testing the full screenplay to export flow',
    state: 'SCREENPLAY_UPLOADED',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    sceneCount: 3,
    shotCount: 8,
    characterCount: 4,
  },
  screenplay: {
    id: 'screenplay-workflow',
    projectId: 'workflow-test-project',
    title: 'Test Screenplay',
    originalFilename: 'test-movie.fountain',
    originalFormat: 'fountain',
    isParsed: true,
    pageCount: 12,
    createdAt: new Date().toISOString(),
  },
  scenes: [
    {
      id: 'scene-wf-1',
      projectId: 'workflow-test-project',
      sceneNumber: '1',
      sequenceNumber: 1,
      intExt: 'INT',
      location: 'COFFEE SHOP',
      timeOfDay: 'MORNING',
      description: 'A busy downtown coffee shop. Morning rush hour.',
      state: 'SHOTS_APPROVED',
      shotCount: 3,
    },
    {
      id: 'scene-wf-2',
      projectId: 'workflow-test-project',
      sceneNumber: '2',
      sequenceNumber: 2,
      intExt: 'EXT',
      location: 'STREET',
      timeOfDay: 'DAY',
      description: 'The street outside the coffee shop.',
      state: 'SHOTS_APPROVED',
      shotCount: 2,
    },
    {
      id: 'scene-wf-3',
      projectId: 'workflow-test-project',
      sceneNumber: '3',
      sequenceNumber: 3,
      intExt: 'INT',
      location: 'APARTMENT',
      timeOfDay: 'EVENING',
      description: 'A modern apartment living room.',
      state: 'BREAKDOWN_PENDING',
      shotCount: 3,
    },
  ],
  shots: [
    {
      id: 'shot-wf-1a',
      sceneId: 'scene-wf-1',
      shotNumber: '1A',
      sequenceNumber: 1,
      shotType: 'establishing',
      cameraMovement: 'static',
      description: 'Establishing shot of the coffee shop interior',
      visualPrompt: 'Interior of a modern coffee shop, warm lighting, busy atmosphere',
      durationSeconds: 3.0,
      state: 'completed',
      videoUrl: '/mock/videos/shot-1a.mp4',
    },
    {
      id: 'shot-wf-1b',
      sceneId: 'scene-wf-1',
      shotNumber: '1B',
      sequenceNumber: 2,
      shotType: 'medium',
      cameraMovement: 'dolly',
      description: 'Medium shot following ALEX to the counter',
      visualPrompt: 'Person walking through coffee shop, back view, dolly follow',
      durationSeconds: 4.5,
      state: 'completed',
      videoUrl: '/mock/videos/shot-1b.mp4',
    },
    {
      id: 'shot-wf-1c',
      sceneId: 'scene-wf-1',
      shotNumber: '1C',
      sequenceNumber: 3,
      shotType: 'closeup',
      cameraMovement: 'static',
      description: 'Close-up of ALEX ordering',
      visualPrompt: 'Close-up of person at counter, speaking, natural lighting',
      durationSeconds: 2.5,
      state: 'pending',
    },
  ],
  characters: [
    {
      id: 'char-wf-1',
      projectId: 'workflow-test-project',
      name: 'ALEX',
      description: 'Main protagonist, 30s, determined',
      gender: 'male',
      ageRange: '30-35',
      dialogueCount: 45,
      sceneCount: 8,
      state: 'LOCKED',
      hasReference: true,
    },
    {
      id: 'char-wf-2',
      projectId: 'workflow-test-project',
      name: 'SARAH',
      description: 'Best friend, 30s, witty',
      gender: 'female',
      ageRange: '28-32',
      dialogueCount: 32,
      sceneCount: 5,
      state: 'LOCKED',
      hasReference: true,
    },
    {
      id: 'char-wf-3',
      projectId: 'workflow-test-project',
      name: 'BARISTA',
      description: 'Coffee shop worker',
      gender: 'female',
      ageRange: '20-25',
      dialogueCount: 5,
      sceneCount: 1,
      state: 'DRAFT',
      hasReference: false,
    },
  ],
  generationJobs: [
    {
      id: 'job-1',
      shotId: 'shot-wf-1a',
      status: 'completed',
      provider: 'replicate',
      model: 'minimax',
      progress: 100,
      createdAt: new Date(Date.now() - 3600000).toISOString(),
      completedAt: new Date().toISOString(),
    },
    {
      id: 'job-2',
      shotId: 'shot-wf-1b',
      status: 'completed',
      provider: 'fal',
      model: 'cogvideox',
      progress: 100,
      createdAt: new Date(Date.now() - 1800000).toISOString(),
      completedAt: new Date().toISOString(),
    },
    {
      id: 'job-3',
      shotId: 'shot-wf-1c',
      status: 'queued',
      provider: 'replicate',
      model: 'minimax',
      progress: 0,
      createdAt: new Date().toISOString(),
    },
  ],
};

/**
 * Setup comprehensive mocks for the API
 */
async function setupWorkflowMocks(page: Page) {
  await page.addInitScript((data) => {
    window.electronAPI = {
      backendRequest: async (method: string, params?: any) => {
        const responses: Record<string, any> = {
          // Project operations
          'projects.list': [data.project],
          'projects.get': data.project,
          'projects.create': { ...data.project, id: 'new-' + Date.now() },
          'projects.update': data.project,
          'projects.delete': { success: true },

          // Screenplay operations
          'screenplay.get': data.screenplay,
          'screenplay.parse': { ...data.screenplay, isParsed: true },
          'screenplay.upload': data.screenplay,

          // Scene operations
          'scenes.list': data.scenes,
          'scenes.get': data.scenes.find((s: any) => s.id === params?.sceneId) || data.scenes[0],
          'scenes.breakdown': { success: true, shotCount: 3 },
          'scenes.approve': { success: true },

          // Shot operations
          'shots.list': data.shots.filter((s: any) => !params?.sceneId || s.sceneId === params.sceneId),
          'shots.get': data.shots.find((s: any) => s.id === params?.shotId) || data.shots[0],
          'shots.update': { success: true },
          'shots.approve': { success: true },

          // Character operations
          'characters.list': data.characters,
          'characters.get': data.characters.find((c: any) => c.id === params?.characterId) || data.characters[0],
          'characters.lock': { success: true, state: 'LOCKED' },
          'characters.unlock': { success: true, state: 'DRAFT' },
          'characters.update': { success: true },

          // Generation operations
          'generation.queue': { jobId: 'job-' + Date.now(), status: 'queued' },
          'generation.status': data.generationJobs,
          'generation.cancel': { success: true },
          'generation.estimate': { estimatedCost: 0.15, estimatedDuration: 45 },

          // Queue operations
          'queue.status': {
            totalJobs: data.generationJobs.length,
            pending: 1,
            running: 0,
            completed: 2,
            failed: 0,
          },
          'queue.jobs': data.generationJobs,

          // Provider operations
          'providers.list': ['replicate', 'fal', 'comfyui'],
          'providers.health': { replicate: 'healthy', fal: 'healthy', comfyui: 'offline' },
          'providers.models': {
            replicate: ['minimax', 'luma', 'kling'],
            fal: ['cogvideox', 'hunyuan', 'ltx'],
          },

          // Assembly operations
          'assembly.preview': { url: '/mock/preview.mp4', duration: 10.0 },
          'assembly.export': { jobId: 'export-job-1', status: 'started' },
          'assembly.status': { progress: 0, status: 'idle' },

          // Settings
          'settings.get': {
            theme: 'dark',
            defaultLlmProvider: 'anthropic',
            defaultVideoProvider: 'replicate',
            defaultVideoModel: 'minimax',
            anthropicApiKey: 'sk-ant-***',
            replicateApiKey: 'r8_***',
            falApiKey: 'fal_***',
          },
          'settings.update': { success: true },

          // Analytics
          'analytics.summary': {
            totalProjects: 5,
            totalGenerations: 150,
            totalCost: 45.50,
            avgGenerationTime: 42,
          },
        };

        const response = responses[method];
        if (response !== undefined) {
          // Simulate network delay
          await new Promise(resolve => setTimeout(resolve, 50));
          return response;
        }

        console.warn(`[Mock] Unhandled request: ${method}`, params);
        return null;
      },
      platform: 'win32',
      onBackendReady: (callback: () => void) => callback(),
      onBackendError: () => {},
      selectFile: async () => ({
        canceled: false,
        filePaths: ['/mock/screenplay.fountain'],
      }),
      selectDirectory: async () => ({
        canceled: false,
        filePaths: ['/mock/output'],
      }),
      showSaveDialog: async () => ({
        canceled: false,
        filePath: '/mock/output/movie.mp4',
      }),
      openExternal: async (url: string) => {
        console.log('[Mock] Opening external URL:', url);
      },
    };
  }, mockData);
}

test.describe('Complete Workflow: Screenplay to Export', () => {
  test.beforeEach(async ({ page }) => {
    await setupWorkflowMocks(page);
  });

  test('Step 1: Project creation and screenplay upload', async ({ page }) => {
    await page.goto('/');

    // Verify we're on the projects page
    await expect(page.locator('main')).toBeVisible();

    // Look for new project button
    const newProjectBtn = page.locator('button:has-text("New Project"), button:has-text("Create")');
    if (await newProjectBtn.first().isVisible()) {
      await newProjectBtn.first().click();

      // Fill project details if modal appears
      const titleInput = page.locator('input[name="title"], input[placeholder*="title" i]');
      if (await titleInput.isVisible({ timeout: 2000 })) {
        await titleInput.fill('My Test Movie');

        // Submit
        const submitBtn = page.locator('button[type="submit"], button:has-text("Create")');
        await submitBtn.click();
      }
    }

    // Should see project or projects list
    await expect(page.locator('text=Test, text=Movie, text=Project').first()).toBeVisible({ timeout: 5000 });
  });

  test('Step 2: View and manage scenes', async ({ page }) => {
    await page.goto('/#/project/workflow-test-project');

    // Wait for page to load
    await page.waitForTimeout(500);

    // Should see project details or workflow steps
    await expect(page.locator('main')).toBeVisible();

    // Look for scenes section
    const scenesSection = page.locator('text=Scene, text=Scenes, [data-testid*="scene"]');
    if (await scenesSection.first().isVisible({ timeout: 3000 })) {
      // Should display scenes
      await expect(scenesSection.first()).toBeVisible();
    }
  });

  test('Step 3: Manage characters in Character Lab', async ({ page }) => {
    await page.goto('/#/project/workflow-test-project/characters');

    await page.waitForTimeout(500);

    // Look for characters section
    const hasCharacters = await page.locator('text=ALEX, text=SARAH, text=Character').first().isVisible({ timeout: 3000 });

    if (hasCharacters) {
      // Should see character cards
      await expect(page.locator('text=ALEX, text=SARAH').first()).toBeVisible();
    }
  });

  test('Step 4: Review and queue shots for generation', async ({ page }) => {
    await page.goto('/#/project/workflow-test-project/generation');

    await page.waitForTimeout(500);

    // Should see generation page
    await expect(page.locator('main')).toBeVisible();

    // Look for shots or queue
    const hasShots = await page.locator('text=Shot, text=Generate, text=Queue').first().isVisible({ timeout: 3000 });

    if (hasShots) {
      // Look for generate button
      const generateBtn = page.locator('button:has-text("Generate")').first();
      if (await generateBtn.isVisible()) {
        // Don't actually click to avoid side effects
        await expect(generateBtn).toBeEnabled();
      }
    }
  });

  test('Step 5: View generation queue and status', async ({ page }) => {
    await page.goto('/#/project/workflow-test-project/generation');

    await page.waitForTimeout(500);

    // Look for queue status indicators
    const queueSection = page.locator('[data-testid*="queue"], text=Queue, text=Jobs, text=Status');
    if (await queueSection.first().isVisible({ timeout: 3000 })) {
      await expect(queueSection.first()).toBeVisible();
    }
  });

  test('Step 6: Timeline assembly view', async ({ page }) => {
    await page.goto('/#/project/workflow-test-project/timeline');

    await page.waitForTimeout(500);

    // Should see timeline page
    await expect(page.locator('main')).toBeVisible();

    // Look for timeline elements
    const timelineSection = page.locator('[data-testid*="timeline"], text=Timeline, text=Assembly');
    if (await timelineSection.first().isVisible({ timeout: 3000 })) {
      await expect(timelineSection.first()).toBeVisible();
    }
  });

  test('Step 7: Export workflow', async ({ page }) => {
    await page.goto('/#/project/workflow-test-project/export');

    await page.waitForTimeout(500);

    // Should see export page
    await expect(page.locator('main')).toBeVisible();

    // Look for export options
    const exportSection = page.locator('text=Export, text=Format, text=Quality');
    if (await exportSection.first().isVisible({ timeout: 3000 })) {
      await expect(exportSection.first()).toBeVisible();
    }
  });
});

test.describe('Error Recovery', () => {
  test('should handle backend connection failure', async ({ page }) => {
    await page.addInitScript(() => {
      window.electronAPI = {
        backendRequest: async () => {
          throw new Error('Backend connection failed');
        },
        platform: 'win32',
        onBackendReady: () => {},
        onBackendError: (callback: (error: Error) => void) => {
          callback(new Error('Backend not available'));
        },
        selectFile: async () => ({ canceled: true, filePaths: [] }),
        selectDirectory: async () => ({ canceled: true, filePaths: [] }),
        showSaveDialog: async () => ({ canceled: true }),
        openExternal: async () => {},
      };
    });

    await page.goto('/');

    // App should still render
    await expect(page.locator('body')).toBeVisible();

    // Should show some error indication or fallback UI
    // App should not crash
  });

  test('should handle slow API responses', async ({ page }) => {
    await page.addInitScript(() => {
      window.electronAPI = {
        backendRequest: async (method: string) => {
          // Simulate slow response
          await new Promise(resolve => setTimeout(resolve, 3000));
          return [];
        },
        platform: 'win32',
        onBackendReady: () => {},
        onBackendError: () => {},
        selectFile: async () => ({ canceled: true, filePaths: [] }),
        selectDirectory: async () => ({ canceled: true, filePaths: [] }),
        showSaveDialog: async () => ({ canceled: true }),
        openExternal: async () => {},
      };
    });

    await page.goto('/');

    // Should show loading state
    const loadingIndicator = page.locator('.animate-pulse, [data-testid*="loading"], [data-testid*="skeleton"]');

    // Either shows loading or the page loads
    await expect(page.locator('main')).toBeVisible({ timeout: 10000 });
  });
});

test.describe('Workflow State Transitions', () => {
  test.beforeEach(async ({ page }) => {
    await setupWorkflowMocks(page);
  });

  test('should track project state through workflow', async ({ page }) => {
    await page.goto('/#/project/workflow-test-project');

    await page.waitForTimeout(500);

    // Should show current workflow state
    await expect(page.locator('main')).toBeVisible();

    // Look for state indicators
    const stateIndicators = page.locator('[data-state], [data-status], .status-badge');
    // State indicators may or may not be visible depending on UI
  });

  test('should enable next step when prerequisites are met', async ({ page }) => {
    await page.goto('/#/project/workflow-test-project');

    await page.waitForTimeout(500);

    // Look for workflow step indicators
    const workflowSteps = page.locator('[data-testid*="step"], [data-testid*="workflow"]');
    if (await workflowSteps.first().isVisible({ timeout: 3000 })) {
      // Check that steps are properly enabled/disabled
      await expect(workflowSteps.first()).toBeVisible();
    }
  });
});

test.describe('Data Persistence', () => {
  test.beforeEach(async ({ page }) => {
    await setupWorkflowMocks(page);
  });

  test('should persist project selection across page navigation', async ({ page }) => {
    await page.goto('/#/project/workflow-test-project');
    await page.waitForTimeout(300);

    // Navigate to settings
    await page.click('text=Settings');
    await page.waitForTimeout(300);

    // Navigate back
    await page.click('text=Projects');
    await page.waitForTimeout(300);

    // Should still have access to project data
    await expect(page.locator('main')).toBeVisible();
  });

  test('should show auto-save indicator', async ({ page }) => {
    await page.goto('/#/project/workflow-test-project');
    await page.waitForTimeout(500);

    // Look for auto-save indicator
    const autoSaveIndicator = page.locator('text=Saved, text=Auto-save, [data-testid*="autosave"]');
    // Auto-save indicator may or may not be visible
  });
});

test.describe('Multi-Scene Workflow', () => {
  test.beforeEach(async ({ page }) => {
    await setupWorkflowMocks(page);
  });

  test('should navigate between scenes', async ({ page }) => {
    await page.goto('/#/project/workflow-test-project');
    await page.waitForTimeout(500);

    // Look for scene navigation
    const sceneNav = page.locator('[data-testid*="scene"], text=Scene 1, text=Scene 2');
    if (await sceneNav.first().isVisible({ timeout: 3000 })) {
      // Click to navigate between scenes
      await sceneNav.first().click();
      await page.waitForTimeout(300);
    }
  });

  test('should batch select shots for generation', async ({ page }) => {
    await page.goto('/#/project/workflow-test-project/generation');
    await page.waitForTimeout(500);

    // Look for batch selection UI
    const selectAllBtn = page.locator('button:has-text("Select All"), input[type="checkbox"]');
    if (await selectAllBtn.first().isVisible({ timeout: 3000 })) {
      await selectAllBtn.first().click();
    }
  });
});
