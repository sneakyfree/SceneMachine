/**
 * Screenplay file upload component with drag-and-drop support.
 */

import { useState, useCallback, useRef, DragEvent } from 'react';

interface ScreenplayUploadProps {
  projectId: string;
  onUploadComplete: (screenplay: ScreenplayResult) => void;
  onError?: (error: string) => void;
  disabled?: boolean;
}

interface ScreenplayResult {
  id: string;
  projectId: string;
  originalFilename: string;
  originalFormat: string;
  isParsed: boolean;
  createdAt: string;
}

type UploadState = 'idle' | 'dragging' | 'uploading' | 'parsing' | 'success' | 'error';

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

export function ScreenplayUpload({
  projectId,
  onUploadComplete,
  onError,
  disabled = false,
}: ScreenplayUploadProps) {
  const [state, setState] = useState<UploadState>('idle');
  const [progress, setProgress] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string>('');
  const inputRef = useRef<HTMLInputElement>(null);

  const validateFile = (filename: string): boolean => {
    const ext = filename.toLowerCase().slice(filename.lastIndexOf('.'));
    return SUPPORTED_EXTENSIONS.includes(ext);
  };

  const uploadAndParse = useCallback(
    async (filePath: string, filename: string) => {
      try {
        setState('uploading');
        setProgress('Uploading screenplay...');

        // Upload the file
        const uploadResult = await window.electronAPI.backendRequest<ScreenplayResult>(
          'screenplays.upload',
          {
            project_id: projectId,
            file_path: filePath,
            filename: filename,
          }
        );

        setState('parsing');
        setProgress('Parsing screenplay...');

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

        if (parseResult.parseErrors && parseResult.parseErrors.length > 0) {
          throw new Error(parseResult.parseErrors.join(', '));
        }

        setState('success');
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
        }, 3000);
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Upload failed';
        setState('error');
        setErrorMessage(message);
        onError?.(message);

        // Reset state after a delay
        setTimeout(() => {
          setState('idle');
          setErrorMessage('');
        }, 5000);
      }
    },
    [projectId, onUploadComplete, onError]
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
        return 'border-blue-500 bg-blue-500/10';
      case 'success':
        return 'border-green-500 bg-green-500/10';
      case 'error':
        return 'border-red-500 bg-red-500/10';
      default:
        return 'border-surface-700 hover:border-surface-600';
    }
  };

  return (
    <div
      className={`
        relative rounded-lg border-2 border-dashed p-8
        transition-colors duration-200 cursor-pointer
        ${getStateStyles()}
        ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
      `}
      onClick={handleFileSelect}
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

      <div className="flex flex-col items-center gap-4 text-center">
        {/* Icon */}
        <div className="w-16 h-16 rounded-full bg-surface-800 flex items-center justify-center">
          {state === 'uploading' || state === 'parsing' ? (
            <svg
              className="w-8 h-8 text-blue-500 animate-spin"
              viewBox="0 0 24 24"
              fill="none"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
          ) : state === 'success' ? (
            <svg className="w-8 h-8 text-green-500" viewBox="0 0 24 24" fill="none">
              <path
                d="M5 13l4 4L19 7"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          ) : state === 'error' ? (
            <svg className="w-8 h-8 text-red-500" viewBox="0 0 24 24" fill="none">
              <path
                d="M6 18L18 6M6 6l12 12"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          ) : (
            <svg className="w-8 h-8 text-surface-400" viewBox="0 0 24 24" fill="none">
              <path
                d="M7 16V4m0 0L3 8m4-4l4 4M17 8v12m0 0l4-4m-4 4l-4-4"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
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

          {(state === 'uploading' || state === 'parsing') && (
            <p className="text-blue-400 font-medium">{progress}</p>
          )}

          {state === 'success' && (
            <p className="text-green-400 font-medium">{progress}</p>
          )}

          {state === 'error' && (
            <p className="text-red-400 font-medium">{errorMessage}</p>
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
      </div>
    </div>
  );
}
