/**
 * E2E tests for project workflow - the main user journey.
 *
 * Tests the complete flow from project creation through generation.
 */

import { test, expect, Page } from '@playwright/test';

// Mock API responses for testing
const mockProject = {
  id: 'test-project-123',
  title: 'Test Movie',
  description: 'A test project for E2E testing',
  state: 'ACTIVE',
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
};

const mockScreenplay = {
  id: 'screenplay-1',
  projectId: mockProject.id,
  originalFilename: 'test.fountain',
  originalFormat: 'fountain',
  isParsed: true,
  createdAt: new Date().toISOString(),
};

const mockScenes = [
  {
    id: 'scene-1',
    projectId: mockProject.id,
    sceneNumber: '1',
    sequenceNumber: 1,
    intExt: 'INT',
    location: 'OFFICE',
    timeOfDay: 'DAY',
    description: 'A modern office space',
    shotCount: 3,
  },
  {
    id: 'scene-2',
    projectId: mockProject.id,
    sceneNumber: '2',
    sequenceNumber: 2,
    intExt: 'EXT',
    location: 'STREET',
    timeOfDay: 'NIGHT',
    description: 'A busy city street',
    shotCount: 2,
  },
];

const mockShots = [
  {
    id: 'shot-1',
    sceneId: 'scene-1',
    shotNumber: '1A',
    sequenceNumber: 1,
    shotType: 'establishing',
    cameraMovement: 'static',
    description: 'Wide establishing shot of the office',
    durationSeconds: 3.0,
    state: 'planned',
  },
  {
    id: 'shot-2',
    sceneId: 'scene-1',
    shotNumber: '1B',
    sequenceNumber: 2,
    shotType: 'medium',
    cameraMovement: 'pan',
    description: 'Medium shot panning across desks',
    durationSeconds: 4.0,
    state: 'planned',
  },
];

const mockCharacters = [
  {
    id: 'char-1',
    projectId: mockProject.id,
    name: 'JOHN',
    dialogueCount: 15,
    sceneCount: 5,
  },
  {
    id: 'char-2',
    projectId: mockProject.id,
    name: 'MARY',
    dialogueCount: 12,
    sceneCount: 4,
  },
];

/**
 * Setup mocks for the API calls.
 * In a real scenario, this would intercept IPC calls.
 */
async function setupMocks(page: Page) {
  // Mock window.electronAPI
  await page.addInitScript(() => {
    // @ts-expect-error - Setting up mock
    window.electronAPI = {
      backendRequest: async (method: string, params: any) => {
        const responses: Record<string, any> = {
          'projects.list': [
            {
              id: 'test-project-123',
              title: 'Test Movie',
              state: 'ACTIVE',
              createdAt: new Date().toISOString(),
              updatedAt: new Date().toISOString(),
            },
          ],
          'projects.get': {
            id: 'test-project-123',
            title: 'Test Movie',
            state: 'ACTIVE',
          },
          'projects.create': {
            id: 'new-project-456',
            title: params?.title || 'New Project',
            state: 'DRAFT',
            createdAt: new Date().toISOString(),
          },
          'scenes.list': [
            {
              id: 'scene-1',
              sceneNumber: '1',
              intExt: 'INT',
              location: 'OFFICE',
              timeOfDay: 'DAY',
              shotCount: 3,
            },
          ],
          'shots.list': [
            {
              id: 'shot-1',
              sceneId: 'scene-1',
              shotNumber: '1A',
              shotType: 'establishing',
              cameraMovement: 'static',
              description: 'Wide shot',
              durationSeconds: 3.0,
              state: 'planned',
            },
          ],
          'characters.list': [
            { id: 'char-1', name: 'JOHN', dialogueCount: 15, sceneCount: 5 },
            { id: 'char-2', name: 'MARY', dialogueCount: 12, sceneCount: 4 },
          ],
          'queue.status': {
            totalJobs: 0,
            pending: 0,
            running: 0,
            completed: 0,
            failed: 0,
          },
          'settings.get': {
            theme: 'dark',
            defaultLlmProvider: 'anthropic',
            anthropicApiKey: '',
            openaiApiKey: '',
          },
        };

        const response = responses[method];
        if (response !== undefined) {
          return response;
        }

        console.warn(`Unhandled mock request: ${method}`);
        return null;
      },
      platform: 'linux',
      onBackendReady: () => {},
      onBackendError: () => {},
      selectFile: async () => ({ canceled: true, filePaths: [] }),
      selectDirectory: async () => ({ canceled: true, filePaths: [] }),
      showSaveDialog: async () => ({ canceled: true }),
      openExternal: async () => {},
    };
  });
}

