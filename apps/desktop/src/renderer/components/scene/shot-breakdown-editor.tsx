/**
 * Enhanced Shot Breakdown Editor
 * 
 * Provides inline editing of shot breakdowns with:
 * - Drag-and-drop reordering
 * - Inline field editing
 * - Quick actions (duplicate, delete, regenerate)
 * - AI suggestions inline
 * - Keyboard shortcuts
 */

import React, { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import {
    GripVertical,
    Trash2,
    Copy,
    RefreshCw,
    Sparkles,
    Video,
    Clock,
    Users,
    MessageSquare,
    ChevronDown,
    ChevronUp,
    Edit3,
    Check,
    X,
    Wand2,
    Camera,
} from 'lucide-react';
import { cn } from '../../lib/utils';

// Types
interface Shot {
    id: string;
    shotNumber: number;
    type: 'wide' | 'medium' | 'close-up' | 'extreme_close' | 'pov' | 'over_shoulder' | 'establishing' | 'insert';
    description: string;
    cameraMovement: 'static' | 'pan' | 'tilt' | 'dolly' | 'tracking' | 'handheld' | 'crane';
    durationSeconds: number;
    characters: string[];
    dialogue?: {
        speaker: string;
        text: string;
        emotion: string;
    };
    notes?: string;
    generated?: boolean;
    generatedUrl?: string;
}

interface ShotEditorProps {
    shots: Shot[];
    characters: string[];
    onShotsChange: (shots: Shot[]) => void;
    onRegenerateShot?: (shotId: string) => void;
    onAISuggest?: (shotId: string) => Promise<Partial<Shot>>;
    className?: string;
}

const SHOT_TYPES: Shot['type'][] = ['wide', 'medium', 'close-up', 'extreme_close', 'pov', 'over_shoulder', 'establishing', 'insert'];
const CAMERA_MOVEMENTS: Shot['cameraMovement'][] = ['static', 'pan', 'tilt', 'dolly', 'tracking', 'handheld', 'crane'];

// Inline editable field
function EditableField({
    value,
    onSave,
    type = 'text',
    options,
    className,
    multiline = false,
}: {
    value: string | number;
    onSave: (value: string | number) => void;
    type?: 'text' | 'number' | 'select';
    options?: string[];
    className?: string;
    multiline?: boolean;
}) {
    const [isEditing, setIsEditing] = useState(false);
    const [editValue, setEditValue] = useState(value);
    const inputRef = useRef<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>(null);

    useEffect(() => {
        if (isEditing && inputRef.current) {
            inputRef.current.focus();
            if ('select' in inputRef.current) {
                inputRef.current.select();
            }
        }
    }, [isEditing]);

    const handleSave = () => {
        onSave(type === 'number' ? Number(editValue) : editValue);
        setIsEditing(false);
    };

    const handleCancel = () => {
        setEditValue(value);
        setIsEditing(false);
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !multiline) {
            handleSave();
        } else if (e.key === 'Escape') {
            handleCancel();
        }
    };

    if (!isEditing) {
        return (
            <button
                onClick={() => setIsEditing(true)}
                className={cn(
                    'flex items-center gap-1 px-2 py-1 rounded hover:bg-surface-700 transition-colors group text-left',
                    className
                )}
            >
                <span className="flex-1 truncate">{value}</span>
                <Edit3 className="w-3 h-3 opacity-0 group-hover:opacity-50" />
            </button>
        );
    }

    if (type === 'select' && options) {
        return (
            <div className="flex items-center gap-1">
                <select
                    ref={inputRef as React.RefObject<HTMLSelectElement>}
                    value={String(editValue)}
                    onChange={(e) => setEditValue(e.target.value)}
                    onBlur={handleSave}
                    onKeyDown={handleKeyDown}
                    className="flex-1 px-2 py-1 bg-surface-800 border border-brand-500 rounded text-sm"
                >
                    {options.map((opt) => (
                        <option key={opt} value={opt}>{opt}</option>
                    ))}
                </select>
            </div>
        );
    }

    if (multiline) {
        return (
            <div className="space-y-2">
                <textarea
                    ref={inputRef as React.RefObject<HTMLTextAreaElement>}
                    value={String(editValue)}
                    onChange={(e) => setEditValue(e.target.value)}
                    onKeyDown={handleKeyDown}
                    rows={3}
                    className="w-full px-2 py-1 bg-surface-800 border border-brand-500 rounded text-sm resize-none"
                />
                <div className="flex items-center gap-1">
                    <button
                        onClick={handleSave}
                        className="p-1 bg-green-500/20 text-green-400 rounded hover:bg-green-500/30"
                    >
                        <Check className="w-3 h-3" />
                    </button>
                    <button
                        onClick={handleCancel}
                        className="p-1 bg-red-500/20 text-red-400 rounded hover:bg-red-500/30"
                    >
                        <X className="w-3 h-3" />
                    </button>
                </div>
            </div>
        );
    }

    return (
        <input
            ref={inputRef as React.RefObject<HTMLInputElement>}
            type={type}
            value={editValue}
            onChange={(e) => setEditValue(type === 'number' ? e.target.valueAsNumber : e.target.value)}
            onBlur={handleSave}
            onKeyDown={handleKeyDown}
            className="w-full px-2 py-1 bg-surface-800 border border-brand-500 rounded text-sm"
        />
    );
}

