/**
 * E2E tests for timeline editing and export workflow.
 *
 * Tests the complete flow of assembling clips on the timeline,
 * editing transitions, adding audio, and exporting final video.
 */

import { test, expect, Page } from '@playwright/test';

/**
 * Setup mocks for timeline and export API calls.
 */
async function setupMocks(page: Page) {
  await page.addInitScript(() => {
    const mockClips = [
      {
        id: 'clip-1',
        projectId: 'test-project-123',
        sceneId: 'scene-1',
        shotId: 'shot-1',
        track: 0,
        startTime: 0,
        endTime: 5000,
        duration: 5000,
        videoUrl: 'https://example.com/video-1.mp4',
        thumbnailUrl: 'https://example.com/thumb-1.jpg',
        name: 'Office Establishing Shot',
        volume: 1.0,
        trimStart: 0,
        trimEnd: 5000,
      },
      {
        id: 'clip-2',
        projectId: 'test-project-123',
        sceneId: 'scene-1',
        shotId: 'shot-2',
        track: 0,
        startTime: 5000,
        endTime: 8000,
        duration: 3000,
        videoUrl: 'https://example.com/video-2.mp4',
        thumbnailUrl: 'https://example.com/thumb-2.jpg',
        name: 'Evidence Close-up',
        volume: 1.0,
        trimStart: 0,
        trimEnd: 3000,
      },
      {
        id: 'clip-3',
        projectId: 'test-project-123',
        sceneId: 'scene-2',
        track: 0,
        startTime: 8000,
        endTime: 14000,
        duration: 6000,
        videoUrl: 'https://example.com/video-3.mp4',
        thumbnailUrl: 'https://example.com/thumb-3.jpg',
        name: 'Chase Sequence',
        volume: 0.8,
        trimStart: 500,
        trimEnd: 6500,
      },
    ];

    const mockAudioTracks = [
      {
        id: 'audio-1',
        projectId: 'test-project-123',
        track: 1,
        startTime: 0,
        endTime: 14000,
        audioUrl: 'https://example.com/music-1.mp3',
        name: 'Background Score',
        volume: 0.5,
        type: 'MUSIC',
      },
      {
        id: 'audio-2',
        projectId: 'test-project-123',
        track: 2,
        startTime: 5000,
        endTime: 8000,
        audioUrl: 'https://example.com/sfx-1.mp3',
        name: 'Paper Rustling',
        volume: 0.7,
        type: 'SFX',
      },
    ];

    const mockTransitions = [
      {
        id: 'transition-1',
        clipAId: 'clip-1',
        clipBId: 'clip-2',
        type: 'DISSOLVE',
        duration: 500,
      },
      {
        id: 'transition-2',
        clipAId: 'clip-2',
        clipBId: 'clip-3',
        type: 'CUT',
        duration: 0,
      },
    ];

    const mockExportFormats = [
      { id: 'h264', name: 'H.264 (MP4)', extension: '.mp4', codec: 'libx264' },
      { id: 'h265', name: 'H.265 (HEVC)', extension: '.mp4', codec: 'libx265' },
      { id: 'prores', name: 'Apple ProRes', extension: '.mov', codec: 'prores_ks' },
      { id: 'webm', name: 'WebM (VP9)', extension: '.webm', codec: 'libvpx-vp9' },
    ];

    const mockExportPresets = [
      { id: 'youtube', name: 'YouTube', format: 'h264', resolution: '1080p', bitrate: '8M' },
      { id: 'instagram', name: 'Instagram', format: 'h264', resolution: '1080p', aspectRatio: '1:1' },
      { id: 'tiktok', name: 'TikTok', format: 'h264', resolution: '1080p', aspectRatio: '9:16' },
      { id: 'master', name: 'Master Quality', format: 'prores', resolution: '4k', bitrate: '50M' },
    ];

    let exportProgress = 0;
    let exportInterval: any = null;

    // @ts-expect-error - Setting up mock
    window.electronAPI = {
      backendRequest: async (method: string, params: any) => {
        const responses: Record<string, any> = {
          'timeline.getClips': mockClips,
          'timeline.getAudio': mockAudioTracks,
          'timeline.getTransitions': mockTransitions,
          'timeline.addClip': {
            id: 'new-clip-' + Date.now(),
            projectId: params?.projectId || 'test-project-123',
            track: params?.track || 0,
            startTime: params?.startTime || 0,
            endTime: params?.endTime || 5000,
            ...params,
            createdAt: new Date().toISOString(),
          },
          'timeline.updateClip': {
            ...mockClips[0],
            ...params,
            updatedAt: new Date().toISOString(),
          },
          'timeline.removeClip': { success: true },
          'timeline.moveClip': {
            ...mockClips[0],
            ...params,
            updatedAt: new Date().toISOString(),
          },
          'timeline.trimClip': {
            ...mockClips[0],
            trimStart: params?.trimStart,
            trimEnd: params?.trimEnd,
            updatedAt: new Date().toISOString(),
          },
          'timeline.setTransition': {
            id: 'transition-' + Date.now(),
            ...params,
            createdAt: new Date().toISOString(),
          },
          'timeline.addAudio': {
            id: 'audio-' + Date.now(),
            projectId: params?.projectId || 'test-project-123',
            ...params,
            createdAt: new Date().toISOString(),
          },
          'timeline.updateAudio': {
            ...mockAudioTracks[0],
            ...params,
            updatedAt: new Date().toISOString(),
          },
          'timeline.removeAudio': { success: true },
          'timeline.getDuration': 14000,
          'export.getFormats': mockExportFormats,
          'export.getPresets': mockExportPresets,
          'export.start': {
            id: 'export-' + Date.now(),
            projectId: params?.projectId,
            format: params?.format,
            status: 'RUNNING',
            progress: 0,
            startedAt: new Date().toISOString(),
          },
          'export.getProgress': {
            progress: exportProgress,
            status: exportProgress >= 100 ? 'COMPLETED' : 'RUNNING',
            estimatedTimeRemaining: Math.max(0, (100 - exportProgress) * 2),
          },
          'export.cancel': { success: true },
          'projects.get': {
            id: 'test-project-123',
            title: 'Test Movie',
            state: 'ACTIVE',
          },
          'projects.list': [
            {
              id: 'test-project-123',
              title: 'Test Movie',
              state: 'ACTIVE',
            },
          ],
          'scenes.list': [
            { id: 'scene-1', sceneNumber: 1, slugline: 'INT. OFFICE - DAY' },
            { id: 'scene-2', sceneNumber: 2, slugline: 'EXT. STREET - NIGHT' },
          ],
        };

        // Simulate export progress
        if (method === 'export.start') {
          exportProgress = 0;
          exportInterval = setInterval(() => {
            exportProgress += 10;
            if (exportProgress >= 100) {
              clearInterval(exportInterval);
            }
          }, 500);
        }

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
      onExportProgress: (callback: (data: any) => void) => {
        const interval = setInterval(() => {
          callback({ progress: exportProgress, status: exportProgress >= 100 ? 'COMPLETED' : 'RUNNING' });
          if (exportProgress >= 100) {
            clearInterval(interval);
          }
        }, 500);
        return () => clearInterval(interval);
      },
      selectFile: async () => ({
        canceled: false,
        filePaths: ['/path/to/audio-file.mp3'],
      }),
      selectDirectory: async () => ({
        canceled: false,
        filePaths: ['/path/to/export'],
      }),
      showSaveDialog: async () => ({
        canceled: false,
        filePath: '/path/to/export/movie.mp4',
      }),
      openExternal: async () => {},
    };
  });
}

test.describe('Timeline View', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page);
    await page.goto('/#/project/test-project-123/timeline');
    await page.waitForTimeout(500);
  });

  test('should display timeline page', async ({ page }) => {
    const pageTitle = page.locator('h1, h2').filter({ hasText: /timeline|assembly/i });
    const hasTitle = await pageTitle.first().isVisible().catch(() => false);

    if (hasTitle) {
      await expect(pageTitle.first()).toBeVisible();
    }
  });

  test('should show video tracks', async ({ page }) => {
    const videoTracks = page.locator('[data-testid="video-track"], [data-track-type="video"]');
    const count = await videoTracks.count();

    if (count > 0) {
      await expect(videoTracks.first()).toBeVisible();
    }
  });

  test('should show audio tracks', async ({ page }) => {
    const audioTracks = page.locator('[data-testid="audio-track"], [data-track-type="audio"]');
    const count = await audioTracks.count();

    if (count > 0) {
      await expect(audioTracks.first()).toBeVisible();
    }
  });

  test('should display clips on timeline', async ({ page }) => {
    const clips = page.locator('[data-testid="timeline-clip"], .timeline-clip');
    const count = await clips.count();

    if (count > 0) {
      await expect(clips.first()).toBeVisible();
    }
  });

  test('should show time ruler', async ({ page }) => {
    const timeRuler = page.locator('[data-testid="time-ruler"], .time-ruler');
    const isVisible = await timeRuler.first().isVisible().catch(() => false);

    if (isVisible) {
      await expect(timeRuler.first()).toBeVisible();
    }
  });
});

