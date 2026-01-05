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

// ============ Project Types ============

export interface DuplicateProjectResponse {
  id: string;
  name: string;
  description: string | null;
  state: string;
  created_at: string;
  updated_at: string;
}

// ============ Generation Types ============

export interface ProviderModel {
  id: string;
  name: string;
  cost_per_second: number;
  supports_text_to_video: boolean;
  supports_image_to_video: boolean;
  max_duration: number;
}

export interface ProviderHealth {
  provider: string;
  name: string;
  available: boolean;
  configured: boolean;
  models: ProviderModel[];
  default_model?: string;
  error?: string;
}

export interface CostEstimateRequest {
  provider: string;
  model_id?: string;
  duration_seconds?: number;
  shot_count?: number;
}

export interface CostEstimateResponse {
  provider: string;
  model_id: string;
  model_name: string;
  duration_seconds: number;
  shot_count: number;
  cost_per_shot: number;
  total_cost: number;
  currency: string;
}

export interface WorkerStatus {
  is_running: boolean;
  is_paused: boolean;
  jobs_processed: number;
  jobs_succeeded: number;
  jobs_failed: number;
  current_job_id?: string;
  uptime_seconds: number;
  success_rate: number;
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
  // Budget settings
  budgetLimitUsd?: number | null;
  budgetPeriodDays?: number;
  // API keys (read-only from get, not used in update)
  apiKeys?: Record<string, { configured: boolean; masked: string | null }>;
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

  /**
   * Duplicate a project.
   */
  async duplicateProject(
    id: string,
    newName?: string,
    includeGeneratedVideos?: boolean
  ): Promise<DuplicateProjectResponse> {
    return this.request<DuplicateProjectResponse>('projects.duplicate', {
      id,
      new_name: newName,
      include_generated_videos: includeGeneratedVideos ?? false,
    });
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

  // ============ Generation ============

  /**
   * Get available models for a specific provider.
   */
  async getProviderModels(providerId: string): Promise<ProviderModel[]> {
    return this.request<ProviderModel[]>('generation.getProviderModels', { providerId });
  }

  /**
   * Get health status for all providers.
   */
  async getProvidersHealth(): Promise<ProviderHealth[]> {
    return this.request<ProviderHealth[]>('generation.getProvidersHealth');
  }

  /**
   * Estimate cost for video generation.
   */
  async estimateCost(params: CostEstimateRequest): Promise<CostEstimateResponse> {
    return this.request<CostEstimateResponse>('generation.estimateCost', params as unknown as Record<string, unknown>);
  }

  /**
   * Get queue worker status.
   */
  async getWorkerStatus(): Promise<WorkerStatus> {
    return this.request<WorkerStatus>('generation.getWorkerStatus');
  }

  /**
   * Pause the queue worker.
   */
  async pauseWorker(): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>('generation.pauseWorker');
  }

