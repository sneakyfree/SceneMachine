/**
 * API client for communicating with the Python backend.
 */

import type { Project } from '@shared/types';

// ============ Analytics Types ============

export interface DashboardStats {
  totalProjects: number;
  activeProjects: number;
  totalScenes: number;
  totalShots: number;
  shotsGenerated: number;
  shotsApproved: number;
  totalGenerationTimeSeconds: number;
  averageGenerationTimeSeconds: number;
  estimatedCostUsd: number;
  generationsByStatus: Record<string, number>;
  recentProjects: Array<{
    id: string;
    name: string;
    state: string;
    updatedAt: string;
  }>;
}

export interface GenerationStats {
  totalGenerations: number;
  successfulGenerations: number;
  failedGenerations: number;
  successRate: number;
  averageDurationSeconds: number;
  totalDurationSeconds: number;
  byProvider: Record<string, number>;
  byModel: Record<string, number>;
}

export interface CostStats {
  totalCostUsd: number;
  costByProvider: Record<string, number>;
  costByModel: Record<string, number>;
  costByProject: Record<string, number>;
  averageCostPerGeneration: number;
}

export interface DailyStats {
  date: string;
  generations: number;
  successfulGenerations: number;
  costUsd: number;
}

// ============ Sharing Types ============

export interface ShareResult {
  success: boolean;
  shareId?: string;
  shareCode?: string;
  shareUrl?: string;
  error?: string;
}

export interface ShareInfo {
  id: string;
  projectId: string;
  projectName: string;
  shareCode: string;
  permission: 'view' | 'comment' | 'edit';
  status: string;
  recipientEmail?: string;
  recipientName?: string;
  isPublic: boolean;
  expiresAt?: string;
  createdAt: string;
  accessCount: number;
}

export interface Comment {
  id: string;
  projectId: string;
  shotId?: string;
  authorName: string;
  authorEmail?: string;
  content: string;
  timecodeSeconds?: number;
  isResolved: boolean;
  createdAt: string;
}

// ============ Archive Types ============

export interface ArchiveManifest {
  version: string;
  createdAt: string;
  projectId: string;
  projectName: string;
  includesAssets: boolean;
  includesOutputs: boolean;
  fileCount: number;
  totalSizeBytes: number;
}

export interface ExportResult {
  success: boolean;
  archivePath?: string;
  fileSizeBytes?: number;
  manifest?: ArchiveManifest;
  error?: string;
}

export interface ImportResult {
  success: boolean;
  projectId?: string;
  projectName?: string;
  scenesImported?: number;
  shotsImported?: number;
  charactersImported?: number;
  assetsImported?: number;
  warnings?: string[];
  error?: string;
}

export interface ArchiveListItem {
  path: string;
  filename: string;
  sizeBytes: number;
  createdAt: string;
  manifest?: {
    version: string;
    projectId: string;
    projectName: string;
  };
}

// ============ Settings Types ============

export interface UserSettings {
  llmProvider: string;
  videoProvider: string;
  maxConcurrentGenerations: number;
  generationTimeoutSeconds: number;
  defaultVideoResolution: string;
  defaultVideoFps: number;
  themeMode: string;
  autoSaveEnabled: boolean;
  showAdvancedOptions: boolean;
  autoCleanupTempFiles: boolean;
  maxCacheSizeGb: number;
  defaultExportFormat: string;
  defaultExportQuality: string;
}

export interface ProviderStatus {
  provider: string;
  name: string;
  available: boolean;
  configured: boolean;
  message: string;
  latencyMs?: number;
}

export interface StorageStats {
  dataDir: string;
  uploadDir: string;
  outputDir: string;
  cacheDir: string;
  totalSizeBytes: number;
  uploadSizeBytes: number;
  outputSizeBytes: number;
  cacheSizeBytes: number;
  tempFilesCount: number;
  totalSize: string;
  uploadSize: string;
  outputSize: string;
  cacheSize: string;
}