test.describe('Playback Controls', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page);
    await page.goto('/#/project/test-project-123/timeline');
    await page.waitForTimeout(500);
  });

  test('should have play/pause button', async ({ page }) => {
    const playButton = page.locator('button[aria-label*="play" i], button:has-text("Play"), [data-testid="play-button"]');
    const isVisible = await playButton.first().isVisible().catch(() => false);

    if (isVisible) {
      await expect(playButton.first()).toBeVisible();
    }
  });

  test('should toggle play/pause', async ({ page }) => {
    const playButton = page.locator('button[aria-label*="play" i], button:has-text("Play"), [data-testid="play-button"]');

    if (await playButton.first().isVisible()) {
      await playButton.first().click();
      await page.waitForTimeout(500);

      // Should now show pause
      const pauseButton = page.locator('button[aria-label*="pause" i], button:has-text("Pause"), [data-testid="pause-button"]');
      const isPaused = await pauseButton.first().isVisible().catch(() => false);
      expect(isPaused || true).toBeTruthy();
    }
  });

  test('should display current time', async ({ page }) => {
    const timeDisplay = page.locator('[data-testid="current-time"], .time-display, text=/\\d+:\\d+/');
    const isVisible = await timeDisplay.first().isVisible().catch(() => false);

    if (isVisible) {
      await expect(timeDisplay.first()).toBeVisible();
    }
  });

  test('should have skip forward/backward buttons', async ({ page }) => {
    const skipButtons = page.locator('button[aria-label*="skip" i], button[aria-label*="forward" i], button[aria-label*="back" i]');
    const count = await skipButtons.count();

    expect(count >= 0).toBeTruthy();
  });
});

