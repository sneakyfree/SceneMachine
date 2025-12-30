/**
 * Project store unit tests.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { act } from '@testing-library/react';
import { useProjectStore } from '../../stores/project-store';
import type { Project } from '@shared/types';

const mockProject: Project = {
  id: 'project-1',
  name: 'Test Project',
  description: 'A test project',
  state: 'draft',
  settings: {},
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
};

describe('ProjectStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useProjectStore.setState({
      currentProject: null,
      sidebarCollapsed: false,
      selectedCharacterId: null,
      selectedSceneId: null,
    });
  });

  describe('setCurrentProject', () => {
    it('should set the current project', () => {
      const { setCurrentProject } = useProjectStore.getState();

      act(() => {
        setCurrentProject(mockProject);
      });

      const state = useProjectStore.getState();
      expect(state.currentProject).toEqual(mockProject);
    });

    it('should clear selections when setting a new project', () => {
      useProjectStore.setState({
        selectedCharacterId: 'char-1',
        selectedSceneId: 'scene-1',
      });

      const { setCurrentProject } = useProjectStore.getState();

      act(() => {
        setCurrentProject(mockProject);
      });

      const state = useProjectStore.getState();
      expect(state.selectedCharacterId).toBeNull();
      expect(state.selectedSceneId).toBeNull();
    });

    it('should allow clearing the current project', () => {
      useProjectStore.setState({ currentProject: mockProject });

      const { setCurrentProject } = useProjectStore.getState();

      act(() => {
        setCurrentProject(null);
      });

      const state = useProjectStore.getState();
      expect(state.currentProject).toBeNull();
    });
  });

  describe('updateProject', () => {
    it('should update project properties', () => {
      useProjectStore.setState({ currentProject: mockProject });

      const { updateProject } = useProjectStore.getState();

      act(() => {
        updateProject({ name: 'Updated Name', description: 'Updated description' });
      });

      const state = useProjectStore.getState();
      expect(state.currentProject?.name).toBe('Updated Name');
      expect(state.currentProject?.description).toBe('Updated description');
      // Other properties should remain unchanged
      expect(state.currentProject?.id).toBe('project-1');
    });

    it('should do nothing if no current project', () => {
      const { updateProject } = useProjectStore.getState();

      // Should not throw
      act(() => {
        updateProject({ name: 'New Name' });
      });

      const state = useProjectStore.getState();
      expect(state.currentProject).toBeNull();
    });
  });

  describe('toggleSidebar', () => {
    it('should toggle sidebar collapsed state', () => {
      expect(useProjectStore.getState().sidebarCollapsed).toBe(false);

      const { toggleSidebar } = useProjectStore.getState();

      act(() => {
        toggleSidebar();
      });

      expect(useProjectStore.getState().sidebarCollapsed).toBe(true);

      act(() => {
        toggleSidebar();
      });

      expect(useProjectStore.getState().sidebarCollapsed).toBe(false);
    });
  });

  describe('selectCharacter', () => {
    it('should set selected character ID', () => {
      const { selectCharacter } = useProjectStore.getState();

      act(() => {
        selectCharacter('char-123');
      });

      expect(useProjectStore.getState().selectedCharacterId).toBe('char-123');
    });

    it('should allow clearing selection', () => {
      useProjectStore.setState({ selectedCharacterId: 'char-123' });

      const { selectCharacter } = useProjectStore.getState();

      act(() => {
        selectCharacter(null);
      });

      expect(useProjectStore.getState().selectedCharacterId).toBeNull();
    });
  });

  describe('selectScene', () => {
    it('should set selected scene ID', () => {
      const { selectScene } = useProjectStore.getState();

      act(() => {
        selectScene('scene-456');
      });

      expect(useProjectStore.getState().selectedSceneId).toBe('scene-456');
    });

    it('should allow clearing selection', () => {
      useProjectStore.setState({ selectedSceneId: 'scene-456' });

      const { selectScene } = useProjectStore.getState();

      act(() => {
        selectScene(null);
      });

      expect(useProjectStore.getState().selectedSceneId).toBeNull();
    });
  });

  describe('reset', () => {
    it('should reset store to initial state', () => {
      useProjectStore.setState({
        currentProject: mockProject,
        sidebarCollapsed: true,
        selectedCharacterId: 'char-1',
        selectedSceneId: 'scene-1',
      });

      const { reset } = useProjectStore.getState();

      act(() => {
        reset();
      });

      const state = useProjectStore.getState();
      expect(state.currentProject).toBeNull();
      expect(state.sidebarCollapsed).toBe(false);
      expect(state.selectedCharacterId).toBeNull();
      expect(state.selectedSceneId).toBeNull();
    });
  });
});