  /**
   * Resume the queue worker.
   */
  async resumeWorker(): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>('generation.resumeWorker');
  }

  // ============ Health & Circuit Breakers ============

  /**
   * Get status of all circuit breakers.
   */
  async getCircuitBreakers(): Promise<CircuitBreakersResponse> {
    return this.request<CircuitBreakersResponse>('health.getCircuitBreakers');
  }

  /**
   * Reset a circuit breaker to closed state.
   */
  async resetCircuitBreaker(name: string): Promise<{ success: boolean; error?: string }> {
    return this.request<{ success: boolean; error?: string }>('health.resetCircuitBreaker', { name });
  }

  // ============ Watermarks ============

  /**
   * List all custom watermarks.
   */
  async listWatermarks(): Promise<WatermarksResponse> {
    return this.request<WatermarksResponse>('watermarks.list');
  }

  /**
   * Upload a new watermark image.
   */
  async uploadWatermark(
    filename: string,
    contentBase64: string
  ): Promise<WatermarkUploadResponse> {
    return this.request<WatermarkUploadResponse>('watermarks.upload', {
      filename,
      content_base64: contentBase64,
    });
  }

  /**
   * Delete a watermark.
   */
  async deleteWatermark(
    watermarkId: string
  ): Promise<{ success: boolean; error?: string }> {
    return this.request<{ success: boolean; error?: string }>('watermarks.delete', {
      watermark_id: watermarkId,
    });
  }

  // ============ ActForge: Performers ============

  /**
   * Search for performers.
   */
  async searchPerformers(params?: PerformerSearchParams): Promise<{
    performers: Performer[];
    total: number;
    hasMore: boolean;
  }> {
    return this.request('performers.search', params as Record<string, unknown>);
  }

  /**
   * Get featured performers.
   */
  async getFeaturedPerformers(limit?: number): Promise<Performer[]> {
    return this.request<Performer[]>('performers.featured', { limit });
  }

  /**
   * Get performer leaderboard.
   */
  async getPerformerLeaderboard(limit?: number): Promise<PerformerLeaderboardEntry[]> {
    return this.request<PerformerLeaderboardEntry[]>('performers.leaderboard', { limit });
  }

  /**
   * Get a performer by ID.
   */
  async getPerformer(id: string): Promise<Performer> {
    return this.request<Performer>('performers.get', { id });
  }

  /**
   * Get ACI breakdown for a performer.
   */
  async getPerformerACI(performerId: string): Promise<ACIBreakdown> {
    return this.request<ACIBreakdown>('performers.getACI', { performerId });
  }

  /**
   * Create a new performer profile.
   */
  async createPerformer(data: PerformerCreateRequest): Promise<Performer> {
    return this.request<Performer>('performers.create', data as unknown as Record<string, unknown>);
  }

  /**
   * Update a performer profile.
   */
  async updatePerformer(
    id: string,
    data: Partial<PerformerCreateRequest>
  ): Promise<Performer> {
    return this.request<Performer>('performers.update', { id, ...data });
  }

  // ============ ActForge: Bookings ============

  /**
   * Create a BLINK booking (10s quick match).
   */
  async createBlinkBooking(data: Omit<BookingCreateRequest, 'booking_mode'>): Promise<Booking> {
    return this.request<Booking>('bookings.blink', data as Record<string, unknown>);
  }

  /**
   * Create a DEEP booking (method acting, 120s).
   */
  async createDeepBooking(data: Omit<BookingCreateRequest, 'booking_mode'>): Promise<Booking> {
    return this.request<Booking>('bookings.deep', data as Record<string, unknown>);
  }

  /**
   * Create an EPIC booking (long-form, 5-20min).
   */
  async createEpicBooking(data: Omit<BookingCreateRequest, 'booking_mode'>): Promise<Booking> {
    return this.request<Booking>('bookings.epic', data as Record<string, unknown>);
  }

  /**
   * Get a booking by ID.
   */
  async getBooking(id: string): Promise<Booking> {
    return this.request<Booking>('bookings.get', { id });
  }

  /**
   * List bookings for a project.
   */
  async listProjectBookings(projectId: string, status?: BookingStatus): Promise<Booking[]> {
    return this.request<Booking[]>('bookings.listByProject', { projectId, status });
  }

  /**
   * Accept a booking (performer action).
   */
  async acceptBooking(bookingId: string): Promise<Booking> {
    return this.request<Booking>('bookings.accept', { bookingId });
  }

  /**
   * Mark a booking as delivered (performer action).
   */
  async deliverBooking(
    bookingId: string,
    deliveryUrl: string,
    notes?: string
  ): Promise<Booking> {
    return this.request<Booking>('bookings.deliver', { bookingId, deliveryUrl, notes });
  }

  /**
   * Approve a delivery (client action).
   */
  async approveBooking(bookingId: string): Promise<Booking> {
    return this.request<Booking>('bookings.approve', { bookingId });
  }

  /**
   * Dispute a delivery (client action).
   */
  async disputeBooking(bookingId: string, reason: string): Promise<Booking> {
    return this.request<Booking>('bookings.dispute', { bookingId, reason });
  }

  /**
   * Rate a completed booking.
   */
  async rateBooking(
    bookingId: string,
    rating: number,
    review?: string,
    wouldRehire?: boolean
  ): Promise<Booking> {
    return this.request<Booking>('bookings.rate', { bookingId, rating, review, wouldRehire });
  }

  /**
   * Calculate payout for a booking.
   */
  async calculatePayout(bookingPriceUsd: number, lifetimeEarningsUsd: number): Promise<PayoutCalculation> {
    return this.request<PayoutCalculation>('bookings.calculatePayout', {
      bookingPriceUsd,
      lifetimeEarningsUsd,
    });
  }

  // ============ GPU Exchange ============

  /**
   * List all GPU providers.
   */
  async listGPUProviders(): Promise<GPUProviderInfo[]> {
    return this.request<GPUProviderInfo[]>('gpuExchange.listProviders');
  }

  /**
   * Get a specific GPU provider.
   */
  async getGPUProvider(providerId: string): Promise<GPUProviderInfo> {
    return this.request<GPUProviderInfo>('gpuExchange.getProvider', { providerId });
  }

  /**
   * Get health status of a GPU provider.
   */
  async getGPUProviderHealth(providerId: string): Promise<GPUProviderHealth> {
    return this.request<GPUProviderHealth>('gpuExchange.getProviderHealth', { providerId });
  }

  /**
   * Get health status of all GPU providers.
   */
  async getAllGPUProvidersHealth(): Promise<AllGPUProvidersHealth> {
    return this.request<AllGPUProvidersHealth>('gpuExchange.getAllProvidersHealth');
  }

  /**
   * Get providers that support a specific GPU type.
   */
  async getProvidersForGPU(gpuType: string): Promise<string[]> {
    return this.request<string[]>('gpuExchange.getProvidersForGPU', { gpuType });
  }

  /**
   * Get pricing for a GPU type from a provider.
   */
  async getGPUPricing(
    providerId: string,
    gpuType: string,
    region?: string
  ): Promise<GPUPricing> {
    return this.request<GPUPricing>('gpuExchange.getPricing', {
      providerId,
      gpuType,
      region,
    });
  }

  /**
   * Compare pricing across providers for a GPU type.
   */
  async compareGPUPricing(gpuType: string, region?: string): Promise<GPUPricingComparison> {
    return this.request<GPUPricingComparison>('gpuExchange.comparePricing', {
      gpuType,
      region,
    });
  }

  /**
   * Get pricing from all providers for a GPU type.
   */
  async getAllGPUPricing(gpuType: string, region?: string): Promise<Record<string, GPUPricing>> {
    return this.request<Record<string, GPUPricing>>('gpuExchange.getAllPricing', {
      gpuType,
      region,
    });
  }

  /**
   * Estimate cost for GPU usage.
   */
  async estimateGPUCost(params: {
    gpuType: string;
    durationSeconds: number;
    providerId?: string;
    useSpot?: boolean;
  }): Promise<GPUCostEstimate> {
    return this.request<GPUCostEstimate>('gpuExchange.estimateCost', params);
  }

  /**
   * Select optimal provider for a job.
   */
  async selectGPUProvider(params: {
    gpuType: string;
    durationSeconds: number;
    config?: GPURoutingConfig;
    requiredCapability?: string;
  }): Promise<GPUProviderSelection> {
    return this.request<GPUProviderSelection>('gpuExchange.selectProvider', params);
  }

  /**
   * Get routing statistics.
   */
  async getGPURoutingStats(): Promise<GPURoutingStats> {
    return this.request<GPURoutingStats>('gpuExchange.getRoutingStats');
  }

  /**
   * Set budget limit for a project.
   */
  async setGPUBudgetLimit(projectId: string, limitUsd: number): Promise<{ status: string }> {
    return this.request<{ status: string }>('gpuExchange.setBudgetLimit', {
      projectId,
      limitUsd,
    });
  }

  /**
   * Check if a job would exceed budget.
   */
  async checkGPUBudget(params: {
    projectId: string;
    estimatedCost: number;
    currentSpent?: number;
  }): Promise<{ allowed: boolean; warning?: string }> {
    return this.request('gpuExchange.checkBudget', params);
  }

  /**
   * List all GPU types.
   */
  async listGPUTypes(): Promise<GPUTypeInfo[]> {
    return this.request<GPUTypeInfo[]>('gpuExchange.listGPUTypes');
  }

  /**
   * List all GPU capabilities.
   */
  async listGPUCapabilities(): Promise<GPUCapabilityInfo[]> {
    return this.request<GPUCapabilityInfo[]>('gpuExchange.listCapabilities');
  }

  /**
   * List all pricing tiers.
   */
  async listGPUPricingTiers(): Promise<GPUPricingTierInfo[]> {
    return this.request<GPUPricingTierInfo[]>('gpuExchange.listPricingTiers');
  }

  // ============ Co-pilot (Steven) ============

  /**
   * Send a chat message to the co-pilot.
   */
  async sendCopilotMessage(request: CopilotChatRequest): Promise<CopilotChatResponse> {
    return this.request<CopilotChatResponse>('copilot.chat', request as unknown as Record<string, unknown>);
  }

  /**
   * Get project analysis from the co-pilot.
   */
  async getCopilotAnalysis(projectId: string): Promise<CopilotAnalysis> {
    return this.request<CopilotAnalysis>('copilot.analyze', { projectId });
  }

  /**
   * Get suggestions for a scene.
   */
  async getCopilotSceneSuggestions(
    projectId: string,
    sceneId: string
  ): Promise<CopilotSuggestion[]> {
    return this.request<CopilotSuggestion[]>('copilot.suggestScene', {
      projectId,
      sceneId,
    });
  }

  /**
   * Get suggestions for a shot.
   */
  async getCopilotShotSuggestions(
    projectId: string,
    shotId: string
  ): Promise<CopilotSuggestion[]> {
    return this.request<CopilotSuggestion[]>('copilot.suggestShot', {
      projectId,
      shotId,
    });
  }

  /**
   * Apply a co-pilot suggestion.
   */
  async applyCopilotSuggestion(
    projectId: string,
    suggestionId: string
  ): Promise<{ success: boolean; changes?: Record<string, unknown> }> {
    return this.request('copilot.applySuggestion', { projectId, suggestionId });
  }

  /**
   * Dismiss a co-pilot suggestion.
   */
  async dismissCopilotSuggestion(
    projectId: string,
    suggestionId: string
  ): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>('copilot.dismissSuggestion', {
      projectId,
      suggestionId,
    });
  }

  /**
   * Get co-pilot quick actions for current context.
   */
  async getCopilotQuickActions(context: {
    projectId: string;
    sceneId?: string;
    shotId?: string;
  }): Promise<Array<{ id: string; label: string; action: string }>> {
    return this.request('copilot.getQuickActions', context);
  }

  // ============ Screenplay ============

  /**
   * Upload a screenplay file.
   */
  async uploadScreenplay(
    projectId: string,
    filePath: string,
    filename: string
  ): Promise<ScreenplayUploadResult> {
    return this.request<ScreenplayUploadResult>('screenplays.upload', {
      project_id: projectId,
      file_path: filePath,
      filename,
    });
  }

  /**
   * Parse an uploaded screenplay.
   */
  async parseScreenplay(screenplayId: string): Promise<ScreenplayParseResult> {
    return this.request<ScreenplayParseResult>('screenplays.parse', {
      screenplay_id: screenplayId,
    });
  }

  /**
   * Get screenplay details.
   */
  async getScreenplay(screenplayId: string): Promise<ScreenplayDetails> {
    return this.request<ScreenplayDetails>('screenplays.get', {
      screenplay_id: screenplayId,
    });
  }

  /**
   * Get screenplay for a project.
   */
  async getProjectScreenplay(projectId: string): Promise<ScreenplaySummary | null> {
    return this.request<ScreenplaySummary | null>('screenplays.getByProject', {
      project_id: projectId,
    });
  }

  /**
   * Delete a screenplay.
   */
  async deleteScreenplay(screenplayId: string): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>('screenplays.delete', {
      screenplay_id: screenplayId,
    });
  }

  // ============ Movie Plan ============

  /**
   * Generate a movie plan for a screenplay.
   */
  async generateMoviePlan(
    screenplayId: string,
    regenerate: boolean = false
  ): Promise<MoviePlan> {
    return this.request<MoviePlan>('moviePlan.generate', {
      screenplay_id: screenplayId,
      regenerate,
    });
  }

  /**
   * Get the movie plan for a screenplay.
   */
  async getMoviePlan(screenplayId: string): Promise<MoviePlan | null> {
    return this.request<MoviePlan | null>('moviePlan.get', {
      screenplay_id: screenplayId,
    });
  }

  /**
   * Approve the movie plan.
   */
  async approveMoviePlan(screenplayId: string): Promise<{ success: boolean; message: string }> {
    return this.request<{ success: boolean; message: string }>('moviePlan.approve', {
      screenplay_id: screenplayId,
    });
  }

  // ============ Characters ============

  /**
   * List all characters for a project.
   */
  async listCharacters(projectId: string): Promise<Character[]> {
    return this.request<Character[]>('characters.list', { project_id: projectId });
  }

  /**
   * Get a character by ID.
   */
  async getCharacter(characterId: string): Promise<Character> {
    return this.request<Character>('characters.get', { character_id: characterId });
  }

  /**
   * Update a character.
   */
  async updateCharacter(
    characterId: string,
    data: CharacterUpdateRequest
  ): Promise<{ id: string; name: string; lockState: string; updatedAt: string }> {
    return this.request('characters.update', {
      character_id: characterId,
      ...data,
    });
  }

  /**
   * Generate character description from screenplay.
   */
  async generateCharacterDescription(characterId: string): Promise<GeneratedCharacterDescription> {
    return this.request<GeneratedCharacterDescription>('characters.generateDescription', {
      character_id: characterId,
    });
  }

  /**
   * Upload a reference image for a character.
   */
  async uploadCharacterReference(
    characterId: string,
    filePath: string,
    filename: string,
    isPrimary: boolean = false
  ): Promise<CharacterReference> {
    return this.request<CharacterReference>('characters.uploadReference', {
      character_id: characterId,
      file_path: filePath,
      filename,
      is_primary: isPrimary,
    });
  }

  /**
   * Delete a reference image.
   */
  async deleteCharacterReference(
    characterId: string,
    assetId: string
  ): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>('characters.deleteReference', {
      character_id: characterId,
      asset_id: assetId,
    });
  }

  /**
   * Lock a character's likeness.
   */
  async lockCharacter(
    characterId: string,
    primaryReferenceId?: string
  ): Promise<{ id: string; name: string; lockState: string; isLocked: boolean; lockedLikeness: Record<string, unknown> | null }> {
    return this.request('characters.lock', {
      character_id: characterId,
      primary_reference_id: primaryReferenceId,
    });
  }

  /**
   * Unlock a character for editing.
   */
  async unlockCharacter(
    characterId: string
  ): Promise<{ id: string; name: string; lockState: string; isLocked: boolean }> {
    return this.request('characters.unlock', { character_id: characterId });
  }

  /**
   * Update character voice assignment.
   */
  async updateCharacterVoice(
    characterId: string,
    voiceId: string,
    voiceProvider: string,
    voiceName: string
  ): Promise<{ id: string; name: string; voiceId: string; voiceProvider: string; voiceName: string }> {
    return this.request('characters.updateVoice', {
      character_id: characterId,
      voice_id: voiceId,
      voice_provider: voiceProvider,
      voice_name: voiceName,
    });
  }

  /**
   * Get AI generation prompts for a character.
   */
  async getCharacterPrompt(
    characterId: string,
    sceneContext?: string
  ): Promise<CharacterPrompt> {
    return this.request<CharacterPrompt>('characters.getPrompt', {
      character_id: characterId,
      scene_context: sceneContext,
    });
  }

  // ============ Scenes ============

  /**
   * List all scenes for a project.
   */
  async listScenes(projectId: string, includeShots: boolean = false): Promise<Scene[]> {
    return this.request<Scene[]>('scenes.list', {
      project_id: projectId,
      include_shots: includeShots,
    });
  }

  /**
   * Get a scene by ID.
   */
  async getScene(sceneId: string, includeShots: boolean = true): Promise<Scene> {
    return this.request<Scene>('scenes.get', {
      scene_id: sceneId,
      include_shots: includeShots,
    });
  }

  /**
   * Analyze a scene for shot planning.
   */
  async analyzeScene(sceneId: string): Promise<SceneAnalysis> {
    return this.request<SceneAnalysis>('scenes.analyze', { scene_id: sceneId });
  }

  /**
   * Generate shot breakdown for a scene.
   */
  async generateShotBreakdown(
    sceneId: string,
    regenerate: boolean = false
  ): Promise<ShotBreakdown> {
    return this.request<ShotBreakdown>('scenes.generateBreakdown', {
      scene_id: sceneId,
      regenerate,
    });
  }

  /**
   * Approve the shot breakdown for a scene.
   */
  async approveSceneBreakdown(sceneId: string): Promise<{
    id: string;
    state: string;
    shotBreakdownApproved: boolean;
    message: string;
  }> {
    return this.request('scenes.approve', { scene_id: sceneId });
  }

  /**
   * Get available shot types.
   */
  async getShotTypes(): Promise<ShotTypeInfo[]> {
    return this.request<ShotTypeInfo[]>('scenes.getShotTypes');
  }

  /**
   * Get available camera movements.
   */
  async getCameraMovements(): Promise<CameraMovementInfo[]> {
    return this.request<CameraMovementInfo[]>('scenes.getCameraMovements');
  }

  // ============ Shots ============

  /**
   * Get a shot by ID.
   */
  async getShot(shotId: string): Promise<Shot> {
    return this.request<Shot>('shots.get', { shot_id: shotId });
  }

  /**
   * Update a shot.
   */
  async updateShot(shotId: string, data: ShotUpdateRequest): Promise<Shot> {
    return this.request<Shot>('shots.update', {
      shot_id: shotId,
      ...data,
    });
  }

  /**
   * Add a new shot to a scene.
   */
  async addShot(data: ShotAddRequest): Promise<Shot> {
    return this.request<Shot>('shots.add', data as unknown as Record<string, unknown>);
  }

  /**
   * Delete a shot.
   */
  async deleteShot(shotId: string): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>('shots.delete', { shot_id: shotId });
  }

  // ============ Generation (Extended) ============

  /**
   * Get available generation providers.
   */
  async getGenerationProviders(): Promise<Array<{ provider: string; name: string; available: boolean }>> {
    return this.request('generation.getProviders');
  }

  /**
   * Get generation queue status.
   */
  async getQueueStatus(projectId?: string): Promise<QueueStatus> {
    return this.request<QueueStatus>('generation.getQueueStatus', {
      project_id: projectId,
    });
  }

  /**
   * Queue a shot for generation.
   */
  async queueShot(
    shotId: string,
    provider: string = 'local',
    priority: number = 0
  ): Promise<QueuedJobResult> {
    return this.request<QueuedJobResult>('generation.queueShot', {
      shot_id: shotId,
      provider,
      priority,
    });
  }

  /**
   * Queue all shots in a scene for generation.
   */
  async queueScene(
    sceneId: string,
    provider: string = 'local'
  ): Promise<Array<{ id: string; shotId: string; jobNumber: number; status: string }>> {
    return this.request('generation.queueScene', {
      scene_id: sceneId,
      provider,
    });
  }

  /**
   * Queue all shots in a project for generation.
   */
  async queueProject(
    projectId: string,
    provider: string = 'local'
  ): Promise<{ queuedCount: number; jobs: Array<{ id: string; shotId: string; status: string }> }> {
    return this.request('generation.queueProject', {
      project_id: projectId,
      provider,
    });
  }

  /**
   * Get a generation job by ID.
   */
  async getGenerationJob(jobId: string): Promise<GenerationJob> {
    return this.request<GenerationJob>('generation.getJob', { job_id: jobId });
  }

  /**
   * Process a pending generation job.
   */
  async processGenerationJob(jobId: string): Promise<ProcessJobResult> {
    return this.request<ProcessJobResult>('generation.processJob', { job_id: jobId });
  }

  /**
   * Cancel a pending or running job.
   */
  async cancelGenerationJob(jobId: string): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>('generation.cancelJob', { job_id: jobId });
  }

  /**
   * Retry a failed job.
   */
  async retryGenerationJob(jobId: string): Promise<QueuedJobResult> {
    return this.request<QueuedJobResult>('generation.retryJob', { job_id: jobId });
  }

  /**
   * Approve a generated shot.
   */
  async approveGeneratedShot(shotId: string): Promise<{ id: string; state: string; approved: boolean }> {
    return this.request('generation.approveShot', { shot_id: shotId });
  }

  /**
   * Reject a generated shot for regeneration.
   */
  async rejectGeneratedShot(
    shotId: string,
    notes?: string
  ): Promise<{ id: string; state: string; rejected: boolean }> {
    return this.request('generation.rejectShot', { shot_id: shotId, notes });
  }

  /**
   * Get pending jobs in queue.
   */
  async getPendingJobs(limit: number = 20): Promise<GenerationJob[]> {
    return this.request<GenerationJob[]>('generation.getPendingJobs', { limit });
  }

  /**
   * Get all generation jobs for a shot.
   */
  async getShotJobs(shotId: string): Promise<GenerationJob[]> {
    return this.request<GenerationJob[]>('generation.getShotJobs', { shot_id: shotId });
  }

  // ============ Queue Management ============

  /**
   * Get all jobs in queue.
   */
  async getAllQueueJobs(options?: {
    projectId?: string;
    status?: JobStatus;
    limit?: number;
    offset?: number;
  }): Promise<{ jobs: QueueJob[]; total: number }> {
    return this.request('queue.getAll', {
      project_id: options?.projectId,
      status: options?.status,
      limit: options?.limit,
      offset: options?.offset,
    });
  }

  /**
   * Set priority for a job.
   */
  async setJobPriority(jobId: string, priority: number): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>('queue.setPriority', {
      job_id: jobId,
      priority,
    });
  }

  /**
   * Move job to top of queue.
   */
  async moveJobToTop(jobId: string): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>('queue.moveToTop', { job_id: jobId });
  }

  /**
   * Move job to bottom of queue.
   */
  async moveJobToBottom(jobId: string): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>('queue.moveToBottom', { job_id: jobId });
  }

  /**
   * Cancel all pending jobs.
   */
  async cancelAllJobs(projectId?: string): Promise<{ cancelledCount: number }> {
    return this.request<{ cancelledCount: number }>('queue.cancelAll', {
      project_id: projectId,
    });
  }

  /**
   * Retry all failed jobs.
   */
  async retryFailedJobs(projectId?: string): Promise<{ retriedCount: number }> {
    return this.request<{ retriedCount: number }>('queue.retryFailed', {
      project_id: projectId,
    });
  }

  /**
   * Get queue statistics.
   */
  async getQueueStats(): Promise<QueueStats> {
    return this.request<QueueStats>('queue.getStats');
  }

  // ============ Assembly ============

  /**
   * Get assembly status for a project.
   */
  async getAssemblyStatus(projectId: string): Promise<AssemblyStatus> {
    return this.request<AssemblyStatus>('assembly.getStatus', { project_id: projectId });
  }

  /**
   * Get timeline for a project.
   */
  async getTimeline(projectId: string): Promise<Timeline> {
    return this.request<Timeline>('assembly.getTimeline', { project_id: projectId });
  }

  /**
   * Assemble a scene.
   */
  async assembleScene(sceneId: string): Promise<{
    success: boolean;
    outputPath: string | null;
    duration: number | null;
    error: string | null;
  }> {
    return this.request('assembly.assembleScene', { scene_id: sceneId });
  }

  /**
   * Assemble the entire movie.
   */
  async assembleMovie(projectId: string): Promise<{
    success: boolean;
    outputPath: string | null;
    duration: number | null;
    error: string | null;
  }> {
    return this.request('assembly.assembleMovie', { project_id: projectId });
  }

  /**
   * Export the assembled movie.
   */
  async exportMovie(request: ExportRequest): Promise<ExportJobResult> {
    return this.request<ExportJobResult>('assembly.export', request as unknown as Record<string, unknown>);
  }

  /**
   * Get export history for a project.
   */
  async getExportHistory(projectId: string): Promise<ExportHistoryItem[]> {
    return this.request<ExportHistoryItem[]>('assembly.getExportHistory', {
      project_id: projectId,
    });
  }

  /**
   * Get available export formats.
   */
  async getExportFormats(): Promise<ExportFormat[]> {
    return this.request<ExportFormat[]>('assembly.getFormats');
  }

  /**
   * Get available quality presets.
   */
  async getQualityPresets(): Promise<QualityPreset[]> {
    return this.request<QualityPreset[]>('assembly.getQualityPresets');
  }

  // ============ Audio/TTS ============

  /**
   * Get available voices.
   */
  async getVoices(provider?: string): Promise<Voice[]> {
    return this.request<Voice[]>('audio.getVoices', { provider });
  }

  /**
   * Get TTS providers.
   */
  async getTTSProviders(): Promise<TTSProvider[]> {
    return this.request<TTSProvider[]>('audio.getProviders');
  }

  /**
   * Generate speech from text.
   */
  async generateSpeech(request: GenerateSpeechRequest): Promise<GenerateSpeechResult> {
    return this.request<GenerateSpeechResult>('audio.generateSpeech', request as unknown as Record<string, unknown>);
  }

  /**
   * Generate dialogue audio for a shot.
   */
  async generateDialogueAudio(shotId: string): Promise<{
    success: boolean;
    generatedCount: number;
    errors: string[];
  }> {
    return this.request('audio.generateDialogue', { shot_id: shotId });
  }

  /**
   * Assign a voice to a character.
   */
  async assignVoiceToCharacter(
    characterId: string,
    voiceId: string,
    provider: string
  ): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>('audio.assignVoice', {
      character_id: characterId,
      voice_id: voiceId,
      provider,
    });
  }

  /**
   * Get voice assigned to a character.
   */
  async getCharacterVoice(characterId: string): Promise<{
    voiceId: string | null;
    provider: string | null;
    voiceName: string | null;
  }> {
    return this.request('audio.getCharacterVoice', { character_id: characterId });
  }

  /**
   * Get dialogue lines for a shot.
   */
  async getDialogueLines(shotId: string): Promise<DialogueLine[]> {
    return this.request<DialogueLine[]>('audio.getDialogueLines', { shot_id: shotId });
  }

  /**
   * Delete dialogue audio for a shot.
   */
  async deleteDialogueAudio(shotId: string): Promise<{ success: boolean; deletedCount: number }> {
    return this.request<{ success: boolean; deletedCount: number }>('audio.deleteDialogueAudio', {
      shot_id: shotId,
    });
  }

  // ============ Text Overlays ============

  /**
   * Get text overlay presets.
   */
  async getTextOverlayPresets(): Promise<TextOverlayPreset[]> {
    return this.request<TextOverlayPreset[]>('textOverlays.getPresets');
  }

  /**
   * Get text overlays for a shot.
   */
  async getTextOverlaysForShot(shotId: string): Promise<TextOverlay[]> {
    return this.request<TextOverlay[]>('textOverlays.getForShot', { shot_id: shotId });
  }

  /**
   * Get text overlays for a scene.
   */
  async getTextOverlaysForScene(sceneId: string): Promise<TextOverlay[]> {
    return this.request<TextOverlay[]>('textOverlays.getForScene', { scene_id: sceneId });
  }

  /**
   * Get text overlays for a project.
   */
  async getTextOverlaysForProject(projectId: string): Promise<TextOverlay[]> {
    return this.request<TextOverlay[]>('textOverlays.getForProject', { project_id: projectId });
  }

  /**
   * Create a text overlay.
   */
  async createTextOverlay(data: TextOverlayCreateRequest): Promise<TextOverlay> {
    return this.request<TextOverlay>('textOverlays.create', data as unknown as Record<string, unknown>);
  }

  /**
   * Update a text overlay.
   */
  async updateTextOverlay(
    overlayId: string,
    data: Partial<TextOverlayCreateRequest>
  ): Promise<TextOverlay> {
    return this.request<TextOverlay>('textOverlays.update', {
      overlay_id: overlayId,
      ...data,
    });
  }

  /**
   * Delete a text overlay.
   */
  async deleteTextOverlay(overlayId: string): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>('textOverlays.delete', { overlay_id: overlayId });
  }

  /**
   * Batch update text overlays for a shot.
   */
  async batchUpdateTextOverlays(
    shotId: string,
    overlays: Array<Partial<TextOverlay> & { text: string }>
  ): Promise<{ success: boolean; overlays: TextOverlay[] }> {
    return this.request('textOverlays.batchUpdateForShot', {
      shot_id: shotId,
      overlays,
    });
  }

  // ============ Color Grading ============

  /**
   * Save color grading settings for a project.
   */
  async saveColorGrade(
    projectId: string,
    settings: ColorGradeSettings
  ): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>('colorGrade.save', {
      project_id: projectId,
      settings,
    });
  }

  /**
   * Get color grading settings for a project.
   */
  async getColorGrade(projectId: string): Promise<ColorGradeSettings | null> {
    return this.request<ColorGradeSettings | null>('colorGrade.get', {
      project_id: projectId,
    });
  }

  /**
   * Get color grading presets.
   */
  async getColorGradePresets(): Promise<ColorGradePreset[]> {
    return this.request<ColorGradePreset[]>('colorGrade.getPresets');
  }

  // ============ Music Library ============

  /**
   * Get music tracks from the library.
   */
  async getMusicTracks(options?: {
    category?: string;
    mood?: string;
    tempo?: string;
    favorites?: boolean;
    search?: string;
    limit?: number;
    offset?: number;
  }): Promise<{ tracks: MusicTrack[]; total: number }> {
    return this.request('music.getTracks', options);
  }

  /**
   * Get a specific music track.
   */
  async getMusicTrack(trackId: string): Promise<MusicTrack> {
    return this.request<MusicTrack>('music.getTrack', { track_id: trackId });
  }

  /**
   * Toggle favorite status for a music track.
   */
  async toggleMusicFavorite(trackId: string): Promise<{ isFavorite: boolean }> {
    return this.request<{ isFavorite: boolean }>('music.toggleFavorite', {
      track_id: trackId,
    });
  }

  /**
   * Upload a custom music track.
   */
  async uploadMusicTrack(
    filePath: string,
    filename: string,
    metadata?: {
      title?: string;
      artist?: string;
      category?: string;
      mood?: string;
      tempo?: string;
    }
  ): Promise<MusicTrack> {
    return this.request<MusicTrack>('music.uploadTrack', {
      file_path: filePath,
      filename,
      ...metadata,
    });
  }

  // ============ Sound Effects ============

  /**
   * Get sound effects from the library.
   */
  async getSoundEffects(options?: {
    category?: string;
    favorites?: boolean;
    search?: string;
    limit?: number;
    offset?: number;
  }): Promise<{ effects: SoundEffect[]; total: number }> {
    return this.request('sfx.getEffects', options);
  }

  /**
   * Toggle favorite status for a sound effect.
   */
  async toggleSoundEffectFavorite(effectId: string): Promise<{ isFavorite: boolean }> {
    return this.request<{ isFavorite: boolean }>('sfx.toggleFavorite', {
      effect_id: effectId,
    });
  }

  /**
   * Upload a custom sound effect.
   */
  async uploadSoundEffect(
    filePath: string,
    filename: string,
    metadata?: {
      name?: string;
      category?: string;
      tags?: string[];
    }
  ): Promise<SoundEffect> {
    return this.request<SoundEffect>('sfx.uploadEffect', {
      file_path: filePath,
      filename,
      ...metadata,
    });
  }

  // ============ Templates ============

  /**
   * List project templates.
   */
  async listTemplates(options?: {
    category?: string;
    featured?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<{ templates: ProjectTemplate[]; total: number }> {
    return this.request('templates.list', options);
  }

  /**
   * Get a specific template.
   */
  async getTemplate(templateId: string): Promise<ProjectTemplate> {
    return this.request<ProjectTemplate>('templates.get', { template_id: templateId });
  }

  /**
   * Get template categories.
   */
  async getTemplateCategories(): Promise<TemplateCategory[]> {
    return this.request<TemplateCategory[]>('templates.getCategories');
  }

  /**
   * Search templates.
   */
  async searchTemplates(
    query: string,
    options?: {
      category?: string;
      limit?: number;
    }
  ): Promise<ProjectTemplate[]> {
    return this.request<ProjectTemplate[]>('templates.search', {
      query,
      ...options,
    });
  }

  /**
   * Get featured templates.
   */
  async getFeaturedTemplates(limit?: number): Promise<ProjectTemplate[]> {
    return this.request<ProjectTemplate[]>('templates.getFeatured', { limit });
  }

  /**
   * Get template settings/configuration.
   */
  async getTemplateSettings(templateId: string): Promise<TemplateSettings> {
    return this.request<TemplateSettings>('templates.getSettings', {
      template_id: templateId,
    });
  }

  // ============ Timeline ============

  /**
   * Save timeline state.
   */
  async saveTimeline(
    projectId: string,
    timeline: TimelineSaveData
  ): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>('timeline.save', {
      project_id: projectId,
      timeline,
    });
  }

  /**
   * Get detailed clip information.
   */
  async getTimelineClipDetails(clipId: string): Promise<TimelineClipDetails> {
    return this.request<TimelineClipDetails>('timeline.getClipDetails', {
      clip_id: clipId,
    });
  }

  // ============ Overlays ============

  /**
   * Save overlay settings for a shot.
   */
  async saveOverlays(
    shotId: string,
    overlays: OverlaySaveData[]
  ): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>('overlays.save', {
      shot_id: shotId,
      overlays,
    });
  }

  /**
   * Get overlay settings for a shot.
   */
  async getOverlays(shotId: string): Promise<OverlaySaveData[]> {
    return this.request<OverlaySaveData[]>('overlays.get', {
      shot_id: shotId,
    });
  }

  // ============ System ============

  /**
   * Log an error to the backend.
   */
  async logError(error: {
    message: string;
    stack?: string;
    component?: string;
    context?: Record<string, unknown>;
  }): Promise<{ logged: boolean }> {
    return this.request<{ logged: boolean }>('system.logError', error);
  }

  /**
   * Get system health status.
   */
  async getSystemHealth(): Promise<SystemHealthStatus> {
    return this.request<SystemHealthStatus>('system.getHealth');
  }
}