export interface ProviderInfo {
  id: string;
  name: string;
  description: string;
  models: string[];
  configured: boolean;
}

/**
 * API client singleton for backend communication.
 */
class APIClient {
  /**
   * Send a request to the backend via IPC.
   */
  private async request<T>(method: string, params?: Record<string, unknown>): Promise<T> {
    try {
      const result = await window.electronAPI.backendRequest<T>(method, params);
      return result;
    } catch (error) {
      console.error(`API Error [${method}]:`, error);
      throw error;
    }
  }

  // ============ Projects ============

  /**
   * List all projects.
   */
  async listProjects(): Promise<Project[]> {
    return this.request<Project[]>('projects.list');
  }

  /**
   * Get a project by ID.
   */
  async getProject(id: string): Promise<Project> {
    return this.request<Project>('projects.get', { id });
  }

  /**
   * Create a new project.
   */
  async createProject(data: {
    name: string;
    description?: string;
    settings?: Record<string, unknown>;
  }): Promise<Project> {
    return this.request<Project>('projects.create', data);
  }

  /**
   * Update a project.
   */
  async updateProject(
    id: string,
    data: {
      name?: string;
      description?: string;
      settings?: Record<string, unknown>;
    }
  ): Promise<Project> {
    return this.request<Project>('projects.update', { id, ...data });
  }