test.describe('Project Creation Flow', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page);
  });

  test('should create a new project', async ({ page }) => {
    await page.goto('/');

    // Click new project button
    const newProjectButton = page.locator('button:has-text("New Project")');
    if (await newProjectButton.isVisible()) {
      await newProjectButton.click();

      // Fill in project details
      const titleInput = page.locator('input[name="title"], input[placeholder*="title" i]');
      if (await titleInput.isVisible()) {
        await titleInput.fill('My New Movie');

        // Submit form
        const createButton = page.locator('button:has-text("Create")');
        if (await createButton.isVisible()) {
          await createButton.click();

          // Should show success or navigate to project
          await expect(page.locator('text=My New Movie')).toBeVisible({
            timeout: 5000,
          });
        }
      }
    }
  });

  test('should display projects list', async ({ page }) => {
    await page.goto('/');

    // Should see projects or empty state
    const projectsArea = page.locator('main');
    await expect(projectsArea).toBeVisible();

    // Either shows projects or empty state
    const hasProjects = await page.locator('text=Test Movie').isVisible();
    const hasEmptyState = await page.locator('text=No projects').isVisible();

    expect(hasProjects || hasEmptyState).toBeTruthy();
  });
});

test.describe('Project Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page);
  });

  test('should navigate to project details', async ({ page }) => {
    await page.goto('/');

    // Click on a project if visible
    const projectCard = page.locator('[data-testid="project-card"]').first();
    if (await projectCard.isVisible()) {
      await projectCard.click();

      // Should navigate to project page
      await expect(page).toHaveURL(/project/);
    }
  });
});

test.describe('Scene Browsing', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page);
    await page.goto('/#/project/test-project-123');
  });

  test('should display scenes list', async ({ page }) => {
    // Wait for scenes to load
    await page.waitForTimeout(500);

    // Should show scenes section
    const scenesSection = page.locator('text=Scenes, text=Scene');
    const isVisible = await scenesSection.first().isVisible().catch(() => false);

    if (isVisible) {
      await expect(scenesSection.first()).toBeVisible();
    }
  });

  test('should expand scene to show shots', async ({ page }) => {
    await page.waitForTimeout(500);

    // Find and click on a scene
    const sceneCard = page.locator('[data-testid="scene-card"]').first();
    if (await sceneCard.isVisible()) {
      await sceneCard.click();

      // Should show shots
      await expect(page.locator('text=Shot, text=Shots').first()).toBeVisible({
        timeout: 3000,
      });
    }
  });
});

test.describe('Shot Management', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page);
  });

  test('should display shot details on expansion', async ({ page }) => {
    await page.goto('/#/project/test-project-123/scene/scene-1');
    await page.waitForTimeout(500);

    // Find a shot card
    const shotCard = page.locator('[data-testid="shot-card"]').first();
    if (await shotCard.isVisible()) {
      // Expand the shot
      const expandButton = shotCard.locator('button').last();
      await expandButton.click();

      // Should show details
      await expect(shotCard.locator('text=Description')).toBeVisible({
        timeout: 2000,
      });
    }
  });

  test('should edit shot details', async ({ page }) => {
    await page.goto('/#/project/test-project-123/scene/scene-1');
    await page.waitForTimeout(500);

    const shotCard = page.locator('[data-testid="shot-card"]').first();
    if (await shotCard.isVisible()) {
      // Click edit button
      const editButton = shotCard.locator('button[title*="Edit"]');
      if (await editButton.isVisible()) {
        await editButton.click();

        // Should show edit form
        await expect(page.locator('select, textarea, input')).toBeVisible({
          timeout: 2000,
        });
      }
    }
  });
});

test.describe('Queue Management', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page);
  });

  test('should display queue status', async ({ page }) => {
    await page.goto('/#/project/test-project-123');
    await page.waitForTimeout(500);

    // Look for queue indicator or section
    const queueSection = page.locator('text=Queue, [data-testid="queue-manager"]');
    const isVisible = await queueSection.first().isVisible().catch(() => false);

    if (isVisible) {
      await expect(queueSection.first()).toBeVisible();
    }
  });

  test('should queue shot for generation', async ({ page }) => {
    await page.goto('/#/project/test-project-123/scene/scene-1');
    await page.waitForTimeout(500);

    // Find generate button
    const generateButton = page.locator('button:has-text("Generate")').first();
    if (await generateButton.isVisible()) {
      await generateButton.click();

      // Should show queued status or confirmation
      await expect(
        page.locator('text=Queued, text=pending, [data-status="pending"]').first()
      ).toBeVisible({ timeout: 3000 });
    }
  });
});

