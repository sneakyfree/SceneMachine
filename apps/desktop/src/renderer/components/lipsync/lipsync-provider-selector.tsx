/**
 * LipSyncProviderSelector Component
 * Dropdown for selecting lip sync provider with status indicators
 */

import React from 'react';
import { Cpu, Zap, ChevronDown, Check, AlertCircle, Loader2 } from 'lucide-react';
import { useLipSyncStore } from '../../stores/lipsync-store';
import { cn } from '../../lib/utils';

interface Provider {
    provider: string;
    name: string;
    available: boolean;
    description?: string;
    requiresGpu?: boolean;
}

interface LipSyncProviderSelectorProps {
    selectedProvider: string;
    onProviderChange: (provider: string) => void;
    className?: string;
    showCapabilities?: boolean;
}

// Provider metadata
const PROVIDER_INFO: Record<string, { description: string; requiresGpu: boolean; icon: React.ReactNode }> = {
    mock: {
        description: 'Testing only - no actual lip sync',
        requiresGpu: false,
        icon: <Cpu className="w-4 h-4" />,
    },
    rhubarb: {
        description: 'Phoneme extraction (analysis only)',
        requiresGpu: false,
        icon: <Cpu className="w-4 h-4" />,
    },
    wav2lip: {
        description: 'AI-based lip sync (CPU/GPU)',
        requiresGpu: false,
        icon: <Zap className="w-4 h-4 text-yellow-500" />,
    },
    sadtalker: {
        description: 'Full talking head animation',
        requiresGpu: true,
        icon: <Zap className="w-4 h-4 text-purple-500" />,
    },
    latentsync: {
        description: 'High-quality GPU lip sync with diffusion',
        requiresGpu: true,
        icon: <Zap className="w-4 h-4 text-green-500" />,
    },
};

export const LipSyncProviderSelector: React.FC<LipSyncProviderSelectorProps> = ({
    selectedProvider,
    onProviderChange,
    className = '',
    showCapabilities = true,
}) => {
    const { providers, isLoadingProviders, fetchProviders } = useLipSyncStore();
    const [isOpen, setIsOpen] = React.useState(false);

    // Fetch providers on mount
    React.useEffect(() => {
        if (providers.length === 0 && !isLoadingProviders) {
            fetchProviders();
        }
    }, [providers.length, isLoadingProviders, fetchProviders]);

    const selectedProviderInfo = providers.find((p) => p.provider === selectedProvider);
    const selectedMeta = PROVIDER_INFO[selectedProvider] || PROVIDER_INFO.mock;

    const handleSelect = (provider: Provider) => {
        if (provider.available) {
            onProviderChange(provider.provider);
            setIsOpen(false);
        }
    };

    if (isLoadingProviders) {
        return (
            <div className={cn('flex items-center gap-2 px-3 py-2 bg-surface-800 rounded-lg', className)}>
                <Loader2 className="w-4 h-4 animate-spin text-surface-400" />
                <span className="text-sm text-surface-400">Loading providers...</span>
            </div>
        );
    }

    return (
        <div className={cn('relative', className)}>
            {/* Selected Provider Button */}
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center justify-between w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg hover:border-surface-600 transition-colors"
            >
                <div className="flex items-center gap-2">
                    {selectedMeta.icon}
                    <div className="text-left">
                        <div className="text-sm font-medium">
                            {selectedProviderInfo?.name || selectedProvider}
                        </div>
                        {showCapabilities && (
                            <div className="text-xs text-surface-500">
                                {selectedMeta.description}
                            </div>
                        )}
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    {selectedMeta.requiresGpu && (
                        <span className="px-1.5 py-0.5 text-[10px] font-medium bg-green-500/20 text-green-400 rounded">
                            GPU
                        </span>
                    )}
                    <ChevronDown
                        className={cn(
                            'w-4 h-4 text-surface-400 transition-transform',
                            isOpen && 'rotate-180'
                        )}
                    />
                </div>
            </button>

            {/* Dropdown */}
            {isOpen && (
                <>
                    {/* Backdrop */}
                    <div
                        className="fixed inset-0 z-10"
                        onClick={() => setIsOpen(false)}
                    />

                    {/* Menu */}
                    <div className="absolute top-full left-0 right-0 mt-1 bg-surface-800 border border-surface-700 rounded-lg shadow-xl z-20 overflow-hidden">
                        {providers.length > 0 ? (
                            providers.map((provider) => {
                                const meta = PROVIDER_INFO[provider.provider] || PROVIDER_INFO.mock;
                                const isSelected = provider.provider === selectedProvider;

                                return (
                                    <button
                                        key={provider.provider}
                                        onClick={() => handleSelect(provider)}
                                        disabled={!provider.available}
                                        className={cn(
                                            'flex items-center justify-between w-full px-3 py-2.5 text-left transition-colors',
                                            isSelected
                                                ? 'bg-brand-500/10'
                                                : provider.available
                                                    ? 'hover:bg-surface-700'
                                                    : 'opacity-50 cursor-not-allowed'
                                        )}
                                    >
                                        <div className="flex items-center gap-2">
                                            {meta.icon}
                                            <div>
                                                <div className="text-sm font-medium flex items-center gap-2">
                                                    {provider.name}
                                                    {!provider.available && (
                                                        <AlertCircle className="w-3 h-3 text-red-400" />
                                                    )}
                                                </div>
                                                <div className="text-xs text-surface-500">
                                                    {meta.description}
                                                </div>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            {meta.requiresGpu && (
                                                <span className="px-1.5 py-0.5 text-[10px] font-medium bg-green-500/20 text-green-400 rounded">
                                                    GPU
                                                </span>
                                            )}
                                            {isSelected && (
                                                <Check className="w-4 h-4 text-brand-400" />
                                            )}
                                        </div>
                                    </button>
                                );
                            })
                        ) : (
                            <div className="px-3 py-4 text-center text-sm text-surface-500">
                                No providers available
                            </div>
                        )}
                    </div>
                </>
            )}
        </div>
    );
};