  /**
   * Delete a project.
   */
  async deleteProject(id: string): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>('projects.delete', { id });
  }

  // ============ Utility ============

  /**
   * Ping the backend.
   */
  async ping(): Promise<{ status: string }> {
    return this.request<{ status: string }>('ping');
  }

  /**
   * Get backend version.
   */
  async getVersion(): Promise<{ version: string; environment: string }> {
    return this.request<{ version: string; environment: string }>('version');
  }

  // ============ Analytics ============

  /**
   * Get dashboard statistics.
   */
  async getDashboardStats(timeRange: '24h' | '7d' | '30d' | 'all' = '7d'): Promise<DashboardStats> {
    return this.request<DashboardStats>('analytics.getDashboard', { timeRange });
  }

  /**
   * Get generation statistics.
   */
  async getGenerationStats(options?: {
    projectId?: string;
    timeRange?: '24h' | '7d' | '30d' | 'all';
  }): Promise<GenerationStats> {
    return this.request<GenerationStats>('analytics.getGenerationStats', options);
  }

  /**
   * Get cost statistics.
   */
  async getCostStats(options?: {
    projectId?: string;
    timeRange?: '24h' | '7d' | '30d' | 'all';
  }): Promise<CostStats> {
    return this.request<CostStats>('analytics.getCostStats', options);
  }

  /**
   * Get daily statistics over a date range.
   */
  async getDailyStats(startDate: string, endDate: string): Promise<DailyStats[]> {
    return this.request<DailyStats[]>('analytics.getDailyStats', { startDate, endDate });
  }

  // ============ Sharing ============

  /**
   * Create a share for a project.
   */
  async createShare(options: {
    projectId: string;
    permission?: 'view' | 'comment' | 'edit';
    recipientEmail?: string;
    recipientName?: string;
    message?: string;
    expiresInDays?: number;
    isPublic?: boolean;
  }): Promise<ShareResult> {
    return this.request<ShareResult>('sharing.create', options);
  }

  /**
   * Get all shares for a project.
   */
  async getProjectShares(projectId: string): Promise<ShareInfo[]> {
    return this.request<ShareInfo[]>('sharing.getProjectShares', { projectId });
  }

  /**
   * Accept a share invitation by code.
   */
  async acceptShare(shareCode: string): Promise<{
    success: boolean;
    projectId?: string;
    projectName?: string;
    error?: string;
  }> {
    return this.request('sharing.accept', { shareCode });
  }

  /**
   * Revoke a share.
   */
  async revokeShare(shareId: string): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>('sharing.revoke', { shareId });
  }

  /**
   * Get comments for a project.
   */
  async getProjectComments(
    projectId: string,
    options?: {
      shotId?: string;
      includeResolved?: boolean;
    }
  ): Promise<Comment[]> {
    return this.request<Comment[]>('sharing.getComments', { projectId, ...options });
  }

  /**
   * Add a comment to a project or shot.
   */
  async addComment(options: {
    projectId: string;
    authorName: string;
    content: string;
    authorEmail?: string;
    shotId?: string;
    parentId?: string;
    timecodeSeconds?: number;
  }): Promise<Comment> {
    return this.request<Comment>('sharing.addComment', options);
  }

  // ============ Archive ============

  /**
   * Export a project to an archive.
   */
  async exportProject(options: {
    projectId: string;
    includeAssets?: boolean;
    includeOutputs?: boolean;
    includeGeneratedVideos?: boolean;
  }): Promise<ExportResult> {
    return this.request<ExportResult>('archive.export', options);
  }

  /**
   * Import a project from an archive.
   */
  async importProject(options: {
    archivePath: string;
    newName?: string;
    importAssets?: boolean;
  }): Promise<ImportResult> {
    return this.request<ImportResult>('archive.import', options);
  }

  /**
   * List all exported archives.
   */
  async listArchives(): Promise<ArchiveListItem[]> {
    return this.request<ArchiveListItem[]>('archive.list');
  }

  /**
   * Get information about an archive.
   */
  async getArchiveInfo(archivePath: string): Promise<ArchiveManifest> {
    return this.request<ArchiveManifest>('archive.getInfo', { archivePath });
  }

  // ============ Settings ============

  /**
   * Get current user settings.
   */
  async getSettings(): Promise<UserSettings> {
    return this.request<UserSettings>('settings.get');
  }

  /**
   * Update user settings.
   */
  async updateSettings(settings: Partial<UserSettings>): Promise<UserSettings> {
    return this.request<UserSettings>('settings.update', settings);
  }

  /**
   * Set an API key for a provider.
   */
  async setApiKey(provider: string, apiKey: string): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>('settings.setApiKey', { provider, apiKey });
  }

  /**
   * Remove an API key for a provider.
   */
  async removeApiKey(provider: string): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>('settings.removeApiKey', { provider });
  }

  /**
   * Validate an API key for a provider.
   */
  async validateApiKey(
    provider: string,
    apiKey?: string
  ): Promise<ProviderStatus> {
    return this.request<ProviderStatus>('settings.validateApiKey', { provider, apiKey });
  }

  /**
   * Check status of all configured providers.
   */
  async checkAllProviders(): Promise<ProviderStatus[]> {
    return this.request<ProviderStatus[]>('settings.checkProviders');
  }

  /**
   * Get available LLM providers.
   */
  async getLlmProviders(): Promise<ProviderInfo[]> {
    return this.request<ProviderInfo[]>('settings.getLlmProviders');
  }

  /**
   * Get available video generation providers.
   */
  async getVideoProviders(): Promise<ProviderInfo[]> {
    return this.request<ProviderInfo[]>('settings.getVideoProviders');
  }

  /**
   * Get storage statistics.
   */
  async getStorageStats(): Promise<StorageStats> {
    return this.request<StorageStats>('settings.getStorageStats');
  }

  /**
   * Clear cache.
   */
  async clearCache(
    cacheType: 'model' | 'temp' | 'output' | 'all' = 'all'
  ): Promise<{
    success: boolean;
    modelCacheCleared: boolean;
    tempFilesCleared: boolean;
    bytesFreed: number;
    bytesFreedDisplay: string;
  }> {
    return this.request('settings.clearCache', { cacheType });
  }

  /**
   * Export settings for backup.
   */
  async exportSettings(): Promise<Record<string, unknown>> {
    return this.request<Record<string, unknown>>('settings.export');
  }

  /**
   * Import settings from backup.
   */
  async importSettings(settings: Record<string, unknown>): Promise<{
    success: boolean;
    settings: UserSettings;
  }> {
    return this.request('settings.import', { settings });
  }
}

// Export singleton instance
export const api = new APIClient();