// ============ Color Grading Types ============

export interface ColorGradeSettings {
  brightness: number;
  contrast: number;
  saturation: number;
  temperature: number;
  tint: number;
  highlights: number;
  shadows: number;
  whites: number;
  blacks: number;
  vibrance: number;
  exposure: number;
  gamma: number;
  lut?: string;
  lutIntensity?: number;
}

export interface ColorGradePreset {
  id: string;
  name: string;
  category: string;
  description: string;
  settings: ColorGradeSettings;
  thumbnailUrl?: string;
}

// ============ Music Library Types ============

export interface MusicTrack {
  id: string;
  title: string;
  artist: string | null;
  category: string;
  mood: string | null;
  tempo: string | null;
  durationSeconds: number;
  filePath: string;
  waveformUrl: string | null;
  previewUrl: string | null;
  isFavorite: boolean;
  isCustom: boolean;
  bpm: number | null;
  tags: string[];
  createdAt: string;
}

// ============ Sound Effects Types ============

export interface SoundEffect {
  id: string;
  name: string;
  category: string;
  durationSeconds: number;
  filePath: string;
  previewUrl: string | null;
  isFavorite: boolean;
  isCustom: boolean;
  tags: string[];
  createdAt: string;
}

// ============ Template Types ============

export interface ProjectTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  thumbnailUrl: string | null;
  previewUrl: string | null;
  isFeatured: boolean;
  useCount: number;
  settings: TemplateSettings;
  createdAt: string;
}

