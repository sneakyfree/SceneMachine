/**
 * Delta Reports Visualization Component
 * 
 * Provides visual diff comparison between snapshots with:
 * - Side-by-side comparison
 * - Highlighted changes
 * - Timeline scrubbing for version history
 * - Export to PDF
 */

import React, { useState, useMemo, useCallback } from 'react';
import {
    GitCompare,
    ChevronLeft,
    ChevronRight,
    Download,
    Eye,
    EyeOff,
    Clock,
    Plus,
    Minus,
    AlertCircle,
} from 'lucide-react';
import { cn } from '../../lib/utils';

// Types
interface Snapshot {
    id: string;
    label: string;
    timestamp: string;
    projectState: Record<string, unknown>;
    metadata: {
        createdBy: string;
        description?: string;
        shotCount: number;
        characterCount: number;
    };
}

interface DeltaChange {
    path: string;
    type: 'added' | 'removed' | 'modified';
    oldValue?: unknown;
    newValue?: unknown;
    description: string;
}

interface DeltaReportsProps {
    snapshots: Snapshot[];
    onExport?: (format: 'pdf' | 'json') => void;
    className?: string;
}

// Diff computation
function computeDelta(from: Snapshot, to: Snapshot): DeltaChange[] {
    const changes: DeltaChange[] = [];

    function compareObjects(
        oldObj: Record<string, unknown>,
        newObj: Record<string, unknown>,
        path: string = ''
    ) {
        const allKeys = new Set([...Object.keys(oldObj || {}), ...Object.keys(newObj || {})]);

        for (const key of allKeys) {
            const currentPath = path ? `${path}.${key}` : key;
            const oldValue = oldObj?.[key];
            const newValue = newObj?.[key];

            if (oldValue === undefined && newValue !== undefined) {
                changes.push({
                    path: currentPath,
                    type: 'added',
                    newValue,
                    description: `Added ${key}`,
                });
            } else if (oldValue !== undefined && newValue === undefined) {
                changes.push({
                    path: currentPath,
                    type: 'removed',
                    oldValue,
                    description: `Removed ${key}`,
                });
            } else if (typeof oldValue === 'object' && typeof newValue === 'object' && oldValue !== null && newValue !== null) {
                if (Array.isArray(oldValue) && Array.isArray(newValue)) {
                    if (oldValue.length !== newValue.length) {
                        changes.push({
                            path: currentPath,
                            type: 'modified',
                            oldValue: oldValue.length,
                            newValue: newValue.length,
                            description: `Changed ${key} count from ${oldValue.length} to ${newValue.length}`,
                        });
                    }
                } else {
                    compareObjects(
                        oldValue as Record<string, unknown>,
                        newValue as Record<string, unknown>,
                        currentPath
                    );
                }
            } else if (JSON.stringify(oldValue) !== JSON.stringify(newValue)) {
                changes.push({
                    path: currentPath,
                    type: 'modified',
                    oldValue,
                    newValue,
                    description: `Changed ${key}`,
                });
            }
        }
    }

    compareObjects(from.projectState as Record<string, unknown>, to.projectState as Record<string, unknown>);
    return changes;
}

// Change badge component
function ChangeBadge({ type }: { type: DeltaChange['type'] }) {
    const styles = {
        added: 'bg-green-500/20 text-green-400 border-green-500/30',
        removed: 'bg-red-500/20 text-red-400 border-red-500/30',
        modified: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    };

    const icons = {
        added: <Plus className="w-3 h-3" />,
        removed: <Minus className="w-3 h-3" />,
        modified: <AlertCircle className="w-3 h-3" />,
    };

    return (
        <span className={cn(
            'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border',
            styles[type]
        )}>
            {icons[type]}
            {type}
        </span>
    );
}

// Snapshot selector
function SnapshotSelector({
    snapshots,
    selectedId,
    onSelect,
    label,
}: {
    snapshots: Snapshot[];
    selectedId: string;
    onSelect: (id: string) => void;
    label: string;
}) {
    return (
        <div className="space-y-2">
            <label className="text-sm text-surface-400">{label}</label>
            <select
                value={selectedId}
                onChange={(e) => onSelect(e.target.value)}
                className="w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg text-sm"
            >
                {snapshots.map((snapshot) => (
                    <option key={snapshot.id} value={snapshot.id}>
                        {snapshot.label} - {new Date(snapshot.timestamp).toLocaleString()}
                    </option>
                ))}
            </select>
        </div>
    );
}

