/**
 * Home page - Project list and creation.
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Film, Trash2, FolderOpen } from 'lucide-react';
import { api } from '../api/client';
import { useProjectStore } from '../stores/project-store';
import { cn, formatDate } from '../lib/utils';
import type { Project } from '@shared/types';

export function HomePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { setCurrentProject } = useProjectStore();
  const [isCreating, setIsCreating] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');

  // Fetch projects
  const { data: projects, isLoading, error } = useQuery({
    queryKey: ['projects'],
    queryFn: () => api.listProjects(),
  });

  // Create project mutation
  const createMutation = useMutation({
    mutationFn: (name: string) => api.createProject({ name }),
    onSuccess: (project) => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      setCurrentProject(project);
      navigate(`/project/${project.id}`);
    },
  });

  // Delete project mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteProject(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newProjectName.trim()) {
      await createMutation.mutateAsync(newProjectName.trim());
      setNewProjectName('');
      setIsCreating(false);
    }
  };

  const handleOpenProject = (project: Project) => {
    setCurrentProject(project);
    navigate(`/project/${project.id}`);
  };

  const handleDeleteProject = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (confirm('Are you sure you want to delete this project? This cannot be undone.')) {
      await deleteMutation.mutateAsync(id);
    }
  };

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold">Projects</h1>
          <p className="text-surface-400 mt-1">
            Create and manage your screenplay-to-movie projects
          </p>
        </div>
        <button
          onClick={() => setIsCreating(true)}
          className="btn-primary flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          New Project
        </button>
      </div>

      {/* Create project dialog */}
      {isCreating && (
        <div className="card mb-8 animate-fade-in">
          <form onSubmit={handleCreateProject}>
            <h3 className="text-lg font-medium mb-4">Create New Project</h3>
            <input
              type="text"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              placeholder="Project name..."
              className="input mb-4"
              autoFocus
            />
            <div className="flex gap-3">
              <button
                type="submit"
                className="btn-primary"
                disabled={!newProjectName.trim() || createMutation.isPending}
              >
                {createMutation.isPending ? 'Creating...' : 'Create Project'}
              </button>
              <button
                type="button"
                onClick={() => {
                  setIsCreating(false);
                  setNewProjectName('');
                }}
                className="btn-secondary"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Loading state */}
      {isLoading && (
        <div className="text-center py-12 text-surface-400">Loading projects...</div>
      )}

      {/* Error state */}
      {error && (
        <div className="card border-red-500/50 bg-red-500/10 text-red-400">
          Failed to load projects. Please check that the backend is running.
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !error && projects?.length === 0 && (
        <div className="text-center py-16">
          <FolderOpen className="w-16 h-16 mx-auto text-surface-600 mb-4" />
          <h3 className="text-lg font-medium mb-2">No projects yet</h3>
          <p className="text-surface-400 mb-6">
            Create your first project to get started with screenplay-to-movie generation.
          </p>
          <button onClick={() => setIsCreating(true)} className="btn-primary">
            <Plus className="w-4 h-4 mr-2" />
            Create Project
          </button>
        </div>
      )}

      {/* Project grid */}
      {!isLoading && !error && projects && projects.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((project) => (
            <div
              key={project.id}
              onClick={() => handleOpenProject(project)}
              className={cn(
                'card cursor-pointer transition-all hover:border-brand-500/50',
                'hover:shadow-lg hover:shadow-brand-500/10'
              )}
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-brand-500/20 flex items-center justify-center">
                    <Film className="w-5 h-5 text-brand-400" />
                  </div>
                  <div>
                    <h3 className="font-medium">{project.name}</h3>
                    <p className="text-sm text-surface-400">
                      {formatDate(project.updatedAt)}
                    </p>
                  </div>
                </div>
                <button
                  onClick={(e) => handleDeleteProject(e, project.id)}
                  className="p-2 text-surface-500 hover:text-red-400 transition-colors"
                  disabled={deleteMutation.isPending}
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>

              {/* Project stats */}
              <div className="flex gap-4 text-sm text-surface-400">
                <span>{project.characterCount || 0} characters</span>
                <span>{project.sceneCount || 0} scenes</span>
              </div>

              {/* Status badge */}
              <div className="mt-3">
                <span
                  className={cn(
                    'text-xs px-2 py-1 rounded-full',
                    project.state === 'empty'
                      ? 'bg-surface-800 text-surface-400'
                      : project.state === 'complete'
                        ? 'bg-green-500/20 text-green-400'
                        : 'bg-brand-500/20 text-brand-400'
                  )}
                >
                  {project.state.replace(/_/g, ' ')}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
