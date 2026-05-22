/**
 * Scene Planning page.
 *
 * Displays scenes from the screenplay and allows users to
 * review, edit, and approve shot breakdowns for each scene.
 */

import { useState, useCallback, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Clapperboard,
  ArrowLeft,
  Play,
  Check,
  ChevronDown,
  ChevronRight,
  Loader2,
  RefreshCw,
  Plus,
  Film,
  Clock,
  AlertTriangle,
  Sparkles,
} from 'lucide-react';
import { ShotCard } from '../components/shot-card';
import { cn } from '../lib/utils';

interface Scene {
  id: string;
  projectId: string;
  sceneNumber: string;
  sequenceNumber: number;
  heading: string;
  sceneType: string;
  location: string;
  timeOfDay: string;
  state: string;
  characterIds: string[];
  analysis?: {
    summary?: string;
    mood?: string;
    pacing?: string;
    importance?: number;
  };
  shotBreakdown?: {
    approach?: string;
    coverageStyle?: string;
    notes?: string;
  };
  shotBreakdownApproved: boolean;
  estimatedDurationSeconds?: number;
  shots?: Shot[];
  shotCount: number;
}

interface Shot {
  id: string;
  shotNumber: string;
  sequenceNumber: number;
  shotType: string;
  cameraMovement: string;
  description: string;
  dialogue?: string;
  action?: string;
  characterIds?: string[];
  durationSeconds: number;
  compositionNotes?: string;
  lightingNotes?: string;
  state: string;
}

interface Character {
  id: string;
  name: string;
}

interface ShotType {
  value: string;
  label: string;
  description: string;
}

interface CameraMovement {
  value: string;
  label: string;
  description: string;
}

