/**
 * Project Archive/Import page.
 * Allows users to export and import projects.
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Archive,
  Download,
  Upload,
  FolderOpen,
  File,
  Trash2,
  Clock,
  HardDrive,
  CheckCircle,
  AlertCircle,
  Loader2,
  ChevronLeft,
  Settings,
  Film,
  Image,
  Video,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { useToast } from '../components/toast';
import { useTranslation } from '../i18n/use-translation';

interface ExportedArchive {
  filename: string;
  projectName: string;
  exportedAt: string;
  fileSize: number;
  version: string;
  path: string;
}

interface ArchiveInfo {
  version: string;
  projectName: string;
  projectId: string;
  exportedAt: string;
  includesAssets: boolean;
  includesOutputs: boolean;
  includesGeneratedVideos: boolean;
  sceneCount: number;
  characterCount: number;
  shotCount: number;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

function formatDate(isoString: string): string {
  return new Date(isoString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function ArchivePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const { t } = useTranslation();

  // Export options
  const [exportProjectId, setExportProjectId] = useState<string | null>(null);
  const [includeAssets, setIncludeAssets] = useState(true);
  const [includeOutputs, setIncludeOutputs] = useState(true);
  const [includeGeneratedVideos, setIncludeGeneratedVideos] = useState(false);

  // Import state
  const [importFile, setImportFile] = useState<string | null>(null);
  const [archiveInfo, setArchiveInfo] = useState<ArchiveInfo | null>(null);
  const [importAssets, setImportAssets] = useState(true);
  const [newProjectName, setNewProjectName] = useState('');

  // Fetch projects for export
  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: () => window.electronAPI.backendRequest<any[]>('projects.list', {}),
  });

  // Fetch existing exports
  const { data: exports, isLoading: exportsLoading } = useQuery({
    queryKey: ['project-exports'],
    queryFn: () => window.electronAPI.backendRequest<ExportedArchive[]>('project.listExports', {}),
  });

  // Export mutation
  const exportMutation = useMutation({
    mutationFn: async () => {
      if (!exportProjectId) throw new Error(t('archive.errorNoProjectSelected', 'No project selected'));

      // Show save dialog
      const result = await window.electronAPI.saveFile({
        title: t('archive.exportProjectDialogTitle', 'Export Project'),
        defaultPath: `project-${Date.now()}.smproject`,
        filters: [{ name: t('archive.fileFilterSmProject', 'SceneMachine Project'), extensions: ['smproject'] }],
      });

      if (result.canceled || !result.filePath) {
        throw new Error('Export cancelled');
      }

      return window.electronAPI.backendRequest('project.export', {
        project_id: exportProjectId,
        output_path: result.filePath,
        include_assets: includeAssets,
        include_outputs: includeOutputs,
        include_generated_videos: includeGeneratedVideos,
      });
    },
    onSuccess: () => {
      showToast(t('archive.toastExportSuccess', 'Project exported successfully'), 'success');
      queryClient.invalidateQueries({ queryKey: ['project-exports'] });
      setExportProjectId(null);
    },
    onError: (error: any) => {
      if (error.message !== 'Export cancelled') {
        showToast(`${t('archive.toastExportFailed', 'Export failed')}: ${error.message}`, 'error');
      }
    },
  });

  // Import mutation
  const importMutation = useMutation({
    mutationFn: async () => {
      if (!importFile) throw new Error(t('archive.errorNoFileSelected', 'No file selected'));

      return window.electronAPI.backendRequest('project.import', {
        archive_path: importFile,
        new_name: newProjectName || undefined,
        import_assets: importAssets,
      });
    },
    onSuccess: (result: any) => {
      showToast(t('archive.toastImportSuccess', 'Project imported successfully'), 'success');
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      setImportFile(null);
      setArchiveInfo(null);
      setNewProjectName('');

      // Navigate to the imported project
      if (result.projectId) {
        navigate(`/project/${result.projectId}`);
      }
    },
    onError: (error: any) => {
      showToast(`${t('archive.toastImportFailed', 'Import failed')}: ${error.message}`, 'error');
    },
  });

  // Handle file selection for import
  const handleSelectImportFile = async () => {
    const result = await window.electronAPI.openFile({
      title: t('archive.selectArchiveDialogTitle', 'Select Project Archive'),
      filters: [
        { name: t('archive.fileFilterSmProject', 'SceneMachine Project'), extensions: ['smproject'] },
        { name: t('archive.fileFilterAllFiles', 'All Files'), extensions: ['*'] },
      ],
      properties: ['openFile'],
    });

    if (!result.canceled && result.filePaths.length > 0) {
      const filePath = result.filePaths[0];
      setImportFile(filePath);

      // Get archive info
      try {
        const info = await window.electronAPI.backendRequest<ArchiveInfo>(
          'project.getArchiveInfo',
          { archive_path: filePath }
        );
        setArchiveInfo(info);
        setNewProjectName(info.projectName);
      } catch (error: any) {
        showToast(`${t('archive.toastReadArchiveFailed', 'Failed to read archive')}: ${error.message}`, 'error');
        setImportFile(null);
      }
    }
  };

  const selectedProject = projects?.find((p) => p.id === exportProjectId);

  return (
    <div className="h-full overflow-y-auto">
      <div className="p-8 max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <button
            onClick={() => navigate('/')}
            className="p-2 hover:bg-surface-800 rounded-lg transition-colors"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Archive className="w-6 h-6 text-brand-400" />
              {t('archive.pageTitle', 'Project Archive')}
            </h1>
            <p className="text-surface-400 mt-1">{t('archive.pageSubtitle', 'Export and import projects as portable archives')}</p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Export Section */}
          <div className="card">
            <div className="flex items-center gap-2 mb-4">
              <Download className="w-5 h-5 text-brand-400" />
              <h2 className="text-lg font-semibold">{t('archive.exportSectionTitle', 'Export Project')}</h2>
            </div>

            {/* Project Selection */}
            <div className="mb-4">
              <label className="block text-sm text-surface-400 mb-2">{t('archive.selectProjectLabel', 'Select Project')}</label>
              <select
                value={exportProjectId || ''}
                onChange={(e) => setExportProjectId(e.target.value || null)}
                className="w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2"
              >
                <option value="">{t('archive.chooseProjectOption', 'Choose a project...')}</option>
                {projects?.map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Project Info */}
            {selectedProject && (
              <div className="mb-4 p-3 bg-surface-800/50 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <Film className="w-4 h-4 text-surface-400" />
                  <span className="font-medium">{selectedProject.name}</span>
                </div>
                <div className="text-sm text-surface-400 space-y-1">
                  <p>{t('archive.stateLabel', 'State')}: {selectedProject.state}</p>
                  <p>{t('archive.scenesLabel', 'Scenes')}: {selectedProject.sceneCount || 0}</p>
                  <p>{t('archive.charactersLabel', 'Characters')}: {selectedProject.characterCount || 0}</p>
                </div>
              </div>
            )}

            {/* Export Options */}
            <div className="space-y-3 mb-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={includeAssets}
                  onChange={(e) => setIncludeAssets(e.target.checked)}
                  className="rounded border-surface-600 bg-surface-800"
                />
                <Image className="w-4 h-4 text-surface-400" />
                <span className="text-sm">{t('archive.includeCharacterImages', 'Include character reference images')}</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={includeOutputs}
                  onChange={(e) => setIncludeOutputs(e.target.checked)}
                  className="rounded border-surface-600 bg-surface-800"
                />
                <HardDrive className="w-4 h-4 text-surface-400" />
                <span className="text-sm">{t('archive.includeOutputFiles', 'Include output files')}</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={includeGeneratedVideos}
                  onChange={(e) => setIncludeGeneratedVideos(e.target.checked)}
                  className="rounded border-surface-600 bg-surface-800"
                />
                <Video className="w-4 h-4 text-surface-400" />
                <span className="text-sm">{t('archive.includeGeneratedVideos', 'Include generated videos (larger file)')}</span>
              </label>
            </div>

            <button
              onClick={() => exportMutation.mutate()}
              disabled={!exportProjectId || exportMutation.isPending}
              className="w-full btn-primary flex items-center justify-center gap-2"
            >
              {exportMutation.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Download className="w-4 h-4" />
              )}
              {t('archive.exportSectionTitle', 'Export Project')}
            </button>
          </div>

          {/* Import Section */}
          <div className="card">
            <div className="flex items-center gap-2 mb-4">
              <Upload className="w-5 h-5 text-brand-400" />
              <h2 className="text-lg font-semibold">{t('archive.importSectionTitle', 'Import Project')}</h2>
            </div>

            {!importFile ? (
              <button
                onClick={handleSelectImportFile}
                className="w-full p-8 border-2 border-dashed border-surface-700 rounded-lg hover:border-surface-600 hover:bg-surface-800/30 transition-colors"
              >
                <FolderOpen className="w-8 h-8 mx-auto mb-2 text-surface-400" />
                <p className="text-surface-400">{t('archive.clickToSelectArchive', 'Click to select archive file')}</p>
                <p className="text-sm text-surface-500 mt-1">{t('archive.smprojectFilesHint', '.smproject files')}</p>
              </button>
            ) : (
              <>
                {/* Archive Info */}
                <div className="mb-4 p-3 bg-surface-800/50 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <File className="w-4 h-4 text-brand-400" />
                    <span className="font-medium text-sm truncate">
                      {importFile.split('/').pop()}
                    </span>
                    <button
                      onClick={() => {
                        setImportFile(null);
                        setArchiveInfo(null);
                      }}
                      className="ml-auto p-1 hover:bg-surface-700 rounded"
                    >
                      <Trash2 className="w-4 h-4 text-surface-400" />
                    </button>
                  </div>

                  {archiveInfo && (
                    <div className="text-sm text-surface-400 space-y-1 mt-3">
                      <p>
                        <span className="text-surface-500">{t('archive.infoProjectLabel', 'Project:')}</span> {archiveInfo.projectName}
                      </p>
                      <p>
                        <span className="text-surface-500">{t('archive.infoExportedLabel', 'Exported:')}</span>{' '}
                        {formatDate(archiveInfo.exportedAt)}
                      </p>
                      <p>
                        <span className="text-surface-500">{t('archive.infoScenesLabel', 'Scenes:')}</span> {archiveInfo.sceneCount}
                      </p>
                      <p>
                        <span className="text-surface-500">{t('archive.infoCharactersLabel', 'Characters:')}</span>{' '}
                        {archiveInfo.characterCount}
                      </p>
                      <div className="flex gap-2 mt-2">
                        {archiveInfo.includesAssets && (
                          <span className="px-2 py-0.5 bg-blue-500/20 text-blue-400 text-xs rounded">
                            {t('archive.badgeAssets', 'Assets')}
                          </span>
                        )}
                        {archiveInfo.includesOutputs && (
                          <span className="px-2 py-0.5 bg-green-500/20 text-green-400 text-xs rounded">
                            {t('archive.badgeOutputs', 'Outputs')}
                          </span>
                        )}
                        {archiveInfo.includesGeneratedVideos && (
                          <span className="px-2 py-0.5 bg-purple-500/20 text-purple-400 text-xs rounded">
                            {t('archive.badgeVideos', 'Videos')}
                          </span>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {/* Import Options */}
                <div className="space-y-3 mb-4">
                  <div>
                    <label className="block text-sm text-surface-400 mb-1">
                      {t('archive.projectNameLabel', 'Project Name (optional)')}
                    </label>
                    <input
                      type="text"
                      value={newProjectName}
                      onChange={(e) => setNewProjectName(e.target.value)}
                      placeholder={t('archive.projectNamePlaceholder', 'Leave empty to use original name')}
                      className="w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2"
                    />
                  </div>

                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={importAssets}
                      onChange={(e) => setImportAssets(e.target.checked)}
                      className="rounded border-surface-600 bg-surface-800"
                    />
                    <span className="text-sm">{t('archive.importAssetsLabel', 'Import assets and media files')}</span>
                  </label>
                </div>

                <button
                  onClick={() => importMutation.mutate()}
                  disabled={importMutation.isPending}
                  className="w-full btn-primary flex items-center justify-center gap-2"
                >
                  {importMutation.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Upload className="w-4 h-4" />
                  )}
                  {t('archive.importSectionTitle', 'Import Project')}
                </button>
              </>
            )}
          </div>
        </div>

        {/* Recent Exports */}
        <div className="mt-8">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Clock className="w-5 h-5 text-surface-400" />
            {t('archive.recentExportsTitle', 'Recent Exports')}
          </h2>

          {exportsLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-surface-400" />
            </div>
          ) : exports && exports.length > 0 ? (
            <div className="space-y-2">
              {exports.map((archive, index) => (
                <div
                  key={index}
                  className="flex items-center gap-4 p-3 bg-surface-800/50 rounded-lg"
                >
                  <Archive className="w-8 h-8 text-brand-400" />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium truncate">{archive.projectName}</p>
                    <p className="text-sm text-surface-400">
                      {formatDate(archive.exportedAt)} &bull; {formatFileSize(archive.fileSize)}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => {
                        setImportFile(archive.path);
                        // Would need to get archive info here
                      }}
                      className="p-2 hover:bg-surface-700 rounded transition-colors"
                      title={t('archive.reimportTitle', 'Re-import this archive')}
                    >
                      <Upload className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-surface-400">
              <Archive className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p>{t('archive.noExportsYet', 'No exports yet')}</p>
              <p className="text-sm text-surface-500">{t('archive.noExportsHint', 'Export a project to see it here')}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