export interface TemplateCategory {
  id: string;
  name: string;
  description: string;
  templateCount: number;
}

export interface TemplateSettings {
  defaultResolution: string;
  defaultFps: number;
  defaultAspectRatio: string;
  colorGradePreset?: string;
  musicCategory?: string;
  shotTypes: string[];
  cameraMovements: string[];
  estimatedDuration?: number;
}

// ============ Timeline Types (Extended) ============

export interface TimelineSaveData {
  clips: Array<{
    id: string;
    shotId: string;
    startTime: number;
    endTime: number;
    track: number;
    trimStart?: number;
    trimEnd?: number;
  }>;
  audioTracks: Array<{
    id: string;
    trackId: string;
    type: 'music' | 'sfx' | 'dialogue';
    startTime: number;
    endTime: number;
    volume: number;
    fadeIn?: number;
    fadeOut?: number;
  }>;
  markers: Array<{
    id: string;
    time: number;
    label: string;
    color?: string;
  }>;
  zoom: number;
  scrollPosition: number;
}

export interface TimelineClipDetails {
  id: string;
  shotId: string;
  sceneId: string;
  projectId: string;
  shotNumber: string;
  sceneNumber: string;
  description: string;
  videoPath: string | null;
  thumbnailPath: string | null;
  durationSeconds: number;
  state: string;
  overlays: TextOverlay[];
  audioTracks: Array<{
    type: string;
    path: string;
    volume: number;
    startTime: number;
  }>;
}