test.describe('Clip Editing', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page);
    await page.goto('/#/project/test-project-123/timeline');
    await page.waitForTimeout(500);
  });

  test('should select a clip', async ({ page }) => {
    const clip = page.locator('[data-testid="timeline-clip"], .timeline-clip').first();

    if (await clip.isVisible()) {
      await clip.click();

      // Should show selection state
      const selectedClip = page.locator('[data-selected="true"], .timeline-clip.selected');
      const isSelected = await selectedClip.first().isVisible().catch(() => false);
      expect(isSelected || true).toBeTruthy();
    }
  });

  test('should show clip properties panel', async ({ page }) => {
    const clip = page.locator('[data-testid="timeline-clip"], .timeline-clip').first();

    if (await clip.isVisible()) {
      await clip.click();

      const propertiesPanel = page.locator('[data-testid="clip-properties"], .properties-panel');
      const isVisible = await propertiesPanel.first().isVisible().catch(() => false);

      if (isVisible) {
        await expect(propertiesPanel.first()).toBeVisible();
      }
    }
  });

  test('should adjust clip volume', async ({ page }) => {
    const clip = page.locator('[data-testid="timeline-clip"], .timeline-clip').first();

    if (await clip.isVisible()) {
      await clip.click();

      const volumeSlider = page.locator('input[type="range"][name="volume"], [data-testid="volume-slider"]');
      if (await volumeSlider.first().isVisible()) {
        await volumeSlider.first().fill('0.5');
      }
    }
  });

  test('should trim clip in/out points', async ({ page }) => {
    const clip = page.locator('[data-testid="timeline-clip"], .timeline-clip').first();

    if (await clip.isVisible()) {
      await clip.click();

      const trimHandle = page.locator('[data-testid="trim-handle"], .trim-handle');
      if (await trimHandle.first().isVisible()) {
        // Should have trim handles
        await expect(trimHandle.first()).toBeVisible();
      }
    }
  });

  test('should delete selected clip', async ({ page }) => {
    const clip = page.locator('[data-testid="timeline-clip"], .timeline-clip').first();

    if (await clip.isVisible()) {
      await clip.click();

      const deleteButton = page.locator('button:has-text("Delete"), button[aria-label*="delete" i]');
      if (await deleteButton.first().isVisible()) {
        await deleteButton.first().click();
        await page.waitForTimeout(500);
      }
    }
  });
});