// Timeline scrubber
function TimelineScrubber({
    snapshots,
    fromId,
    toId,
    onFromChange,
    onToChange,
}: {
    snapshots: Snapshot[];
    fromId: string;
    toId: string;
    onFromChange: (id: string) => void;
    onToChange: (id: string) => void;
}) {
    const sortedSnapshots = useMemo(() =>
        [...snapshots].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()),
        [snapshots]
    );

    const fromIndex = sortedSnapshots.findIndex(s => s.id === fromId);
    const toIndex = sortedSnapshots.findIndex(s => s.id === toId);

    return (
        <div className="space-y-3">
            <div className="flex items-center gap-2 text-sm text-surface-400">
                <Clock className="w-4 h-4" />
                <span>Version Timeline</span>
            </div>

            <div className="relative">
                {/* Timeline track */}
                <div className="h-2 bg-surface-700 rounded-full" />

                {/* Snapshot markers */}
                <div className="absolute inset-0 flex items-center justify-between px-1">
                    {sortedSnapshots.map((snapshot, index) => {
                        const isFrom = snapshot.id === fromId;
                        const isTo = snapshot.id === toId;
                        const isInRange = index >= fromIndex && index <= toIndex;

                        return (
                            <button
                                key={snapshot.id}
                                onClick={() => {
                                    if (index < fromIndex) onFromChange(snapshot.id);
                                    else if (index > toIndex) onToChange(snapshot.id);
                                }}
                                className={cn(
                                    'w-4 h-4 rounded-full border-2 transition-all cursor-pointer',
                                    isFrom && 'bg-blue-500 border-blue-400 scale-125',
                                    isTo && 'bg-green-500 border-green-400 scale-125',
                                    !isFrom && !isTo && isInRange && 'bg-brand-500/50 border-brand-400/50',
                                    !isFrom && !isTo && !isInRange && 'bg-surface-600 border-surface-500 hover:bg-surface-500'
                                )}
                                title={`${snapshot.label} - ${new Date(snapshot.timestamp).toLocaleDateString()}`}
                            />
                        );
                    })}
                </div>

                {/* Range highlight */}
                {fromIndex < toIndex && (
                    <div
                        className="absolute top-0 h-2 bg-brand-500/30 rounded-full"
                        style={{
                            left: `${(fromIndex / (sortedSnapshots.length - 1)) * 100}%`,
                            width: `${((toIndex - fromIndex) / (sortedSnapshots.length - 1)) * 100}%`,
                        }}
                    />
                )}
            </div>

            <div className="flex justify-between text-xs text-surface-400">
                <span>{sortedSnapshots[0]?.label}</span>
                <span>{sortedSnapshots[sortedSnapshots.length - 1]?.label}</span>
            </div>
        </div>
    );
}

