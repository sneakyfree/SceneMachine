/**
 * Vitest test setup file.
 * Configures global mocks and test utilities.
 */

import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach, beforeAll, vi } from 'vitest';

// Cleanup after each test
afterEach(() => {
  cleanup();
});

// Mock window.electronAPI
const mockBackendRequest = vi.fn();

beforeAll(() => {
  // Mock Electron API
  Object.defineProperty(window, 'electronAPI', {
    value: {
      backendRequest: mockBackendRequest,
      platform: 'linux',
      onBackendReady: vi.fn(),
      onBackendError: vi.fn(),
      selectFile: vi.fn(),
      selectDirectory: vi.fn(),
      showSaveDialog: vi.fn(),
      openExternal: vi.fn(),
    },
    writable: true,
  });

  // Mock matchMedia
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });

  // Mock ResizeObserver
  global.ResizeObserver = vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
  }));

  // Mock IntersectionObserver
  global.IntersectionObserver = vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
  }));

  // Mock URL.createObjectURL
  global.URL.createObjectURL = vi.fn(() => 'blob:mock-url');
  global.URL.revokeObjectURL = vi.fn();
});

// Export mock for use in tests
export { mockBackendRequest };
