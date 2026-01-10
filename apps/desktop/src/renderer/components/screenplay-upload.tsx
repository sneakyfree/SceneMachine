/**
 * Screenplay file upload component with drag-and-drop support.
 *
 * Features progress indicators for:
 * - File upload (bytes sent)
 * - Parsing (screenplay structure)
 * - LLM analysis (AI enhancement)
 */

import { useState, useCallback, useRef, useEffect, DragEvent } from 'react';
import { Upload, FileText, CheckCircle, AlertCircle, Brain, Sparkles } from 'lucide-react';
import { cn } from '../lib/utils';

interface ScreenplayUploadProps {
  projectId: string;
  onUploadComplete: (screenplay: ScreenplayResult) => void;
  onError?: (error: string) => void;
  disabled?: boolean;
  /**
   * Whether to perform LLM analysis after parsing
   */
  enableAiAnalysis?: boolean;
}

interface ScreenplayResult {
  id: string;
  projectId: string;
  originalFilename: string;
  originalFormat: string;
  isParsed: boolean;
  createdAt: string;
}

type UploadState = 'idle' | 'dragging' | 'uploading' | 'parsing' | 'analyzing' | 'success' | 'error';

interface ProgressPhase {
  id: UploadState;
  label: string;
  description: string;
  estimatedSeconds: number;
}

const PROGRESS_PHASES: ProgressPhase[] = [
  { id: 'uploading', label: 'Uploading', description: 'Sending file to server...', estimatedSeconds: 5 },
  { id: 'parsing', label: 'Parsing', description: 'Extracting screenplay structure...', estimatedSeconds: 10 },
  { id: 'analyzing', label: 'AI Analysis', description: 'Analyzing with AI...', estimatedSeconds: 30 },
];

const SUPPORTED_EXTENSIONS = ['.fountain', '.spmd', '.pdf', '.fdx', '.txt'];
const FILE_FILTERS = [
  {
    name: 'Screenplay Files',
    extensions: ['fountain', 'spmd', 'pdf', 'fdx', 'txt'],
  },
  {
    name: 'Fountain',
    extensions: ['fountain', 'spmd'],
  },
  {
    name: 'PDF',
    extensions: ['pdf'],
  },
  {
    name: 'Final Draft',
    extensions: ['fdx'],
  },
];

/**
 * Progress bar component for upload phases
 */
