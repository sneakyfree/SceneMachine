/**
 * AssetPreview Component
 * Modal preview for assets with metadata display and quick actions
 */

import React from 'react';
import {
    X,
    Download,
    Trash2,
    Copy,
    Star,
    StarOff,
    Tag,
    ChevronLeft,
    ChevronRight,
    Play,
    Pause,
    Volume2,
    VolumeX,
    Maximize2,
    FileText,
    Image,
    Film,
    Music,
    Clock,
    HardDrive,
    Calendar,
    Edit2,
    Check,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import type { Asset, AssetType } from './asset-library';

interface AssetPreviewProps {
    asset: Asset;
    onClose: () => void;
    onNext?: () => void;
    onPrevious?: () => void;
    onFavoriteToggle: () => void;
    onDelete: () => void;
    onTagsUpdate: (tags: string[]) => void;
    onRename?: (name: string) => void;
    availableTags: string[];
    hasNext?: boolean;
    hasPrevious?: boolean;
    className?: string;
}

// Type icons
const TYPE_ICONS: Record<AssetType, React.ReactNode> = {
    image: <Image className="w-5 h-5 text-blue-400" />,
    video: <Film className="w-5 h-5 text-purple-400" />,
    audio: <Music className="w-5 h-5 text-green-400" />,
    document: <FileText className="w-5 h-5 text-yellow-400" />,
    other: <FileText className="w-5 h-5 text-surface-400" />,
};

// Format file size
const formatSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
};

// Image preview
const ImagePreview: React.FC<{ src: string; alt: string }> = ({ src, alt }) => (
    <div className="flex-1 flex items-center justify-center bg-black/50 overflow-hidden">
        <img
            src={src}
            alt={alt}
            className="max-w-full max-h-full object-contain"
        />
    </div>
);

