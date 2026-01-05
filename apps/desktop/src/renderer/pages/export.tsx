/**
 * Export page for assembling and exporting movies.
 */

import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Download,
  Film,
  Play,
  Settings,
  ChevronLeft,
  Loader2,
  Check,
  AlertTriangle,
  FileVideo,
  HardDrive,
  Clock,
  Folder,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { TimelinePreview } from '../components/timeline-preview';
import { WatermarkPicker } from '../components/watermark-picker';
import { api } from '../api/client';

// Export format options
interface ExportFormat {
  value: string;
  label: string;
  description: string;
  extension: string;
}

interface QualityPreset {
  value: string;
  label: string;
  description: string;
  bitrate: string;
}

interface WatermarkSettings {
  enabled: boolean;
  path: string | null;
  position: string;
  opacity: number;
}

interface ExportSettings {
  format: string;
  quality: string;
  resolution: string;
  frameRate: number;
  includeAudio: boolean;
  includeSubtitles: boolean;
  includeTextOverlays: boolean;
  watermark: WatermarkSettings;
  outputFilename: string;
}

interface AssemblyStatus {
  projectId: string;
  isReady: boolean;
  totalScenes: number;
  totalShots: number;
  generatedShots: number;
  missingShots: string[];
  totalDuration: number;
}

interface TimelineData {
  projectId: string;
  totalDuration: number;
  scenes: Array<{
    sceneId: string;
    sceneNumber: string;
    title?: string;
    duration: number;
    shots: Array<{
      shotId: string;
      shotNumber: string;
      duration: number;
      hasOutput: boolean;
      thumbnail?: string;
    }>;
  }>;
}

const resolutionOptions = [
  { value: '1920x1080', label: '1080p (Full HD)', aspect: '16:9' },
  { value: '2560x1440', label: '1440p (2K)', aspect: '16:9' },
  { value: '3840x2160', label: '2160p (4K)', aspect: '16:9' },
  { value: '1280x720', label: '720p (HD)', aspect: '16:9' },
];

const frameRateOptions = [
  { value: 24, label: '24 fps (Cinema)' },
  { value: 25, label: '25 fps (PAL)' },
  { value: 30, label: '30 fps (NTSC)' },
  { value: 60, label: '60 fps (Smooth)' },
];