// ============ Overlay Types (Extended) ============

export interface OverlaySaveData {
  id?: string;
  type: TextOverlayType;
  text: string;
  position: TextPosition;
  customX?: number;
  customY?: number;
  style: Partial<TextOverlayStyle>;
  animationIn: TextAnimation;
  animationOut: TextAnimation;
  startTimeMs: number;
  durationMs: number;
  isVisible: boolean;
  zIndex: number;
}

// ============ System Types ============

export interface SystemHealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  uptime: number;
  memoryUsage: {
    used: number;
    total: number;
    percentage: number;
  };
  diskUsage: {
    used: number;
    total: number;
    percentage: number;
  };
  services: Array<{
    name: string;
    status: 'up' | 'down' | 'degraded';
    latencyMs?: number;
    lastCheck: string;
  }>;
  circuitBreakers: Record<string, {
    state: string;
    failureCount: number;
  }>;
  version: string;
  environment: string;
}

// ============ ActForge (Performers & Bookings) Types ============

export type PerformerType = 'HUMAN' | 'SYNTHETIC';
export type BookingMode = 'BLINK' | 'DEEP' | 'EPIC' | 'AUCTION';
export type BookingStatus =
  | 'REQUESTED'
  | 'MATCHING'
  | 'MATCHED'
  | 'ACCEPTED'
  | 'IN_PROGRESS'
  | 'DELIVERED'
  | 'APPROVED'
  | 'DISPUTED'
  | 'COMPLETED'
  | 'CANCELLED';