// Shot card component
function ShotCard({
    shot,
    characters,
    isExpanded,
    onToggleExpand,
    onUpdate,
    onDelete,
    onDuplicate,
    onRegenerate,
    onAISuggest,
    isDragging,
    dragHandleProps,
}: {
    shot: Shot;
    characters: string[];
    isExpanded: boolean;
    onToggleExpand: () => void;
    onUpdate: (updates: Partial<Shot>) => void;
    onDelete: () => void;
    onDuplicate: () => void;
    onRegenerate?: () => void;
    onAISuggest?: () => void;
    isDragging: boolean;
    dragHandleProps?: React.HTMLAttributes<HTMLButtonElement>;
}) {
    const [isSuggesting, setIsSuggesting] = useState(false);

    const handleAISuggest = async () => {
        if (!onAISuggest) return;
        setIsSuggesting(true);
        try {
            await onAISuggest();
        } finally {
            setIsSuggesting(false);
        }
    };

    return (
        <div
            className={cn(
                'border border-surface-700 rounded-lg overflow-hidden transition-all',
                isDragging && 'opacity-50 border-brand-500',
                isExpanded ? 'bg-surface-800' : 'bg-surface-800/50 hover:bg-surface-800'
            )}
        >
            {/* Header */}
            <div className="flex items-center gap-3 p-3">
                {/* Drag handle */}
                <button
                    {...dragHandleProps}
                    className="p-1 text-surface-500 hover:text-surface-300 cursor-grab active:cursor-grabbing"
                    aria-label="Drag to reorder"
                >
                    <GripVertical className="w-4 h-4" />
                </button>

                {/* Shot number */}
                <div className="flex items-center justify-center w-8 h-8 rounded-full bg-brand-500/20 text-brand-400 font-bold text-sm">
                    {shot.shotNumber}
                </div>

                {/* Shot type */}
                <div className="flex-shrink-0">
                    <EditableField
                        value={shot.type}
                        onSave={(v) => onUpdate({ type: v as Shot['type'] })}
                        type="select"
                        options={SHOT_TYPES}
                        className="text-sm font-medium"
                    />
                </div>

                {/* Duration */}
                <div className="flex items-center gap-1 text-surface-400 text-sm">
                    <Clock className="w-3 h-3" />
                    <EditableField
                        value={shot.durationSeconds}
                        onSave={(v) => onUpdate({ durationSeconds: Number(v) })}
                        type="number"
                        className="w-12"
                    />
                    <span>s</span>
                </div>

                {/* Characters */}
                <div className="flex items-center gap-1 text-surface-400 text-sm">
                    <Users className="w-3 h-3" />
                    <span>{shot.characters.length}</span>
                </div>

                {/* Dialogue indicator */}
                {shot.dialogue && (
                    <div className="flex items-center gap-1 text-surface-400 text-sm">
                        <MessageSquare className="w-3 h-3" />
                    </div>
                )}

                {/* Generated indicator */}
                {shot.generated && (
                    <div className="flex items-center gap-1 text-green-400 text-xs">
                        <Video className="w-3 h-3" />
                        <span>Generated</span>
                    </div>
                )}

                {/* Spacer */}
                <div className="flex-1" />

                {/* Quick actions */}
                <div className="flex items-center gap-1">
                    <button
                        onClick={handleAISuggest}
                        disabled={isSuggesting}
                        className="p-1.5 text-surface-400 hover:text-brand-400 hover:bg-brand-500/10 rounded transition-colors"
                        title="AI Suggestions"
                    >
                        {isSuggesting ? (
                            <RefreshCw className="w-4 h-4 animate-spin" />
                        ) : (
                            <Wand2 className="w-4 h-4" />
                        )}
                    </button>

                    {onRegenerate && (
                        <button
                            onClick={onRegenerate}
                            className="p-1.5 text-surface-400 hover:text-amber-400 hover:bg-amber-500/10 rounded transition-colors"
                            title="Regenerate shot"
                        >
                            <RefreshCw className="w-4 h-4" />
                        </button>
                    )}

                    <button
                        onClick={onDuplicate}
                        className="p-1.5 text-surface-400 hover:text-surface-200 hover:bg-surface-700 rounded transition-colors"
                        title="Duplicate shot"
                    >
                        <Copy className="w-4 h-4" />
                    </button>

                    <button
                        onClick={onDelete}
                        className="p-1.5 text-surface-400 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors"
                        title="Delete shot"
                    >
                        <Trash2 className="w-4 h-4" />
                    </button>

                    <button
                        onClick={onToggleExpand}
                        className="p-1.5 text-surface-400 hover:text-surface-200 hover:bg-surface-700 rounded transition-colors"
                    >
                        {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </button>
                </div>
            </div>

            {/* Expanded content */}
            {isExpanded && (
                <div className="px-3 pb-3 space-y-3 border-t border-surface-700 pt-3">
                    {/* Description */}
                    <div>
                        <label className="text-xs text-surface-400 mb-1 block">Description</label>
                        <EditableField
                            value={shot.description}
                            onSave={(v) => onUpdate({ description: String(v) })}
                            multiline
                            className="w-full"
                        />
                    </div>

                    {/* Camera movement */}
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="text-xs text-surface-400 mb-1 block">Camera Movement</label>
                            <EditableField
                                value={shot.cameraMovement}
                                onSave={(v) => onUpdate({ cameraMovement: v as Shot['cameraMovement'] })}
                                type="select"
                                options={CAMERA_MOVEMENTS}
                            />
                        </div>

                        <div>
                            <label className="text-xs text-surface-400 mb-1 block">Characters</label>
                            <div className="flex flex-wrap gap-1">
                                {characters.map((char) => (
                                    <button
                                        key={char}
                                        onClick={() => {
                                            const newChars = shot.characters.includes(char)
                                                ? shot.characters.filter((c) => c !== char)
                                                : [...shot.characters, char];
                                            onUpdate({ characters: newChars });
                                        }}
                                        className={cn(
                                            'px-2 py-0.5 rounded-full text-xs transition-colors',
                                            shot.characters.includes(char)
                                                ? 'bg-brand-500/30 text-brand-300'
                                                : 'bg-surface-700 text-surface-400 hover:bg-surface-600'
                                        )}
                                    >
                                        {char}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>

                    {/* Dialogue */}
                    {shot.dialogue && (
                        <div className="p-3 bg-surface-900/50 rounded-lg space-y-2">
                            <div className="flex items-center gap-2 text-xs text-surface-400">
                                <MessageSquare className="w-3 h-3" />
                                <span>Dialogue</span>
                            </div>
                            <div className="grid grid-cols-3 gap-2">
                                <EditableField
                                    value={shot.dialogue.speaker}
                                    onSave={(v) => onUpdate({ dialogue: { ...shot.dialogue!, speaker: String(v) } })}
                                    type="select"
                                    options={characters}
                                />
                                <div className="col-span-2">
                                    <EditableField
                                        value={shot.dialogue.text}
                                        onSave={(v) => onUpdate({ dialogue: { ...shot.dialogue!, text: String(v) } })}
                                        multiline
                                    />
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Notes */}
                    <div>
                        <label className="text-xs text-surface-400 mb-1 block">Notes</label>
                        <EditableField
                            value={shot.notes || ''}
                            onSave={(v) => onUpdate({ notes: String(v) || undefined })}
                            multiline
                            className="w-full"
                        />
                    </div>
                </div>
            )}
        </div>
    );
}

// Main component
export function ShotBreakdownEditor({
    shots,
    characters,
    onShotsChange,
    onRegenerateShot,
    onAISuggest,
    className,
}: ShotEditorProps) {
    const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
    const [draggedId, setDraggedId] = useState<string | null>(null);

    const toggleExpand = useCallback((id: string) => {
        setExpandedIds((prev) => {
            const next = new Set(prev);
            if (next.has(id)) {
                next.delete(id);
            } else {
                next.add(id);
            }
            return next;
        });
    }, []);

    const updateShot = useCallback((id: string, updates: Partial<Shot>) => {
        onShotsChange(
            shots.map((s) => (s.id === id ? { ...s, ...updates } : s))
        );
    }, [shots, onShotsChange]);

    const deleteShot = useCallback((id: string) => {
        onShotsChange(
            shots.filter((s) => s.id !== id).map((s, i) => ({ ...s, shotNumber: i + 1 }))
        );
    }, [shots, onShotsChange]);

    const duplicateShot = useCallback((id: string) => {
        const index = shots.findIndex((s) => s.id === id);
        if (index === -1) return;

        const newShot: Shot = {
            ...shots[index],
            id: `shot-${Date.now()}`,
            shotNumber: index + 2,
            generated: false,
            generatedUrl: undefined,
        };

        const newShots = [...shots];
        newShots.splice(index + 1, 0, newShot);

        onShotsChange(
            newShots.map((s, i) => ({ ...s, shotNumber: i + 1 }))
        );
    }, [shots, onShotsChange]);

    const handleAISuggest = useCallback(async (id: string) => {
        if (!onAISuggest) return;
        const suggestion = await onAISuggest(id);
        updateShot(id, suggestion);
    }, [onAISuggest, updateShot]);

    const addNewShot = useCallback(() => {
        const newShot: Shot = {
            id: `shot-${Date.now()}`,
            shotNumber: shots.length + 1,
            type: 'medium',
            description: 'New shot description...',
            cameraMovement: 'static',
            durationSeconds: 3,
            characters: [],
        };
        onShotsChange([...shots, newShot]);
        setExpandedIds((prev) => new Set([...prev, newShot.id]));
    }, [shots, onShotsChange]);

    // Calculate totals
    const totalDuration = useMemo(() =>
        shots.reduce((sum, s) => sum + s.durationSeconds, 0),
        [shots]
    );

    const generatedCount = useMemo(() =>
        shots.filter((s) => s.generated).length,
        [shots]
    );

    return (
        <div className={cn('space-y-4', className)}>
            {/* Header with stats */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <h3 className="text-lg font-semibold flex items-center gap-2">
                        <Camera className="w-5 h-5 text-brand-400" />
                        Shot Breakdown
                    </h3>
                    <div className="flex items-center gap-3 text-sm text-surface-400">
                        <span>{shots.length} shots</span>
                        <span>•</span>
                        <span>{Math.floor(totalDuration / 60)}:{String(Math.floor(totalDuration % 60)).padStart(2, '0')}</span>
                        <span>•</span>
                        <span className="text-green-400">{generatedCount} generated</span>
                    </div>
                </div>

                <div className="flex items-center gap-2">
                    <button
                        onClick={() => setExpandedIds(expandedIds.size === shots.length ? new Set() : new Set(shots.map(s => s.id)))}
                        className="text-sm text-surface-400 hover:text-surface-200"
                    >
                        {expandedIds.size === shots.length ? 'Collapse All' : 'Expand All'}
                    </button>

                    <button
                        onClick={addNewShot}
                        className="flex items-center gap-2 px-4 py-2 bg-brand-500 hover:bg-brand-600 rounded-lg transition-colors font-medium"
                    >
                        <Sparkles className="w-4 h-4" />
                        Add Shot
                    </button>
                </div>
            </div>

            {/* Shot list */}
            <div className="space-y-2">
                {shots.map((shot) => (
                    <ShotCard
                        key={shot.id}
                        shot={shot}
                        characters={characters}
                        isExpanded={expandedIds.has(shot.id)}
                        onToggleExpand={() => toggleExpand(shot.id)}
                        onUpdate={(updates) => updateShot(shot.id, updates)}
                        onDelete={() => deleteShot(shot.id)}
                        onDuplicate={() => duplicateShot(shot.id)}
                        onRegenerate={onRegenerateShot ? () => onRegenerateShot(shot.id) : undefined}
                        onAISuggest={onAISuggest ? () => handleAISuggest(shot.id) : undefined}
                        isDragging={draggedId === shot.id}
                    />
                ))}
            </div>

            {/* Empty state */}
            {shots.length === 0 && (
                <div className="p-8 text-center border-2 border-dashed border-surface-700 rounded-lg">
                    <Camera className="w-12 h-12 text-surface-500 mx-auto mb-4" />
                    <h4 className="text-lg font-medium mb-2">No Shots Yet</h4>
                    <p className="text-surface-400 mb-4">
                        Add shots manually or use AI to generate a breakdown.
                    </p>
                    <button
                        onClick={addNewShot}
                        className="px-4 py-2 bg-brand-500 hover:bg-brand-600 rounded-lg transition-colors font-medium"
                    >
                        Add First Shot
                    </button>
                </div>
            )}

            {/* Keyboard shortcuts hint */}
            <div className="text-xs text-surface-500 text-center">
                Press <kbd className="px-1 py-0.5 bg-surface-700 rounded">Enter</kbd> to save inline edits,{' '}
                <kbd className="px-1 py-0.5 bg-surface-700 rounded">Esc</kbd> to cancel
            </div>
        </div>
    );
}

export default ShotBreakdownEditor;
