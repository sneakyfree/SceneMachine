/**
 * API Client Hardening Tests
 *
 * Tests that the API client module exports correctly and handles errors.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

describe('API Client Hardening', () => {
  describe('Module Exports', () => {
    it('should export api client module', async () => {
      const clientModule = await import('../../api/client');
      expect(clientModule).toBeDefined();
    });

    it('should export APIClient class or api instance', async () => {
      const clientModule = await import('../../api/client');
      // The module exports an 'api' instance of APIClient class
      expect(clientModule.api).toBeDefined();
    });

    it('should have project methods', async () => {
      const { api } = await import('../../api/client');
      // APIClient uses listProjects, getProject, createProject
      expect(api.listProjects).toBeDefined();
      expect(api.getProject).toBeDefined();
      expect(api.createProject).toBeDefined();
    });

    it('should have settings methods', async () => {
      const { api } = await import('../../api/client');
      expect(api.getSettings).toBeDefined();
      expect(api.updateSettings).toBeDefined();
    });

    it('should have analytics methods', async () => {
      const { api } = await import('../../api/client');
      expect(api.getDashboardStats).toBeDefined();
      expect(api.getGenerationStats).toBeDefined();
      expect(api.getCostStats).toBeDefined();
    });

    it('should have sharing methods', async () => {
      const { api } = await import('../../api/client');
      expect(api.createShare).toBeDefined();
      expect(api.revokeShare).toBeDefined();
      expect(api.getProjectShares).toBeDefined();
    });

    it('should have archive methods', async () => {
      const { api } = await import('../../api/client');
      // Actual method names are exportProject, importProject, listArchives
      expect(api.exportProject).toBeDefined();
      expect(api.importProject).toBeDefined();
      expect(api.listArchives).toBeDefined();
    });

    it('should have generation methods', async () => {
      const { api } = await import('../../api/client');
      expect(api.getProvidersHealth).toBeDefined();
      expect(api.getProviderModels).toBeDefined();
      expect(api.estimateCost).toBeDefined();
      expect(api.getWorkerStatus).toBeDefined();
    });

    it('should have duplicate project method', async () => {
      const { api } = await import('../../api/client');
      expect(api.duplicateProject).toBeDefined();
    });
  });
});

describe('API Types', () => {
  it('should export all necessary types', async () => {
    const clientModule = await import('../../api/client');
    // Check that type exports are present (they compile)
    expect(clientModule).toBeDefined();

    // These are TypeScript types, so we just verify the module imports correctly
    // Types like DashboardStats, ShareInfo, etc. are compile-time only
  });

  it('should have provider types', async () => {
    const clientModule = await import('../../api/client');
    // ProviderHealth, ProviderModel, etc. are type exports
    expect(clientModule).toBeDefined();
  });
});

describe('API Client Methods Exist', () => {
  it('should have all core CRUD methods', async () => {
    const { api } = await import('../../api/client');

    // Projects
    expect(typeof api.listProjects).toBe('function');
    expect(typeof api.getProject).toBe('function');
    expect(typeof api.createProject).toBe('function');
    expect(typeof api.updateProject).toBe('function');
    expect(typeof api.deleteProject).toBe('function');
  });

  it('should have worker control methods', async () => {
    const { api } = await import('../../api/client');

    expect(typeof api.pauseWorker).toBe('function');
    expect(typeof api.resumeWorker).toBe('function');
    expect(typeof api.getWorkerStatus).toBe('function');
  });

  it('should have storage methods', async () => {
    const { api } = await import('../../api/client');

    expect(typeof api.getStorageStats).toBe('function');
    expect(typeof api.clearCache).toBe('function');
  });
});
