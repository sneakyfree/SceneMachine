/**
 * Home page - Project list and creation.
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Film, Trash2, FolderOpen, Keyboard, Search, X, RefreshCw } from 'lucide-react';
import { api } from '../api/client';
import { useProjectStore } from '../stores/project-store';
import { cn, formatDate } from '../lib/utils';
import { DataLoadError, FieldError } from '../components/error-display';
import { useToast } from '../components/toast';
import { announce } from '../lib/accessibility';
import { LoadingContainer, SkeletonProjectCard } from '../components/skeleton';
import { useTranslation } from '../i18n/use-translation';
import type { Project } from '@shared/types';

export function HomePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { addToast } = useToast();
  const { setCurrentProject } = useProjectStore();
  const { t } = useTranslation();
  const [isCreating, setIsCreating] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [showShortcuts, setShowShortcuts] = useState(false);
  const [projectToDelete, setProjectToDelete] = useState<Project | null>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const createInputRef = useRef<HTMLInputElement>(null);

  // Fetch projects
  const {
    data: projects,
    isLoading,
    error,
    refetch,
    isRefetching,
  } = useQuery({
    queryKey: ['projects'],
    queryFn: () => api.listProjects(),
  });

  // Filter projects by search
  const filteredProjects =
    projects?.filter((p) => p.name.toLowerCase().includes(searchQuery.toLowerCase())) || [];

  // Create project mutation
  const createMutation = useMutation({
    mutationFn: (name: string) => api.createProject({ name }),
    onSuccess: (project) => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      setCurrentProject(project);
      addToast({
        type: 'success',
        title: t('home.toastCreatedTitle', 'Project Created'),
        message: `"${project.name}" has been created successfully.`,
      });
      announce(`Project ${project.name} created`);
      navigate(`/project/${project.id}`);
    },
    onError: (error) => {
      addToast({
        type: 'error',
        title: t('home.toastCreateFailedTitle', 'Creation Failed'),
        message: t('home.toastCreateFailedMessage', 'Failed to create project. Please try again.'),
      });
      announce(t('home.announceCreateFailed', 'Failed to create project'));
    },
  });

  // Delete project mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteProject(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      addToast({
        type: 'success',
        title: t('home.toastDeletedTitle', 'Project Deleted'),
        message: t('home.toastDeletedMessage', 'Project has been deleted.'),
      });
      announce(t('home.announceDeleted', 'Project deleted'));
      setProjectToDelete(null);
    },
    onError: () => {
      addToast({
        type: 'error',
        title: t('home.toastDeleteFailedTitle', 'Delete Failed'),
        message: t('home.toastDeleteFailedMessage', 'Failed to delete project. Please try again.'),
      });
      announce(t('home.announceDeleteFailed', 'Failed to delete project'));
    },
  });

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      const isInputFocused = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA';

      // ? - Show shortcuts
      if (e.key === '?' && !isInputFocused) {
        e.preventDefault();
        setShowShortcuts(true);
        announce(t('home.announceShortcutsOpened', 'Keyboard shortcuts opened'));
      }
      // Escape - Close dialogs
      if (e.key === 'Escape') {
        if (showShortcuts) {
          setShowShortcuts(false);
          announce(t('home.announceShortcutsClosed', 'Shortcuts closed'));
        } else if (projectToDelete) {
          setProjectToDelete(null);
          announce(t('home.announceDeleteCancelled', 'Delete cancelled'));
        } else if (isCreating) {
          setIsCreating(false);
          setNewProjectName('');
          announce(t('home.announceCreateCancelled', 'Create cancelled'));
        }
      }
      // N - New project
      if (e.key === 'n' && !isInputFocused && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        setIsCreating(true);
        setTimeout(() => createInputRef.current?.focus(), 100);
        announce(t('home.announceCreateNew', 'Create new project'));
      }
      // / - Focus search
      if (e.key === '/' && !isInputFocused) {
        e.preventDefault();
        searchInputRef.current?.focus();
        announce(t('home.announceSearchFocused', 'Search focused'));
      }
      // R - Refresh
      if (e.key === 'r' && !isInputFocused && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        refetch();
        announce(t('home.announceRefreshing', 'Refreshing projects'));
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [showShortcuts, isCreating, projectToDelete, refetch]);

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
    announce(`Opening ${project.name}`);
    navigate(`/project/${project.id}`);
  };

  const handleDeleteProject = async (e: React.MouseEvent, project: Project) => {
    e.stopPropagation();
    setProjectToDelete(project);
  };

  const confirmDelete = async () => {
    if (projectToDelete) {
      await deleteMutation.mutateAsync(projectToDelete.id);
    }
  };

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">{t('home.heading', 'Projects')}</h1>
          <p className="text-surface-400 mt-1">
            {t('home.subheading', 'Create and manage your screenplay-to-movie projects')}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowShortcuts(true)}
            className="p-2 text-surface-400 hover:text-surface-200 hover:bg-surface-700 rounded-lg"
            title={t('home.shortcutsButtonTitle', 'Keyboard shortcuts (?)')}
            aria-label={t('home.shortcutsButtonAria', 'Show keyboard shortcuts')}
          >
            <Keyboard className="w-5 h-5" />
          </button>
          <button
            onClick={() => refetch()}
            disabled={isRefetching}
            className="p-2 text-surface-400 hover:text-surface-200 hover:bg-surface-700 rounded-lg"
            title={t('home.refreshButtonTitle', 'Refresh (R)')}
            aria-label={t('home.refreshButtonAria', 'Refresh projects')}
          >
            <RefreshCw className={cn('w-5 h-5', isRefetching && 'animate-spin')} />
          </button>
          <button
            onClick={() => setIsCreating(true)}
            className="btn-primary flex items-center gap-2"
            title={t('home.newProjectButtonTitle', 'New Project (N)')}
          >
            <Plus className="w-4 h-4" />
            {t('home.newProject', 'New Project')}
          </button>
        </div>
      </div>

      {/* Search bar */}
      {projects && projects.length > 0 && (
        <div className="relative mb-6">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-surface-400" />
          <input
            ref={searchInputRef}
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t('home.searchPlaceholder', 'Search projects... (press / to focus)')}
            className="w-full pl-10 pr-10 py-2 bg-surface-800 border border-surface-700 rounded-lg focus:border-brand-500 focus:outline-none"
            aria-label={t('home.searchAria', 'Search projects')}
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-surface-400 hover:text-surface-200"
              aria-label={t('home.clearSearchAria', 'Clear search')}
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>
      )}

      {/* Create project dialog */}
      {isCreating && (
        <div
          className="card mb-8 animate-fade-in"
          role="dialog"
          aria-labelledby="create-project-title"
        >
          <form onSubmit={handleCreateProject}>
            <h3 id="create-project-title" className="text-lg font-medium mb-4">
              {t('home.createDialogTitle', 'Create New Project')}
            </h3>
            <input
              ref={createInputRef}
              type="text"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              placeholder={t('home.projectNamePlaceholder', 'Project name...')}
              className="input mb-4"
              autoFocus
              aria-label={t('home.projectNameAria', 'Project name')}
            />
            <div className="flex gap-3">
              <button
                type="submit"
                className="btn-primary"
                disabled={!newProjectName.trim() || createMutation.isPending}
              >
                {createMutation.isPending
                  ? t('home.creating', 'Creating...')
                  : t('home.createProject', 'Create Project')}
              </button>
              <button
                type="button"
                onClick={() => {
                  setIsCreating(false);
                  setNewProjectName('');
                  announce(t('home.announceCreateCancelled', 'Create cancelled'));
                }}
                className="btn-secondary"
              >
                {t('home.cancel', 'Cancel')}
              </button>
            </div>
            <p className="mt-3 text-xs text-surface-500">
              {t('home.pressEscapePrefix', 'Press')}{' '}
              <kbd className="px-1 py-0.5 bg-surface-700 rounded text-xs">Escape</kbd>{' '}
              {t('home.pressEscapeSuffix', 'to cancel')}
            </p>
          </form>
        </div>
      )}

      {/* Loading state with skeletons */}
      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <SkeletonProjectCard key={i} />
          ))}
        </div>
      )}

      {/* Error state */}
      {error && (
        <DataLoadError
          entity="projects"
          error={error}
          onRetry={() => queryClient.invalidateQueries({ queryKey: ['projects'] })}
        />
      )}

      {/* Empty state */}
      {!isLoading && !error && projects?.length === 0 && (
        <div className="text-center py-16">
          <FolderOpen className="w-16 h-16 mx-auto text-surface-600 mb-4" />
          <h3 className="text-lg font-medium mb-2">{t('home.emptyTitle', 'No projects yet')}</h3>
          <p className="text-surface-400 mb-6">
            {t(
              'home.emptyDescription',
              'Create your first project to get started with screenplay-to-movie generation.'
            )}
          </p>
          <button onClick={() => setIsCreating(true)} className="btn-primary">
            <Plus className="w-4 h-4 mr-2" />
            {t('home.createProject', 'Create Project')}
          </button>
        </div>
      )}

      {/* Project grid */}
      {!isLoading && !error && projects && projects.length > 0 && (
        <>
          {/* Search results info */}
          {searchQuery && (
            <p className="text-sm text-surface-400 mb-4">
              {filteredProjects.length} project{filteredProjects.length !== 1 ? 's' : ''}{' '}
              {t('home.found', 'found')}
              {filteredProjects.length === 0 && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="ml-2 text-brand-400 hover:text-brand-300"
                >
                  {t('home.clearSearch', 'Clear search')}
                </button>
              )}
            </p>
          )}

          <div
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
            role="list"
            aria-label="Projects"
          >
            {filteredProjects.map((project) => (
              <div
                key={project.id}
                onClick={() => handleOpenProject(project)}
                className={cn(
                  'card cursor-pointer transition-all hover:border-brand-500/50',
                  'hover:shadow-lg hover:shadow-brand-500/10'
                )}
                role="listitem"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    handleOpenProject(project);
                  }
                }}
                aria-label={`${project.name}, ${project.characterCount || 0} characters, ${project.sceneCount || 0} scenes, ${project.state}`}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-brand-500/20 flex items-center justify-center">
                      <Film className="w-5 h-5 text-brand-400" />
                    </div>
                    <div>
                      <h3 className="font-medium">{project.name}</h3>
                      <p className="text-sm text-surface-400">{formatDate(project.updatedAt)}</p>
                    </div>
                  </div>
                  <button
                    onClick={(e) => handleDeleteProject(e, project)}
                    className="p-2 text-surface-500 hover:text-red-400 transition-colors"
                    disabled={deleteMutation.isPending}
                    aria-label={`Delete ${project.name}`}
                    title={t('home.deleteProjectTitle', 'Delete project')}
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>

                {/* Project stats */}
                <div className="flex gap-4 text-sm text-surface-400">
                  <span>
                    {project.characterCount || 0} {t('home.characters', 'characters')}
                  </span>
                  <span>
                    {project.sceneCount || 0} {t('home.scenes', 'scenes')}
                  </span>
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
                    {t(`home.state.${project.state}`, project.state.replace(/_/g, ' '))}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Delete confirmation modal */}
      {projectToDelete && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
          onClick={() => setProjectToDelete(null)}
          role="dialog"
          aria-modal="true"
          aria-labelledby="delete-title"
        >
          <div
            className="bg-surface-900 rounded-lg shadow-xl max-w-md w-full mx-4 overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6">
              <h2 id="delete-title" className="text-lg font-medium mb-2">
                {t('home.deleteModalTitle', 'Delete Project?')}
              </h2>
              <p className="text-surface-400 mb-6">
                {t('home.deleteConfirmPrefix', 'Are you sure you want to delete')}{' '}
                <strong>"{projectToDelete.name}"</strong>?{' '}
                {t('home.deleteConfirmSuffix', 'This action cannot be undone.')}
              </p>
              <div className="flex gap-3 justify-end">
                <button
                  onClick={() => setProjectToDelete(null)}
                  className="px-4 py-2 bg-surface-700 hover:bg-surface-600 rounded-lg"
                >
                  {t('home.cancel', 'Cancel')}
                </button>
                <button
                  onClick={confirmDelete}
                  disabled={deleteMutation.isPending}
                  className="px-4 py-2 bg-red-500 hover:bg-red-600 rounded-lg flex items-center gap-2"
                >
                  {deleteMutation.isPending ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      {t('home.deleting', 'Deleting...')}
                    </>
                  ) : (
                    <>
                      <Trash2 className="w-4 h-4" />
                      {t('home.delete', 'Delete')}
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Keyboard shortcuts modal */}
      {showShortcuts && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
          onClick={() => setShowShortcuts(false)}
          role="dialog"
          aria-modal="true"
          aria-labelledby="shortcuts-title"
        >
          <div
            className="bg-surface-900 rounded-lg shadow-xl max-w-md w-full mx-4 overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-4 border-b border-surface-700 flex items-center justify-between">
              <h2 id="shortcuts-title" className="text-lg font-medium flex items-center gap-2">
                <Keyboard className="w-5 h-5 text-brand-400" />
                {t('home.shortcutsTitle', 'Keyboard Shortcuts')}
              </h2>
              <button
                onClick={() => setShowShortcuts(false)}
                className="p-1 hover:bg-surface-700 rounded"
                aria-label={t('home.closeShortcutsAria', 'Close shortcuts')}
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-4 space-y-3">
              <div className="flex items-center justify-between py-2 border-b border-surface-800">
                <span className="text-surface-300">{t('home.shortcutNewProject', 'New project')}</span>
                <kbd className="px-2 py-1 bg-surface-800 rounded text-sm font-mono">N</kbd>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-surface-800">
                <span className="text-surface-300">{t('home.shortcutSearch', 'Search projects')}</span>
                <kbd className="px-2 py-1 bg-surface-800 rounded text-sm font-mono">/</kbd>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-surface-800">
                <span className="text-surface-300">{t('home.shortcutRefresh', 'Refresh list')}</span>
                <kbd className="px-2 py-1 bg-surface-800 rounded text-sm font-mono">R</kbd>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-surface-800">
                <span className="text-surface-300">{t('home.shortcutShow', 'Show shortcuts')}</span>
                <kbd className="px-2 py-1 bg-surface-800 rounded text-sm font-mono">?</kbd>
              </div>
              <div className="flex items-center justify-between py-2">
                <span className="text-surface-300">{t('home.shortcutClose', 'Close/Cancel')}</span>
                <kbd className="px-2 py-1 bg-surface-800 rounded text-sm font-mono">Escape</kbd>
              </div>
            </div>
            <div className="p-4 bg-surface-800/50 text-center">
              <p className="text-sm text-surface-400">
                {t('home.pressQuestionPrefix', 'Press')}{' '}
                <kbd className="px-1.5 py-0.5 bg-surface-700 rounded text-xs font-mono">?</kbd>{' '}
                {t('home.pressQuestionSuffix', 'anytime to see shortcuts')}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