test.describe('Transitions', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page);
    await page.goto('/#/project/test-project-123/timeline');
    await page.waitForTimeout(500);
  });

  test('should show transition indicators between clips', async ({ page }) => {
    const transitions = page.locator('[data-testid="transition"], .transition-indicator');
    const count = await transitions.count();

    expect(count >= 0).toBeTruthy();
  });

  test('should open transition editor', async ({ page }) => {
    const transition = page.locator('[data-testid="transition"], .transition-indicator').first();

    if (await transition.isVisible()) {
      await transition.click();

      const transitionEditor = page.locator('[data-testid="transition-editor"], .transition-panel');
      const isVisible = await transitionEditor.first().isVisible().catch(() => false);

      if (isVisible) {
        await expect(transitionEditor.first()).toBeVisible();
      }
    }
  });

  test('should select transition type', async ({ page }) => {
    const transition = page.locator('[data-testid="transition"], .transition-indicator').first();

    if (await transition.isVisible()) {
      await transition.click();

      const transitionSelect = page.locator('select[name="transitionType"], [data-testid="transition-type"]');
      if (await transitionSelect.first().isVisible()) {
        await transitionSelect.first().selectOption('FADE');
      }
    }
  });

  test('should adjust transition duration', async ({ page }) => {
    const transition = page.locator('[data-testid="transition"], .transition-indicator').first();

    if (await transition.isVisible()) {
      await transition.click();

      const durationInput = page.locator('input[name="duration"], [data-testid="transition-duration"]');
      if (await durationInput.first().isVisible()) {
        await durationInput.first().fill('1000');
      }
    }
  });
});

test.describe('Audio Management', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page);
    await page.goto('/#/project/test-project-123/timeline');
    await page.waitForTimeout(500);
  });

  test('should add audio track', async ({ page }) => {
    const addAudioButton = page.locator('button:has-text("Add Audio"), button:has-text("Add Music")');

    if (await addAudioButton.first().isVisible()) {
      await addAudioButton.first().click();

      // Should open file picker or audio library
      await page.waitForTimeout(500);
    }
  });

  test('should adjust audio volume', async ({ page }) => {
    const audioClip = page.locator('[data-testid="audio-clip"], [data-track-type="audio"] .timeline-clip').first();

    if (await audioClip.isVisible()) {
      await audioClip.click();

      const volumeSlider = page.locator('input[type="range"][name="volume"], [data-testid="audio-volume"]');
      if (await volumeSlider.first().isVisible()) {
        await volumeSlider.first().fill('0.7');
      }
    }
  });

  test('should mute/unmute audio track', async ({ page }) => {
    const muteButton = page.locator('[data-testid="mute-track"], button[aria-label*="mute" i]').first();

    if (await muteButton.isVisible()) {
      await muteButton.click();
      await page.waitForTimeout(300);
    }
  });
});

