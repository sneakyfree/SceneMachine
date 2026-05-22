/**
 * Tests for ScreenplayUpload component.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '../test-utils';
import userEvent from '@testing-library/user-event';
import { ScreenplayUpload } from '../../components/screenplay-upload';

// Mock the electronAPI
const mockBackendRequest = vi.fn();
const mockOpenFile = vi.fn();

beforeEach(() => {
  vi.clearAllMocks();

  // Reset window.electronAPI mock
  Object.defineProperty(window, 'electronAPI', {
    value: {
      backendRequest: mockBackendRequest,
      openFile: mockOpenFile,
      platform: 'linux',
    },
    writable: true,
  });
});

describe('ScreenplayUpload', () => {
  const mockOnUploadComplete = vi.fn();
  const mockOnError = vi.fn();

  const defaultProps = {
    projectId: 'project-123',
    onUploadComplete: mockOnUploadComplete,
    onError: mockOnError,
  };

  describe('Initial Rendering', () => {
    it('renders upload prompt text', () => {
      render(<ScreenplayUpload {...defaultProps} />);

      expect(screen.getByText(/Drop screenplay here or click to browse/)).toBeInTheDocument();
    });

    it('renders supported format info', () => {
      render(<ScreenplayUpload {...defaultProps} />);

      expect(
        screen.getByText(/Supports Fountain, PDF, Final Draft, and plain text/)
      ).toBeInTheDocument();
    });

    it('renders format badges', () => {
      render(<ScreenplayUpload {...defaultProps} />);

      expect(screen.getByText('.fountain')).toBeInTheDocument();
      expect(screen.getByText('.pdf')).toBeInTheDocument();
      expect(screen.getByText('.fdx')).toBeInTheDocument();
      expect(screen.getByText('.txt')).toBeInTheDocument();
    });
  });

  describe('File Selection', () => {
    it('opens file dialog on click', async () => {
      const user = userEvent.setup();
      mockOpenFile.mockResolvedValue({ canceled: true, filePaths: [] });

      render(<ScreenplayUpload {...defaultProps} />);

      const dropzone = screen.getByText(/Drop screenplay here/).closest('div')!;
      await user.click(dropzone);

      expect(mockOpenFile).toHaveBeenCalledWith({
        title: 'Select Screenplay',
        filters: expect.any(Array),
        properties: ['openFile'],
      });
    });

    it('handles canceled file selection', async () => {
      const user = userEvent.setup();
      mockOpenFile.mockResolvedValue({ canceled: true, filePaths: [] });

      render(<ScreenplayUpload {...defaultProps} />);

      const dropzone = screen.getByText(/Drop screenplay here/).closest('div')!;
      await user.click(dropzone);

      // Should remain in idle state
      expect(screen.getByText(/Drop screenplay here/)).toBeInTheDocument();
      expect(mockBackendRequest).not.toHaveBeenCalled();
    });

    it('uploads and parses valid file', async () => {
      const user = userEvent.setup();
      const mockScreenplay = {
        id: 'screenplay-1',
        projectId: 'project-123',
        originalFilename: 'test.fountain',
        originalFormat: 'fountain',
        isParsed: true,
        createdAt: new Date().toISOString(),
      };

      mockOpenFile.mockResolvedValue({
        canceled: false,
        filePaths: ['/path/to/test.fountain'],
      });

      mockBackendRequest
        .mockResolvedValueOnce(mockScreenplay) // screenplays.upload
        .mockResolvedValueOnce({
          // screenplays.parse
          id: 'screenplay-1',
          isParsed: true,
          parseErrors: null,
          metadata: { scene_count: 10, character_count: 5, element_count: 100 },
        })
        .mockResolvedValueOnce(mockScreenplay); // screenplays.get

      render(<ScreenplayUpload {...defaultProps} />);

      const dropzone = screen.getByText(/Drop screenplay here/).closest('div')!;
      await user.click(dropzone);

      // Should show uploading state
      await waitFor(() => {
        expect(screen.getByText(/Uploading screenplay/)).toBeInTheDocument();
      });

      // Then parsing state
      await waitFor(() => {
        expect(screen.getByText(/Parsing screenplay/)).toBeInTheDocument();
      });

      // Finally success
      await waitFor(() => {
        expect(screen.getByText(/Parsed 10 scenes/)).toBeInTheDocument();
      });

      expect(mockOnUploadComplete).toHaveBeenCalledWith(mockScreenplay);
    });

    it('shows error for unsupported file format', async () => {
      const user = userEvent.setup();
      mockOpenFile.mockResolvedValue({
        canceled: false,
        filePaths: ['/path/to/test.doc'],
      });

      render(<ScreenplayUpload {...defaultProps} />);

      const dropzone = screen.getByText(/Drop screenplay here/).closest('div')!;
      await user.click(dropzone);

      await waitFor(() => {
        expect(screen.getByText(/Unsupported file format/)).toBeInTheDocument();
      });
    });

    it('handles upload error', async () => {
      const user = userEvent.setup();
      mockOpenFile.mockResolvedValue({
        canceled: false,
        filePaths: ['/path/to/test.fountain'],
      });

      mockBackendRequest.mockRejectedValue(new Error('Upload failed'));

      render(<ScreenplayUpload {...defaultProps} />);

      const dropzone = screen.getByText(/Drop screenplay here/).closest('div')!;
      await user.click(dropzone);

      await waitFor(() => {
        expect(screen.getByText(/Upload failed/)).toBeInTheDocument();
      });

      expect(mockOnError).toHaveBeenCalledWith('Upload failed');
    });

    it('handles parse errors', async () => {
      const user = userEvent.setup();
      mockOpenFile.mockResolvedValue({
        canceled: false,
        filePaths: ['/path/to/test.fountain'],
      });

      mockBackendRequest
        .mockResolvedValueOnce({ id: 'screenplay-1' }) // upload
        .mockResolvedValueOnce({
          id: 'screenplay-1',
          isParsed: false,
          parseErrors: ['Invalid scene header', 'Missing character'],
          metadata: {},
        }); // parse

      render(<ScreenplayUpload {...defaultProps} />);

      const dropzone = screen.getByText(/Drop screenplay here/).closest('div')!;
      await user.click(dropzone);

      await waitFor(() => {
        expect(screen.getByText(/Invalid scene header/)).toBeInTheDocument();
      });
    });
  });

  describe('Drag and Drop', () => {
    it('shows dragging state on drag over', () => {
      render(<ScreenplayUpload {...defaultProps} />);

      const dropzone = screen.getByText(/Drop screenplay here/).closest('div')!;

      fireEvent.dragOver(dropzone, {
        dataTransfer: { files: [] },
      });

      expect(screen.getByText(/Drop screenplay to upload/)).toBeInTheDocument();
    });

    it('returns to idle on drag leave', () => {
      render(<ScreenplayUpload {...defaultProps} />);

      const dropzone = screen.getByText(/Drop screenplay here/).closest('div')!;

      fireEvent.dragOver(dropzone, {
        dataTransfer: { files: [] },
      });

      fireEvent.dragLeave(dropzone);

      expect(screen.getByText(/Drop screenplay here/)).toBeInTheDocument();
    });

    it('shows error for unsupported dropped file', async () => {
      render(<ScreenplayUpload {...defaultProps} />);

      const dropzone = screen.getByText(/Drop screenplay here/).closest('div')!;

      const file = new File(['content'], 'test.doc', { type: 'application/msword' });

      fireEvent.drop(dropzone, {
        dataTransfer: {
          files: [file],
        },
      });

      await waitFor(() => {
        expect(screen.getByText(/Unsupported file format/)).toBeInTheDocument();
      });
    });

    it('handles dropped file without path property', async () => {
      render(<ScreenplayUpload {...defaultProps} />);

      const dropzone = screen.getByText(/Drop screenplay here/).closest('div')!;

      const file = new File(['content'], 'test.fountain', { type: 'text/plain' });
      // Note: In browser environment, File objects don't have 'path' property

      fireEvent.drop(dropzone, {
        dataTransfer: {
          files: [file],
        },
      });

      await waitFor(() => {
        expect(screen.getByText(/Drag and drop not fully supported/)).toBeInTheDocument();
      });
    });
  });

  describe('Disabled State', () => {
    it('does not open file dialog when disabled', async () => {
      const user = userEvent.setup();
      render(<ScreenplayUpload {...defaultProps} disabled={true} />);

      const dropzone = screen.getByText(/Drop screenplay here/).closest('div')!;
      await user.click(dropzone);

      expect(mockOpenFile).not.toHaveBeenCalled();
    });

    it('applies disabled styles', () => {
      render(<ScreenplayUpload {...defaultProps} disabled={true} />);

      const dropzone = screen.getByText(/Drop screenplay here/).closest('div')!;
      expect(dropzone).toHaveClass('opacity-50');
      expect(dropzone).toHaveClass('cursor-not-allowed');
    });

    it('ignores drag over when disabled', () => {
      render(<ScreenplayUpload {...defaultProps} disabled={true} />);

      const dropzone = screen.getByText(/Drop screenplay here/).closest('div')!;

      fireEvent.dragOver(dropzone, {
        dataTransfer: { files: [] },
      });

      // Should not change to dragging state
      expect(screen.getByText(/Drop screenplay here/)).toBeInTheDocument();
    });
  });

  describe('State Styles', () => {
    it('applies idle styles', () => {
      render(<ScreenplayUpload {...defaultProps} />);

      const dropzone = screen.getByText(/Drop screenplay here/).closest('div')!;
      expect(dropzone).toHaveClass('border-surface-700');
    });

    it('applies dragging styles', () => {
      render(<ScreenplayUpload {...defaultProps} />);

      const dropzone = screen.getByText(/Drop screenplay here/).closest('div')!;

      fireEvent.dragOver(dropzone, {
        dataTransfer: { files: [] },
      });

      expect(dropzone).toHaveClass('border-primary-500');
      expect(dropzone).toHaveClass('bg-primary-500/10');
    });
  });

  describe('File Validation', () => {
    it.each([
      ['test.fountain', true],
      ['test.spmd', true],
      ['test.pdf', true],
      ['test.fdx', true],
      ['test.txt', true],
      ['test.FOUNTAIN', true],
      ['test.PDF', true],
      ['test.doc', false],
      ['test.docx', false],
      ['test.rtf', false],
      ['test', false],
    ])('validates %s as %s', async (filename, shouldBeValid) => {
      const user = userEvent.setup();

      if (shouldBeValid) {
        mockOpenFile.mockResolvedValue({
          canceled: false,
          filePaths: [`/path/to/${filename}`],
        });
        mockBackendRequest
          .mockResolvedValueOnce({ id: 'screenplay-1' })
          .mockResolvedValueOnce({
            id: 'screenplay-1',
            isParsed: true,
            parseErrors: null,
            metadata: {},
          })
          .mockResolvedValueOnce({ id: 'screenplay-1' });
      } else {
        mockOpenFile.mockResolvedValue({
          canceled: false,
          filePaths: [`/path/to/${filename}`],
        });
      }

      render(<ScreenplayUpload {...defaultProps} />);

      const dropzone = screen.getByText(/Drop screenplay here/).closest('div')!;
      await user.click(dropzone);

      if (shouldBeValid) {
        await waitFor(() => {
          expect(mockBackendRequest).toHaveBeenCalled();
        });
      } else {
        await waitFor(() => {
          expect(screen.getByText(/Unsupported file format/)).toBeInTheDocument();
        });
      }
    });
  });
});