// Video preview
const VideoPreview: React.FC<{ src: string }> = ({ src }) => {
    const [isPlaying, setIsPlaying] = React.useState(false);
    const [isMuted, setIsMuted] = React.useState(false);
    const videoRef = React.useRef<HTMLVideoElement>(null);

    const togglePlay = () => {
        if (videoRef.current) {
            if (isPlaying) {
                videoRef.current.pause();
            } else {
                videoRef.current.play();
            }
            setIsPlaying(!isPlaying);
        }
    };

    return (
        <div className="relative flex-1 flex items-center justify-center bg-black">
            <video
                ref={videoRef}
                src={src}
                muted={isMuted}
                className="max-w-full max-h-full"
                onEnded={() => setIsPlaying(false)}
            />

            {/* Controls */}
            <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-2 bg-black/80 rounded-full px-4 py-2">
                <button onClick={togglePlay} className="p-1 hover:text-brand-400">
                    {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
                </button>
                <button onClick={() => setIsMuted(!isMuted)} className="p-1 hover:text-brand-400">
                    {isMuted ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
                </button>
            </div>
        </div>
    );
};

// Audio preview
const AudioPreview: React.FC<{ src: string; name: string }> = ({ src, name }) => {
    const [isPlaying, setIsPlaying] = React.useState(false);
    const [progress, setProgress] = React.useState(0);
    const audioRef = React.useRef<HTMLAudioElement>(null);

    const togglePlay = () => {
        if (audioRef.current) {
            if (isPlaying) {
                audioRef.current.pause();
            } else {
                audioRef.current.play();
            }
            setIsPlaying(!isPlaying);
        }
    };

    React.useEffect(() => {
        const audio = audioRef.current;
        if (!audio) return;

        const handleTimeUpdate = () => {
            setProgress((audio.currentTime / audio.duration) * 100);
        };

        audio.addEventListener('timeupdate', handleTimeUpdate);
        return () => audio.removeEventListener('timeupdate', handleTimeUpdate);
    }, []);

    return (
        <div className="flex-1 flex flex-col items-center justify-center gap-6 bg-gradient-to-b from-surface-800 to-surface-900">
            <audio ref={audioRef} src={src} onEnded={() => setIsPlaying(false)} />

            {/* Icon */}
            <div className="w-32 h-32 rounded-full bg-gradient-to-br from-green-500 to-green-600 flex items-center justify-center">
                <Music className="w-16 h-16 text-white" />
            </div>

            {/* Name */}
            <h3 className="text-lg font-medium">{name}</h3>

            {/* Controls */}
            <div className="flex items-center gap-4">
                <button
                    onClick={togglePlay}
                    className="w-14 h-14 rounded-full bg-brand-500 hover:bg-brand-600 flex items-center justify-center"
                >
                    {isPlaying ? (
                        <Pause className="w-6 h-6 text-white" />
                    ) : (
                        <Play className="w-6 h-6 text-white ml-1" />
                    )}
                </button>
            </div>

            {/* Progress bar */}
            <div className="w-64 h-1 bg-surface-700 rounded-full overflow-hidden">
                <div
                    className="h-full bg-brand-500 transition-all"
                    style={{ width: `${progress}%` }}
                />
            </div>
        </div>
    );
};

// Document preview
const DocumentPreview: React.FC<{ name: string; size: number }> = ({ name, size }) => (
    <div className="flex-1 flex flex-col items-center justify-center gap-4 bg-surface-800">
        <FileText className="w-24 h-24 text-yellow-400 opacity-50" />
        <h3 className="text-lg font-medium">{name}</h3>
        <p className="text-sm text-surface-400">{formatSize(size)}</p>
        <p className="text-xs text-surface-500">Preview not available</p>
    </div>
);

export const AssetPreview: React.FC<AssetPreviewProps> = ({
    asset,
    onClose,
    onNext,
    onPrevious,
    onFavoriteToggle,
    onDelete,
    onTagsUpdate,
    onRename,
    availableTags,
    hasNext,
    hasPrevious,
    className = '',
}) => {
    const [isEditingName, setIsEditingName] = React.useState(false);
    const [editedName, setEditedName] = React.useState(asset.name);
    const [showTagInput, setShowTagInput] = React.useState(false);
    const [newTag, setNewTag] = React.useState('');

    // Handle keyboard shortcuts
    React.useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'Escape') onClose();
            if (e.key === 'ArrowRight' && onNext && hasNext) onNext();
            if (e.key === 'ArrowLeft' && onPrevious && hasPrevious) onPrevious();
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [onClose, onNext, onPrevious, hasNext, hasPrevious]);

    // Save name
    const handleSaveName = () => {
        if (editedName.trim() && onRename) {
            onRename(editedName.trim());
        }
        setIsEditingName(false);
    };

    // Add tag
    const handleAddTag = () => {
        if (newTag.trim() && !asset.tags.includes(newTag.trim())) {
            onTagsUpdate([...asset.tags, newTag.trim()]);
        }
        setNewTag('');
        setShowTagInput(false);
    };

    // Remove tag
    const handleRemoveTag = (tag: string) => {
        onTagsUpdate(asset.tags.filter((t) => t !== tag));
    };

    return (
        <div className={cn('fixed inset-0 z-50 flex', className)}>
            {/* Backdrop */}
            <div className="absolute inset-0 bg-black/80" onClick={onClose} />

            {/* Content */}
            <div className="relative flex-1 flex">
                {/* Main preview area */}
                <div className="flex-1 flex flex-col">
                    {/* Header */}
                    <div className="flex items-center justify-between p-4 bg-surface-900/80 backdrop-blur-sm">
                        <div className="flex items-center gap-3">
                            {TYPE_ICONS[asset.type]}
                            {isEditingName ? (
                                <div className="flex items-center gap-2">
                                    <input
                                        type="text"
                                        value={editedName}
                                        onChange={(e) => setEditedName(e.target.value)}
                                        onKeyDown={(e) => e.key === 'Enter' && handleSaveName()}
                                        className="px-2 py-1 bg-surface-800 border border-surface-600 rounded text-sm"
                                        autoFocus
                                    />
                                    <button onClick={handleSaveName} className="p-1 hover:text-green-400">
                                        <Check className="w-4 h-4" />
                                    </button>
                                </div>
                            ) : (
                                <h2 className="text-lg font-medium flex items-center gap-2">
                                    {asset.name}
                                    {onRename && (
                                        <button
                                            onClick={() => setIsEditingName(true)}
                                            className="p-1 hover:text-brand-400 opacity-0 group-hover:opacity-100"
                                        >
                                            <Edit2 className="w-4 h-4" />
                                        </button>
                                    )}
                                </h2>
                            )}
                        </div>

                        <div className="flex items-center gap-2">
                            <button
                                onClick={onFavoriteToggle}
                                className={cn(
                                    'p-2 rounded-lg transition-colors',
                                    asset.isFavorite ? 'text-yellow-400' : 'text-surface-400 hover:text-yellow-400'
                                )}
                            >
                                {asset.isFavorite ? (
                                    <Star className="w-5 h-5 fill-current" />
                                ) : (
                                    <StarOff className="w-5 h-5" />
                                )}
                            </button>
                            <button className="p-2 hover:bg-surface-700 rounded-lg">
                                <Download className="w-5 h-5" />
                            </button>
                            <button
                                onClick={onDelete}
                                className="p-2 hover:bg-red-500/20 text-red-400 rounded-lg"
                            >
                                <Trash2 className="w-5 h-5" />
                            </button>
                            <button onClick={onClose} className="p-2 hover:bg-surface-700 rounded-lg">
                                <X className="w-5 h-5" />
                            </button>
                        </div>
                    </div>

                    {/* Preview */}
                    {asset.type === 'image' && asset.thumbnailUrl && (
                        <ImagePreview src={asset.thumbnailUrl} alt={asset.name} />
                    )}
                    {asset.type === 'video' && asset.path && (
                        <VideoPreview src={asset.path} />
                    )}
                    {asset.type === 'audio' && asset.path && (
                        <AudioPreview src={asset.path} name={asset.name} />
                    )}
                    {(asset.type === 'document' || asset.type === 'other') && (
                        <DocumentPreview name={asset.name} size={asset.size} />
                    )}

                    {/* Navigation arrows */}
                    {hasPrevious && onPrevious && (
                        <button
                            onClick={onPrevious}
                            className="absolute left-4 top-1/2 -translate-y-1/2 p-2 bg-black/50 hover:bg-black/70 rounded-full"
                        >
                            <ChevronLeft className="w-6 h-6" />
                        </button>
                    )}
                    {hasNext && onNext && (
                        <button
                            onClick={onNext}
                            className="absolute right-[320px] top-1/2 -translate-y-1/2 p-2 bg-black/50 hover:bg-black/70 rounded-full"
                        >
                            <ChevronRight className="w-6 h-6" />
                        </button>
                    )}
                </div>

                {/* Sidebar */}
                <div className="w-80 bg-surface-900 border-l border-surface-700 overflow-y-auto">
                    <div className="p-4 space-y-6">
                        {/* File info */}
                        <div>
                            <h3 className="text-sm font-medium text-surface-400 mb-3">File Information</h3>
                            <div className="space-y-2 text-sm">
                                <div className="flex items-center gap-2">
                                    <HardDrive className="w-4 h-4 text-surface-500" />
                                    <span className="text-surface-400">Size:</span>
                                    <span>{formatSize(asset.size)}</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <Calendar className="w-4 h-4 text-surface-500" />
                                    <span className="text-surface-400">Created:</span>
                                    <span>{asset.createdAt.toLocaleDateString()}</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <Clock className="w-4 h-4 text-surface-500" />
                                    <span className="text-surface-400">Modified:</span>
                                    <span>{asset.updatedAt.toLocaleDateString()}</span>
                                </div>
                            </div>
                        </div>

                        {/* Tags */}
                        <div>
                            <h3 className="text-sm font-medium text-surface-400 mb-3 flex items-center justify-between">
                                Tags
                                <button
                                    onClick={() => setShowTagInput(!showTagInput)}
                                    className="p-1 hover:bg-surface-700 rounded"
                                >
                                    <Tag className="w-4 h-4" />
                                </button>
                            </h3>

                            <div className="flex flex-wrap gap-1">
                                {asset.tags.map((tag) => (
                                    <span
                                        key={tag}
                                        className="inline-flex items-center gap-1 px-2 py-1 bg-surface-800 rounded text-xs group"
                                    >
                                        {tag}
                                        <button
                                            onClick={() => handleRemoveTag(tag)}
                                            className="opacity-0 group-hover:opacity-100 hover:text-red-400"
                                        >
                                            <X className="w-3 h-3" />
                                        </button>
                                    </span>
                                ))}

                                {showTagInput && (
                                    <input
                                        type="text"
                                        value={newTag}
                                        onChange={(e) => setNewTag(e.target.value)}
                                        onKeyDown={(e) => e.key === 'Enter' && handleAddTag()}
                                        onBlur={() => {
                                            if (!newTag.trim()) setShowTagInput(false);
                                        }}
                                        placeholder="Add tag..."
                                        className="px-2 py-1 bg-surface-800 border border-surface-600 rounded text-xs w-20"
                                        autoFocus
                                        list="tag-suggestions"
                                    />
                                )}
                                <datalist id="tag-suggestions">
                                    {availableTags.filter((t) => !asset.tags.includes(t)).map((tag) => (
                                        <option key={tag} value={tag} />
                                    ))}
                                </datalist>
                            </div>
                        </div>

                        {/* Metadata */}
                        {asset.metadata && Object.keys(asset.metadata).length > 0 && (
                            <div>
                                <h3 className="text-sm font-medium text-surface-400 mb-3">Metadata</h3>
                                <div className="space-y-1 text-xs">
                                    {Object.entries(asset.metadata).map(([key, value]) => (
                                        <div key={key} className="flex justify-between">
                                            <span className="text-surface-500">{key}</span>
                                            <span>{String(value)}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};