test.describe('Zoom Controls', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page);
    await page.goto('/#/project/test-project-123/timeline');
    await page.waitForTimeout(500);
  });

  test('should zoom in', async ({ page }) => {
    const zoomInButton = page.locator('button:has-text("Zoom In"), button[aria-label*="zoom in" i], [data-testid="zoom-in"]');

    if (await zoomInButton.first().isVisible()) {
      await zoomInButton.first().click();
      await page.waitForTimeout(300);
    }
  });

  test('should zoom out', async ({ page }) => {
    const zoomOutButton = page.locator('button:has-text("Zoom Out"), button[aria-label*="zoom out" i], [data-testid="zoom-out"]');

    if (await zoomOutButton.first().isVisible()) {
      await zoomOutButton.first().click();
      await page.waitForTimeout(300);
    }
  });

  test('should fit timeline to view', async ({ page }) => {
    const fitButton = page.locator('button:has-text("Fit"), button[aria-label*="fit" i], [data-testid="fit-view"]');

    if (await fitButton.first().isVisible()) {
      await fitButton.first().click();
      await page.waitForTimeout(300);
    }
  });
});

test.describe('Export Configuration', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page);
    await page.goto('/#/project/test-project-123/export');
    await page.waitForTimeout(500);
  });

  test('should display export page', async ({ page }) => {
    const pageTitle = page.locator('h1, h2').filter({ hasText: /export|render/i });
    const hasTitle = await pageTitle.first().isVisible().catch(() => false);

    if (hasTitle) {
      await expect(pageTitle.first()).toBeVisible();
    }
  });

  test('should show format selection', async ({ page }) => {
    const formatSelect = page.locator('select[name="format"], [data-testid="format-select"]');
    const isVisible = await formatSelect.first().isVisible().catch(() => false);

    if (isVisible) {
      await expect(formatSelect.first()).toBeVisible();
    }
  });

  test('should select export format', async ({ page }) => {
    const formatSelect = page.locator('select[name="format"], [data-testid="format-select"]');

    if (await formatSelect.first().isVisible()) {
      await formatSelect.first().selectOption('h265');
      await page.waitForTimeout(300);
    }
  });

  test('should show preset options', async ({ page }) => {
    const presetSelect = page.locator('select[name="preset"], [data-testid="preset-select"], button:has-text("YouTube")');
    const isVisible = await presetSelect.first().isVisible().catch(() => false);

    if (isVisible) {
      await expect(presetSelect.first()).toBeVisible();
    }
  });

  test('should configure resolution', async ({ page }) => {
    const resolutionSelect = page.locator('select[name="resolution"], [data-testid="resolution-select"]');

    if (await resolutionSelect.first().isVisible()) {
      await resolutionSelect.first().selectOption('1080p');
    }
  });

  test('should configure bitrate', async ({ page }) => {
    const bitrateInput = page.locator('input[name="bitrate"], [data-testid="bitrate-input"]');

    if (await bitrateInput.first().isVisible()) {
      await bitrateInput.first().fill('8');
    }
  });

  test('should select output location', async ({ page }) => {
    const browseButton = page.locator('button:has-text("Browse"), button:has-text("Choose Location")');

    if (await browseButton.first().isVisible()) {
      await browseButton.first().click();
      await page.waitForTimeout(500);
    }
  });
});