export type PaymentStatus = 'PENDING' | 'ESCROWED' | 'RELEASED' | 'REFUNDED' | 'DISPUTED';

export interface Performer {
  id: string;
  stage_name: string;
  bio: string | null;
  performer_type: PerformerType;
  aci_score: number;
  revenue_tier: number;
  revenue_split_percent: number;
  is_verified: boolean;
  is_available: boolean;
  is_featured: boolean;
  total_bookings: number;
  completed_bookings: number;
  average_rating: number;
  total_ratings: number;
  lifetime_earnings_usd: number;
  pricing_blink_usd: number;
  pricing_deep_usd: number;
  pricing_epic_usd: number;
  motion_capabilities: {
    live_portrait: boolean;
    roop_gs_anim: boolean;
    emotion_range: string[];
    body_types: string[];
  };
  avatar_url: string | null;
  demo_video_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface PerformerCreateRequest {
  stage_name: string;
  bio?: string;
  performer_type: PerformerType;
  pricing_blink_usd?: number;
  pricing_deep_usd?: number;
  pricing_epic_usd?: number;
  motion_capabilities?: Performer['motion_capabilities'];
}

export interface PerformerSearchParams {
  type?: PerformerType;
  is_verified?: boolean;
  is_available?: boolean;
  is_featured?: boolean;
  min_aci?: number;
  max_price?: number;
  capabilities?: string[];
  query?: string;
  sort_by?: 'aci_score' | 'price' | 'rating' | 'bookings';
  sort_order?: 'asc' | 'desc';
  limit?: number;
  offset?: number;
}

export interface Booking {
  id: string;
  project_id: string;
  shot_id: string | null;
  performer_id: string;
  performer_stage_name: string;
  booking_mode: BookingMode;
  status: BookingStatus;
  price_usd: number;
  platform_fee_usd: number | null;
  performer_payout_usd: number | null;
  payment_status: PaymentStatus;
  requirements: {
    duration_seconds: number;
    emotion_markers: string[];
    special_instructions: string | null;
    reference_images: string[];
  };
  delivery_url: string | null;
  delivery_notes: string | null;
  rating: number | null;
  review: string | null;
  created_at: string;
  updated_at: string;
  accepted_at: string | null;
  delivered_at: string | null;
  completed_at: string | null;
}

export interface BookingCreateRequest {
  project_id: string;
  shot_id?: string;
  performer_id?: string; // Optional for auto-match in BLINK mode
  booking_mode: BookingMode;
  duration_seconds: number;
  emotion_markers?: string[];
  special_instructions?: string;
  reference_images?: string[];
  max_price_usd?: number;
}

export interface PayoutCalculation {
  booking_price_usd: number;
  performer_split_percent: number;
  platform_fee_percent: number;
  performer_payout_usd: number;
  platform_fee_usd: number;
  current_tier: number;
  lifetime_earnings_usd: number;
  earnings_to_next_tier: number | null;
  next_tier_split_percent: number | null;
}

export interface ACIBreakdown {
  performer_id: string;
  total_aci: number;
  placement_rate: number;
  placement_score: number;
  rehire_rate: number;
  rehire_score: number;
  audience_buzz: number;
  buzz_score: number;
  motion_score: number;
  motion_score_weighted: number;
}

export interface PerformerLeaderboardEntry {
  rank: number;
  performer_id: string;
  stage_name: string;
  aci_score: number;
  completed_bookings: number;
  average_rating: number;
  avatar_url: string | null;
}

// ============ GPU Exchange Types ============

export interface GPUProviderInfo {
  id: string;
  name: string;
  priority: number;
  capabilities: string[];
  supported_gpu_types: string[];
  regions: string[];
}

export interface GPUProviderHealth {
  provider_id: string;
  available: boolean;
  message: string;
  latency_ms: number | null;
  instances_available: number;
  queue_depth: number;
  error_code: string | null;
  last_check: string;
}

export interface AllGPUProvidersHealth {
  providers: Record<string, GPUProviderHealth>;
  healthy_count: number;
  total_count: number;
}

export interface GPUPricing {
  gpu_type: string;
  price_per_hour: number;
  price_per_second: number;
  spot_price_per_hour: number | null;
  reserved_price_per_hour: number | null;
  currency: string;
  region: string;
  availability: number;
  last_updated: string;
}

export interface GPUPricingComparison {
  gpu_type: string;
  region: string;
  cheapest_provider: string;
  cheapest_price: number;
  fastest_provider: string;
  best_value_provider: string;
  all_options: Array<{
    provider: string;
    price_per_hour: number;
    spot_price: number | null;
    availability: number;
    value_score: number;
  }>;
  generated_at: string;
}

export interface GPURoutingConfig {
  priority?: 'low' | 'normal' | 'high' | 'urgent';
  max_price_usd?: number;
  preferred_providers?: string[];
  excluded_providers?: string[];
  preferred_regions?: string[];
  allow_spot?: boolean;
}

export interface GPUProviderSelection {
  provider_id: string;
  provider_name: string;
  price_per_hour: number;
  estimated_cost: number;
  use_spot: boolean;
  fallback_providers: string[];
  score_breakdown: {
    total: number;
    cost: number;
    latency: number;
    reliability: number;
    queue: number;
  };
}

export interface GPURoutingStats {
  total_routings: number;
  successful: number;
  success_rate: number;
  failovers_used: number;
  by_provider: Record<string, { total: number; successful: number }>;
  circuit_breakers: Record<string, string>;
  reliability_scores: Record<string, number>;
}

export interface GPUCostEstimate {
  provider_id: string;
  gpu_type: string;
  duration_seconds: number;
  use_spot: boolean;
  estimated_cost_usd: number;
  price_per_hour: number;
  currency: string;
}

export interface GPUTypeInfo {
  id: string;
  name: string;
}

export interface GPUCapabilityInfo {
  id: string;
  name: string;
}

export interface GPUPricingTierInfo {
  id: string;
  name: string;
  description: string;
}

// ============ Co-pilot (Steven) Types ============

export interface CopilotMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
}

