/**
 * Collaboration Store
 *
 * Manages real-time collaboration state including collaborator presence,
 * cursor positions, and edit locks.
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

// Predefined cursor colors for collaborators
export const CURSOR_COLORS = [
  '#FF6B6B', // Red
  '#4ECDC4', // Teal
  '#FFE66D', // Yellow
  '#95E1D3', // Mint
  '#F38181', // Coral
  '#AA96DA', // Purple
  '#FCBAD3', // Pink
  '#A8D8EA', // Light Blue
] as const;

export interface Collaborator {
  id: string;
  name: string;
  avatarUrl?: string;
  color: string;
  isOnline: boolean;
  lastSeen: Date;
  currentElement?: string; // ID of element they're currently editing
}

export interface CursorPosition {
  x: number;
  y: number;
  element?: string; // ID of element the cursor is over
  timestamp: number;
}

export interface EditLock {
  elementId: string;
  userId: string;
  userName: string;
  lockedAt: Date;
  expiresAt: Date;
}

interface CollaborationState {
  // Connection state
  isConnected: boolean;
  projectId: string | null;
  currentUserId: string | null;
  currentUserName: string | null;

  // Collaborators
  collaborators: Record<string, Collaborator>;
  cursors: Record<string, CursorPosition>;

  // Edit locks
  locks: Record<string, EditLock>;

  // Local cursor position (for throttling)
  localCursorPosition: CursorPosition | null;

  // Actions
  connect: (projectId: string, userId: string, userName: string) => void;
  disconnect: () => void;

  // Collaborator actions
  addCollaborator: (collaborator: Collaborator) => void;
  removeCollaborator: (userId: string) => void;
  updateCollaboratorStatus: (userId: string, isOnline: boolean) => void;

  // Cursor actions
  updateCursor: (userId: string, position: CursorPosition) => void;
  removeCursor: (userId: string) => void;
  setLocalCursor: (x: number, y: number, element?: string) => void;

  // Lock actions
  requestLock: (elementId: string) => Promise<boolean>;
  releaseLock: (elementId: string) => void;
  setLock: (lock: EditLock) => void;
  removeLock: (elementId: string) => void;
  isElementLocked: (elementId: string) => boolean;
  getElementLock: (elementId: string) => EditLock | null;

  // Helpers
  getAssignedColor: (userId: string) => string;
}

export const useCollaborationStore = create<CollaborationState>()(
  devtools(
    (set, get) => ({
      // Initial state
      isConnected: false,
      projectId: null,
      currentUserId: null,
      currentUserName: null,
      collaborators: {},
      cursors: {},
      locks: {},
      localCursorPosition: null,

      // Connection actions
      connect: (projectId, userId, userName) => {
        set({
          isConnected: true,
          projectId,
          currentUserId: userId,
          currentUserName: userName,
        });

        // In a real implementation, this would connect to WebSocket
        console.log(`[Collaboration] Connected to project ${projectId} as ${userName}`);
      },

      disconnect: () => {
        set({
          isConnected: false,
          projectId: null,
          currentUserId: null,
          currentUserName: null,
          collaborators: {},
          cursors: {},
          locks: {},
          localCursorPosition: null,
        });

        console.log('[Collaboration] Disconnected');
      },

      // Collaborator actions
      addCollaborator: (collaborator) => {
        set((state) => ({
          collaborators: {
            ...state.collaborators,
            [collaborator.id]: collaborator,
          },
        }));
      },

      removeCollaborator: (userId) => {
        set((state) => {
          const { [userId]: removed, ...rest } = state.collaborators;
          const { [userId]: removedCursor, ...restCursors } = state.cursors;
          return {
            collaborators: rest,
            cursors: restCursors,
          };
        });
      },

      updateCollaboratorStatus: (userId, isOnline) => {
        set((state) => {
          const collaborator = state.collaborators[userId];
          if (!collaborator) return state;

          return {
            collaborators: {
              ...state.collaborators,
              [userId]: {
                ...collaborator,
                isOnline,
                lastSeen: new Date(),
              },
            },
          };
        });
      },

      // Cursor actions
      updateCursor: (userId, position) => {
        set((state) => ({
          cursors: {
            ...state.cursors,
            [userId]: position,
          },
        }));
      },

      removeCursor: (userId) => {
        set((state) => {
          const { [userId]: removed, ...rest } = state.cursors;
          return { cursors: rest };
        });
      },

      setLocalCursor: (x, y, element) => {
        const position: CursorPosition = {
          x,
          y,
          element,
          timestamp: Date.now(),
        };

        set({ localCursorPosition: position });

        // In a real implementation, this would emit the cursor position via WebSocket
        // Throttled to 20 updates per second (50ms minimum between updates)
      },

      // Lock actions
      requestLock: async (elementId) => {
        const state = get();
        const existingLock = state.locks[elementId];

        // If already locked by another user, deny
        if (existingLock && existingLock.userId !== state.currentUserId) {
          return false;
        }

        // If already locked by current user, extend
        if (existingLock && existingLock.userId === state.currentUserId) {
          const extendedLock: EditLock = {
            ...existingLock,
            expiresAt: new Date(Date.now() + 30000), // Extend by 30 seconds
          };
          set((s) => ({
            locks: {
              ...s.locks,
              [elementId]: extendedLock,
            },
          }));
          return true;
        }

        // Request new lock
        // In a real implementation, this would request the lock via WebSocket
        const newLock: EditLock = {
          elementId,
          userId: state.currentUserId!,
          userName: state.currentUserName!,
          lockedAt: new Date(),
          expiresAt: new Date(Date.now() + 30000), // 30 second lock
        };

        set((s) => ({
          locks: {
            ...s.locks,
            [elementId]: newLock,
          },
        }));

        return true;
      },

      releaseLock: (elementId) => {
        const state = get();
        const lock = state.locks[elementId];

        // Only release if we own the lock
        if (lock && lock.userId === state.currentUserId) {
          set((s) => {
            const { [elementId]: removed, ...rest } = s.locks;
            return { locks: rest };
          });

          // In a real implementation, this would notify via WebSocket
        }
      },

      setLock: (lock) => {
        set((state) => ({
          locks: {
            ...state.locks,
            [lock.elementId]: lock,
          },
        }));
      },

      removeLock: (elementId) => {
        set((state) => {
          const { [elementId]: removed, ...rest } = state.locks;
          return { locks: rest };
        });
      },

      isElementLocked: (elementId) => {
        const state = get();
        const lock = state.locks[elementId];

        if (!lock) return false;

        // Check if lock is expired
        if (new Date() > lock.expiresAt) {
          // Auto-remove expired lock
          get().removeLock(elementId);
          return false;
        }

        // If locked by current user, it's not "locked" from their perspective
        if (lock.userId === state.currentUserId) return false;

        return true;
      },

      getElementLock: (elementId) => {
        const state = get();
        const lock = state.locks[elementId];

        if (!lock) return null;

        // Check if lock is expired
        if (new Date() > lock.expiresAt) {
          get().removeLock(elementId);
          return null;
        }

        return lock;
      },

      // Helpers
      getAssignedColor: (userId) => {
        const state = get();
        const collaboratorIds = Object.keys(state.collaborators);
        const index = collaboratorIds.indexOf(userId);
        if (index === -1) {
          // Assign next available color
          return CURSOR_COLORS[collaboratorIds.length % CURSOR_COLORS.length];
        }
        return CURSOR_COLORS[index % CURSOR_COLORS.length];
      },
    }),
    {
      name: 'collaboration-store',
    }
  )
);

// Selectors
export const selectCollaborators = (state: CollaborationState) =>
  Object.values(state.collaborators).filter((c) => c.isOnline);

export const selectOnlineCount = (state: CollaborationState) =>
  Object.values(state.collaborators).filter((c) => c.isOnline).length;

export const selectCursors = (state: CollaborationState) => state.cursors;

export const selectLocks = (state: CollaborationState) => state.locks;

export default useCollaborationStore;