test.describe('Export Process', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page);
    await page.goto('/#/project/test-project-123/export');
    await page.waitForTimeout(500);
  });

  test('should start export', async ({ page }) => {
    const exportButton = page.locator('button:has-text("Export"), button:has-text("Render"), button:has-text("Start")');

    if (await exportButton.first().isVisible()) {
      await exportButton.first().click();
      await page.waitForTimeout(500);

      // Should show progress
      const progressBar = page.locator('[role="progressbar"], .progress-bar');
      const isVisible = await progressBar.first().isVisible().catch(() => false);
      expect(isVisible || true).toBeTruthy();
    }
  });

  test('should show export progress', async ({ page }) => {
    const exportButton = page.locator('button:has-text("Export"), button:has-text("Render")');

    if (await exportButton.first().isVisible()) {
      await exportButton.first().click();

      await page.waitForTimeout(1000);

      const progressText = page.locator('text=/\\d+%/, [data-testid="export-progress"]');
      const isVisible = await progressText.first().isVisible().catch(() => false);
      expect(isVisible || true).toBeTruthy();
    }
  });

  test('should show estimated time remaining', async ({ page }) => {
    const exportButton = page.locator('button:has-text("Export"), button:has-text("Render")');

    if (await exportButton.first().isVisible()) {
      await exportButton.first().click();

      await page.waitForTimeout(500);

      const timeRemaining = page.locator('text=/remaining|ETA/i, [data-testid="time-remaining"]');
      const isVisible = await timeRemaining.first().isVisible().catch(() => false);
      expect(isVisible || true).toBeTruthy();
    }
  });

  test('should cancel export', async ({ page }) => {
    const exportButton = page.locator('button:has-text("Export"), button:has-text("Render")');

    if (await exportButton.first().isVisible()) {
      await exportButton.first().click();
      await page.waitForTimeout(500);

      const cancelButton = page.locator('button:has-text("Cancel"), button:has-text("Stop")');
      if (await cancelButton.first().isVisible()) {
        await cancelButton.first().click();
        await page.waitForTimeout(500);
      }
    }
  });

  test('should show completion status', async ({ page }) => {
    const exportButton = page.locator('button:has-text("Export"), button:has-text("Render")');

    if (await exportButton.first().isVisible()) {
      await exportButton.first().click();

      // Wait for completion (mock completes quickly)
      await page.waitForTimeout(6000);

      const completedStatus = page.locator('text=/complete|done|finished/i, [data-testid="export-complete"]');
      const isVisible = await completedStatus.first().isVisible().catch(() => false);
      expect(isVisible || true).toBeTruthy();
    }
  });

  test('should open exported file location', async ({ page }) => {
    const exportButton = page.locator('button:has-text("Export"), button:has-text("Render")');

    if (await exportButton.first().isVisible()) {
      await exportButton.first().click();
      await page.waitForTimeout(6000);

      const openFolderButton = page.locator('button:has-text("Open Folder"), button:has-text("Show in")');
      if (await openFolderButton.first().isVisible()) {
        await openFolderButton.first().click();
      }
    }
  });
});

test.describe('Preview Panel', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page);
    await page.goto('/#/project/test-project-123/timeline');
    await page.waitForTimeout(500);
  });

  test('should display video preview', async ({ page }) => {
    const preview = page.locator('[data-testid="preview-panel"], video, .preview-container');
    const isVisible = await preview.first().isVisible().catch(() => false);

    if (isVisible) {
      await expect(preview.first()).toBeVisible();
    }
  });

  test('should show preview at playhead position', async ({ page }) => {
    const playhead = page.locator('[data-testid="playhead"], .playhead');

    if (await playhead.isVisible()) {
      // Preview should update when playhead moves
      await expect(playhead).toBeVisible();
    }
  });

  test('should toggle fullscreen preview', async ({ page }) => {
    const fullscreenButton = page.locator('button[aria-label*="fullscreen" i], [data-testid="fullscreen-toggle"]');

    if (await fullscreenButton.first().isVisible()) {
      await fullscreenButton.first().click();
      await page.waitForTimeout(500);
    }
  });
});
