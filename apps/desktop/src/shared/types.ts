/**
 * Shared types between main and renderer processes.
 */

// Project state enum matching backend
export enum ProjectState {
  EMPTY = 'empty',
  SCREENPLAY_UPLOADED = 'screenplay_uploaded',
  SCREENPLAY_PARSED = 'screenplay_parsed',
  PLAN_GENERATED = 'plan_generated',
  PLAN_APPROVED = 'plan_approved',
  CHARACTERS_IN_PROGRESS = 'characters_in_progress',
  CHARACTERS_LOCKED = 'characters_locked',
  SCENES_PLANNING = 'scenes_planning',
  SCENES_APPROVED = 'scenes_approved',
  GENERATING = 'generating',
  GENERATION_COMPLETE = 'generation_complete',
  ASSEMBLY_IN_PROGRESS = 'assembly_in_progress',
  COMPLETE = 'complete',
  EXPORTED = 'exported',
}

// Character lock state
export enum CharacterLockState {
  UNDEFINED = 'undefined',
  DRAFT = 'draft',
  REFERENCE_UPLOADED = 'reference_uploaded',
  GENERATING = 'generating',
  REVIEW = 'review',
  LOCKED = 'locked',
}

// Scene state
export enum SceneState {
  PARSED = 'parsed',
  PLANNED = 'planned',
  PLAN_APPROVED = 'plan_approved',
  GENERATING = 'generating',
  GENERATED = 'generated',
  REVIEW = 'review',
  APPROVED = 'approved',
  LOCKED = 'locked',
}

// Shot state
export enum ShotState {
  PLANNED = 'planned',
  QUEUED = 'queued',
  GENERATING = 'generating',
  GENERATED = 'generated',
  FAILED = 'failed',
  REVIEW = 'review',
  APPROVED = 'approved',
  REJECTED = 'rejected',
  REGENERATING = 'regenerating',
}

// API response types
export interface Project {
  id: string;
  name: string;
  description?: string;
  state: ProjectState;
  settings: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface Character {
  id: string;
  projectId: string;
  name: string;
  screenplayName: string;
  description?: string;
  ageRangeMin?: number;
  ageRangeMax?: number;
  gender: 'male' | 'female' | 'non_binary' | 'unspecified';
  lockState: CharacterLockState;
  isLocked: boolean;
  sceneCount: number;
  dialogueCount: number;
  isProtagonist: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface Scene {
  id: string;
  projectId: string;
  sceneNumber: string;
  sequenceNumber: number;
  sceneType: 'interior' | 'exterior' | 'interior_exterior';
  location: string;
  timeOfDay: string;
  rawContent: string;
  state: SceneState;
  estimatedDurationSeconds?: number;
  createdAt: string;
  updatedAt: string;
}

export interface Shot {
  id: string;
  sceneId: string;
  shotNumber: string;
  sequenceNumber: number;
  shotType: string;
  cameraMovement: string;
  description: string;
  dialogue?: string;
  action?: string;
  durationSeconds: number;
  state: ShotState;
  outputVideoPath?: string;
  createdAt: string;
  updatedAt: string;
}

// IPC types
export interface ElectronAPI {
  backendRequest: <T>(method: string, params?: Record<string, unknown>) => Promise<T>;
  openFile: (options: OpenDialogOptions) => Promise<OpenDialogResult>;
  saveFile: (options: SaveDialogOptions) => Promise<SaveDialogResult>;
  platform: string;
  versions: {
    node: string;
    electron: string;
    chrome: string;
  };
}

export interface OpenDialogOptions {
  title?: string;
  defaultPath?: string;
  filters?: FileFilter[];
  properties?: Array<'openFile' | 'openDirectory' | 'multiSelections'>;
}

export interface OpenDialogResult {
  canceled: boolean;
  filePaths: string[];
}

export interface SaveDialogOptions {
  title?: string;
  defaultPath?: string;
  filters?: FileFilter[];
}

export interface SaveDialogResult {
  canceled: boolean;
  filePath?: string;
}

export interface FileFilter {
  name: string;
  extensions: string[];
}

// Declare global window type
declare global {
  interface Window {
    electronAPI: ElectronAPI;
  }
}
