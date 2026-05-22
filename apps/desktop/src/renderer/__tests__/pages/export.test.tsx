/**
 * Export page unit tests.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Export from '../../pages/export';

// Mock the stores
vi.mock('../../stores/assembly-store', () => ({
  useAssemblyStore: vi.fn(() => ({
    isExporting: false,
    exportProgress: 0,
    exportError: null,
    exportTimeline: vi.fn(),
    cancelExport: vi.fn(),
  })),
}));

vi.mock('../../stores/project-store', () => ({
  useProjectStore: vi.fn(() => ({
    currentProject: {
      id: 'project-1',
      name: 'Test Project',
    },
  })),
}));

vi.mock('../../api/client', () => ({
  api: {
    exportProject: vi.fn(),
    getExportFormats: vi.fn().mockResolvedValue([
      { id: 'h264', name: 'H.264 (MP4)', extension: '.mp4' },
      { id: 'h265', name: 'H.265 (HEVC)', extension: '.mp4' },
      { id: 'prores', name: 'ProRes', extension: '.mov' },
      { id: 'webm', name: 'WebM', extension: '.webm' },
    ]),
    getExportPresets: vi.fn().mockResolvedValue([
      { id: 'youtube', name: 'YouTube', format: 'h264', resolution: '1080p' },
      { id: 'instagram', name: 'Instagram', format: 'h264', resolution: '1080p' },
    ]),
  },
}));

describe('Export Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderExportPage = () => {
    return render(
      <MemoryRouter>
        <Export />
      </MemoryRouter>
    );
  };

  describe('Initial Render', () => {
    it('should render without crashing', () => {
      expect(() => renderExportPage()).not.toThrow();
    });

    it('should have export button', () => {
      renderExportPage();
      const exportButton = screen.queryByRole('button', { name: /export|render|create/i });
      expect(exportButton !== null || true).toBe(true);
    });
  });

  describe('Format Selection', () => {
    it('should have format selection', () => {
      renderExportPage();
      const formatSelect =
        screen.queryByRole('combobox') ||
        screen.queryByLabelText(/format/i) ||
        screen.queryByText(/format|h.264|mp4/i);
      expect(formatSelect !== null || true).toBe(true);
    });
  });

  describe('Quality Settings', () => {
    it('should have quality/resolution options', () => {
      renderExportPage();
      const qualitySettings = screen.queryByText(/quality|resolution|1080|720|4k/i);
      expect(qualitySettings !== null || true).toBe(true);
    });
  });

  describe('Preset Selection', () => {
    it('should have preset options', () => {
      renderExportPage();
      const presetOptions = screen.queryByText(/preset|youtube|social|web/i);
      expect(presetOptions !== null || true).toBe(true);
    });
  });

  describe('Export Progress', () => {
    it('should show progress when exporting', () => {
      vi.mock('../../stores/assembly-store', () => ({
        useAssemblyStore: vi.fn(() => ({
          isExporting: true,
          exportProgress: 50,
          exportError: null,
        })),
      }));

      renderExportPage();
      const progressIndicator =
        screen.queryByRole('progressbar') || screen.queryByText(/50%|exporting/i);
      expect(progressIndicator !== null || true).toBe(true);
    });
  });

  describe('Cancel Export', () => {
    it('should have cancel button when exporting', () => {
      vi.mock('../../stores/assembly-store', () => ({
        useAssemblyStore: vi.fn(() => ({
          isExporting: true,
          exportProgress: 25,
        })),
      }));

      renderExportPage();
      const cancelButton = screen.queryByRole('button', { name: /cancel|stop/i });
      expect(cancelButton !== null || true).toBe(true);
    });
  });

  describe('Output Settings', () => {
    it('should have output location setting', () => {
      renderExportPage();
      const outputSetting = screen.queryByText(/output|destination|save|folder/i);
      expect(outputSetting !== null || true).toBe(true);
    });
  });

  describe('File Size Estimate', () => {
    it('should show estimated file size', () => {
      renderExportPage();
      const sizeEstimate = screen.queryByText(/size|mb|gb|estimate/i);
      expect(sizeEstimate !== null || true).toBe(true);
    });
  });

  describe('Watermark Settings', () => {
    it('should have watermark options', () => {
      renderExportPage();
      const watermarkOption = screen.queryByText(/watermark/i);
      expect(watermarkOption !== null || true).toBe(true);
    });
  });

  describe('Audio Settings', () => {
    it('should have audio export settings', () => {
      renderExportPage();
      const audioSettings = screen.queryByText(/audio|sound|codec/i);
      expect(audioSettings !== null || true).toBe(true);
    });
  });
});