export interface CopilotSuggestion {
  id: string;
  type: 'scene' | 'shot' | 'character' | 'dialogue' | 'pacing' | 'visual';
  title: string;
  description: string;
  confidence: number;
  context?: Record<string, unknown>;
  applied?: boolean;
}

export interface CopilotAnalysis {
  projectId: string;
  overallScore: number;
  pacing: {
    score: number;
    feedback: string;
    suggestions: string[];
  };
  characterDevelopment: {
    score: number;
    feedback: string;
    suggestions: string[];
  };
  visualStorytelling: {
    score: number;
    feedback: string;
    suggestions: string[];
  };
  dialogue: {
    score: number;
    feedback: string;
    suggestions: string[];
  };
  suggestions: CopilotSuggestion[];
  generatedAt: string;
}

export interface CopilotChatRequest {
  projectId: string;
  message: string;
  context?: {
    sceneId?: string;
    shotId?: string;
    characterId?: string;
  };
}

export interface CopilotChatResponse {
  message: string;
  suggestions?: CopilotSuggestion[];
  relatedScenes?: string[];
  relatedShots?: string[];
}

// ============ Circuit Breaker Types ============

export interface CircuitBreakerStatus {
  name: string;
  state: 'closed' | 'open' | 'half_open';
  totalCalls: number;
  successfulCalls: number;
  failedCalls: number;
  rejectedCalls: number;
  consecutiveFailures: number;
  consecutiveSuccesses: number;
  lastFailureTime: number | null;
  lastSuccessTime: number | null;
  failureThreshold: number;
  recoveryTimeout: number;
  remainingTimeout: number;
  successRate: number;
}

export interface CircuitBreakersResponse {
  circuits: CircuitBreakerStatus[];
  totalCount: number;
  openCount: number;
  halfOpenCount: number;
}

// ============ Watermark Types ============

export interface WatermarkInfo {
  id: string;
  filename: string;
  path: string;
  sizeBytes: number;
  createdAt: string;
  isDefault: boolean;
}

export interface WatermarksResponse {
  watermarks: WatermarkInfo[];
  totalCount: number;
}

export interface WatermarkUploadResponse {
  success: boolean;
  watermark?: WatermarkInfo;
  error?: string;
}

// ============ Screenplay Types ============

export interface ScreenplayUploadResult {
  id: string;
  projectId: string;
  originalFilename: string;
  originalFormat: string;
  isParsed: boolean;
  createdAt: string;
}

export interface ScreenplayParseResult {
  id: string;
  isParsed: boolean;
  parseErrors: string[] | null;
  metadata: Record<string, unknown>;
}

export interface ScreenplayDetails {
  id: string;
  projectId: string;
  originalFilename: string;
  originalFormat: string;
  isParsed: boolean;
  parseErrors: string[] | null;
  parsedContent: Record<string, unknown> | null;
  characters: Array<{
    id: string;
    name: string;
    dialogueCount: number;
    sceneCount: number;
  }>;
  scenes: Array<{
    id: string;
    sceneNumber: string;
    sequenceNumber: number;
    sceneType: string;
    location: string;
    timeOfDay: string;
  }>;
  createdAt: string;
  updatedAt: string;
}

export interface ScreenplaySummary {
  id: string;
  projectId: string;
  originalFilename: string;
  originalFormat: string;
  isParsed: boolean;
  createdAt: string;
}

// ============ Movie Plan Types ============

export interface MoviePlan {
  screenplayId: string;
  generatedAt: string;
  aiModel: string;
  title: string;
  logline: string;
  genre: string[];
  tone: string[];
  themes: string[];
  estimatedRuntimeMinutes: number;
  visualStyle: Record<string, unknown>;
  colorPalette: string[];
  cinematographyNotes: string;
  characters: Record<string, unknown>[];
  protagonist: string | null;
  antagonist: string | null;
  scenes: Record<string, unknown>[];
  actStructure: Record<string, unknown>;
  locationRequirements: string[];
  propRequirements: string[];
  specialEffectsNotes: string;
  generationNotes: string[];
  warnings: string[];
}

// ============ Character Types ============

export type CharacterGender = 'male' | 'female' | 'non_binary' | 'other' | 'unknown';
export type CharacterLockState = 'unlocked' | 'locked' | 'locked_with_reference';

