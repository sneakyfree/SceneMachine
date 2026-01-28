/**
 * AudioLibraryPanel Component
 * Collapsible panel for browsing and dragging audio to timeline
 */

import React from 'react';
import { Music, Volume2, ChevronDown, ChevronRight, Search, FolderOpen } from 'lucide-react';
import { cn } from '../../lib/utils';
import { DraggableAudioItem, AudioItem } from './draggable-audio-item';

interface AudioLibraryPanelProps {
    isOpen: boolean;
    onToggle: () => void;
    onAudioSelect?: (item: AudioItem) => void;
    className?: string;
}

// Mock audio items - in production, these would come from the audio store
const MOCK_AUDIO_ITEMS: AudioItem[] = [
    { id: 'dia-1', name: 'Character A Dialogue', type: 'dialogue', duration: 3.5, src: '/audio/dia-1.wav' },
    { id: 'dia-2', name: 'Character B Response', type: 'dialogue', duration: 2.8, src: '/audio/dia-2.wav' },
    { id: 'mus-1', name: 'Cinematic Theme', type: 'music', duration: 120, src: '/audio/theme.mp3' },
    { id: 'mus-2', name: 'Ambient Background', type: 'music', duration: 180, src: '/audio/ambient.mp3' },
    { id: 'sfx-1', name: 'Footsteps', type: 'sfx', duration: 1.5, src: '/audio/footsteps.wav' },
    { id: 'sfx-2', name: 'Door Slam', type: 'sfx', duration: 0.8, src: '/audio/door.wav' },
    { id: 'sfx-3', name: 'Thunder', type: 'sfx', duration: 4.2, src: '/audio/thunder.wav' },
    { id: 'vo-1', name: 'Narrator Intro', type: 'voiceover', duration: 8.5, src: '/audio/narrator.wav' },
];

type AudioCategory = 'all' | 'dialogue' | 'music' | 'sfx' | 'voiceover';

const CATEGORIES: { id: AudioCategory; label: string; icon: React.ReactNode }[] = [
    { id: 'all', label: 'All Audio', icon: <FolderOpen className="w-4 h-4" /> },
    { id: 'dialogue', label: 'Dialogue', icon: <Volume2 className="w-4 h-4" /> },
    { id: 'music', label: 'Music', icon: <Music className="w-4 h-4" /> },
    { id: 'sfx', label: 'SFX', icon: <Volume2 className="w-4 h-4" /> },
    { id: 'voiceover', label: 'Voiceover', icon: <Volume2 className="w-4 h-4" /> },
];

export const AudioLibraryPanel: React.FC<AudioLibraryPanelProps> = ({
    isOpen,
    onToggle,
    onAudioSelect,
    className = '',
}) => {
    const [searchQuery, setSearchQuery] = React.useState('');
    const [selectedCategory, setSelectedCategory] = React.useState<AudioCategory>('all');
    const [selectedItemId, setSelectedItemId] = React.useState<string | null>(null);

    // Filter audio items
    const filteredItems = MOCK_AUDIO_ITEMS.filter((item) => {
        const matchesSearch = item.name.toLowerCase().includes(searchQuery.toLowerCase());
        const matchesCategory = selectedCategory === 'all' || item.type === selectedCategory;
        return matchesSearch && matchesCategory;
    });

    const handleItemSelect = (item: AudioItem) => {
        setSelectedItemId(item.id);
        onAudioSelect?.(item);
    };

    return (
        <div className={cn('flex flex-col bg-surface-900 border-l border-surface-700', className)}>
            {/* Header */}
            <button
                onClick={onToggle}
                className="flex items-center justify-between p-3 hover:bg-surface-800 transition-colors"
            >
                <div className="flex items-center gap-2">
                    <Music className="w-4 h-4 text-brand-400" />
                    <span className="font-medium text-sm">Audio Library</span>
                </div>
                {isOpen ? (
                    <ChevronDown className="w-4 h-4 text-surface-400" />
                ) : (
                    <ChevronRight className="w-4 h-4 text-surface-400" />
                )}
            </button>

            {/* Content */}
            {isOpen && (
                <div className="flex-1 flex flex-col overflow-hidden">
                    {/* Search */}
                    <div className="p-2">
                        <div className="relative">
                            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-500" />
                            <input
                                type="text"
                                placeholder="Search audio..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="w-full pl-8 pr-3 py-1.5 bg-surface-800 border border-surface-700 rounded text-sm focus:outline-none focus:border-brand-500"
                            />
                        </div>
                    </div>

                    {/* Categories */}
                    <div className="flex gap-1 px-2 pb-2 overflow-x-auto">
                        {CATEGORIES.map((cat) => (
                            <button
                                key={cat.id}
                                onClick={() => setSelectedCategory(cat.id)}
                                className={cn(
                                    'flex items-center gap-1 px-2 py-1 rounded text-xs whitespace-nowrap transition-colors',
                                    selectedCategory === cat.id
                                        ? 'bg-brand-500/20 text-brand-400'
                                        : 'bg-surface-800 text-surface-400 hover:bg-surface-700'
                                )}
                            >
                                {cat.icon}
                                {cat.label}
                            </button>
                        ))}
                    </div>

                    {/* Items list */}
                    <div className="flex-1 overflow-y-auto px-2 pb-2 space-y-1">
                        {filteredItems.length > 0 ? (
                            filteredItems.map((item) => (
                                <DraggableAudioItem
                                    key={item.id}
                                    item={item}
                                    isSelected={selectedItemId === item.id}
                                    onSelect={handleItemSelect}
                                    compact
                                />
                            ))
                        ) : (
                            <div className="text-center py-8 text-surface-500 text-sm">
                                No audio items found
                            </div>
                        )}
                    </div>

                    {/* Drag hint */}
                    <div className="p-2 border-t border-surface-700">
                        <p className="text-xs text-surface-500 text-center">
                            Drag items to timeline tracks
                        </p>
                    </div>
                </div>
            )}
        </div>
    );
};
