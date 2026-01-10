/**
 * Project detail page.
 */

import { useEffect, useCallback, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query';
import {
  Film,
  FileText,
  Users,
  Clapperboard,
  Play,
  Download,
  ChevronRight,
  Upload,
  Loader2,
  Share2,
  MessageSquare,
  Copy,
} from 'lucide-react';
import { api } from '../api/client';
import { useProjectStore } from '../stores/project-store';
import { cn } from '../lib/utils';
import { ProjectState } from '@shared/types';
import { ScreenplayUpload, MoviePlanViewer, ShareDialog, CommentsPanel } from '../components';
import { DataLoadError } from '../components/error-display';
import { useSharingStore } from '../stores/sharing-store';
import { useToast } from '../stores/toast-store';

// Workflow steps
const workflowSteps = [
  {
    id: 'screenplay',
    title: 'Upload Screenplay',
    description: 'Import your screenplay file',
    icon: FileText,
    states: [ProjectState.EMPTY],
  },
  {
    id: 'plan',
    title: 'Movie Plan',
    description: 'Review AI-generated movie plan',
    icon: Film,
    states: [ProjectState.SCREENPLAY_UPLOADED, ProjectState.SCREENPLAY_PARSED, ProjectState.PLAN_GENERATED],
  },
  {
    id: 'characters',
    title: 'Character Lab',
    description: 'Define and lock character looks',
    icon: Users,
    states: [ProjectState.PLAN_APPROVED, ProjectState.CHARACTERS_IN_PROGRESS],
  },
  {
    id: 'scenes',
    title: 'Scene Planning',
    description: 'Review and approve shot breakdowns',
    icon: Clapperboard,
    states: [ProjectState.CHARACTERS_LOCKED, ProjectState.SCENES_PLANNING],
  },
  {
    id: 'generate',
    title: 'Generate',
    description: 'Generate video content',
    icon: Play,
    states: [ProjectState.SCENES_APPROVED, ProjectState.GENERATING, ProjectState.GENERATION_COMPLETE],
  },
  {
    id: 'export',
    title: 'Export',
    description: 'Assemble and export final movie',
    icon: Download,
    states: [ProjectState.ASSEMBLY_IN_PROGRESS, ProjectState.COMPLETE, ProjectState.EXPORTED],
  },
];

function getStepStatus(stepStates: ProjectState[], currentState: ProjectState) {
  const allStates = Object.values(ProjectState);
  const currentIndex = allStates.indexOf(currentState);
  const stepStartIndex = allStates.indexOf(stepStates[0]);
  const stepEndIndex = allStates.indexOf(stepStates[stepStates.length - 1]);

  if (currentIndex > stepEndIndex) return 'complete';
  if (currentIndex >= stepStartIndex && currentIndex <= stepEndIndex) return 'current';
  return 'pending';
}

export function ProjectPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { setCurrentProject } = useProjectStore();
  const queryClient = useQueryClient();

  // Sharing state
  const [isShareDialogOpen, setIsShareDialogOpen] = useState(false);
  const { isCommentsPanelOpen, setCommentsPanelOpen, shares, fetchShares } = useSharingStore();

  // Duplicate state
  const [isDuplicating, setIsDuplicating] = useState(false);
  const toast = useToast();

  // Fetch project details
  const { data: project, isLoading, error } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => api.getProject(projectId!),
    enabled: !!projectId,
  });

  // Update store when project loads
  useEffect(() => {
    if (project) {
      setCurrentProject(project);
    }
  }, [project, setCurrentProject]);

  // Fetch shares when project loads
  useEffect(() => {
    if (projectId) {
      fetchShares(projectId);
    }
  }, [projectId, fetchShares]);

  // Handle screenplay upload completion
  const handleScreenplayUpload = useCallback(() => {
    // Invalidate project query to refetch with new screenplay data
    queryClient.invalidateQueries({ queryKey: ['project', projectId] });
  }, [queryClient, projectId]);

  const handleUploadError = useCallback((error: string) => {
    console.error('Screenplay upload error:', error);
  }, []);

  // Movie plan query
  const { data: moviePlan, isLoading: isLoadingPlan } = useQuery({
    queryKey: ['moviePlan', project?.screenplay?.id],
    queryFn: async () => {
      if (!project?.screenplay?.id) return null;
      return window.electronAPI.backendRequest<any>('moviePlan.get', {
        screenplay_id: project.screenplay.id,
      });
    },
    enabled: !!project?.screenplay?.id && project?.screenplay?.isParsed,
  });

  // Generate movie plan mutation
  const generatePlanMutation = useMutation({
    mutationFn: async (regenerate: boolean = false) => {
      if (!project?.screenplay?.id) throw new Error('No screenplay');
      return window.electronAPI.backendRequest<any>('moviePlan.generate', {
        screenplay_id: project.screenplay.id,
        regenerate,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['moviePlan', project?.screenplay?.id] });
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
    },
  });

  // Approve movie plan mutation
  const approvePlanMutation = useMutation({
    mutationFn: async () => {
      if (!project?.screenplay?.id) throw new Error('No screenplay');
      return window.electronAPI.backendRequest<any>('moviePlan.approve', {
        screenplay_id: project.screenplay.id,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
    },
  });

  // Auto-generate plan when screenplay is parsed but no plan exists
  useEffect(() => {
    if (
      project?.screenplay?.isParsed &&
      !moviePlan &&
      !isLoadingPlan &&
      !generatePlanMutation.isPending &&
      (project.state === ProjectState.SCREENPLAY_PARSED ||
        project.state === ProjectState.SCREENPLAY_UPLOADED)
    ) {
      generatePlanMutation.mutate(false);
    }
  }, [project, moviePlan, isLoadingPlan, generatePlanMutation]);

  const handleApprovePlan = useCallback(() => {
    approvePlanMutation.mutate();
  }, [approvePlanMutation]);

  const handleRegeneratePlan = useCallback(() => {
    generatePlanMutation.mutate(true);
  }, [generatePlanMutation]);

  // Handle project duplication
  const handleDuplicateProject = useCallback(async () => {
    if (!projectId || isDuplicating) return;

    setIsDuplicating(true);
    try {
      const result = await api.duplicateProject(projectId);
      toast.success(
        'Project Duplicated',
        `Created "${result.name}"`
      );
      // Invalidate projects list to show the new project
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      // Navigate to the new project
      navigate(`/project/${result.id}`);
    } catch (error) {
      toast.error(
        'Duplication Failed',
        error instanceof Error ? error.message : 'Failed to duplicate project'
      );
    } finally {
      setIsDuplicating(false);
    }
  }, [projectId, isDuplicating, toast, queryClient, navigate]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-surface-400">Loading project...</div>
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="flex items-center justify-center h-full p-8">
        <DataLoadError
          entity="project"
          error={error || new Error('Project not found')}
          onRetry={() => queryClient.invalidateQueries({ queryKey: ['project', projectId] })}
        />
      </div>
    );
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold">{project.name}</h1>
          {project.description && (
            <p className="text-surface-400 mt-1">{project.description}</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleDuplicateProject}
            disabled={isDuplicating}
            className="flex items-center gap-2 px-3 py-2 bg-surface-800 text-surface-300 hover:bg-surface-700 rounded-lg transition-colors disabled:opacity-50"
            title="Duplicate Project"
          >
            {isDuplicating ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Copy className="w-4 h-4" />
            )}
            <span className="text-sm">{isDuplicating ? 'Duplicating...' : 'Duplicate'}</span>
          </button>
          <button
            onClick={() => setCommentsPanelOpen(!isCommentsPanelOpen)}
            className={cn(
              'flex items-center gap-2 px-3 py-2 rounded-lg transition-colors',
              isCommentsPanelOpen
                ? 'bg-brand-500/20 text-brand-300'
                : 'bg-surface-800 text-surface-300 hover:bg-surface-700'
            )}
          >
            <MessageSquare className="w-4 h-4" />
            <span className="text-sm">Comments</span>
          </button>
          <button
            onClick={() => setIsShareDialogOpen(true)}
            className="flex items-center gap-2 px-3 py-2 bg-brand-600 hover:bg-brand-500 text-white rounded-lg transition-colors"
          >
            <Share2 className="w-4 h-4" />
            <span className="text-sm">Share</span>
            {shares.length > 0 && (
              <span className="px-1.5 py-0.5 bg-white/20 text-xs rounded">
                {shares.length}
              </span>
            )}
          </button>
        </div>
      </div>

      {/* Workflow Steps */}
      <div className="card mb-8">
        <h2 className="text-lg font-medium mb-6">Workflow Progress</h2>
        <div className="flex items-center justify-between">
          {workflowSteps.map((step, index) => {
            const status = getStepStatus(step.states, project.state as ProjectState);
            const Icon = step.icon;

            return (
              <div key={step.id} className="flex items-center">
                <div className="flex flex-col items-center">
                  <div
                    className={cn(
                      'w-12 h-12 rounded-full flex items-center justify-center mb-2',
                      status === 'complete' && 'bg-green-500/20 text-green-400',
                      status === 'current' && 'bg-brand-500/20 text-brand-400',
                      status === 'pending' && 'bg-surface-800 text-surface-500'
                    )}
                  >
                    <Icon className="w-5 h-5" />
                  </div>
                  <span
                    className={cn(
                      'text-sm font-medium',
                      status === 'current' && 'text-brand-400',
                      status === 'pending' && 'text-surface-500'
                    )}
                  >
                    {step.title}
                  </span>
                  <span className="text-xs text-surface-500 text-center max-w-[100px]">
                    {step.description}
                  </span>
                </div>
                {index < workflowSteps.length - 1 && (
                  <ChevronRight className="w-5 h-5 mx-4 text-surface-600" />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Current Step Content */}
      {project.state === ProjectState.EMPTY && (
        <div className="card">
          <h3 className="text-lg font-medium mb-4">Upload Your Screenplay</h3>
          <p className="text-surface-400 mb-6">
            Start by uploading your screenplay file to begin the movie generation process.
          </p>
          <ScreenplayUpload
            projectId={projectId!}
            onUploadComplete={handleScreenplayUpload}
            onError={handleUploadError}
          />
        </div>
      )}

      {/* Movie Plan Section */}
      {(project.state === ProjectState.SCREENPLAY_UPLOADED ||
        project.state === ProjectState.SCREENPLAY_PARSED ||
        project.state === ProjectState.PLAN_GENERATED) && (
        <div className="card">
          {(isLoadingPlan || generatePlanMutation.isPending) && !moviePlan ? (
            <div className="flex flex-col items-center justify-center py-16">
              <Loader2 className="w-12 h-12 text-brand-400 animate-spin mb-4" />
              <h3 className="text-lg font-medium mb-2">Generating Movie Plan</h3>
              <p className="text-surface-400 text-center max-w-md">
                Analyzing your screenplay to create a comprehensive movie plan.
                This includes character analysis, scene breakdowns, and visual style recommendations.
              </p>
            </div>
          ) : moviePlan ? (
            <MoviePlanViewer
              plan={moviePlan}
              onApprove={handleApprovePlan}
              onRegenerate={handleRegeneratePlan}
              isApproving={approvePlanMutation.isPending}
              isRegenerating={generatePlanMutation.isPending}
            />
          ) : (
            <div className="flex flex-col items-center justify-center py-16">
              <Film className="w-12 h-12 text-surface-600 mb-4" />
              <h3 className="text-lg font-medium mb-2">No Movie Plan Yet</h3>
              <p className="text-surface-400 mb-4">
                Generate a movie plan to analyze your screenplay.
              </p>
              <button
                onClick={() => generatePlanMutation.mutate(false)}
                className="btn-primary"
              >
                Generate Movie Plan
              </button>
            </div>
          )}
        </div>
      )}

      {/* Character Lab Section */}
      {(project.state === ProjectState.PLAN_APPROVED ||
        project.state === ProjectState.CHARACTERS_IN_PROGRESS) && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-lg font-medium flex items-center gap-2">
                <Users className="w-5 h-5 text-brand-400" />
                Character Lab
              </h3>
              <p className="text-surface-400 text-sm mt-1">
                Define and lock character appearances before generating scenes.
              </p>
            </div>
            <button
              onClick={() => navigate(`/project/${projectId}/characters`)}
              className="btn-primary"
            >
              Open Character Lab
            </button>
          </div>

          {/* Character Progress */}
          {project.characters && project.characters.length > 0 && (
            <div className="bg-surface-800/50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-surface-400">Characters Locked</span>
                <span className="text-sm font-medium">
                  {project.characters.filter((c) => c.isLocked).length}/
                  {project.characters.length}
                </span>
              </div>
              <div className="w-full h-2 bg-surface-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-brand-500 transition-all"
                  style={{
                    width: `${
                      (project.characters.filter((c) => c.isLocked).length /
                        project.characters.length) *
                      100
                    }%`,
                  }}
                />
              </div>
            </div>
          )}
        </div>
      )}

      {/* Scene Planning Section */}
      {(project.state === ProjectState.CHARACTERS_LOCKED ||
        project.state === ProjectState.SCENES_PLANNING) && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-lg font-medium flex items-center gap-2">
                <Clapperboard className="w-5 h-5 text-brand-400" />
                Scene Planning
              </h3>
              <p className="text-surface-400 text-sm mt-1">
                Review and approve shot breakdowns for each scene.
              </p>
            </div>
            <button
              onClick={() => navigate(`/project/${projectId}/scenes`)}
              className="btn-primary"
            >
              Open Scene Planning
            </button>
          </div>

          {/* Scene Progress */}
          {project.scenes && project.scenes.length > 0 && (
            <div className="bg-surface-800/50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-surface-400">Scenes Approved</span>
                <span className="text-sm font-medium">
                  {project.scenes.filter((s) => s.shotBreakdownApproved).length}/
                  {project.scenes.length}
                </span>
              </div>
              <div className="w-full h-2 bg-surface-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-brand-500 transition-all"
                  style={{
                    width: `${
                      (project.scenes.filter((s) => s.shotBreakdownApproved).length /
                        project.scenes.length) *
                      100
                    }%`,
                  }}
                />
              </div>
            </div>
          )}
        </div>
      )}

      {/* Generation Section */}
      {(project.state === ProjectState.SCENES_APPROVED ||
        project.state === ProjectState.GENERATING ||
        project.state === ProjectState.GENERATION_COMPLETE) && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-lg font-medium flex items-center gap-2">
                <Play className="w-5 h-5 text-brand-400" />
                Generation
              </h3>
              <p className="text-surface-400 text-sm mt-1">
                Generate and review video content for each shot.
              </p>
            </div>
            <button
              onClick={() => navigate(`/project/${projectId}/generate`)}
              className="btn-primary"
            >
              Open Generation
            </button>
          </div>

          {/* Generation Progress */}
          {project.state === ProjectState.GENERATING && (
            <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4">
              <div className="flex items-center gap-2">
                <Loader2 className="w-5 h-5 text-yellow-400 animate-spin" />
                <span className="text-yellow-300">Generation in progress...</span>
              </div>
            </div>
          )}

          {project.state === ProjectState.GENERATION_COMPLETE && (
            <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-4">
              <div className="flex items-center gap-2">
                <Play className="w-5 h-5 text-green-400" />
                <span className="text-green-300">All shots generated. Ready for export.</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Export Section */}
      {(project.state === ProjectState.ASSEMBLY_IN_PROGRESS ||
        project.state === ProjectState.COMPLETE ||
        project.state === ProjectState.EXPORTED) && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-lg font-medium flex items-center gap-2">
                <Download className="w-5 h-5 text-brand-400" />
                Export
              </h3>
              <p className="text-surface-400 text-sm mt-1">
                Assemble and export your final movie.
              </p>
            </div>
            <button
              onClick={() => navigate(`/project/${projectId}/export`)}
              className="btn-primary"
            >
              Open Export
            </button>
          </div>

          {/* Export Status */}
          {project.state === ProjectState.ASSEMBLY_IN_PROGRESS && (
            <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4">
              <div className="flex items-center gap-2">
                <Loader2 className="w-5 h-5 text-yellow-400 animate-spin" />
                <span className="text-yellow-300">Assembly in progress...</span>
              </div>
            </div>
          )}

          {project.state === ProjectState.COMPLETE && (
            <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
              <div className="flex items-center gap-2">
                <Download className="w-5 h-5 text-blue-400" />
                <span className="text-blue-300">Movie assembled. Ready for export.</span>
              </div>
            </div>
          )}

          {project.state === ProjectState.EXPORTED && (
            <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-4">
              <div className="flex items-center gap-2">
                <Download className="w-5 h-5 text-green-400" />
                <span className="text-green-300">Movie exported successfully!</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Quick Stats */}
      <div className="grid grid-cols-3 gap-4 mt-8">
        <div className="card">
          <div className="text-surface-400 text-sm mb-1">Characters</div>
          <div className="text-2xl font-bold">{project.characterCount || 0}</div>
          {project.characters && project.characters.length > 0 && (
            <div className="text-sm text-surface-500 mt-1">
              {project.characters.filter((c) => c.isLocked).length} locked
            </div>
          )}
        </div>
        <div className="card">
          <div className="text-surface-400 text-sm mb-1">Scenes</div>
          <div className="text-2xl font-bold">{project.sceneCount || 0}</div>
          {project.scenes && project.scenes.length > 0 && (
            <div className="text-sm text-surface-500 mt-1">
              {project.scenes.filter((s) => s.shotBreakdownApproved).length} approved
            </div>
          )}
        </div>
        <div className="card">
          <div className="text-surface-400 text-sm mb-1">Screenplay</div>
          <div className="text-2xl font-bold">
            {project.screenplay ? (
              <span className="text-green-400">Uploaded</span>
            ) : (
              <span className="text-surface-500">None</span>
            )}
          </div>
          {project.screenplay?.title && (
            <div className="text-sm text-surface-500 mt-1 truncate">
              {project.screenplay.title}
            </div>
          )}
        </div>
      </div>

      {/* Share Dialog */}
      <ShareDialog
        projectId={projectId!}
        projectName={project.name}
        isOpen={isShareDialogOpen}
        onClose={() => setIsShareDialogOpen(false)}
      />

      {/* Comments Panel */}
      <CommentsPanel
        projectId={projectId!}
        isOpen={isCommentsPanelOpen}
        onClose={() => setCommentsPanelOpen(false)}
      />
    </div>
  );
}