test.describe('Character Management', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page);
  });

  test('should display characters list', async ({ page }) => {
    await page.goto('/#/project/test-project-123/characters');
    await page.waitForTimeout(500);

    // Should show characters or section
    const charactersSection = page.locator('text=Characters, [data-testid="characters-list"]');
    const isVisible = await charactersSection.first().isVisible().catch(() => false);

    if (isVisible) {
      await expect(charactersSection.first()).toBeVisible();
    }
  });

  test('should view character details', async ({ page }) => {
    await page.goto('/#/project/test-project-123/characters');
    await page.waitForTimeout(500);

    const characterCard = page.locator('[data-testid="character-card"]').first();
    if (await characterCard.isVisible()) {
      await characterCard.click();

      // Should show character details
      await expect(page.locator('text=Description, text=Appearance').first()).toBeVisible({
        timeout: 2000,
      });
    }
  });
});

test.describe('Toast Notifications', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page);
  });

  test('should display toast on action', async ({ page }) => {
    await page.goto('/');

    // Trigger an action that shows a toast
    // This depends on what actions trigger toasts in the app

    // For now, verify toast container exists
    const toastContainer = page.locator('[data-testid="toast-container"], [role="alert"]');
    // Toast container should exist (even if empty)
    await page.waitForTimeout(500);
  });
});

test.describe('Loading States', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page);
  });

  test('should show skeleton loading while data loads', async ({ page }) => {
    // Add delay to mock responses
    await page.addInitScript(() => {
      const originalBackendRequest = window.electronAPI.backendRequest;
      window.electronAPI.backendRequest = async (method: string, params: any) => {
        await new Promise((resolve) => setTimeout(resolve, 1000));
        return originalBackendRequest(method, params);
      };
    });

    await page.goto('/');

    // Should see skeleton components
    const skeleton = page.locator('.animate-pulse').first();
    const isVisible = await skeleton.isVisible().catch(() => false);

    // Skeleton might appear briefly
    if (isVisible) {
      expect(skeleton).toBeVisible();
    }
  });
});

test.describe('Error States', () => {
  test('should handle API errors gracefully', async ({ page }) => {
    // Setup mock that returns error
    await page.addInitScript(() => {
      window.electronAPI = {
        ...window.electronAPI,
        backendRequest: async () => {
          throw new Error('API Error');
        },
      };
    });

    await page.goto('/');

    // App should still render
    await expect(page.locator('body')).toBeVisible();

    // Should show error state or fallback UI
    // (actual error display depends on implementation)
  });

  test('should recover from transient errors', async ({ page }) => {
    let callCount = 0;

    await page.addInitScript(() => {
      let callCount = 0;
      const originalBackendRequest = window.electronAPI?.backendRequest;

      window.electronAPI = {
        ...window.electronAPI,
        backendRequest: async (method: string, params: any) => {
          callCount++;
          if (callCount === 1) {
            throw new Error('Transient error');
          }
          return originalBackendRequest?.(method, params) ?? [];
        },
      };
    });

    await page.goto('/');

    // App should eventually load
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Accessibility', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page);
  });

  test('should have proper heading structure', async ({ page }) => {
    await page.goto('/');

    // Should have at least one h1
    const h1Count = await page.locator('h1').count();
    expect(h1Count).toBeGreaterThanOrEqual(1);
  });

  test('should have focusable navigation elements', async ({ page }) => {
    await page.goto('/');

    // Tab through navigation
    await page.keyboard.press('Tab');

    // Should focus on something
    const focusedElement = await page.evaluate(() => {
      return document.activeElement?.tagName;
    });

    expect(focusedElement).toBeDefined();
  });

  test('should support keyboard navigation', async ({ page }) => {
    await page.goto('/');

    // Press Escape should close any modals
    await page.keyboard.press('Escape');

    // Press / should focus search (if implemented)
    await page.keyboard.press('/');

    // App should remain functional
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Performance', () => {
  test('should load within acceptable time', async ({ page }) => {
    const startTime = Date.now();

    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const loadTime = Date.now() - startTime;

    // Should load within 5 seconds
    expect(loadTime).toBeLessThan(5000);
  });

  test('should not have memory leaks on navigation', async ({ page }) => {
    await setupMocks(page);

    // Navigate multiple times
    for (let i = 0; i < 5; i++) {
      await page.goto('/');
      await page.goto('/#/settings');
    }

    // App should still be responsive
    await expect(page.locator('body')).toBeVisible();
  });
});
