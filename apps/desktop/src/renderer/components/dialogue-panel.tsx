/**
 * Dialogue panel for generating and managing character dialogue audio.
 * Allows TTS generation, preview, and sync with video timeline.
 */

import { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  MessageSquare,
  Play,
  Pause,
  Volume2,
  VolumeX,
  Loader2,
  RefreshCw,
  Download,
  Trash2,
  Clock,
  User,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  CheckCircle,
  Wand2,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { useToast } from './toast';

interface DialogueLine {
  id: string;
  characterId: string;
  characterName: string;
  text: string;
  sceneNumber: number;
  shotId?: string;
  audioUrl?: string;
  audioDuration?: number;
  generationStatus: 'pending' | 'generating' | 'completed' | 'failed';
  syncOffset?: number; // milliseconds offset for sync
}

interface DialoguePanelProps {
  projectId: string;
  sceneId?: string;
  shotId?: string;
  onDialogueGenerated?: (dialogueId: string, audioUrl: string) => void;
  onDialogueSync?: (dialogueId: string, offset: number) => void;
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  const ms = Math.floor((seconds % 1) * 10);
  return mins > 0 ? `${mins}:${secs.toString().padStart(2, '0')}.${ms}` : `${secs}.${ms}s`;
}

function DialogueLineItem({
  line,
  onGenerate,
  onPlay,
  onDelete,
  isPlaying,
  isGenerating,
}: {
  line: DialogueLine;
  onGenerate: () => void;
  onPlay: () => void;
  onDelete: () => void;
  isPlaying: boolean;
  isGenerating: boolean;
}) {
  const getStatusIcon = () => {
    switch (line.generationStatus) {
      case 'generating':
        return <Loader2 className="w-4 h-4 animate-spin text-blue-400" />;
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-400" />;
      case 'failed':
        return <AlertCircle className="w-4 h-4 text-red-400" />;
      default:
        return <Clock className="w-4 h-4 text-surface-500" />;
    }
  };

  return (
    <div className="bg-surface-800/50 rounded-lg p-3 border border-surface-700">
      {/* Header */}
      <div className="flex items-center gap-2 mb-2">
        <div className="w-6 h-6 rounded-full bg-brand-500/20 flex items-center justify-center text-xs font-bold text-brand-400">
          {line.characterName[0]}
        </div>
        <span className="font-medium text-sm">{line.characterName}</span>
        <span className="text-xs text-surface-500">Scene {line.sceneNumber}</span>
        <div className="ml-auto">{getStatusIcon()}</div>
      </div>

      {/* Dialogue text */}
      <p className="text-sm text-surface-300 mb-3 leading-relaxed">
        "{line.text}"
      </p>

      {/* Audio controls */}
      <div className="flex items-center gap-2">
        {line.audioUrl ? (
          <>
            <button
              onClick={onPlay}
              className={cn(
                'p-2 rounded-lg transition-colors',
                isPlaying
                  ? 'bg-brand-500 text-white'
                  : 'bg-surface-700 hover:bg-surface-600'
              )}
            >
              {isPlaying ? (
                <Pause className="w-4 h-4" />
              ) : (
                <Play className="w-4 h-4" />
              )}
            </button>
            {line.audioDuration && (
              <span className="text-xs text-surface-400">
                {formatDuration(line.audioDuration)}
              </span>
            )}
            <div className="flex-1" />
            <button
              onClick={onGenerate}
              disabled={isGenerating}
              className="p-2 text-surface-400 hover:text-surface-200 hover:bg-surface-700 rounded transition-colors disabled:opacity-50"
              title="Regenerate"
            >
              <RefreshCw className={cn('w-4 h-4', isGenerating && 'animate-spin')} />
            </button>
            <button
              onClick={onDelete}
              className="p-2 text-surface-400 hover:text-red-400 hover:bg-surface-700 rounded transition-colors"
              title="Delete audio"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </>
        ) : (
          <button
            onClick={onGenerate}
            disabled={isGenerating}
            className="btn-secondary text-sm flex items-center gap-2"
          >
            {isGenerating ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Wand2 className="w-4 h-4" />
            )}
            Generate Audio
          </button>
        )}
      </div>
    </div>
  );
}

