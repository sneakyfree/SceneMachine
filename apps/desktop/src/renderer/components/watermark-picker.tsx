/**
 * Watermark picker component for selecting and uploading watermarks.
 */

import React, { useCallback, useRef, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Check, Image, Loader2, Plus, Trash2, Upload, X, AlertTriangle } from 'lucide-react';
import { api, type WatermarkInfo } from '../api/client';
import { cn } from '../lib/utils';
import { useToast } from '../stores/toast-store';

// Position options for watermark placement
const POSITION_OPTIONS = [
  { value: 'top_left', label: 'Top Left' },
  { value: 'top_center', label: 'Top Center' },
  { value: 'top_right', label: 'Top Right' },
  { value: 'center_left', label: 'Center Left' },
  { value: 'center', label: 'Center' },
  { value: 'center_right', label: 'Center Right' },
  { value: 'bottom_left', label: 'Bottom Left' },
  { value: 'bottom_center', label: 'Bottom Center' },
  { value: 'bottom_right', label: 'Bottom Right' },
];

interface WatermarkPickerProps {
  /** Currently selected watermark path */
  selectedPath: string | null;
  /** Current position setting */
  position: string;
  /** Current opacity (0-1) */
  opacity: number;
  /** Whether watermark is enabled */
  enabled: boolean;
  /** Called when watermark selection changes */
  onSelect: (path: string | null) => void;
  /** Called when position changes */
  onPositionChange: (position: string) => void;
  /** Called when opacity changes */
  onOpacityChange: (opacity: number) => void;
  /** Called when enabled state changes */
  onEnabledChange: (enabled: boolean) => void;
}

/**
 * Format file size in human readable format.
 */
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * Watermark thumbnail with selection state.
 */
function WatermarkThumbnail({
  watermark,
  selected,
  onSelect,
  onDelete,
  isDeleting,
}: {
  watermark: WatermarkInfo;
  selected: boolean;
  onSelect: () => void;
  onDelete?: () => void;
  isDeleting?: boolean;
}) {
  return (
    <div
      className={cn(
        'relative group rounded-lg border-2 p-2 cursor-pointer transition-all',
        selected
          ? 'border-brand-500 bg-brand-500/10'
          : 'border-surface-700 hover:border-surface-500 bg-surface-800/50'
      )}
      onClick={onSelect}
    >
      {/* Thumbnail */}
      <div className="aspect-video bg-surface-900 rounded overflow-hidden flex items-center justify-center">
        <img
          src={`file://${watermark.path}`}
          alt={watermark.filename}
          className="max-w-full max-h-full object-contain"
          onError={(e) => {
            // Replace with placeholder on error
            e.currentTarget.style.display = 'none';
          }}
        />
      </div>

      {/* Label */}
      <div className="mt-1.5 text-xs truncate" title={watermark.filename}>
        {watermark.filename}
      </div>
      <div className="text-xs text-surface-500">
        {formatFileSize(watermark.sizeBytes)}
        {watermark.isDefault && <span className="ml-1 text-brand-400">(Built-in)</span>}
      </div>

      {/* Selected indicator */}
      {selected && (
        <div className="absolute top-1 right-1 w-5 h-5 bg-brand-500 rounded-full flex items-center justify-center">
          <Check className="w-3 h-3 text-white" />
        </div>
      )}

      {/* Delete button (only for user-uploaded) */}
      {!watermark.isDefault && onDelete && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          disabled={isDeleting}
          className="absolute top-1 left-1 w-6 h-6 bg-red-500/80 hover:bg-red-500 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
          title="Delete watermark"
        >
          {isDeleting ? (
            <Loader2 className="w-3 h-3 animate-spin text-white" />
          ) : (
            <Trash2 className="w-3 h-3 text-white" />
          )}
        </button>
      )}
    </div>
  );
}

/**
 * Upload dropzone for adding new watermarks.
 */
function UploadDropzone({
  onUpload,
  isUploading,
}: {
  onUpload: (file: File) => void;
  isUploading: boolean;
}) {
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);

      const file = e.dataTransfer.files[0];
      if (file && file.type.startsWith('image/')) {
        onUpload(file);
      }
    },
    [onUpload]
  );

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        onUpload(file);
      }
    },
    [onUpload]
  );

  return (
    <div
      className={cn(
        'border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-colors',
        isDragging
          ? 'border-brand-500 bg-brand-500/10'
          : 'border-surface-700 hover:border-surface-500'
      )}
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/png,image/jpeg,image/webp,image/gif"
        onChange={handleFileSelect}
        className="hidden"
      />

      {isUploading ? (
        <Loader2 className="w-8 h-8 mx-auto text-brand-400 animate-spin" />
      ) : (
        <Upload className="w-8 h-8 mx-auto text-surface-400" />
      )}
      <p className="mt-2 text-sm text-surface-400">
        {isUploading ? 'Uploading...' : 'Drop image or click to upload'}
      </p>
      <p className="text-xs text-surface-500 mt-1">PNG, JPG, WebP, GIF (max 5MB)</p>
    </div>
  );
}

/**
 * Main watermark picker component.
 */