export function ScenePlanningPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [expandedScenes, setExpandedScenes] = useState<Set<string>>(new Set());
  const [selectedSceneId, setSelectedSceneId] = useState<string | null>(null);

  // Fetch scenes
  const { data: scenes, isLoading: isLoadingScenes } = useQuery({
    queryKey: ['scenes', projectId],
    queryFn: async () => {
      const result = await window.electronAPI.backendRequest<Scene[]>('scenes.list', {
        project_id: projectId,
        include_shots: true,
      });
      return result;
    },
    enabled: !!projectId,
  });

  // Fetch characters for display
  const { data: characters } = useQuery({
    queryKey: ['characters', projectId],
    queryFn: async () => {
      const result = await window.electronAPI.backendRequest<Character[]>('characters.list', {
        project_id: projectId,
      });
      return result;
    },
    enabled: !!projectId,
  });

  // Fetch shot types
  const { data: shotTypes } = useQuery({
    queryKey: ['shotTypes'],
    queryFn: async () => {
      const result = await window.electronAPI.backendRequest<ShotType[]>('scenes.getShotTypes', {});
      return result;
    },
  });

  // Fetch camera movements
  const { data: cameraMovements } = useQuery({
    queryKey: ['cameraMovements'],
    queryFn: async () => {
      const result = await window.electronAPI.backendRequest<CameraMovement[]>(
        'scenes.getCameraMovements',
        {}
      );
      return result;
    },
  });

  // Generate breakdown mutation
  const generateBreakdownMutation = useMutation({
    mutationFn: async ({
      sceneId,
      regenerate = false,
    }: {
      sceneId: string;
      regenerate?: boolean;
    }) => {
      return window.electronAPI.backendRequest('scenes.generateBreakdown', {
        scene_id: sceneId,
        regenerate,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scenes', projectId] });
    },
  });

  // Approve breakdown mutation
  const approveBreakdownMutation = useMutation({
    mutationFn: async (sceneId: string) => {
      return window.electronAPI.backendRequest('scenes.approve', {
        scene_id: sceneId,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scenes', projectId] });
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
    },
  });

  // Update shot mutation
  const updateShotMutation = useMutation({
    mutationFn: async ({ shotId, data }: { shotId: string; data: Partial<Shot> }) => {
      return window.electronAPI.backendRequest('shots.update', {
        shot_id: shotId,
        shot_type: data.shotType,
        camera_movement: data.cameraMovement,
        description: data.description,
        duration_seconds: data.durationSeconds,
        composition_notes: data.compositionNotes,
        lighting_notes: data.lightingNotes,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scenes', projectId] });
    },
  });

  // Add shot mutation
  const addShotMutation = useMutation({
    mutationFn: async ({
      sceneId,
      shotType,
      description,
      afterShotId,
    }: {
      sceneId: string;
      shotType: string;
      description: string;
      afterShotId?: string;
    }) => {
      return window.electronAPI.backendRequest('shots.add', {
        scene_id: sceneId,
        shot_type: shotType,
        description,
        after_shot_id: afterShotId,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scenes', projectId] });
    },
  });

  // Delete shot mutation
  const deleteShotMutation = useMutation({
    mutationFn: async (shotId: string) => {
      return window.electronAPI.backendRequest('shots.delete', {
        shot_id: shotId,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scenes', projectId] });
    },
  });

  const toggleSceneExpanded = useCallback((sceneId: string) => {
    setExpandedScenes((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(sceneId)) {
        newSet.delete(sceneId);
      } else {
        newSet.add(sceneId);
      }
      return newSet;
    });
  }, []);

  const handleGenerateBreakdown = useCallback(
    (sceneId: string, regenerate = false) => {
      generateBreakdownMutation.mutate({ sceneId, regenerate });
    },
    [generateBreakdownMutation]
  );

  const handleApproveBreakdown = useCallback(
    (sceneId: string) => {
      approveBreakdownMutation.mutate(sceneId);
    },
    [approveBreakdownMutation]
  );

  const handleUpdateShot = useCallback(
    (shotId: string, data: Partial<Shot>) => {
      updateShotMutation.mutate({ shotId, data });
    },
    [updateShotMutation]
  );

  const handleDeleteShot = useCallback(
    (shotId: string) => {
      deleteShotMutation.mutate(shotId);
    },
    [deleteShotMutation]
  );

  const handleAddShot = useCallback(
    (sceneId: string) => {
      addShotMutation.mutate({
        sceneId,
        shotType: 'medium',
        description: 'New shot',
      });
    },
    [addShotMutation]
  );

  // Stats
  const totalScenes = scenes?.length ?? 0;
  const approvedScenes = scenes?.filter((s) => s.shotBreakdownApproved).length ?? 0;
  const allApproved = totalScenes > 0 && approvedScenes === totalScenes;
  const totalDuration = scenes?.reduce((acc, s) => acc + (s.estimatedDurationSeconds || 0), 0) ?? 0;

  if (isLoadingScenes) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-surface-400">Loading scenes...</div>
      </div>
    );
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate(`/project/${projectId}`)}
            className="p-2 hover:bg-surface-800 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Clapperboard className="w-7 h-7 text-brand-400" />
              Scene Planning
            </h1>
            <p className="text-surface-400 mt-1">
              Review and approve shot breakdowns for each scene
            </p>
          </div>
        </div>

        {/* Progress Stats */}
        <div className="flex items-center gap-6">
          <div className="text-right">
            <div className="text-sm text-surface-400">Scenes Approved</div>
            <div className="text-2xl font-bold">
              {approvedScenes}/{totalScenes}
            </div>
          </div>
          <div className="text-right">
            <div className="text-sm text-surface-400">Est. Duration</div>
            <div className="text-2xl font-bold">
              {Math.floor(totalDuration / 60)}:
              {String(Math.floor(totalDuration % 60)).padStart(2, '0')}
            </div>
          </div>
          {allApproved ? (
            <div className="flex items-center gap-2 px-4 py-2 bg-green-500/20 text-green-400 rounded-lg">
              <Check className="w-5 h-5" />
              <span>All Approved</span>
            </div>
          ) : (
            <div className="flex items-center gap-2 px-4 py-2 bg-yellow-500/20 text-yellow-400 rounded-lg">
              <AlertTriangle className="w-5 h-5" />
              <span>In Progress</span>
            </div>
          )}
        </div>
      </div>

      {/* Scene List */}
      {scenes && scenes.length > 0 ? (
        <div className="space-y-4">
          {scenes.map((scene) => {
            const isExpanded = expandedScenes.has(scene.id);
            const hasBreakdown = scene.shots && scene.shots.length > 0;
            const isGenerating =
              generateBreakdownMutation.isPending &&
              generateBreakdownMutation.variables?.sceneId === scene.id;

            return (
              <div
                key={scene.id}
                className={cn(
                  'card overflow-hidden',
                  scene.shotBreakdownApproved && 'border-green-500/30'
                )}
              >
                {/* Scene Header */}
                <div
                  className="flex items-center gap-4 p-4 cursor-pointer hover:bg-surface-800/50 transition-colors"
                  onClick={() => toggleSceneExpanded(scene.id)}
                >
                  {/* Expand Icon */}
                  <div className="text-surface-500">
                    {isExpanded ? (
                      <ChevronDown className="w-5 h-5" />
                    ) : (
                      <ChevronRight className="w-5 h-5" />
                    )}
                  </div>

                  {/* Scene Number */}
                  <div className="flex items-center justify-center w-12 h-12 rounded-lg bg-surface-700 font-mono text-lg font-bold">
                    {scene.sceneNumber}
                  </div>

                  {/* Scene Info */}
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium truncate">{scene.heading}</h3>
                    <div className="flex items-center gap-2 text-sm text-surface-400 mt-1">
                      <span>{scene.location}</span>
                      <span className="text-surface-600">•</span>
                      <span>{scene.timeOfDay}</span>
                      {scene.analysis?.mood && (
                        <>
                          <span className="text-surface-600">•</span>
                          <span className="capitalize">{scene.analysis.mood}</span>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Shot Count & Duration */}
                  <div className="flex items-center gap-4 text-sm">
                    <div className="flex items-center gap-1 text-surface-400">
                      <Film className="w-4 h-4" />
                      <span>{scene.shotCount || scene.shots?.length || 0} shots</span>
                    </div>
                    {scene.estimatedDurationSeconds && (
                      <div className="flex items-center gap-1 text-surface-400">
                        <Clock className="w-4 h-4" />
                        <span>{scene.estimatedDurationSeconds.toFixed(1)}s</span>
                      </div>
                    )}
                  </div>

                  {/* Status */}
                  {scene.shotBreakdownApproved ? (
                    <div className="flex items-center gap-1 px-3 py-1 bg-green-500/20 text-green-400 rounded-full text-sm">
                      <Check className="w-4 h-4" />
                      <span>Approved</span>
                    </div>
                  ) : hasBreakdown ? (
                    <div className="px-3 py-1 bg-brand-500/20 text-brand-400 rounded-full text-sm">
                      Planned
                    </div>
                  ) : (
                    <div className="px-3 py-1 bg-surface-700 text-surface-400 rounded-full text-sm">
                      Pending
                    </div>
                  )}
                </div>

                {/* Expanded Content */}
                {isExpanded && (
                  <div className="border-t border-surface-700">
                    {/* Scene Analysis */}
                    {scene.analysis && (
                      <div className="bg-surface-800/30 p-4 border-b border-surface-700">
                        <div className="grid grid-cols-4 gap-4 text-sm">
                          {scene.analysis.summary && (
                            <div className="col-span-2">
                              <span className="text-surface-500">Summary:</span>
                              <p className="text-surface-300 mt-1">{scene.analysis.summary}</p>
                            </div>
                          )}
                          {scene.analysis.pacing && (
                            <div>
                              <span className="text-surface-500">Pacing:</span>
                              <p className="text-surface-300 mt-1 capitalize">
                                {scene.analysis.pacing}
                              </p>
                            </div>
                          )}
                          {scene.analysis.importance && (
                            <div>
                              <span className="text-surface-500">Importance:</span>
                              <p className="text-surface-300 mt-1">
                                {scene.analysis.importance}/10
                              </p>
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Shot Breakdown */}
                    <div className="p-4">
                      {isGenerating ? (
                        <div className="flex flex-col items-center justify-center py-8">
                          <Loader2 className="w-8 h-8 text-brand-400 animate-spin mb-3" />
                          <p className="text-surface-400">Generating shot breakdown...</p>
                        </div>
                      ) : hasBreakdown ? (
                        <>
                          {/* Breakdown Info */}
                          {scene.shotBreakdown && (
                            <div className="mb-4 p-3 bg-brand-500/10 border border-brand-500/30 rounded-lg">
                              <div className="flex items-start gap-2">
                                <Sparkles className="w-4 h-4 text-brand-400 mt-0.5" />
                                <div>
                                  <p className="text-sm text-brand-300">
                                    {scene.shotBreakdown.approach}
                                  </p>
                                  {scene.shotBreakdown.coverageStyle && (
                                    <p className="text-xs text-surface-400 mt-1">
                                      Coverage: {scene.shotBreakdown.coverageStyle}
                                    </p>
                                  )}
                                </div>
                              </div>
                            </div>
                          )}

                          {/* Shot List */}
                          <div className="space-y-2 mb-4">
                            {scene.shots?.map((shot) => (
                              <ShotCard
                                key={shot.id}
                                shot={shot}
                                characters={characters}
                                shotTypes={shotTypes || []}
                                cameraMovements={cameraMovements || []}
                                onUpdate={handleUpdateShot}
                                onDelete={handleDeleteShot}
                                disabled={
                                  scene.shotBreakdownApproved ||
                                  updateShotMutation.isPending ||
                                  deleteShotMutation.isPending
                                }
                              />
                            ))}
                          </div>

                          {/* Actions */}
                          <div className="flex items-center justify-between pt-4 border-t border-surface-700">
                            <div className="flex gap-2">
                              <button
                                onClick={() => handleAddShot(scene.id)}
                                disabled={scene.shotBreakdownApproved || addShotMutation.isPending}
                                className="btn-secondary text-sm"
                              >
                                <Plus className="w-4 h-4 mr-1" />
                                Add Shot
                              </button>
                              <button
                                onClick={() => handleGenerateBreakdown(scene.id, true)}
                                disabled={scene.shotBreakdownApproved}
                                className="btn-secondary text-sm"
                              >
                                <RefreshCw className="w-4 h-4 mr-1" />
                                Regenerate
                              </button>
                            </div>
                            {!scene.shotBreakdownApproved && (
                              <button
                                onClick={() => handleApproveBreakdown(scene.id)}
                                disabled={approveBreakdownMutation.isPending}
                                className="btn-primary"
                              >
                                <Check className="w-4 h-4 mr-1" />
                                Approve Breakdown
                              </button>
                            )}
                          </div>
                        </>
                      ) : (
                        <div className="flex flex-col items-center justify-center py-8">
                          <Film className="w-12 h-12 text-surface-600 mb-3" />
                          <p className="text-surface-400 mb-4">No shot breakdown generated yet</p>
                          <button
                            onClick={() => handleGenerateBreakdown(scene.id)}
                            className="btn-primary"
                          >
                            <Sparkles className="w-4 h-4 mr-1" />
                            Generate Shot Breakdown
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <div className="text-center py-16">
          <Clapperboard className="w-16 h-16 mx-auto text-surface-600 mb-4" />
          <h3 className="text-lg font-medium mb-2">No Scenes Found</h3>
          <p className="text-surface-400">Scenes will appear here once a screenplay is parsed.</p>
        </div>
      )}

      {/* Continue Button */}
      {allApproved && (
        <div className="fixed bottom-8 right-8">
          <button
            onClick={() => navigate(`/project/${projectId}`)}
            className="btn-primary shadow-lg"
          >
            <Play className="w-4 h-4 mr-2" />
            Continue to Generation
          </button>
        </div>
      )}
    </div>
  );
}
