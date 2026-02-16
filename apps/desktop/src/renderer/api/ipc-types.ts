/**
 * Type-safe IPC method names.
 *
 * This union type contains all registered IPC handler method names
 * from the Python backend (scenemachine/ipc/handlers.py).
 *
 * Using this type ensures the TypeScript compiler catches typos
 * in IPC method names at build time.
 */

export type IPCMethod =
    // Health & System
    | 'ping'
    | 'version'
    // Projects
    | 'projects.list'
    | 'projects.get'
    | 'projects.create'
    | 'projects.update'
    | 'projects.delete'
    | 'projects.duplicate'
    // Screenplay
    | 'screenplay.upload'
    | 'screenplay.parse'
    | 'screenplay.get'
    | 'screenplay.getByProject'
    | 'screenplay.delete'
    // Movie Plan
    | 'moviePlan.generate'
    | 'moviePlan.get'
    | 'moviePlan.approve'
    // Characters
    | 'characters.list'
    | 'characters.get'
    | 'characters.update'
    | 'characters.generateDescription'
    | 'characters.uploadReference'
    | 'characters.deleteReference'
    | 'characters.generateVariations'
    // Scenes
    | 'scenes.list'
    | 'scenes.get'
    | 'scenes.update'
    | 'scenes.listShots'
    // Shots
    | 'shots.get'
    | 'shots.update'
    | 'shots.updatePrompt'
    | 'shots.regeneratePrompt'
    | 'shots.generateImage'
    | 'shots.generateVideo'
    | 'shots.estimateCost'
    | 'shots.batchEstimateCost'
    // Generation
    | 'generation.getJob'
    | 'generation.cancelJob'
    | 'generation.retryJob'
    | 'generation.getQueueStatus'
    | 'generation.getProviders'
    | 'generation.getProviderStatus'
    | 'generation.getCostEstimate'
    // Assembly
    | 'assembly.create'
    | 'assembly.getStatus'
    | 'assembly.getPreview'
    // Export
    | 'export.start'
    | 'export.getStatus'
    | 'export.getHistory'
    // Settings
    | 'settings.get'
    | 'settings.update'
    | 'settings.getProviderConfig'
    | 'settings.updateProviderConfig'
    // Analytics
    | 'analytics.getProjectStats'
    | 'analytics.getGenerationStats'
    | 'analytics.getCostBreakdown'
    // Sharing
    | 'sharing.create'
    | 'sharing.get'
    | 'sharing.revoke'
    | 'sharing.list'
    // Archive
    | 'archive.create'
    | 'archive.restore'
    | 'archive.list'
    // Audio
    | 'audio.generateTTS'
    | 'audio.uploadTrack'
    | 'audio.listTracks'
    | 'audio.deleteTrack'
    // Watermarks
    | 'watermarks.upload'
    | 'watermarks.list'
    | 'watermarks.delete'
    // Copilot
    | 'copilot.chat'
    | 'copilot.getHistory'
    | 'copilot.clearHistory'
    | 'copilot.getSuggestions'
    | 'copilot.generateShotBreakdown'
    // Performers (ActForge)
    | 'performers.search'
    | 'performers.featured'
    | 'performers.leaderboard'
    | 'performers.get'
    | 'performers.getACI'
    | 'performers.seed'
    // Bookings (ActForge)
    | 'bookings.blink'
    | 'bookings.deep'
    | 'bookings.epic'
    | 'bookings.get'
    | 'bookings.listByProject'
    | 'bookings.accept'
    | 'bookings.deliver'
    | 'bookings.approve'
    | 'bookings.dispute'
    | 'bookings.rate'
    // Snapshots
    | 'snapshots.compare';

/**
 * Type-safe backendRequest wrapper.
 *
 * Usage:
 *   import { IPCMethod } from './ipc-types';
 *   const result = await window.electronAPI.backendRequest<ProjectList>('projects.list');
 */
export interface TypedElectronAPI {
    backendRequest: <T>(method: IPCMethod, params?: Record<string, unknown>) => Promise<T>;
}