// Change list item
function ChangeItem({ change, showDetails }: { change: DeltaChange; showDetails: boolean }) {
    const [expanded, setExpanded] = useState(false);

    const formatValue = (value: unknown): string => {
        if (value === undefined) return 'undefined';
        if (value === null) return 'null';
        if (typeof value === 'object') return JSON.stringify(value, null, 2);
        return String(value);
    };

    return (
        <div className="border border-surface-700 rounded-lg overflow-hidden">
            <button
                onClick={() => setExpanded(!expanded)}
                className="w-full flex items-center gap-3 px-4 py-3 hover:bg-surface-800/50 transition-colors text-left"
            >
                <ChangeBadge type={change.type} />
                <div className="flex-1 min-w-0">
                    <div className="font-medium truncate">{change.description}</div>
                    <div className="text-xs text-surface-400 font-mono truncate">{change.path}</div>
                </div>
                <ChevronRight className={cn(
                    'w-4 h-4 text-surface-400 transition-transform',
                    expanded && 'rotate-90'
                )} />
            </button>

            {expanded && showDetails && (
                <div className="px-4 pb-3 grid grid-cols-2 gap-4">
                    {change.oldValue !== undefined && (
                        <div>
                            <div className="text-xs text-red-400 mb-1">Old Value</div>
                            <pre className="text-xs bg-red-500/10 border border-red-500/20 rounded p-2 overflow-auto max-h-32">
                                {formatValue(change.oldValue)}
                            </pre>
                        </div>
                    )}
                    {change.newValue !== undefined && (
                        <div>
                            <div className="text-xs text-green-400 mb-1">New Value</div>
                            <pre className="text-xs bg-green-500/10 border border-green-500/20 rounded p-2 overflow-auto max-h-32">
                                {formatValue(change.newValue)}
                            </pre>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

// Summary stats
function DeltaSummary({ changes }: { changes: DeltaChange[] }) {
    const stats = useMemo(() => ({
        added: changes.filter(c => c.type === 'added').length,
        removed: changes.filter(c => c.type === 'removed').length,
        modified: changes.filter(c => c.type === 'modified').length,
    }), [changes]);

    return (
        <div className="flex items-center gap-4 p-4 bg-surface-800/50 rounded-lg">
            <div className="flex items-center gap-2 text-green-400">
                <Plus className="w-4 h-4" />
                <span className="font-medium">{stats.added}</span>
                <span className="text-surface-400 text-sm">added</span>
            </div>
            <div className="flex items-center gap-2 text-red-400">
                <Minus className="w-4 h-4" />
                <span className="font-medium">{stats.removed}</span>
                <span className="text-surface-400 text-sm">removed</span>
            </div>
            <div className="flex items-center gap-2 text-amber-400">
                <AlertCircle className="w-4 h-4" />
                <span className="font-medium">{stats.modified}</span>
                <span className="text-surface-400 text-sm">modified</span>
            </div>
        </div>
    );
}

// Main component
export function DeltaReportsVisualization({
    snapshots,
    onExport,
    className,
}: DeltaReportsProps) {
    const [fromId, setFromId] = useState(snapshots[0]?.id || '');
    const [toId, setToId] = useState(snapshots[snapshots.length - 1]?.id || '');
    const [showDetails, setShowDetails] = useState(true);
    const [filterType, setFilterType] = useState<DeltaChange['type'] | 'all'>('all');

    const fromSnapshot = snapshots.find(s => s.id === fromId);
    const toSnapshot = snapshots.find(s => s.id === toId);

    const changes = useMemo(() => {
        if (!fromSnapshot || !toSnapshot) return [];
        return computeDelta(fromSnapshot, toSnapshot);
    }, [fromSnapshot, toSnapshot]);

    const filteredChanges = useMemo(() => {
        if (filterType === 'all') return changes;
        return changes.filter(c => c.type === filterType);
    }, [changes, filterType]);

    const handleExportPDF = useCallback(() => {
        onExport?.('pdf');
    }, [onExport]);

    if (snapshots.length < 2) {
        return (
            <div className={cn('p-8 text-center', className)}>
                <GitCompare className="w-12 h-12 text-surface-500 mx-auto mb-4" />
                <h3 className="text-lg font-medium mb-2">Not Enough Snapshots</h3>
                <p className="text-surface-400">
                    Create at least 2 snapshots to compare changes.
                </p>
            </div>
        );
    }

    return (
        <div className={cn('space-y-6', className)}>
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <GitCompare className="w-6 h-6 text-brand-400" />
                    <h2 className="text-xl font-semibold">Delta Report</h2>
                </div>

                <div className="flex items-center gap-2">
                    <button
                        onClick={() => setShowDetails(!showDetails)}
                        className={cn(
                            'p-2 rounded-lg transition-colors',
                            showDetails ? 'bg-brand-500/20 text-brand-400' : 'bg-surface-700 text-surface-400'
                        )}
                        title={showDetails ? 'Hide details' : 'Show details'}
                    >
                        {showDetails ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                    </button>

                    <button
                        onClick={handleExportPDF}
                        className="flex items-center gap-2 px-4 py-2 bg-surface-700 hover:bg-surface-600 rounded-lg transition-colors"
                    >
                        <Download className="w-4 h-4" />
                        <span>Export PDF</span>
                    </button>
                </div>
            </div>

            {/* Snapshot selectors */}
            <div className="grid grid-cols-2 gap-4">
                <SnapshotSelector
                    snapshots={snapshots}
                    selectedId={fromId}
                    onSelect={setFromId}
                    label="From (older)"
                />
                <SnapshotSelector
                    snapshots={snapshots}
                    selectedId={toId}
                    onSelect={setToId}
                    label="To (newer)"
                />
            </div>

            {/* Timeline scrubber */}
            <TimelineScrubber
                snapshots={snapshots}
                fromId={fromId}
                toId={toId}
                onFromChange={setFromId}
                onToChange={setToId}
            />

            {/* Summary */}
            <DeltaSummary changes={changes} />

            {/* Filter tabs */}
            <div className="flex items-center gap-2">
                {(['all', 'added', 'removed', 'modified'] as const).map((type) => (
                    <button
                        key={type}
                        onClick={() => setFilterType(type)}
                        className={cn(
                            'px-3 py-1.5 rounded-full text-sm font-medium transition-colors',
                            filterType === type
                                ? 'bg-brand-500 text-white'
                                : 'bg-surface-700 text-surface-300 hover:bg-surface-600'
                        )}
                    >
                        {type === 'all' ? 'All Changes' : type.charAt(0).toUpperCase() + type.slice(1)}
                        {type !== 'all' && (
                            <span className="ml-1.5 opacity-70">
                                ({changes.filter(c => c.type === type).length})
                            </span>
                        )}
                    </button>
                ))}
            </div>

            {/* Changes list */}
            <div className="space-y-2">
                {filteredChanges.length === 0 ? (
                    <div className="p-8 text-center text-surface-400">
                        {changes.length === 0
                            ? 'No changes between these snapshots'
                            : 'No changes match the current filter'}
                    </div>
                ) : (
                    filteredChanges.map((change, index) => (
                        <ChangeItem key={`${change.path}-${index}`} change={change} showDetails={showDetails} />
                    ))
                )}
            </div>
        </div>
    );
}

export default DeltaReportsVisualization;
