/**
 * GenerateDialogueButton Component
 * Button to generate TTS audio for shot dialogue
 */

import React from 'react';
import { Volume2, Loader2 } from 'lucide-react';
import { useAudioStore } from '../../stores/audio-store';
import { useToast } from '../../stores/toast-store';

interface Shot {
  id: string;
  shotNumber: string;
  dialogue?: string | null;
}

interface GenerateDialogueButtonProps {
  /** Single shot for individual generation */
  shot?: Shot;
  /** Multiple shots for batch generation */
  shots?: Shot[];
  /** Character ID for voice selection */
  characterId?: string;
  /** Callback when generation completes */
  onComplete?: (shotId: string, audioPath: string) => void;
  /** Additional CSS classes */
  className?: string;
  /** Compact mode for shot cards */
  compact?: boolean;
}

export const GenerateDialogueButton: React.FC<GenerateDialogueButtonProps> = ({
  shot,
  shots,
  characterId: _characterId,
  onComplete,
  className = '',
  compact = false,
}) => {
  const { generateSpeech, fetchProviders, fetchVoices, voices, isGenerating, error } =
    useAudioStore();
  const toast = useToast();

  const [localGenerating, setLocalGenerating] = React.useState(false);
  const [progress, setProgress] = React.useState({ current: 0, total: 0 });

  // Determine shots to process
  const targetShots = shots || (shot ? [shot] : []);
  const shotsWithDialogue = targetShots.filter((s) => s.dialogue && s.dialogue.trim().length > 0);

  // Fetch providers and voices on mount
  React.useEffect(() => {
    const init = async () => {
      try {
        await fetchProviders();
        await fetchVoices();
      } catch (err) {
        console.error('Failed to initialize audio settings:', err);
      }
    };
    init();
  }, [fetchProviders, fetchVoices]);

  const handleGenerate = async () => {
    if (shotsWithDialogue.length === 0) {
      toast.warning('No Dialogue', 'No shots have dialogue to generate.');
      return;
    }

    setLocalGenerating(true);
    setProgress({ current: 0, total: shotsWithDialogue.length });

    const defaultVoice = voices[0]?.id || 'default';
    let successCount = 0;
    let failCount = 0;

    for (let i = 0; i < shotsWithDialogue.length; i++) {
      const currentShot = shotsWithDialogue[i];
      setProgress({ current: i + 1, total: shotsWithDialogue.length });

      try {
        const result = await generateSpeech(currentShot.dialogue!, defaultVoice);

        if (result?.audio_path && onComplete) {
          onComplete(currentShot.id, result.audio_path);
        }
        successCount++;
      } catch (err: any) {
        console.error(`Failed to generate dialogue for shot ${currentShot.shotNumber}:`, err);
        failCount++;
      }
    }

    setLocalGenerating(false);
    setProgress({ current: 0, total: 0 });

    // Show result toast
    if (failCount === 0) {
      toast.success(
        'Dialogue Generated',
        `Successfully generated ${successCount} audio ${successCount === 1 ? 'clip' : 'clips'}.`
      );
    } else if (successCount > 0) {
      toast.warning(
        'Partial Success',
        `Generated ${successCount} of ${shotsWithDialogue.length} clips. ${failCount} failed.`
      );
    } else {
      toast.error('Generation Failed', 'Failed to generate dialogue audio.');
    }
  };

  const isProcessing = localGenerating || isGenerating;
  const hasDialogue = shotsWithDialogue.length > 0;
  const isBatch = shotsWithDialogue.length > 1;

  // Progress text
  const progressText =
    progress.total > 0
      ? `${progress.current}/${progress.total}`
      : isBatch
        ? `${shotsWithDialogue.length} shots`
        : '';

  if (compact) {
    return (
      <button
        onClick={handleGenerate}
        disabled={isProcessing || !hasDialogue}
        className={`p-2 rounded transition-colors flex items-center justify-center ${
          isProcessing
            ? 'bg-blue-500/20 text-blue-400 cursor-wait'
            : hasDialogue
              ? 'bg-purple-500/10 text-purple-400 hover:bg-purple-500/20'
              : 'bg-gray-500/10 text-gray-500 cursor-not-allowed'
        } ${className}`}
        title={
          !hasDialogue
            ? 'No dialogue to generate'
            : isProcessing
              ? `Generating... ${progressText}`
              : 'Generate dialogue audio'
        }
        aria-label="Generate dialogue audio"
      >
        {isProcessing ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : (
          <Volume2 className="w-4 h-4" />
        )}
      </button>
    );
  }

  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      <button
        onClick={handleGenerate}
        disabled={isProcessing || !hasDialogue}
        className={`px-4 py-2 rounded-lg font-medium text-sm transition-colors flex items-center gap-2 ${
          isProcessing
            ? 'bg-blue-500 text-white cursor-wait'
            : hasDialogue
              ? 'bg-purple-600 hover:bg-purple-700 text-white'
              : 'bg-gray-300 text-gray-500 cursor-not-allowed'
        }`}
        aria-label={
          isProcessing ? `Generating dialogue ${progressText}` : 'Generate dialogue audio'
        }
      >
        {isProcessing ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            Generating... {progressText}
          </>
        ) : (
          <>
            <Volume2 className="w-4 h-4" />
            Generate Dialogue {isBatch && `(${shotsWithDialogue.length})`}
          </>
        )}
      </button>

      {error && (
        <div
          className="text-xs text-red-600 px-2 py-1 bg-red-50 rounded border border-red-200"
          role="alert"
        >
          {error}
        </div>
      )}

      {!hasDialogue && !compact && (
        <div className="text-xs text-gray-500 mt-1">No shots have dialogue text to generate.</div>
      )}
    </div>
  );
};