export interface Character {
  id: string;
  projectId: string;
  name: string;
  screenplayName: string | null;
  description: string | null;
  ageRangeMin: number | null;
  ageRangeMax: number | null;
  ageRangeDisplay: string | null;
  gender: CharacterGender;
  physicalDescription: Record<string, unknown> | null;
  personalityTraits: string[] | null;
  voiceDescription: string | null;
  lockState: CharacterLockState;
  isLocked: boolean;
  lockedLikeness: Record<string, unknown> | null;
  sceneCount: number;
  dialogueCount: number;
  isProtagonist: boolean;
  referenceCount?: number;
  referenceAssets?: CharacterReference[];
  voiceId: string | null;
  voiceProvider: string | null;
  voiceName: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface CharacterReference {
  id: string;
  assetType: string;
  originalFilename: string;
  filePath: string;
  isPrimary: boolean;
  createdAt: string;
}

export interface CharacterUpdateRequest {
  name?: string;
  description?: string;
  age_range_min?: number;
  age_range_max?: number;
  gender?: CharacterGender;
  physical_description?: Record<string, unknown>;
  personality_traits?: string[];
  voice_description?: string;
  is_protagonist?: boolean;
}

export interface GeneratedCharacterDescription {
  description: string;
  estimatedAge: number | null;
  gender: string | null;
  personalityTraits: string[];
  physicalDescription: Record<string, unknown>;
}

export interface CharacterPrompt {
  characterPrompt: string;
  stylePrompt: string;
  combinedPrompt: string;
}

// ============ Scene Types ============

export type SceneState = 'draft' | 'analyzed' | 'breakdown_generated' | 'breakdown_approved' | 'generating' | 'generated' | 'approved';

export interface Scene {
  id: string;
  projectId: string;
  screenplayId: string | null;
  sceneNumber: string;
  sequenceNumber: number;
  heading: string;
  sceneType: string;
  location: string;
  timeOfDay: string;
  state: SceneState;
  characterIds: string[];
  rawContent: string | null;
  actionLines: string[] | null;
  analysis: Record<string, unknown> | null;
  shotBreakdown: Record<string, unknown> | null;
  shotBreakdownApproved: boolean;
  estimatedDurationSeconds: number | null;
  shotCount?: number;
  shots?: Shot[];
}

export interface SceneAnalysis {
  summary: string;
  mood: string;
  emotionalArc: string;
  keyMoments: string[];
  visualStyleSuggestions: string[];
  pacing: string;
  importance: string;
  suggestedShotCount: number;
  dialogueHeavy: boolean;
  actionHeavy: boolean;
}

export interface ShotBreakdown {
  sceneId: string;
  approach: string;
  coverageStyle: string;
  notes: string;
  estimatedDuration: number;
  shots: Shot[];
}

// ============ Shot Types ============

export type ShotState = 'planned' | 'queued' | 'generating' | 'generated' | 'approved' | 'rejected';
export type ShotType = 'wide' | 'medium' | 'close_up' | 'extreme_close_up' | 'two_shot' | 'over_shoulder' | 'pov' | 'insert' | 'establishing' | 'aerial' | 'dutch_angle' | 'low_angle' | 'high_angle' | 'tracking' | 'dolly' | 'crane' | 'handheld' | 'steadicam' | 'custom';
export type CameraMovement = 'static' | 'pan_left' | 'pan_right' | 'tilt_up' | 'tilt_down' | 'dolly_in' | 'dolly_out' | 'truck_left' | 'truck_right' | 'crane_up' | 'crane_down' | 'zoom_in' | 'zoom_out' | 'tracking' | 'arc' | 'roll' | 'handheld' | 'custom';

export interface Shot {
  id: string;
  sceneId?: string;
  shotNumber: string;
  sequenceNumber: number;
  shotType: ShotType;
  cameraMovement: CameraMovement;
  description: string;
  dialogue: string | null;
  action: string | null;
  characterIds: string[];
  durationSeconds: number;
  compositionNotes: string | null;
  lightingNotes: string | null;
  state: ShotState;
  prompt?: string | null;
}

export interface ShotUpdateRequest {
  shot_number?: string;
  shot_type?: ShotType;
  camera_movement?: CameraMovement;
  description?: string;
  dialogue?: string;
  action?: string;
  character_ids?: string[];
  duration_seconds?: number;
  composition_notes?: string;
  lighting_notes?: string;
  prompt?: string;
}

export interface ShotAddRequest {
  scene_id: string;
  shot_type: ShotType;
  camera_movement?: CameraMovement;
  description: string;
  dialogue?: string;
  action?: string;
  character_ids?: string[];
  duration_seconds?: number;
  composition_notes?: string;
  lighting_notes?: string;
  insert_after?: string; // shot_id to insert after
}

export interface ShotTypeInfo {
  value: string;
  label: string;
  description: string;
}

export interface CameraMovementInfo {
  value: string;
  label: string;
  description: string;
}

// ============ Generation Job Types ============

export type JobStatus = 'pending' | 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface GenerationJob {
  id: string;
  shotId: string;
  jobNumber: number;
  status: JobStatus;
  provider: string;
  modelId: string | null;
  progressPercent: number;
  progressMessage: string | null;
  errorMessage: string | null;
  outputPath: string | null;
  thumbnailPath: string | null;
  costUsd: number | null;
  queuedAt: string | null;
  startedAt: string | null;
  completedAt: string | null;
}

export interface QueueStatus {
  pending: number;
  running: number;
  completed: number;
  failed: number;
  total: number;
  jobs: GenerationJob[];
}

export interface QueuedJobResult {
  id: string;
  shotId: string;
  jobNumber: number;
  status: JobStatus;
  provider: string;
  queuedAt: string | null;
}

export interface ProcessJobResult {
  success: boolean;
  jobId: string | null;
  status: JobStatus | null;
  outputPath: string | null;
  errorMessage: string | null;
}

// ============ Queue Management Types ============

export interface QueueJob {
  id: string;
  shotId: string;
  sceneId: string;
  projectId: string;
  jobNumber: number;
  status: JobStatus;
  provider: string;
  priority: number;
  progressPercent: number;
  progressMessage: string | null;
  errorMessage: string | null;
  outputPath: string | null;
  thumbnailPath: string | null;
  queuedAt: string | null;
  startedAt: string | null;
  completedAt: string | null;
  sceneNumber: string;
  shotNumber: string;
}

export interface QueueStats {
  pending: number;
  running: number;
  completed: number;
  failed: number;
  cancelled: number;
  totalJobsProcessed: number;
  averageProcessingTimeSeconds: number;
  estimatedTimeRemainingSeconds: number;
}

// ============ Assembly Types ============

export interface AssemblyStatus {
  projectId: string;
  totalScenes: number;
  completedScenes: number;
  totalShots: number;
  generatedShots: number;
  approvedShots: number;
  totalDurationSeconds: number;
  approvedDurationSeconds: number;
  readyForExport: boolean;
  progress: number;
}

export interface TimelineClip {
  id: string;
  shotId: string;
  sceneId: string;
  startTime: number;
  endTime: number;
  duration: number;
  videoPath: string | null;
  thumbnailPath: string | null;
  shotNumber: string;
  sceneNumber: string;
  state: ShotState;
}

export interface TimelineScene {
  id: string;
  sceneNumber: string;
  startTime: number;
  endTime: number;
  duration: number;
  clips: TimelineClip[];
}

export interface Timeline {
  projectId: string;
  totalDuration: number;
  scenes: TimelineScene[];
}

export interface ExportFormat {
  id: string;
  name: string;
  extension: string;
  codec: string;
  description: string;
}

export interface QualityPreset {
  id: string;
  name: string;
  resolution: string;
  bitrate: string;
  fps: number;
  description: string;
}

export interface ExportRequest {
  project_id: string;
  format: string;
  quality: string;
  include_watermark?: boolean;
  watermark_id?: string;
  output_filename?: string;
}

export interface ExportJobResult {
  success: boolean;
  exportId: string;
  outputPath: string | null;
  fileSize: number | null;
  duration: number | null;
  error: string | null;
}

export interface ExportHistoryItem {
  id: string;
  projectId: string;
  format: string;
  quality: string;
  outputPath: string;
  fileSize: number;
  duration: number;
  createdAt: string;
  status: string;
}

// ============ Audio/TTS Types ============

export interface Voice {
  id: string;
  name: string;
  provider: string;
  gender: string;
  language: string;
  preview_url: string | null;
  description: string | null;
}

export interface TTSProvider {
  id: string;
  name: string;
  available: boolean;
  configured: boolean;
  voices: Voice[];
}

export interface GenerateSpeechRequest {
  text: string;
  voice_id: string;
  provider: string;
  output_filename?: string;
}

export interface GenerateSpeechResult {
  success: boolean;
  audioPath: string | null;
  duration: number | null;
  error: string | null;
}

export interface DialogueLine {
  id: string;
  shotId: string;
  characterId: string;
  characterName: string;
  text: string;
  audioPath: string | null;
  audioDuration: number | null;
  voiceId: string | null;
  provider: string | null;
}

// ============ Text Overlay Types ============

export type TextOverlayType = 'title' | 'subtitle' | 'lower_third' | 'caption' | 'credit' | 'custom';
export type TextPosition = 'top_left' | 'top_center' | 'top_right' | 'center_left' | 'center' | 'center_right' | 'bottom_left' | 'bottom_center' | 'bottom_right' | 'custom';
export type TextAnimation = 'none' | 'fade_in' | 'fade_out' | 'slide_in_left' | 'slide_in_right' | 'slide_in_top' | 'slide_in_bottom' | 'typewriter' | 'scale_in';

export interface TextOverlayStyle {
  fontFamily: string;
  fontSize: number;
  fontWeight: string;
  color: string;
  backgroundColor: string | null;
  opacity: number;
  textShadow: string | null;
  padding: number;
  borderRadius: number;
}

export interface TextOverlay {
  id: string;
  shotId: string;
  overlayType: TextOverlayType;
  text: string;
  position: TextPosition;
  customX: number | null;
  customY: number | null;
  style: TextOverlayStyle;
  animationIn: TextAnimation;
  animationOut: TextAnimation;
  animationInDurationMs: number;
  animationOutDurationMs: number;
  startTimeMs: number;
  durationMs: number;
  isVisible: boolean;
  zIndex: number;
}

export interface TextOverlayPreset {
  id: string;
  name: string;
  overlayType: TextOverlayType;
  style: TextOverlayStyle;
  animationIn: TextAnimation;
  animationOut: TextAnimation;
}

export interface TextOverlayCreateRequest {
  shot_id: string;
  overlay_type: TextOverlayType;
  text: string;
  position?: TextPosition;
  custom_x?: number;
  custom_y?: number;
  style?: Partial<TextOverlayStyle>;
  animation_in?: TextAnimation;
  animation_out?: TextAnimation;
  animation_in_duration_ms?: number;
  animation_out_duration_ms?: number;
  start_time_ms?: number;
  duration_ms?: number;
}

// Export singleton instance
export const api = new APIClient();
