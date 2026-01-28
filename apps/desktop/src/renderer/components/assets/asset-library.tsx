/**
 * AssetLibrary Component
 * Comprehensive asset management with tagging, search, and bulk operations
 */

import React from 'react';
import {
    Search,
    Filter,
    Grid,
    List,
    Tag,
    Folder,
    Check,
    X,
    ChevronDown,
    MoreHorizontal,
    Trash2,
    Download,
    Move,
    Copy,
    Star,
    StarOff,
    Clock,
    FileText,
    Image,
    Film,
    Music,
    SortAsc,
    SortDesc,
    Plus,
} from 'lucide-react';
import { cn } from '../../lib/utils';

// Asset types
export type AssetType = 'image' | 'video' | 'audio' | 'document' | 'other';

// Asset interface
export interface Asset {
    id: string;
    name: string;
    type: AssetType;
    size: number;
    path: string;
    thumbnailUrl?: string;
    tags: string[];
    folder?: string;
    isFavorite: boolean;
    createdAt: Date;
    updatedAt: Date;
    metadata?: Record<string, any>;
}

// Sort options
export type SortField = 'name' | 'size' | 'createdAt' | 'updatedAt' | 'type';
export type SortDirection = 'asc' | 'desc';

// View mode
export type ViewMode = 'grid' | 'list';

interface AssetLibraryProps {
    assets: Asset[];
    selectedIds: string[];
    onSelect: (ids: string[]) => void;
    onAssetOpen: (asset: Asset) => void;
    onTagsUpdate: (assetId: string, tags: string[]) => void;
    onFavoriteToggle: (assetId: string) => void;
    onDelete: (assetIds: string[]) => void;
    onMove?: (assetIds: string[], folder: string) => void;
    onDuplicate?: (assetIds: string[]) => void;
    availableTags: string[];
    folders: string[];
    className?: string;
}

// Type icons
const TYPE_ICONS: Record<AssetType, React.ReactNode> = {
    image: <Image className="w-4 h-4 text-blue-400" />,
    video: <Film className="w-4 h-4 text-purple-400" />,
    audio: <Music className="w-4 h-4 text-green-400" />,
    document: <FileText className="w-4 h-4 text-yellow-400" />,
    other: <FileText className="w-4 h-4 text-surface-400" />,
};

// Format file size
const formatSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
};