function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);

  if (hours > 0) {
    return `${hours}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

export function ExportPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // State for export settings - initialized with defaults, overridden by user settings
  const [settings, setSettings] = useState<ExportSettings>({
    format: 'mp4_h264',
    quality: 'high',
    resolution: '1920x1080',
    frameRate: 24,
    includeAudio: true,
    includeSubtitles: false,
    includeTextOverlays: true,
    watermark: {
      enabled: false,
      path: null,
      position: 'bottom_right',
      opacity: 0.7,
    },
    outputFilename: '',
  });
  const [settingsInitialized, setSettingsInitialized] = useState(false);

  // Fetch user settings to use as defaults
  const { data: userSettings } = useQuery({
    queryKey: ['settings'],
    queryFn: () => api.getSettings(),
    staleTime: 60000,
  });

  // Apply user settings as defaults (only once when loaded)
  useEffect(() => {
    if (userSettings && !settingsInitialized) {
      setSettings((prev) => ({
        ...prev,
        format: userSettings.defaultExportFormat || prev.format,
        quality: userSettings.defaultExportQuality || prev.quality,
        resolution: userSettings.defaultVideoResolution || prev.resolution,
        frameRate: userSettings.defaultVideoFps || prev.frameRate,
      }));
      setSettingsInitialized(true);
    }
  }, [userSettings, settingsInitialized]);

  // State for export progress
  const [exportProgress, setExportProgress] = useState<{
    active: boolean;
    percent: number;
    stage: string;
    message: string;
  }>({
    active: false,
    percent: 0,
    stage: '',
    message: '',
  });

  // Selected items for timeline
  const [selectedSceneId, setSelectedSceneId] = useState<string>();
  const [selectedShotId, setSelectedShotId] = useState<string>();

  // Fetch project
  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () =>
      window.electronAPI.backendRequest<any>('projects.get', { id: projectId }),
    enabled: !!projectId,
  });

  // Fetch assembly status
  const { data: assemblyStatus, isLoading: isLoadingStatus } = useQuery({
    queryKey: ['assemblyStatus', projectId],
    queryFn: () =>
      window.electronAPI.backendRequest<AssemblyStatus>('assembly.getStatus', {
        project_id: projectId,
      }),
    enabled: !!projectId,
    refetchInterval: 5000, // Refresh every 5 seconds
  });

  // Fetch timeline
  const { data: timeline, isLoading: isLoadingTimeline } = useQuery({
    queryKey: ['timeline', projectId],
    queryFn: () =>
      window.electronAPI.backendRequest<TimelineData>('assembly.getTimeline', {
        project_id: projectId,
      }),
    enabled: !!projectId,
  });

  // Fetch export formats
  const { data: formats } = useQuery({
    queryKey: ['exportFormats'],
    queryFn: () =>
      window.electronAPI.backendRequest<ExportFormat[]>('assembly.getFormats', {}),
  });

  // Fetch quality presets
  const { data: qualityPresets } = useQuery({
    queryKey: ['qualityPresets'],
    queryFn: () =>
      window.electronAPI.backendRequest<QualityPreset[]>(
        'assembly.getQualityPresets',
        {}
      ),
  });

  // Fetch export history
  const { data: exportHistory } = useQuery({
    queryKey: ['exportHistory', projectId],
    queryFn: () =>
      window.electronAPI.backendRequest<any[]>('assembly.getExportHistory', {
        project_id: projectId,
      }),
    enabled: !!projectId,
  });

  // Set default filename from project name
  useEffect(() => {
    if (project?.name && !settings.outputFilename) {
      const safeName = project.name.replace(/[^a-zA-Z0-9-_]/g, '_');
      setSettings((prev) => ({ ...prev, outputFilename: safeName }));
    }
  }, [project?.name]);

  // Assemble movie mutation
  const assembleMutation = useMutation({
    mutationFn: () =>
      window.electronAPI.backendRequest<any>('assembly.assembleMovie', {
        project_id: projectId,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assemblyStatus', projectId] });
    },
  });

  // Export mutation
  const exportMutation = useMutation({
    mutationFn: () =>
      window.electronAPI.backendRequest<any>('assembly.export', {
        project_id: projectId,
        format: settings.format,
        quality: settings.quality,
        resolution: settings.resolution,
        frame_rate: settings.frameRate,
        include_audio: settings.includeAudio,
        include_subtitles: settings.includeSubtitles,
        include_text_overlays: settings.includeTextOverlays,
        watermark: settings.watermark.enabled,
        watermark_path: settings.watermark.enabled ? settings.watermark.path : null,
        watermark_position: settings.watermark.position,
        watermark_opacity: settings.watermark.opacity,
        output_filename: settings.outputFilename || undefined,
      }),
    onMutate: () => {
      setExportProgress({
        active: true,
        percent: 0,
        stage: 'starting',
        message: 'Starting export...',
      });
    },
    onSuccess: (result) => {
      setExportProgress({
        active: false,
        percent: 100,
        stage: 'complete',
        message: 'Export complete!',
      });
      queryClient.invalidateQueries({ queryKey: ['exportHistory', projectId] });
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
    },
    onError: (error) => {
      setExportProgress({
        active: false,
        percent: 0,
        stage: 'error',
        message: error instanceof Error ? error.message : 'Export failed',
      });
    },
  });

  const handleExport = useCallback(() => {
    exportMutation.mutate();
  }, [exportMutation]);

  const handleSettingChange = useCallback(
    <K extends keyof ExportSettings>(key: K, value: ExportSettings[K]) => {
      setSettings((prev) => ({ ...prev, [key]: value }));
    },
    []
  );

  // Calculate estimated file size
  const estimatedSize = (() => {
    if (!timeline) return null;

    const qualityMultiplier = {
      draft: 0.5,
      standard: 1,
      high: 2,
      master: 4,
    }[settings.quality] || 1;

    const resolutionMultiplier =
      parseInt(settings.resolution.split('x')[0]) / 1920;

    // Rough estimate: ~5 MB per minute at 1080p standard quality
    const baseMBPerMinute = 5;
    const estimatedMB =
      (timeline.totalDuration / 60) *
      baseMBPerMinute *
      qualityMultiplier *
      resolutionMultiplier;

    return estimatedMB * 1024 * 1024; // Convert to bytes
  })();

  if (isLoadingStatus || isLoadingTimeline) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 text-brand-400 animate-spin" />
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-surface-800">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate(`/project/${projectId}`)}
            className="p-2 hover:bg-surface-800 rounded-lg transition-colors"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-xl font-bold flex items-center gap-2">
              <Download className="w-5 h-5 text-brand-400" />
              Export Movie
            </h1>
            <p className="text-sm text-surface-400">{project?.name}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {assemblyStatus?.isReady ? (
            <button
              onClick={handleExport}
              disabled={exportMutation.isPending}
              className="btn-primary flex items-center gap-2"
            >
              {exportMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Exporting...
                </>
              ) : (
                <>
                  <Download className="w-4 h-4" />
                  Export Movie
                </>
              )}
            </button>
          ) : (
            <div className="flex items-center gap-2 text-yellow-400">
              <AlertTriangle className="w-4 h-4" />
              <span className="text-sm">
                {assemblyStatus?.generatedShots || 0}/{assemblyStatus?.totalShots || 0} shots
                generated
              </span>
            </div>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-hidden flex">
        {/* Main content */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* Assembly Status */}
          <div className="card mb-6">
            <h2 className="text-lg font-medium mb-4 flex items-center gap-2">
              <Film className="w-5 h-5 text-brand-400" />
              Assembly Status
            </h2>

            {assemblyStatus && (
              <div className="space-y-4">
                {/* Progress */}
                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-surface-400">Shots Generated</span>
                    <span>
                      {assemblyStatus.generatedShots}/{assemblyStatus.totalShots}
                    </span>
                  </div>
                  <div className="w-full h-2 bg-surface-800 rounded-full overflow-hidden">
                    <div
                      className={cn(
                        'h-full transition-all',
                        assemblyStatus.isReady ? 'bg-green-500' : 'bg-brand-500'
                      )}
                      style={{
                        width: `${
                          assemblyStatus.totalShots > 0
                            ? (assemblyStatus.generatedShots /
                                assemblyStatus.totalShots) *
                              100
                            : 0
                        }%`,
                      }}
                    />
                  </div>
                </div>

                {/* Stats grid */}
                <div className="grid grid-cols-3 gap-4">
                  <div className="bg-surface-800/50 rounded-lg p-3">
                    <div className="text-surface-400 text-xs mb-1">Scenes</div>
                    <div className="text-xl font-bold">{assemblyStatus.totalScenes}</div>
                  </div>
                  <div className="bg-surface-800/50 rounded-lg p-3">
                    <div className="text-surface-400 text-xs mb-1">Total Duration</div>
                    <div className="text-xl font-bold">
                      {formatDuration(assemblyStatus.totalDuration)}
                    </div>
                  </div>
                  <div className="bg-surface-800/50 rounded-lg p-3">
                    <div className="text-surface-400 text-xs mb-1">Status</div>
                    <div
                      className={cn(
                        'text-xl font-bold',
                        assemblyStatus.isReady ? 'text-green-400' : 'text-yellow-400'
                      )}
                    >
                      {assemblyStatus.isReady ? 'Ready' : 'Pending'}
                    </div>
                  </div>
                </div>

                {/* Missing shots warning */}
                {assemblyStatus.missingShots.length > 0 && (
                  <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-3">
                    <div className="flex items-center gap-2 text-yellow-400 mb-2">
                      <AlertTriangle className="w-4 h-4" />
                      <span className="font-medium">Missing Shots</span>
                    </div>
                    <p className="text-sm text-surface-400">
                      The following shots need to be generated:{' '}
                      {assemblyStatus.missingShots.join(', ')}
                      {assemblyStatus.missingShots.length >= 10 && '...'}
                    </p>
                    <button
                      onClick={() => navigate(`/project/${projectId}/generate`)}
                      className="mt-2 text-sm text-brand-400 hover:text-brand-300"
                    >
                      Go to Generation
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Timeline Preview */}
          {timeline && (
            <div className="card mb-6">
              <h2 className="text-lg font-medium mb-4 flex items-center gap-2">
                <Play className="w-5 h-5 text-brand-400" />
                Timeline Preview
              </h2>
              <TimelinePreview
                scenes={timeline.scenes}
                totalDuration={timeline.totalDuration}
                selectedSceneId={selectedSceneId}
                selectedShotId={selectedShotId}
                onSceneClick={setSelectedSceneId}
                onShotClick={(sceneId, shotId) => {
                  setSelectedSceneId(sceneId);
                  setSelectedShotId(shotId);
                }}
              />
            </div>
          )}

          {/* Export Progress */}
          {exportProgress.active && (
            <div className="card mb-6">
              <h2 className="text-lg font-medium mb-4 flex items-center gap-2">
                <Loader2 className="w-5 h-5 text-brand-400 animate-spin" />
                Export Progress
              </h2>
              <div className="space-y-4">
                <div className="w-full h-3 bg-surface-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-brand-500 transition-all"
                    style={{ width: `${exportProgress.percent}%` }}
                  />
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-surface-400">{exportProgress.stage}</span>
                  <span>{exportProgress.percent.toFixed(0)}%</span>
                </div>
                <p className="text-sm text-surface-400">{exportProgress.message}</p>
              </div>
            </div>
          )}

          {/* Export History */}
          {exportHistory && exportHistory.length > 0 && (
            <div className="card">
              <h2 className="text-lg font-medium mb-4 flex items-center gap-2">
                <FileVideo className="w-5 h-5 text-brand-400" />
                Export History
              </h2>
              <div className="space-y-2">
                {exportHistory.map((item: any, idx: number) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-3 bg-surface-800/50 rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <FileVideo className="w-5 h-5 text-surface-400" />
                      <div>
                        <p className="font-medium">{item.filename}</p>
                        <p className="text-xs text-surface-400">
                          {item.format} - {item.quality} -{' '}
                          {formatFileSize(item.fileSize)}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-surface-400">
                        {new Date(item.exportedAt).toLocaleDateString()}
                      </span>
                      <button
                        onClick={() => {
                          // Open file location
                          window.electronAPI.showItemInFolder(item.outputPath);
                        }}
                        className="p-2 hover:bg-surface-700 rounded transition-colors"
                        title="Show in folder"
                      >
                        <Folder className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Settings Sidebar */}
        <div className="w-80 border-l border-surface-800 overflow-y-auto p-4">
          <h2 className="text-lg font-medium mb-4 flex items-center gap-2">
            <Settings className="w-5 h-5 text-brand-400" />
            Export Settings
          </h2>

          <div className="space-y-4">
            {/* Format */}
            <div>
              <label className="block text-sm text-surface-400 mb-2">Format</label>
              <select
                value={settings.format}
                onChange={(e) => handleSettingChange('format', e.target.value)}
                className="w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2"
              >
                {formats?.map((fmt) => (
                  <option key={fmt.value} value={fmt.value}>
                    {fmt.label}
                  </option>
                )) || (
                  <>
                    <option value="mp4_h264">MP4 (H.264)</option>
                    <option value="mp4_h265">MP4 (H.265/HEVC)</option>
                    <option value="mov_prores">MOV (ProRes)</option>
                    <option value="webm_vp9">WebM (VP9)</option>
                  </>
                )}
              </select>
            </div>

            {/* Quality */}
            <div>
              <label className="block text-sm text-surface-400 mb-2">Quality</label>
              <select
                value={settings.quality}
                onChange={(e) => handleSettingChange('quality', e.target.value)}
                className="w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2"
              >
                {qualityPresets?.map((preset) => (
                  <option key={preset.value} value={preset.value}>
                    {preset.label}
                  </option>
                )) || (
                  <>
                    <option value="draft">Draft (Fast)</option>
                    <option value="standard">Standard</option>
                    <option value="high">High</option>
                    <option value="master">Master (Slow)</option>
                  </>
                )}
              </select>
            </div>

            {/* Resolution */}
            <div>
              <label className="block text-sm text-surface-400 mb-2">Resolution</label>
              <select
                value={settings.resolution}
                onChange={(e) => handleSettingChange('resolution', e.target.value)}
                className="w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2"
              >
                {resolutionOptions.map((res) => (
                  <option key={res.value} value={res.value}>
                    {res.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Frame Rate */}
            <div>
              <label className="block text-sm text-surface-400 mb-2">Frame Rate</label>
              <select
                value={settings.frameRate}
                onChange={(e) =>
                  handleSettingChange('frameRate', parseInt(e.target.value))
                }
                className="w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2"
              >
                {frameRateOptions.map((fps) => (
                  <option key={fps.value} value={fps.value}>
                    {fps.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Output Filename */}
            <div>
              <label className="block text-sm text-surface-400 mb-2">
                Output Filename
              </label>
              <input
                type="text"
                value={settings.outputFilename}
                onChange={(e) => handleSettingChange('outputFilename', e.target.value)}
                placeholder="movie_export"
                className="w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2"
              />
            </div>

            {/* Toggles */}
            <div className="space-y-3 pt-2">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.includeAudio}
                  onChange={(e) =>
                    handleSettingChange('includeAudio', e.target.checked)
                  }
                  className="w-4 h-4 rounded border-surface-600 bg-surface-800"
                />
                <span className="text-sm">Include Audio</span>
              </label>

              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.includeSubtitles}
                  onChange={(e) =>
                    handleSettingChange('includeSubtitles', e.target.checked)
                  }
                  className="w-4 h-4 rounded border-surface-600 bg-surface-800"
                />
                <span className="text-sm">Include Subtitles</span>
              </label>

              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.includeTextOverlays}
                  onChange={(e) =>
                    handleSettingChange('includeTextOverlays', e.target.checked)
                  }
                  className="w-4 h-4 rounded border-surface-600 bg-surface-800"
                />
                <span className="text-sm">Include Text Overlays</span>
              </label>
            </div>

            {/* Watermark Settings */}
            <div className="pt-2 border-t border-surface-700">
              <WatermarkPicker
                selectedPath={settings.watermark.path}
                position={settings.watermark.position}
                opacity={settings.watermark.opacity}
                enabled={settings.watermark.enabled}
                onSelect={(path) =>
                  setSettings((prev) => ({
                    ...prev,
                    watermark: { ...prev.watermark, path },
                  }))
                }
                onPositionChange={(position) =>
                  setSettings((prev) => ({
                    ...prev,
                    watermark: { ...prev.watermark, position },
                  }))
                }
                onOpacityChange={(opacity) =>
                  setSettings((prev) => ({
                    ...prev,
                    watermark: { ...prev.watermark, opacity },
                  }))
                }
                onEnabledChange={(enabled) =>
                  setSettings((prev) => ({
                    ...prev,
                    watermark: { ...prev.watermark, enabled },
                  }))
                }
              />
            </div>

            {/* Estimated Size */}
            {estimatedSize && (
              <div className="pt-4 border-t border-surface-700">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-surface-400">Estimated Size</span>
                  <span className="font-medium">{formatFileSize(estimatedSize)}</span>
                </div>
                <div className="flex items-center justify-between text-sm mt-2">
                  <span className="text-surface-400">Duration</span>
                  <span className="font-medium">
                    {formatDuration(timeline?.totalDuration || 0)}
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