export function WatermarkPicker({
  selectedPath,
  position,
  opacity,
  enabled,
  onSelect,
  onPositionChange,
  onOpacityChange,
  onEnabledChange,
}: WatermarkPickerProps) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // Fetch watermarks
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['watermarks'],
    queryFn: () => api.listWatermarks(),
  });

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      // Read file as base64
      const reader = new FileReader();
      const base64 = await new Promise<string>((resolve, reject) => {
        reader.onload = () => {
          const result = reader.result as string;
          // Remove data URL prefix
          const base64Data = result.split(',')[1];
          resolve(base64Data);
        };
        reader.onerror = reject;
        reader.readAsDataURL(file);
      });

      return api.uploadWatermark(file.name, base64);
    },
    onSuccess: (result) => {
      if (result.success && result.watermark) {
        toast.success('Watermark Uploaded', result.watermark.filename);
        queryClient.invalidateQueries({ queryKey: ['watermarks'] });
        // Auto-select the new watermark
        onSelect(result.watermark.path);
        if (!enabled) {
          onEnabledChange(true);
        }
      } else {
        toast.error('Upload Failed', result.error || 'Unknown error');
      }
    },
    onError: (error) => {
      toast.error('Upload Failed', String(error));
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteWatermark(id),
    onSuccess: (result, id) => {
      if (result.success) {
        toast.success('Watermark Deleted');
        queryClient.invalidateQueries({ queryKey: ['watermarks'] });
        // Clear selection if deleted watermark was selected
        const deletedWatermark = data?.watermarks.find((w) => w.id === id);
        if (deletedWatermark && deletedWatermark.path === selectedPath) {
          onSelect(null);
        }
      } else {
        toast.error('Delete Failed', result.error || 'Unknown error');
      }
      setDeletingId(null);
    },
    onError: (error) => {
      toast.error('Delete Failed', String(error));
      setDeletingId(null);
    },
  });

  const handleDelete = (id: string) => {
    setDeletingId(id);
    deleteMutation.mutate(id);
  };

  return (
    <div className="space-y-4">
      {/* Enable toggle */}
      <label className="flex items-center gap-3 cursor-pointer">
        <input
          type="checkbox"
          checked={enabled}
          onChange={(e) => onEnabledChange(e.target.checked)}
          className="w-4 h-4 rounded border-surface-600 bg-surface-800"
        />
        <span className="text-sm font-medium">Add Watermark</span>
      </label>

      {enabled && (
        <>
          {/* Watermark gallery */}
          <div>
            <label className="block text-sm text-surface-400 mb-2">Select Watermark</label>

            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-brand-400" />
              </div>
            ) : error ? (
              <div className="text-center py-4">
                <AlertTriangle className="w-6 h-6 text-yellow-400 mx-auto mb-2" />
                <p className="text-sm text-surface-400">Failed to load watermarks</p>
                <button
                  onClick={() => refetch()}
                  className="text-sm text-brand-400 hover:text-brand-300 mt-1"
                >
                  Retry
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-3 gap-3">
                {/* Upload box */}
                <UploadDropzone
                  onUpload={(file) => uploadMutation.mutate(file)}
                  isUploading={uploadMutation.isPending}
                />

                {/* None option */}
                <div
                  className={cn(
                    'rounded-lg border-2 p-2 cursor-pointer transition-all flex flex-col items-center justify-center',
                    !selectedPath
                      ? 'border-brand-500 bg-brand-500/10'
                      : 'border-surface-700 hover:border-surface-500 bg-surface-800/50'
                  )}
                  onClick={() => onSelect(null)}
                >
                  <X className="w-8 h-8 text-surface-400" />
                  <span className="text-sm text-surface-400 mt-2">None</span>
                </div>

                {/* Watermark thumbnails */}
                {data?.watermarks.map((watermark) => (
                  <WatermarkThumbnail
                    key={watermark.id}
                    watermark={watermark}
                    selected={watermark.path === selectedPath}
                    onSelect={() => onSelect(watermark.path)}
                    onDelete={watermark.isDefault ? undefined : () => handleDelete(watermark.id)}
                    isDeleting={deletingId === watermark.id}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Position selector */}
          {selectedPath && (
            <div>
              <label className="block text-sm text-surface-400 mb-2">Position</label>
              <div className="grid grid-cols-3 gap-2">
                {POSITION_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => onPositionChange(opt.value)}
                    className={cn(
                      'px-2 py-1.5 text-xs rounded border transition-colors',
                      position === opt.value
                        ? 'border-brand-500 bg-brand-500/20 text-brand-400'
                        : 'border-surface-700 hover:border-surface-500 text-surface-400'
                    )}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Opacity slider */}
          {selectedPath && (
            <div>
              <label className="block text-sm text-surface-400 mb-2">
                Opacity: {Math.round(opacity * 100)}%
              </label>
              <input
                type="range"
                min={0}
                max={100}
                value={opacity * 100}
                onChange={(e) => onOpacityChange(parseInt(e.target.value) / 100)}
                className="w-full h-2 bg-surface-700 rounded-lg appearance-none cursor-pointer"
              />
            </div>
          )}
        </>
      )}
    </div>
  );
}

/**
 * Simplified watermark toggle with picker dialog.
 */
export function WatermarkToggle({
  enabled,
  selectedPath,
  onEnabledChange,
  onOpenPicker,
}: {
  enabled: boolean;
  selectedPath: string | null;
  onEnabledChange: (enabled: boolean) => void;
  onOpenPicker: () => void;
}) {
  return (
    <div className="flex items-center gap-3">
      <label className="flex items-center gap-3 cursor-pointer flex-1">
        <input
          type="checkbox"
          checked={enabled}
          onChange={(e) => onEnabledChange(e.target.checked)}
          className="w-4 h-4 rounded border-surface-600 bg-surface-800"
        />
        <span className="text-sm">Add Watermark</span>
      </label>

      {enabled && (
        <button
          onClick={onOpenPicker}
          className="px-2 py-1 text-xs bg-surface-700 hover:bg-surface-600 rounded flex items-center gap-1"
        >
          <Image className="w-3 h-3" />
          {selectedPath ? 'Change' : 'Select'}
        </button>
      )}
    </div>
  );
}
