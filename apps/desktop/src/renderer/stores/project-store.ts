/**
 * Global project state store using Zustand.
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
import type { Project } from '@shared/types';

interface ProjectStoreState {
  // Current project
  currentProject: Project | null;

  // UI state
  sidebarCollapsed: boolean;
  selectedCharacterId: string | null;
  selectedSceneId: string | null;

  // Actions
  setCurrentProject: (project: Project | null) => void;
  updateProject: (updates: Partial<Project>) => void;
  toggleSidebar: () => void;
  selectCharacter: (id: string | null) => void;
  selectScene: (id: string | null) => void;
  reset: () => void;
}

const initialState = {
  currentProject: null,
  sidebarCollapsed: false,
  selectedCharacterId: null,
  selectedSceneId: null,
};

export const useProjectStore = create<ProjectStoreState>()(
  devtools(
    persist(
      immer((set) => ({
        ...initialState,

        setCurrentProject: (project) =>
          set((state) => {
            state.currentProject = project;
            state.selectedCharacterId = null;
            state.selectedSceneId = null;
          }),

        updateProject: (updates) =>
          set((state) => {
            if (state.currentProject) {
              Object.assign(state.currentProject, updates);
            }
          }),

        toggleSidebar: () =>
          set((state) => {
            state.sidebarCollapsed = !state.sidebarCollapsed;
          }),

        selectCharacter: (id) =>
          set((state) => {
            state.selectedCharacterId = id;
          }),

        selectScene: (id) =>
          set((state) => {
            state.selectedSceneId = id;
          }),

        reset: () => set(initialState),
      })),
      {
        name: 'scenemachine-project-store',
        partialize: (state) => ({
          sidebarCollapsed: state.sidebarCollapsed,
        }),
      }
    ),
    { name: 'ProjectStore' }
  )
);