function UploadProgressBar({
  percentage,
  phase,
  phases,
  elapsedSeconds,
  className,
}: {
  percentage: number;
  phase: UploadState;
  phases: ProgressPhase[];
  elapsedSeconds: number;
  className?: string;
}) {
  const currentPhaseIndex = phases.findIndex((p) => p.id === phase);
  const currentPhase = phases[currentPhaseIndex];

  // Calculate ETA based on current phase
  const getEta = () => {
    if (!currentPhase || percentage >= 100) return null;

    const remainingPercentage = 100 - percentage;
    const elapsedForPhase = elapsedSeconds;
    const estimatedTotal = currentPhase.estimatedSeconds;

    // Use actual elapsed time if available, otherwise estimate
    if (elapsedForPhase > 0 && percentage > 0) {
      const rate = percentage / elapsedForPhase;
      const remaining = remainingPercentage / rate;
      return Math.max(1, Math.ceil(remaining));
    }

    return Math.ceil((remainingPercentage / 100) * estimatedTotal);
  };

  const eta = getEta();

  return (
    <div className={cn('w-full', className)}>
      {/* Phase steps */}
      <div className="flex items-center justify-between mb-3">
        {phases.map((p, index) => {
          const isActive = p.id === phase;
          const isCompleted = currentPhaseIndex > index;

          return (
            <div key={p.id} className="flex items-center">
              {/* Step indicator */}
              <div
                className={cn(
                  'w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors',
                  isCompleted
                    ? 'bg-green-500 text-white'
                    : isActive
                    ? 'bg-primary-500 text-white'
                    : 'bg-surface-700 text-surface-400'
                )}
              >
                {isCompleted ? (
                  <CheckCircle className="w-4 h-4" />
                ) : p.id === 'uploading' ? (
                  <Upload className="w-4 h-4" />
                ) : p.id === 'parsing' ? (
                  <FileText className="w-4 h-4" />
                ) : (
                  <Brain className="w-4 h-4" />
                )}
              </div>

              {/* Connector line */}
              {index < phases.length - 1 && (
                <div
                  className={cn(
                    'w-12 h-0.5 mx-2 transition-colors',
                    isCompleted ? 'bg-green-500' : 'bg-surface-700'
                  )}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Phase labels */}
      <div className="flex justify-between text-xs mb-3">
        {phases.map((p, index) => {
          const isActive = p.id === phase;
          const isCompleted = currentPhaseIndex > index;

          return (
            <span
              key={p.id}
              className={cn(
                'transition-colors',
                isCompleted
                  ? 'text-green-400'
                  : isActive
                  ? 'text-primary-400'
                  : 'text-surface-500'
              )}
            >
              {p.label}
            </span>
          );
        })}
      </div>

      {/* Progress bar */}
      <div className="h-2 bg-surface-700 rounded-full overflow-hidden">
        <div
          className="h-full bg-primary-500 transition-all duration-300 ease-out"
          style={{ width: `${percentage}%` }}
        />
      </div>

      {/* Progress details */}
      <div className="flex justify-between items-center mt-2 text-xs">
        <span className="text-surface-400">
          {currentPhase?.description || 'Processing...'}
        </span>
        <div className="flex items-center gap-2">
          {eta !== null && (
            <span className="text-surface-500">
              ~{eta}s remaining
            </span>
          )}
          <span className="text-surface-300 font-medium">{percentage.toFixed(0)}%</span>
        </div>
      </div>
    </div>
  );
}

export function ScreenplayUpload({
  projectId,
  onUploadComplete,
  onError,
  disabled = false,
  enableAiAnalysis = true,
}: ScreenplayUploadProps) {
  const [state, setState] = useState<UploadState>('idle');
  const [progress, setProgress] = useState<string>('');
  const [percentage, setPercentage] = useState<number>(0);
  const [phaseStartTime, setPhaseStartTime] = useState<number>(0);
  const [elapsedSeconds, setElapsedSeconds] = useState<number>(0);
  const [errorMessage, setErrorMessage] = useState<string>('');
  const inputRef = useRef<HTMLInputElement>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  // Update elapsed time during active phases
  useEffect(() => {
    if (state === 'uploading' || state === 'parsing' || state === 'analyzing') {
      timerRef.current = setInterval(() => {
        setElapsedSeconds(Math.floor((Date.now() - phaseStartTime) / 1000));
      }, 1000);

      return () => {
        if (timerRef.current) {
          clearInterval(timerRef.current);
        }
      };
    }
  }, [state, phaseStartTime]);

  // Get phases based on enableAiAnalysis
  const activePhases = enableAiAnalysis
    ? PROGRESS_PHASES
    : PROGRESS_PHASES.filter((p) => p.id !== 'analyzing');

  const validateFile = (filename: string): boolean => {
    const ext = filename.toLowerCase().slice(filename.lastIndexOf('.'));
    return SUPPORTED_EXTENSIONS.includes(ext);
  };

  const startPhase = (phase: UploadState) => {
    setState(phase);
    setPhaseStartTime(Date.now());
    setElapsedSeconds(0);
    setPercentage(0);
  };

  const uploadAndParse = useCallback(
    async (filePath: string, filename: string) => {
      try {
        // Phase 1: Uploading
        startPhase('uploading');
        setProgress('Uploading screenplay...');

        // Simulate upload progress (in real implementation, use XHR with progress events)
        const uploadProgressInterval = setInterval(() => {
          setPercentage((prev) => Math.min(prev + 10, 90));
        }, 200);

        // Upload the file
        const uploadResult = await window.electronAPI.backendRequest<ScreenplayResult>(
          'screenplays.upload',
          {
            project_id: projectId,
            file_path: filePath,
            filename: filename,
          }
        );

        clearInterval(uploadProgressInterval);
        setPercentage(100);

        // Phase 2: Parsing
        startPhase('parsing');
        setProgress('Parsing screenplay structure...');

        // Simulate parsing progress
        const parseProgressInterval = setInterval(() => {
          setPercentage((prev) => Math.min(prev + 5, 90));
        }, 300);

        // Parse the file
        const parseResult = await window.electronAPI.backendRequest<{
          id: string;
          isParsed: boolean;
          parseErrors: string[] | null;
          metadata: {
            scene_count?: number;
            character_count?: number;
            element_count?: number;
          };
        }>('screenplays.parse', {
          screenplay_id: uploadResult.id,
        });

        clearInterval(parseProgressInterval);
        setPercentage(100);

        if (parseResult.parseErrors && parseResult.parseErrors.length > 0) {
          throw new Error(parseResult.parseErrors.join(', '));
        }

        // Phase 3: AI Analysis (optional)
        if (enableAiAnalysis) {
          startPhase('analyzing');
          setProgress('Analyzing with AI...');

          // Simulate AI analysis progress
          const analyzeProgressInterval = setInterval(() => {
            setPercentage((prev) => Math.min(prev + 2, 95));
          }, 500);

          // Perform AI analysis
          try {
            await window.electronAPI.backendRequest<{
              suggestions: Array<{ type: string; content: string }>;
              analysis: {
                themes?: string[];
                tone?: string;
                pacing?: string;
              };
            }>('screenplays.analyze', {
              screenplay_id: uploadResult.id,
            });
          } catch (analysisError) {
            // AI analysis is optional, continue even if it fails
            console.warn('AI analysis failed:', analysisError);
          }

          clearInterval(analyzeProgressInterval);
          setPercentage(100);
        }

        // Success
        setState('success');
        setPercentage(100);
        setProgress(
          `Parsed ${parseResult.metadata.scene_count || 0} scenes, ` +
            `${parseResult.metadata.character_count || 0} characters`
        );

        // Get full screenplay data
        const screenplay = await window.electronAPI.backendRequest<ScreenplayResult>(
          'screenplays.get',
          { screenplay_id: uploadResult.id }
        );

        onUploadComplete(screenplay);

        // Reset state after a delay
        setTimeout(() => {
          setState('idle');
          setProgress('');
          setPercentage(0);
        }, 3000);
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Upload failed';
        setState('error');
        setErrorMessage(message);
        setPercentage(0);
        onError?.(message);

        // Reset state after a delay
        setTimeout(() => {
          setState('idle');
          setErrorMessage('');
          setPercentage(0);
        }, 5000);
      }
    },
    [projectId, onUploadComplete, onError, enableAiAnalysis]
  );

  const handleFileSelect = useCallback(async () => {
    if (disabled || state !== 'idle') return;

    try {
      const result = await window.electronAPI.openFile({
        title: 'Select Screenplay',
        filters: FILE_FILTERS,
        properties: ['openFile'],
      });

      if (result.canceled || result.filePaths.length === 0) {
        return;
      }

      const filePath = result.filePaths[0];
      const filename = filePath.split(/[\\/]/).pop() || 'screenplay';

      if (!validateFile(filename)) {
        setState('error');
        setErrorMessage(`Unsupported file format. Supported: ${SUPPORTED_EXTENSIONS.join(', ')}`);
        return;
      }

      await uploadAndParse(filePath, filename);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to select file';
      setState('error');
      setErrorMessage(message);
    }
  }, [disabled, state, uploadAndParse]);

  const handleDragOver = useCallback(
    (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      if (!disabled && state === 'idle') {
        setState('dragging');
      }
    },
    [disabled, state]
  );

  const handleDragLeave = useCallback(
    (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      if (state === 'dragging') {
        setState('idle');
      }
    },
    [state]
  );

  const handleDrop = useCallback(
    async (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();

      if (disabled) {
        setState('idle');
        return;
      }

      // Note: In Electron with sandbox, we may need to handle this differently
      // The dropped file path needs to be passed to the backend
      const files = e.dataTransfer.files;

      if (files.length === 0) {
        setState('idle');
        return;
      }

      const file = files[0];
      const filename = file.name;

      if (!validateFile(filename)) {
        setState('error');
        setErrorMessage(`Unsupported file format. Supported: ${SUPPORTED_EXTENSIONS.join(', ')}`);
        setTimeout(() => {
          setState('idle');
          setErrorMessage('');
        }, 3000);
        return;
      }

      // For dropped files, we can use the file's path property (if available in Electron)
      // If path is not available, we'll fall back to file dialog
      const filePath = (file as File & { path?: string }).path;

      if (!filePath) {
        // Fallback: ask user to use file dialog
        setState('error');
        setErrorMessage('Drag and drop not fully supported. Please use the file browser.');
        setTimeout(() => {
          setState('idle');
          setErrorMessage('');
        }, 3000);
        return;
      }

      await uploadAndParse(filePath, filename);
    },
    [disabled, uploadAndParse]
  );

  const getStateStyles = () => {
    switch (state) {
      case 'dragging':
        return 'border-primary-500 bg-primary-500/10';
      case 'uploading':
      case 'parsing':
      case 'analyzing':
        return 'border-blue-500 bg-blue-500/10';
      case 'success':
        return 'border-green-500 bg-green-500/10';
      case 'error':
        return 'border-red-500 bg-red-500/10';
      default:
        return 'border-surface-700 hover:border-surface-600';
    }
  };

  const isProcessing = state === 'uploading' || state === 'parsing' || state === 'analyzing';

  return (
    <div
      className={cn(
        'relative rounded-lg border-2 border-dashed p-8 transition-colors duration-200',
        getStateStyles(),
        disabled ? 'opacity-50 cursor-not-allowed' : isProcessing ? 'cursor-wait' : 'cursor-pointer'
      )}
      onClick={isProcessing ? undefined : handleFileSelect}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <input
        ref={inputRef}
        type="file"
        accept={SUPPORTED_EXTENSIONS.join(',')}
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) {
            const filePath = (file as File & { path?: string }).path;
            if (filePath) {
              uploadAndParse(filePath, file.name);
            }
          }
        }}
      />

      {/* Show progress bar when processing */}
      {isProcessing ? (
        <div className="flex flex-col items-center gap-6">
          {/* Animated icon */}
          <div className="w-16 h-16 rounded-full bg-surface-800 flex items-center justify-center">
            {state === 'uploading' ? (
              <Upload className="w-8 h-8 text-blue-500 animate-bounce" />
            ) : state === 'parsing' ? (
              <FileText className="w-8 h-8 text-blue-500 animate-pulse" />
            ) : (
              <div className="relative">
                <Brain className="w-8 h-8 text-purple-500 animate-pulse" />
                <Sparkles className="w-4 h-4 text-yellow-400 absolute -top-1 -right-1 animate-ping" />
              </div>
            )}
          </div>

          {/* Progress bar */}
          <UploadProgressBar
            percentage={percentage}
            phase={state}
            phases={activePhases}
            elapsedSeconds={elapsedSeconds}
            className="w-full max-w-md"
          />
        </div>
      ) : (
        <div className="flex flex-col items-center gap-4 text-center">
          {/* Icon */}
          <div className="w-16 h-16 rounded-full bg-surface-800 flex items-center justify-center">
            {state === 'success' ? (
              <CheckCircle className="w-8 h-8 text-green-500" />
            ) : state === 'error' ? (
              <AlertCircle className="w-8 h-8 text-red-500" />
            ) : (
              <Upload className="w-8 h-8 text-surface-400" />
            )}
          </div>

          {/* Text */}
          <div>
            {state === 'idle' && (
              <>
                <p className="text-surface-200 font-medium">
                  Drop screenplay here or click to browse
                </p>
                <p className="text-surface-500 text-sm mt-1">
                  Supports Fountain, PDF, Final Draft, and plain text
                </p>
              </>
            )}

            {state === 'dragging' && (
              <p className="text-primary-400 font-medium">Drop screenplay to upload</p>
            )}

            {state === 'success' && (
              <div className="flex items-center gap-2 justify-center">
                <CheckCircle className="w-5 h-5 text-green-400" />
                <p className="text-green-400 font-medium">{progress}</p>
              </div>
            )}

            {state === 'error' && (
              <div className="flex items-center gap-2 justify-center">
                <AlertCircle className="w-5 h-5 text-red-400" />
                <p className="text-red-400 font-medium">{errorMessage}</p>
              </div>
            )}
          </div>

          {/* Format badges */}
          {state === 'idle' && (
            <div className="flex gap-2 flex-wrap justify-center">
              {['.fountain', '.pdf', '.fdx', '.txt'].map((ext) => (
                <span
                  key={ext}
                  className="px-2 py-0.5 bg-surface-800 rounded text-xs text-surface-400"
                >
                  {ext}
                </span>
              ))}
            </div>
          )}

          {/* AI analysis badge */}
          {state === 'idle' && enableAiAnalysis && (
            <div className="flex items-center gap-1.5 px-2 py-1 bg-purple-500/10 rounded-full text-xs text-purple-400">
              <Sparkles className="w-3 h-3" />
              <span>AI analysis enabled</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
