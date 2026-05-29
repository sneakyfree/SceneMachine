/**
 * Batch operations toolbar for multi-select actions on shots.
 * Allows bulk editing, approval, regeneration, and deletion.
 */

import { useState } from 'react';
import {
  CheckSquare,
  Square,
  Play,
  Pause,
  RefreshCw,
  Trash2,
  Clock,
  Camera,
  Edit3,
  X,
  Check,
  AlertTriangle,
  Loader2,
  Copy,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { useTranslation } from '../i18n/use-translation';

export interface Shot {
  id: string;
  shot_number: string;
  shot_type: string;
  duration_seconds: number;
  state: string;
  description?: string;
}

interface BatchOperationsProps {
  shots: Shot[];
  selectedIds: Set<string>;
  onSelectionChange: (ids: Set<string>) => void;
  onBatchUpdate: (ids: string[], updates: Partial<Shot>) => Promise<void>;
  onBatchQueue: (ids: string[]) => Promise<void>;
  onBatchCancel: (ids: string[]) => Promise<void>;
  onBatchDelete: (ids: string[]) => Promise<void>;
  onBatchDuplicate?: (ids: string[]) => Promise<void>;
  isProcessing?: boolean;
}

// Shot type options
const SHOT_TYPES = [
  { value: 'WIDE', labelKey: 'batchOps.shotTypeWide', label: 'Wide' },
  { value: 'MEDIUM', labelKey: 'batchOps.shotTypeMedium', label: 'Medium' },
  { value: 'CLOSE', labelKey: 'batchOps.shotTypeCloseUp', label: 'Close Up' },
  { value: 'EXTREME_CLOSE', labelKey: 'batchOps.shotTypeExtremeClose', label: 'Extreme Close' },
  { value: 'OVER_SHOULDER', labelKey: 'batchOps.shotTypeOverShoulder', label: 'Over Shoulder' },
  { value: 'POV', labelKey: 'batchOps.shotTypePov', label: 'POV' },
  { value: 'INSERT', labelKey: 'batchOps.shotTypeInsert', label: 'Insert' },
  { value: 'TWO_SHOT', labelKey: 'batchOps.shotTypeTwoShot', label: 'Two Shot' },
];

// Duration presets
const DURATION_PRESETS = [
  { value: 2, label: '2s' },
  { value: 3, label: '3s' },
  { value: 4, label: '4s' },
  { value: 5, label: '5s' },
  { value: 8, label: '8s' },
  { value: 10, label: '10s' },
];

export function BatchOperations({
  shots,
  selectedIds,
  onSelectionChange,
  onBatchUpdate,
  onBatchQueue,
  onBatchCancel,
  onBatchDelete,
  onBatchDuplicate,
  isProcessing = false,
}: BatchOperationsProps) {
  const { t } = useTranslation();
  const [showBulkEdit, setShowBulkEdit] = useState(false);
  const [bulkShotType, setBulkShotType] = useState<string>('');
  const [bulkDuration, setBulkDuration] = useState<number | ''>('');
  const [confirmDelete, setConfirmDelete] = useState(false);

  const selectedCount = selectedIds.size;
  const allSelected = selectedCount === shots.length && shots.length > 0;
  const someSelected = selectedCount > 0 && selectedCount < shots.length;

  // Get selected shots
  const selectedShots = shots.filter((s) => selectedIds.has(s.id));

  // Count shots by state
  const pendingCount = selectedShots.filter((s) => s.state === 'planned').length;
  const processingCount = selectedShots.filter((s) => s.state === 'generating').length;
  const completedCount = selectedShots.filter((s) => s.state === 'completed').length;

  const handleSelectAll = () => {
    if (allSelected) {
      onSelectionChange(new Set());
    } else {
      onSelectionChange(new Set(shots.map((s) => s.id)));
    }
  };

  const handleBulkEdit = async () => {
    const updates: Partial<Shot> = {};
    if (bulkShotType) updates.shot_type = bulkShotType;
    if (bulkDuration) updates.duration_seconds = bulkDuration;

    if (Object.keys(updates).length > 0) {
      await onBatchUpdate(Array.from(selectedIds), updates);
      setShowBulkEdit(false);
      setBulkShotType('');
      setBulkDuration('');
    }
  };

  const handleBulkQueue = async () => {
    const pendingIds = selectedShots.filter((s) => s.state === 'planned').map((s) => s.id);
    if (pendingIds.length > 0) {
      await onBatchQueue(pendingIds);
    }
  };

  const handleBulkCancel = async () => {
    const processingIds = selectedShots
      .filter((s) => s.state === 'generating' || s.state === 'queued')
      .map((s) => s.id);
    if (processingIds.length > 0) {
      await onBatchCancel(processingIds);
    }
  };

  const handleBulkDelete = async () => {
    if (confirmDelete) {
      await onBatchDelete(Array.from(selectedIds));
      setConfirmDelete(false);
      onSelectionChange(new Set());
    } else {
      setConfirmDelete(true);
      setTimeout(() => setConfirmDelete(false), 3000);
    }
  };

  const handleBulkDuplicate = async () => {
    if (onBatchDuplicate) {
      await onBatchDuplicate(Array.from(selectedIds));
    }
  };

  if (shots.length === 0) {
    return null;
  }

  return (
    <div className="space-y-2">
      {/* Selection bar */}
      <div className="flex items-center gap-4 p-3 bg-surface-800 rounded-lg">
        {/* Select all checkbox */}
        <button
          onClick={handleSelectAll}
          className="flex items-center gap-2 text-sm hover:text-brand-400 transition-colors"
        >
          {allSelected ? (
            <CheckSquare className="w-5 h-5 text-brand-400" />
          ) : someSelected ? (
            <div className="w-5 h-5 border-2 border-brand-400 rounded flex items-center justify-center">
              <div className="w-2 h-2 bg-brand-400 rounded-sm" />
            </div>
          ) : (
            <Square className="w-5 h-5" />
          )}
          {allSelected
            ? t('batchOps.deselectAll', 'Deselect All')
            : t('batchOps.selectAll', 'Select All')}
        </button>

        {/* Selection count */}
        {selectedCount > 0 && (
          <span className="text-sm text-surface-400">
            {selectedCount} {t('batchOps.of', 'of')} {shots.length}{' '}
            {t('batchOps.selected', 'selected')}
          </span>
        )}

        {/* Spacer */}
        <div className="flex-1" />

        {/* Action buttons */}
        {selectedCount > 0 && (
          <div className="flex items-center gap-2">
            {/* Bulk edit */}
            <button
              onClick={() => setShowBulkEdit(!showBulkEdit)}
              className={cn(
                'px-3 py-1.5 text-sm rounded flex items-center gap-1.5 transition-colors',
                showBulkEdit ? 'bg-brand-500 text-white' : 'bg-surface-700 hover:bg-surface-600'
              )}
            >
              <Edit3 className="w-4 h-4" />
              {t('batchOps.edit', 'Edit')}
            </button>

            {/* Queue selected */}
            {pendingCount > 0 && (
              <button
                onClick={handleBulkQueue}
                disabled={isProcessing}
                className="px-3 py-1.5 text-sm bg-green-500/20 text-green-400 hover:bg-green-500/30 rounded flex items-center gap-1.5 disabled:opacity-50"
              >
                <Play className="w-4 h-4" />
                {t('batchOps.queue', 'Queue')} ({pendingCount})
              </button>
            )}

            {/* Cancel selected */}
            {processingCount > 0 && (
              <button
                onClick={handleBulkCancel}
                disabled={isProcessing}
                className="px-3 py-1.5 text-sm bg-yellow-500/20 text-yellow-400 hover:bg-yellow-500/30 rounded flex items-center gap-1.5 disabled:opacity-50"
              >
                <Pause className="w-4 h-4" />
                {t('batchOps.cancel', 'Cancel')} ({processingCount})
              </button>
            )}

            {/* Duplicate */}
            {onBatchDuplicate && (
              <button
                onClick={handleBulkDuplicate}
                disabled={isProcessing}
                className="px-3 py-1.5 text-sm bg-surface-700 hover:bg-surface-600 rounded flex items-center gap-1.5 disabled:opacity-50"
              >
                <Copy className="w-4 h-4" />
                {t('batchOps.duplicate', 'Duplicate')}
              </button>
            )}

            {/* Delete selected */}
            <button
              onClick={handleBulkDelete}
              disabled={isProcessing}
              className={cn(
                'px-3 py-1.5 text-sm rounded flex items-center gap-1.5 disabled:opacity-50 transition-colors',
                confirmDelete
                  ? 'bg-red-500 text-white'
                  : 'bg-red-500/20 text-red-400 hover:bg-red-500/30'
              )}
            >
              {confirmDelete ? (
                <>
                  <AlertTriangle className="w-4 h-4" />
                  {t('batchOps.confirmDelete', 'Confirm Delete')}
                </>
              ) : (
                <>
                  <Trash2 className="w-4 h-4" />
                  {t('batchOps.delete', 'Delete')}
                </>
              )}
            </button>

            {/* Clear selection */}
            <button
              onClick={() => onSelectionChange(new Set())}
              className="icon-btn p-2 text-surface-400 hover:text-surface-200 transition-colors rounded"
              title={t('batchOps.clearSelection', 'Clear selection')}
              aria-label={t('batchOps.clearSelection', 'Clear selection')}
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      {/* Bulk edit panel */}
      {showBulkEdit && selectedCount > 0 && (
        <div className="p-4 bg-surface-800 rounded-lg space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="font-medium">
              {t('batchOps.bulkEdit', 'Bulk Edit')} {selectedCount}{' '}
              {t('batchOps.shots', 'Shots')}
            </h4>
            <button
              onClick={() => setShowBulkEdit(false)}
              className="text-surface-400 hover:text-surface-200"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* Shot type */}
            <div>
              <label className="block text-sm text-surface-400 mb-2">
                <Camera className="w-4 h-4 inline mr-1" />
                {t('batchOps.shotType', 'Shot Type')}
              </label>
              <select
                value={bulkShotType}
                onChange={(e) => setBulkShotType(e.target.value)}
                className="w-full bg-surface-900 border border-surface-700 rounded-lg px-3 py-2"
              >
                <option value="">{t('batchOps.keepCurrent', 'Keep current')}</option>
                {SHOT_TYPES.map((type) => (
                  <option key={type.value} value={type.value}>
                    {t(type.labelKey, type.label)}
                  </option>
                ))}
              </select>
            </div>

            {/* Duration */}
            <div>
              <label className="block text-sm text-surface-400 mb-2">
                <Clock className="w-4 h-4 inline mr-1" />
                {t('batchOps.duration', 'Duration')}
              </label>
              <div className="flex gap-2">
                <input
                  type="number"
                  value={bulkDuration}
                  onChange={(e) =>
                    setBulkDuration(e.target.value ? parseFloat(e.target.value) : '')
                  }
                  placeholder={t('batchOps.keepCurrent', 'Keep current')}
                  min={0.5}
                  max={60}
                  step={0.5}
                  className="flex-1 bg-surface-900 border border-surface-700 rounded-lg px-3 py-2"
                />
                <div className="flex gap-1">
                  {DURATION_PRESETS.slice(0, 4).map((preset) => (
                    <button
                      key={preset.value}
                      onClick={() => setBulkDuration(preset.value)}
                      className={cn(
                        'px-2 py-1 text-xs rounded transition-colors',
                        bulkDuration === preset.value
                          ? 'bg-brand-500 text-white'
                          : 'bg-surface-700 hover:bg-surface-600'
                      )}
                    >
                      {preset.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Apply button */}
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setShowBulkEdit(false)}
              className="px-4 py-2 text-sm bg-surface-700 hover:bg-surface-600 rounded-lg"
            >
              {t('batchOps.cancel', 'Cancel')}
            </button>
            <button
              onClick={handleBulkEdit}
              disabled={isProcessing || (!bulkShotType && !bulkDuration)}
              className="px-4 py-2 text-sm bg-brand-500 hover:bg-brand-600 rounded-lg flex items-center gap-2 disabled:opacity-50"
            >
              {isProcessing ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Check className="w-4 h-4" />
              )}
              {t('batchOps.applyTo', 'Apply to')} {selectedCount}{' '}
              {t('batchOps.shotsLower', 'shots')}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Selectable shot item component.
 */
export function SelectableShot({
  shot,
  selected,
  onSelect,
  children,
}: {
  shot: Shot;
  selected: boolean;
  onSelect: (id: string, selected: boolean) => void;
  children: React.ReactNode;
}) {
  const handleClick = (e: React.MouseEvent) => {
    // If clicking the checkbox area, toggle selection
    if ((e.target as HTMLElement).closest('.selection-checkbox')) {
      e.stopPropagation();
      onSelect(shot.id, !selected);
    }
  };

  return (
    <div
      className={cn(
        'relative group transition-colors',
        selected && 'ring-2 ring-brand-500 rounded-lg'
      )}
      onClick={handleClick}
    >
      {/* Selection checkbox */}
      <div className="selection-checkbox absolute top-2 left-2 z-10">
        <button
          onClick={() => onSelect(shot.id, !selected)}
          className={cn(
            'w-6 h-6 rounded flex items-center justify-center transition-all',
            selected
              ? 'bg-brand-500 text-white'
              : 'bg-surface-800/80 text-surface-400 opacity-0 group-hover:opacity-100'
          )}
        >
          {selected ? <Check className="w-4 h-4" /> : <Square className="w-4 h-4" />}
        </button>
      </div>

      {children}
    </div>
  );
}