// Tag input component
const TagInput: React.FC<{
    tags: string[];
    availableTags: string[];
    onChange: (tags: string[]) => void;
}> = ({ tags, availableTags, onChange }) => {
    const [input, setInput] = React.useState('');
    const [showSuggestions, setShowSuggestions] = React.useState(false);

    const suggestions = availableTags.filter(
        (t) => !tags.includes(t) && t.toLowerCase().includes(input.toLowerCase())
    );

    const addTag = (tag: string) => {
        if (!tags.includes(tag)) {
            onChange([...tags, tag]);
        }
        setInput('');
        setShowSuggestions(false);
    };

    const removeTag = (tag: string) => {
        onChange(tags.filter((t) => t !== tag));
    };

    return (
        <div className="relative">
            <div className="flex flex-wrap gap-1 p-2 bg-surface-800 border border-surface-700 rounded-lg min-h-[40px]">
                {tags.map((tag) => (
                    <span
                        key={tag}
                        className="inline-flex items-center gap-1 px-2 py-0.5 bg-brand-500/20 text-brand-400 rounded text-xs"
                    >
                        <Tag className="w-3 h-3" />
                        {tag}
                        <button onClick={() => removeTag(tag)} className="hover:text-red-400">
                            <X className="w-3 h-3" />
                        </button>
                    </span>
                ))}
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onFocus={() => setShowSuggestions(true)}
                    onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
                    onKeyDown={(e) => {
                        if (e.key === 'Enter' && input.trim()) {
                            addTag(input.trim());
                        }
                    }}
                    placeholder={tags.length === 0 ? 'Add tags...' : ''}
                    className="flex-1 min-w-[80px] bg-transparent border-none outline-none text-sm"
                />
            </div>

            {showSuggestions && suggestions.length > 0 && (
                <div className="absolute top-full left-0 right-0 mt-1 bg-surface-800 border border-surface-700 rounded-lg shadow-lg z-10 max-h-40 overflow-y-auto">
                    {suggestions.map((tag) => (
                        <button
                            key={tag}
                            onClick={() => addTag(tag)}
                            className="w-full px-3 py-1.5 text-left text-sm hover:bg-surface-700 flex items-center gap-2"
                        >
                            <Tag className="w-3 h-3 text-surface-400" />
                            {tag}
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
};

// Asset card for grid view
const AssetCard: React.FC<{
    asset: Asset;
    isSelected: boolean;
    onSelect: (multiSelect: boolean) => void;
    onOpen: () => void;
    onFavoriteToggle: () => void;
}> = ({ asset, isSelected, onSelect, onOpen, onFavoriteToggle }) => (
    <div
        className={cn(
            'relative group rounded-lg overflow-hidden border-2 transition-all cursor-pointer',
            isSelected
                ? 'border-brand-500 bg-brand-500/10'
                : 'border-transparent hover:border-surface-600 bg-surface-800'
        )}
        onClick={(e) => onSelect(e.metaKey || e.ctrlKey)}
        onDoubleClick={onOpen}
    >
        {/* Thumbnail */}
        <div className="aspect-square bg-surface-700 flex items-center justify-center">
            {asset.thumbnailUrl ? (
                <img
                    src={asset.thumbnailUrl}
                    alt={asset.name}
                    className="w-full h-full object-cover"
                />
            ) : (
                <div className="w-12 h-12">{TYPE_ICONS[asset.type]}</div>
            )}
        </div>

        {/* Selection checkbox */}
        <div
            className={cn(
                'absolute top-2 left-2 w-5 h-5 rounded border-2 transition-all flex items-center justify-center',
                isSelected
                    ? 'bg-brand-500 border-brand-500 opacity-100'
                    : 'bg-surface-900/50 border-surface-500 opacity-0 group-hover:opacity-100'
            )}
        >
            {isSelected && <Check className="w-3 h-3 text-white" />}
        </div>

        {/* Favorite button */}
        <button
            onClick={(e) => {
                e.stopPropagation();
                onFavoriteToggle();
            }}
            className={cn(
                'absolute top-2 right-2 p-1 rounded transition-all',
                asset.isFavorite
                    ? 'text-yellow-400 opacity-100'
                    : 'text-surface-400 opacity-0 group-hover:opacity-100 hover:text-yellow-400'
            )}
        >
            {asset.isFavorite ? <Star className="w-4 h-4 fill-current" /> : <StarOff className="w-4 h-4" />}
        </button>

        {/* Info */}
        <div className="p-2">
            <div className="flex items-center gap-1 mb-1">
                {TYPE_ICONS[asset.type]}
                <span className="text-xs font-medium truncate flex-1">{asset.name}</span>
            </div>
            <div className="flex items-center gap-2 text-xs text-surface-500">
                <span>{formatSize(asset.size)}</span>
                {asset.tags.length > 0 && (
                    <span className="flex items-center gap-1">
                        <Tag className="w-3 h-3" />
                        {asset.tags.length}
                    </span>
                )}
            </div>
        </div>
    </div>
);

// Asset row for list view
const AssetRow: React.FC<{
    asset: Asset;
    isSelected: boolean;
    onSelect: (multiSelect: boolean) => void;
    onOpen: () => void;
    onFavoriteToggle: () => void;
    onTagsUpdate: (tags: string[]) => void;
    availableTags: string[];
}> = ({ asset, isSelected, onSelect, onOpen, onFavoriteToggle, onTagsUpdate, availableTags }) => {
    const [showTagEditor, setShowTagEditor] = React.useState(false);

    return (
        <div
            className={cn(
                'flex items-center gap-3 px-3 py-2 border-b border-surface-700 hover:bg-surface-800 cursor-pointer',
                isSelected && 'bg-brand-500/10'
            )}
            onClick={(e) => onSelect(e.metaKey || e.ctrlKey)}
            onDoubleClick={onOpen}
        >
            {/* Checkbox */}
            <div
                className={cn(
                    'w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0',
                    isSelected ? 'bg-brand-500 border-brand-500' : 'border-surface-600'
                )}
            >
                {isSelected && <Check className="w-3 h-3 text-white" />}
            </div>

            {/* Icon */}
            {TYPE_ICONS[asset.type]}

            {/* Name */}
            <span className="flex-1 text-sm truncate">{asset.name}</span>

            {/* Tags */}
            <div className="flex items-center gap-1 max-w-[200px]">
                {asset.tags.slice(0, 3).map((tag) => (
                    <span key={tag} className="px-1.5 py-0.5 bg-surface-700 rounded text-xs">
                        {tag}
                    </span>
                ))}
                {asset.tags.length > 3 && (
                    <span className="text-xs text-surface-500">+{asset.tags.length - 3}</span>
                )}
                <button
                    onClick={(e) => {
                        e.stopPropagation();
                        setShowTagEditor(!showTagEditor);
                    }}
                    className="p-1 hover:bg-surface-700 rounded"
                >
                    <Tag className="w-3 h-3 text-surface-400" />
                </button>
            </div>

            {/* Size */}
            <span className="text-xs text-surface-500 w-20 text-right">{formatSize(asset.size)}</span>

            {/* Date */}
            <span className="text-xs text-surface-500 w-24">
                {asset.updatedAt.toLocaleDateString()}
            </span>

            {/* Favorite */}
            <button
                onClick={(e) => {
                    e.stopPropagation();
                    onFavoriteToggle();
                }}
                className={cn(
                    'p-1 rounded',
                    asset.isFavorite ? 'text-yellow-400' : 'text-surface-500 hover:text-yellow-400'
                )}
            >
                {asset.isFavorite ? <Star className="w-4 h-4 fill-current" /> : <StarOff className="w-4 h-4" />}
            </button>
        </div>
    );
};

export const AssetLibrary: React.FC<AssetLibraryProps> = ({
    assets,
    selectedIds,
    onSelect,
    onAssetOpen,
    onTagsUpdate,
    onFavoriteToggle,
    onDelete,
    onMove,
    onDuplicate,
    availableTags,
    folders,
    className = '',
}) => {
    const [viewMode, setViewMode] = React.useState<ViewMode>('grid');
    const [searchQuery, setSearchQuery] = React.useState('');
    const [filterType, setFilterType] = React.useState<AssetType | 'all'>('all');
    const [filterTag, setFilterTag] = React.useState<string | null>(null);
    const [sortField, setSortField] = React.useState<SortField>('updatedAt');
    const [sortDirection, setSortDirection] = React.useState<SortDirection>('desc');
    const [showFilters, setShowFilters] = React.useState(false);
    const [showBulkActions, setShowBulkActions] = React.useState(false);

    // Filter and sort assets
    const filteredAssets = React.useMemo(() => {
        let result = [...assets];

        // Search
        if (searchQuery) {
            const query = searchQuery.toLowerCase();
            result = result.filter(
                (a) =>
                    a.name.toLowerCase().includes(query) ||
                    a.tags.some((t) => t.toLowerCase().includes(query))
            );
        }

        // Type filter
        if (filterType !== 'all') {
            result = result.filter((a) => a.type === filterType);
        }

        // Tag filter
        if (filterTag) {
            result = result.filter((a) => a.tags.includes(filterTag));
        }

        // Sort
        result.sort((a, b) => {
            let comparison = 0;
            switch (sortField) {
                case 'name':
                    comparison = a.name.localeCompare(b.name);
                    break;
                case 'size':
                    comparison = a.size - b.size;
                    break;
                case 'createdAt':
                    comparison = a.createdAt.getTime() - b.createdAt.getTime();
                    break;
                case 'updatedAt':
                    comparison = a.updatedAt.getTime() - b.updatedAt.getTime();
                    break;
                case 'type':
                    comparison = a.type.localeCompare(b.type);
                    break;
            }
            return sortDirection === 'asc' ? comparison : -comparison;
        });

        return result;
    }, [assets, searchQuery, filterType, filterTag, sortField, sortDirection]);

    // Selection handlers
    const handleSelect = (assetId: string, multiSelect: boolean) => {
        if (multiSelect) {
            if (selectedIds.includes(assetId)) {
                onSelect(selectedIds.filter((id) => id !== assetId));
            } else {
                onSelect([...selectedIds, assetId]);
            }
        } else {
            onSelect([assetId]);
        }
    };

    const handleSelectAll = () => {
        if (selectedIds.length === filteredAssets.length) {
            onSelect([]);
        } else {
            onSelect(filteredAssets.map((a) => a.id));
        }
    };

    // Toggle sort
    const handleSort = (field: SortField) => {
        if (sortField === field) {
            setSortDirection((d) => (d === 'asc' ? 'desc' : 'asc'));
        } else {
            setSortField(field);
            setSortDirection('asc');
        }
    };

    return (
        <div className={cn('flex flex-col bg-surface-900 rounded-xl', className)}>
            {/* Toolbar */}
            <div className="flex items-center gap-3 p-3 border-b border-surface-700">
                {/* Search */}
                <div className="relative flex-1 max-w-md">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-500" />
                    <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder="Search assets..."
                        className="w-full pl-9 pr-3 py-2 bg-surface-800 border border-surface-700 rounded-lg text-sm focus:border-brand-500 focus:outline-none"
                    />
                </div>

                {/* Filters toggle */}
                <button
                    onClick={() => setShowFilters(!showFilters)}
                    className={cn(
                        'flex items-center gap-1 px-3 py-2 rounded-lg text-sm transition-colors',
                        showFilters ? 'bg-brand-500/20 text-brand-400' : 'bg-surface-800 hover:bg-surface-700'
                    )}
                >
                    <Filter className="w-4 h-4" />
                    Filters
                    {(filterType !== 'all' || filterTag) && (
                        <span className="w-2 h-2 rounded-full bg-brand-500" />
                    )}
                </button>

                {/* View mode */}
                <div className="flex items-center bg-surface-800 rounded-lg p-1">
                    <button
                        onClick={() => setViewMode('grid')}
                        className={cn(
                            'p-1.5 rounded',
                            viewMode === 'grid' ? 'bg-surface-700' : 'hover:bg-surface-700'
                        )}
                    >
                        <Grid className="w-4 h-4" />
                    </button>
                    <button
                        onClick={() => setViewMode('list')}
                        className={cn(
                            'p-1.5 rounded',
                            viewMode === 'list' ? 'bg-surface-700' : 'hover:bg-surface-700'
                        )}
                    >
                        <List className="w-4 h-4" />
                    </button>
                </div>

                {/* Sort */}
                <button
                    onClick={() => handleSort(sortField)}
                    className="flex items-center gap-1 px-3 py-2 bg-surface-800 hover:bg-surface-700 rounded-lg text-sm"
                >
                    {sortDirection === 'asc' ? <SortAsc className="w-4 h-4" /> : <SortDesc className="w-4 h-4" />}
                    {sortField}
                </button>
            </div>

            {/* Filter bar */}
            {showFilters && (
                <div className="flex items-center gap-3 px-3 py-2 bg-surface-800 border-b border-surface-700">
                    {/* Type filter */}
                    <select
                        value={filterType}
                        onChange={(e) => setFilterType(e.target.value as AssetType | 'all')}
                        className="px-2 py-1 bg-surface-700 border border-surface-600 rounded text-sm"
                    >
                        <option value="all">All Types</option>
                        <option value="image">Images</option>
                        <option value="video">Videos</option>
                        <option value="audio">Audio</option>
                        <option value="document">Documents</option>
                    </select>

                    {/* Tag filter */}
                    <select
                        value={filterTag || ''}
                        onChange={(e) => setFilterTag(e.target.value || null)}
                        className="px-2 py-1 bg-surface-700 border border-surface-600 rounded text-sm"
                    >
                        <option value="">All Tags</option>
                        {availableTags.map((tag) => (
                            <option key={tag} value={tag}>{tag}</option>
                        ))}
                    </select>

                    {/* Clear filters */}
                    {(filterType !== 'all' || filterTag) && (
                        <button
                            onClick={() => {
                                setFilterType('all');
                                setFilterTag(null);
                            }}
                            className="text-xs text-surface-400 hover:text-white"
                        >
                            Clear filters
                        </button>
                    )}
                </div>
            )}

            {/* Bulk actions bar */}
            {selectedIds.length > 0 && (
                <div className="flex items-center gap-3 px-3 py-2 bg-brand-500/10 border-b border-brand-500/30">
                    <span className="text-sm">
                        {selectedIds.length} selected
                    </span>
                    <div className="flex items-center gap-1">
                        <button
                            onClick={() => onDelete(selectedIds)}
                            className="p-1.5 hover:bg-red-500/20 rounded text-red-400"
                            title="Delete"
                        >
                            <Trash2 className="w-4 h-4" />
                        </button>
                        {onDuplicate && (
                            <button
                                onClick={() => onDuplicate(selectedIds)}
                                className="p-1.5 hover:bg-surface-700 rounded"
                                title="Duplicate"
                            >
                                <Copy className="w-4 h-4" />
                            </button>
                        )}
                        {onMove && (
                            <button
                                onClick={() => setShowBulkActions(!showBulkActions)}
                                className="p-1.5 hover:bg-surface-700 rounded"
                                title="Move"
                            >
                                <Move className="w-4 h-4" />
                            </button>
                        )}
                    </div>
                    <button
                        onClick={() => onSelect([])}
                        className="ml-auto text-xs text-surface-400 hover:text-white"
                    >
                        Clear selection
                    </button>
                </div>
            )}

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-3">
                {filteredAssets.length === 0 ? (
                    <div className="text-center py-12 text-surface-500">
                        <Folder className="w-12 h-12 mx-auto mb-3 opacity-50" />
                        <p>No assets found</p>
                    </div>
                ) : viewMode === 'grid' ? (
                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
                        {filteredAssets.map((asset) => (
                            <AssetCard
                                key={asset.id}
                                asset={asset}
                                isSelected={selectedIds.includes(asset.id)}
                                onSelect={(multi) => handleSelect(asset.id, multi)}
                                onOpen={() => onAssetOpen(asset)}
                                onFavoriteToggle={() => onFavoriteToggle(asset.id)}
                            />
                        ))}
                    </div>
                ) : (
                    <div className="border border-surface-700 rounded-lg overflow-hidden">
                        {/* List header */}
                        <div className="flex items-center gap-3 px-3 py-2 bg-surface-800 text-xs font-medium text-surface-400">
                            <button
                                onClick={handleSelectAll}
                                className="w-5 h-5 rounded border-2 border-surface-600 flex items-center justify-center"
                            >
                                {selectedIds.length === filteredAssets.length && <Check className="w-3 h-3" />}
                            </button>
                            <span className="w-4" />
                            <button onClick={() => handleSort('name')} className="flex-1 text-left hover:text-white">
                                Name
                            </button>
                            <span className="w-[200px]">Tags</span>
                            <button onClick={() => handleSort('size')} className="w-20 text-right hover:text-white">
                                Size
                            </button>
                            <button onClick={() => handleSort('updatedAt')} className="w-24 hover:text-white">
                                Modified
                            </button>
                            <span className="w-8" />
                        </div>

                        {/* List items */}
                        {filteredAssets.map((asset) => (
                            <AssetRow
                                key={asset.id}
                                asset={asset}
                                isSelected={selectedIds.includes(asset.id)}
                                onSelect={(multi) => handleSelect(asset.id, multi)}
                                onOpen={() => onAssetOpen(asset)}
                                onFavoriteToggle={() => onFavoriteToggle(asset.id)}
                                onTagsUpdate={(tags) => onTagsUpdate(asset.id, tags)}
                                availableTags={availableTags}
                            />
                        ))}
                    </div>
                )}
            </div>

            {/* Status bar */}
            <div className="flex items-center justify-between px-3 py-2 border-t border-surface-700 text-xs text-surface-500">
                <span>{filteredAssets.length} items</span>
                <span>{formatSize(filteredAssets.reduce((sum, a) => sum + a.size, 0))} total</span>
            </div>
        </div>
    );
};

// Hook for asset library state
export function useAssetLibrary(initialAssets: Asset[] = []) {
    const [assets, setAssets] = React.useState<Asset[]>(initialAssets);
    const [selectedIds, setSelectedIds] = React.useState<string[]>([]);
    const [availableTags, setAvailableTags] = React.useState<string[]>([]);

    // Extract unique tags from assets
    React.useEffect(() => {
        const tags = new Set<string>();
        assets.forEach((a) => a.tags.forEach((t) => tags.add(t)));
        setAvailableTags(Array.from(tags).sort());
    }, [assets]);

    const updateTags = React.useCallback((assetId: string, tags: string[]) => {
        setAssets((prev) =>
            prev.map((a) => (a.id === assetId ? { ...a, tags } : a))
        );
    }, []);

    const toggleFavorite = React.useCallback((assetId: string) => {
        setAssets((prev) =>
            prev.map((a) => (a.id === assetId ? { ...a, isFavorite: !a.isFavorite } : a))
        );
    }, []);

    const deleteAssets = React.useCallback((ids: string[]) => {
        setAssets((prev) => prev.filter((a) => !ids.includes(a.id)));
        setSelectedIds((prev) => prev.filter((id) => !ids.includes(id)));
    }, []);

    const duplicateAssets = React.useCallback((ids: string[]) => {
        setAssets((prev) => {
            const toDuplicate = prev.filter((a) => ids.includes(a.id));
            const duplicates = toDuplicate.map((a) => ({
                ...a,
                id: `${a.id}-copy-${Date.now()}`,
                name: `${a.name} (copy)`,
                createdAt: new Date(),
                updatedAt: new Date(),
            }));
            return [...prev, ...duplicates];
        });
    }, []);

    return {
        assets,
        selectedIds,
        availableTags,
        setAssets,
        setSelectedIds,
        updateTags,
        toggleFavorite,
        deleteAssets,
        duplicateAssets,
    };
}