export function DialoguePanel({
  projectId,
  sceneId,
  shotId,
  onDialogueGenerated,
  onDialogueSync,
}: DialoguePanelProps) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const audioRef = useRef<HTMLAudioElement>(null);

  const [isExpanded, setIsExpanded] = useState(true);
  const [playingId, setPlayingId] = useState<string | null>(null);
  const [generatingIds, setGeneratingIds] = useState<Set<string>>(new Set());
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);

  // Fetch dialogue lines
  const { data: dialogueLines, isLoading } = useQuery({
    queryKey: ['dialogue', projectId, sceneId, shotId],
    queryFn: async () => {
      const params: Record<string, string> = { project_id: projectId };
      if (sceneId) params.scene_id = sceneId;
      if (shotId) params.shot_id = shotId;

      return window.electronAPI.backendRequest<DialogueLine[]>(
        'audio.getDialogueLines',
        params
      );
    },
    enabled: !!projectId,
  });

  // Generate dialogue mutation
  const generateMutation = useMutation({
    mutationFn: async (dialogueId: string) => {
      setGeneratingIds((prev) => new Set(prev).add(dialogueId));

      const result = await window.electronAPI.backendRequest<{
        audioUrl: string;
        duration: number;
      }>('audio.generateDialogue', {
        dialogue_id: dialogueId,
      });

      return { dialogueId, ...result };
    },
    onSuccess: (result) => {
      setGeneratingIds((prev) => {
        const next = new Set(prev);
        next.delete(result.dialogueId);
        return next;
      });

      queryClient.invalidateQueries({ queryKey: ['dialogue', projectId] });
      onDialogueGenerated?.(result.dialogueId, result.audioUrl);
      showToast('Dialogue audio generated', 'success');
    },
    onError: (error: any, dialogueId) => {
      setGeneratingIds((prev) => {
        const next = new Set(prev);
        next.delete(dialogueId);
        return next;
      });
      showToast(`Generation failed: ${error.message}`, 'error');
    },
  });

  // Generate all mutation
  const generateAllMutation = useMutation({
    mutationFn: async () => {
      const pending = dialogueLines?.filter(
        (d) => d.generationStatus === 'pending' || d.generationStatus === 'failed'
      ) || [];

      for (const line of pending) {
        setGeneratingIds((prev) => new Set(prev).add(line.id));
        try {
          await window.electronAPI.backendRequest('audio.generateDialogue', {
            dialogue_id: line.id,
          });
        } catch (error) {
          console.error(`Failed to generate dialogue ${line.id}:`, error);
        }
        setGeneratingIds((prev) => {
          const next = new Set(prev);
          next.delete(line.id);
          return next;
        });
      }

      return pending.length;
    },
    onSuccess: (count) => {
      queryClient.invalidateQueries({ queryKey: ['dialogue', projectId] });
      showToast(`Generated ${count} dialogue clips`, 'success');
    },
  });

  // Delete audio mutation
  const deleteMutation = useMutation({
    mutationFn: async (dialogueId: string) => {
      return window.electronAPI.backendRequest('audio.deleteDialogueAudio', {
        dialogue_id: dialogueId,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dialogue', projectId] });
      showToast('Audio deleted', 'success');
    },
  });

  // Handle audio playback
  const handlePlay = (line: DialogueLine) => {
    if (!audioRef.current || !line.audioUrl) return;

    if (playingId === line.id) {
      audioRef.current.pause();
      setPlayingId(null);
    } else {
      audioRef.current.src = line.audioUrl;
      audioRef.current.volume = isMuted ? 0 : volume;
      audioRef.current.play();
      setPlayingId(line.id);
    }
  };

  // Handle audio ended
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleEnded = () => setPlayingId(null);
    audio.addEventListener('ended', handleEnded);
    return () => audio.removeEventListener('ended', handleEnded);
  }, []);

  // Update volume
  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = isMuted ? 0 : volume;
    }
  }, [volume, isMuted]);

  const pendingCount = dialogueLines?.filter(
    (d) => d.generationStatus === 'pending' || d.generationStatus === 'failed'
  ).length ?? 0;
  const completedCount = dialogueLines?.filter(
    (d) => d.generationStatus === 'completed'
  ).length ?? 0;

  return (
    <div className="bg-surface-900 border border-surface-800 rounded-xl overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-surface-800/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <MessageSquare className="w-5 h-5 text-brand-400" />
          <span className="font-medium">Dialogue</span>
          <span className="text-sm text-surface-400">
            {completedCount}/{dialogueLines?.length ?? 0} generated
          </span>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-5 h-5 text-surface-400" />
        ) : (
          <ChevronDown className="w-5 h-5 text-surface-400" />
        )}
      </button>

      {isExpanded && (
        <div className="p-4 pt-0">
          {/* Controls */}
          <div className="flex items-center gap-3 mb-4">
            {/* Volume */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => setIsMuted(!isMuted)}
                className="icon-btn p-2 text-surface-400 hover:text-surface-200 transition-colors rounded"
                aria-label={isMuted ? 'Unmute dialogue' : 'Mute dialogue'}
              >
                {isMuted ? (
                  <VolumeX className="w-4 h-4" />
                ) : (
                  <Volume2 className="w-4 h-4" />
                )}
              </button>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={volume}
                onChange={(e) => setVolume(parseFloat(e.target.value))}
                className="w-20 accent-brand-500"
              />
            </div>

            <div className="flex-1" />

            {/* Generate all button */}
            {pendingCount > 0 && (
              <button
                onClick={() => generateAllMutation.mutate()}
                disabled={generateAllMutation.isPending}
                className="btn-primary text-sm"
              >
                {generateAllMutation.isPending ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Wand2 className="w-4 h-4 mr-2" />
                )}
                Generate All ({pendingCount})
              </button>
            )}
          </div>

          {/* Dialogue list */}
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-surface-400" />
            </div>
          ) : dialogueLines && dialogueLines.length > 0 ? (
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {dialogueLines.map((line) => (
                <DialogueLineItem
                  key={line.id}
                  line={line}
                  onGenerate={() => generateMutation.mutate(line.id)}
                  onPlay={() => handlePlay(line)}
                  onDelete={() => deleteMutation.mutate(line.id)}
                  isPlaying={playingId === line.id}
                  isGenerating={generatingIds.has(line.id)}
                />
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-surface-400">
              <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>No dialogue lines found</p>
              <p className="text-sm text-surface-500 mt-1">
                Dialogue will appear here once a screenplay is parsed
              </p>
            </div>
          )}
        </div>
      )}

      {/* Hidden audio element */}
      <audio ref={audioRef} className="hidden" />
    </div>
  );
}

/**
 * Compact dialogue indicator for shot cards.
 */
export function DialogueIndicator({
  dialogueCount,
  generatedCount,
}: {
  dialogueCount: number;
  generatedCount: number;
}) {
  if (dialogueCount === 0) return null;

  const isComplete = generatedCount === dialogueCount;

  return (
    <div
      className={cn(
        'flex items-center gap-1 px-2 py-0.5 rounded text-xs',
        isComplete
          ? 'bg-green-500/20 text-green-400'
          : 'bg-surface-700 text-surface-400'
      )}
    >
      <MessageSquare className="w-3 h-3" />
      <span>
        {generatedCount}/{dialogueCount}
      </span>
    </div>
  );
}
