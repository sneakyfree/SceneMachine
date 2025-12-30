/**
 * Command palette component (Cmd+K).
 * Provides quick access to navigation, actions, and search.
 */

import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Search,
  Home,
  Settings,
  HelpCircle,
  BarChart3,
  Archive,
  Film,
  Users,
  Clapperboard,
  Sparkles,
  Download,
  Clock,
  FolderOpen,
  Plus,
  Play,
  Pause,
  Moon,
  Sun,
  X,
  Command,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { useProjectStore } from '../stores/project-store';

interface CommandItem {
  id: string;
  label: string;
  description?: string;
  icon: React.ReactNode;
  shortcut?: string;
  action: () => void;
  category: 'navigation' | 'project' | 'actions' | 'recent' | 'settings';
  keywords?: string[];
}

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

export function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const navigate = useNavigate();
  const { currentProject } = useProjectStore();
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Fetch projects for search
  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: () =>
      window.electronAPI?.backendRequest<any[]>('projects.list', {}) ?? [],
    enabled: isOpen,
  });

  // Build command list
  const commands = useMemo<CommandItem[]>(() => {
    const items: CommandItem[] = [
      // Navigation
      {
        id: 'nav-home',
        label: 'Go to Projects',
        description: 'View all projects',
        icon: <Home className="w-4 h-4" />,
        shortcut: 'Ctrl+H',
        action: () => { navigate('/'); onClose(); },
        category: 'navigation',
        keywords: ['home', 'dashboard'],
      },
      {
        id: 'nav-settings',
        label: 'Open Settings',
        description: 'Configure application settings',
        icon: <Settings className="w-4 h-4" />,
        shortcut: 'Ctrl+,',
        action: () => { navigate('/settings'); onClose(); },
        category: 'navigation',
        keywords: ['preferences', 'config'],
      },
      {
        id: 'nav-analytics',
        label: 'View Analytics',
        description: 'Usage statistics and metrics',
        icon: <BarChart3 className="w-4 h-4" />,
        action: () => { navigate('/analytics'); onClose(); },
        category: 'navigation',
        keywords: ['stats', 'metrics', 'usage'],
      },
      {
        id: 'nav-archive',
        label: 'Project Archive',
        description: 'Import and export projects',
        icon: <Archive className="w-4 h-4" />,
        action: () => { navigate('/archive'); onClose(); },
        category: 'navigation',
        keywords: ['import', 'export', 'backup'],
      },
      {
        id: 'nav-help',
        label: 'Help & Documentation',
        description: 'Get help using SceneMachine',
        icon: <HelpCircle className="w-4 h-4" />,
        action: () => { navigate('/help'); onClose(); },
        category: 'navigation',
        keywords: ['docs', 'support', 'faq'],
      },

      // Actions
      {
        id: 'action-new-project',
        label: 'Create New Project',
        description: 'Start a new screenplay project',
        icon: <Plus className="w-4 h-4" />,
        action: () => {
          window.dispatchEvent(new CustomEvent('app:new-project'));
          onClose();
        },
        category: 'actions',
        keywords: ['add', 'create', 'start'],
      },
    ];

    // Add current project navigation if available
    if (currentProject) {
      items.push(
        {
          id: 'proj-overview',
          label: `${currentProject.name}: Overview`,
          description: 'Project dashboard',
          icon: <Film className="w-4 h-4" />,
          shortcut: 'Ctrl+1',
          action: () => { navigate(`/project/${currentProject.id}`); onClose(); },
          category: 'project',
          keywords: ['dashboard', 'project'],
        },
        {
          id: 'proj-characters',
          label: `${currentProject.name}: Characters`,
          description: 'Character lab',
          icon: <Users className="w-4 h-4" />,
          shortcut: 'Ctrl+2',
          action: () => { navigate(`/project/${currentProject.id}/characters`); onClose(); },
          category: 'project',
          keywords: ['actors', 'cast'],
        },
        {
          id: 'proj-scenes',
          label: `${currentProject.name}: Scene Planning`,
          description: 'Plan and edit scenes',
          icon: <Clapperboard className="w-4 h-4" />,
          shortcut: 'Ctrl+3',
          action: () => { navigate(`/project/${currentProject.id}/scenes`); onClose(); },
          category: 'project',
          keywords: ['shots', 'breakdown'],
        },
        {
          id: 'proj-generate',
          label: `${currentProject.name}: Generation`,
          description: 'Generate video shots',
          icon: <Sparkles className="w-4 h-4" />,
          shortcut: 'Ctrl+4',
          action: () => { navigate(`/project/${currentProject.id}/generate`); onClose(); },
          category: 'project',
          keywords: ['ai', 'create', 'video'],
        },
        {
          id: 'proj-timeline',
          label: `${currentProject.name}: Timeline`,
          description: 'Video timeline editor',
          icon: <Clock className="w-4 h-4" />,
          action: () => { navigate(`/project/${currentProject.id}/timeline`); onClose(); },
          category: 'project',
          keywords: ['edit', 'arrange'],
        },
        {
          id: 'proj-export',
          label: `${currentProject.name}: Export`,
          description: 'Export final video',
          icon: <Download className="w-4 h-4" />,
          shortcut: 'Ctrl+5',
          action: () => { navigate(`/project/${currentProject.id}/export`); onClose(); },
          category: 'project',
          keywords: ['render', 'output'],
        }
      );
    }

    // Add recent projects
    if (projects) {
      const recentProjects = projects.slice(0, 5);
      recentProjects.forEach((project) => {
        if (project.id !== currentProject?.id) {
          items.push({
            id: `recent-${project.id}`,
            label: project.name,
            description: `${project.state} - ${project.sceneCount || 0} scenes`,
            icon: <FolderOpen className="w-4 h-4" />,
            action: () => { navigate(`/project/${project.id}`); onClose(); },
            category: 'recent',
            keywords: ['project', 'open'],
          });
        }
      });
    }

    return items;
  }, [currentProject, projects, navigate, onClose]);

  // Filter commands based on query
  const filteredCommands = useMemo(() => {
    if (!query.trim()) return commands;

    const lowerQuery = query.toLowerCase();
    return commands.filter((cmd) => {
      const matchLabel = cmd.label.toLowerCase().includes(lowerQuery);
      const matchDesc = cmd.description?.toLowerCase().includes(lowerQuery);
      const matchKeywords = cmd.keywords?.some((k) => k.includes(lowerQuery));
      return matchLabel || matchDesc || matchKeywords;
    });
  }, [commands, query]);

  // Group commands by category
  const groupedCommands = useMemo(() => {
    const groups: Record<string, CommandItem[]> = {
      navigation: [],
      project: [],
      actions: [],
      recent: [],
      settings: [],
    };

    filteredCommands.forEach((cmd) => {
      groups[cmd.category].push(cmd);
    });

    return groups;
  }, [filteredCommands]);

  // Reset selection when query changes
  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  // Focus input when opened
  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  // Handle keyboard navigation
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    const totalItems = filteredCommands.length;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex((prev) => (prev + 1) % totalItems);
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex((prev) => (prev - 1 + totalItems) % totalItems);
        break;
      case 'Enter':
        e.preventDefault();
        if (filteredCommands[selectedIndex]) {
          filteredCommands[selectedIndex].action();
        }
        break;
      case 'Escape':
        e.preventDefault();
        onClose();
        break;
    }
  }, [filteredCommands, selectedIndex, onClose]);

  // Scroll selected item into view
  useEffect(() => {
    const selectedElement = listRef.current?.querySelector(`[data-index="${selectedIndex}"]`);
    selectedElement?.scrollIntoView({ block: 'nearest' });
  }, [selectedIndex]);

  if (!isOpen) return null;

  const categoryLabels: Record<string, string> = {
    navigation: 'Navigation',
    project: 'Current Project',
    actions: 'Actions',
    recent: 'Recent Projects',
    settings: 'Settings',
  };

  let globalIndex = 0;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh] bg-black/50 backdrop-blur-sm"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Command palette"
    >
      <div
        className="w-full max-w-xl bg-surface-900 border border-surface-700 rounded-xl shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
        role="combobox"
        aria-expanded="true"
        aria-haspopup="listbox"
        aria-owns="command-list"
      >
        {/* Search Input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-surface-700">
          <Search className="w-5 h-5 text-surface-400" aria-hidden="true" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search commands..."
            className="flex-1 bg-transparent border-none outline-none text-white placeholder-surface-500"
            role="searchbox"
            aria-label="Search commands"
            aria-autocomplete="list"
            aria-controls="command-list"
            aria-activedescendant={filteredCommands[selectedIndex]?.id}
          />
          <kbd className="px-2 py-1 bg-surface-800 rounded text-xs text-surface-400 font-mono" aria-hidden="true">
            esc
          </kbd>
        </div>

        {/* Results */}
        <div
          ref={listRef}
          id="command-list"
          role="listbox"
          aria-label="Command results"
          className="max-h-80 overflow-y-auto p-2"
        >
          {filteredCommands.length === 0 ? (
            <div className="py-8 text-center text-surface-400" role="status" aria-live="polite">
              <Search className="w-8 h-8 mx-auto mb-2 opacity-50" aria-hidden="true" />
              <p>No commands found</p>
              <p className="text-sm text-surface-500">Try a different search term</p>
            </div>
          ) : (
            Object.entries(groupedCommands).map(([category, items]) => {
              if (items.length === 0) return null;

              return (
                <div key={category} className="mb-2" role="group" aria-labelledby={`group-${category}`}>
                  <div
                    id={`group-${category}`}
                    className="px-2 py-1 text-xs font-medium text-surface-500 uppercase"
                    role="presentation"
                  >
                    {categoryLabels[category]}
                  </div>
                  {items.map((cmd) => {
                    const index = globalIndex++;
                    const isSelected = index === selectedIndex;

                    return (
                      <button
                        key={cmd.id}
                        id={cmd.id}
                        data-index={index}
                        onClick={cmd.action}
                        role="option"
                        aria-selected={isSelected}
                        className={cn(
                          'w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left transition-colors',
                          isSelected
                            ? 'bg-brand-500/20 text-brand-300'
                            : 'text-surface-200 hover:bg-surface-800'
                        )}
                      >
                        <div
                          className={cn(
                            'p-1.5 rounded-md',
                            isSelected ? 'bg-brand-500/20' : 'bg-surface-800'
                          )}
                          aria-hidden="true"
                        >
                          {cmd.icon}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="font-medium truncate">{cmd.label}</div>
                          {cmd.description && (
                            <div className="text-sm text-surface-400 truncate">
                              {cmd.description}
                            </div>
                          )}
                        </div>
                        {cmd.shortcut && (
                          <kbd
                            className="px-2 py-1 bg-surface-800 rounded text-xs text-surface-400 font-mono"
                            aria-label={`Keyboard shortcut: ${cmd.shortcut}`}
                          >
                            {cmd.shortcut.replace('Ctrl', navigator.platform.includes('Mac') ? '⌘' : 'Ctrl')}
                          </kbd>
                        )}
                      </button>
                    );
                  })}
                </div>
              );
            })
          )}
        </div>

        {/* Footer - Keyboard hints */}
        <div
          className="flex items-center justify-between px-4 py-2 border-t border-surface-700 bg-surface-800/50"
          aria-hidden="true"
        >
          <div className="flex items-center gap-4 text-xs text-surface-400">
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-surface-700 rounded">↑</kbd>
              <kbd className="px-1.5 py-0.5 bg-surface-700 rounded">↓</kbd>
              to navigate
            </span>
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-surface-700 rounded">↵</kbd>
              to select
            </span>
          </div>
          <div className="flex items-center gap-1 text-xs text-surface-500">
            <Command className="w-3 h-3" />
            <span>K to open</span>
          </div>
        </div>

        {/* Screen reader announcements */}
        <div className="sr-only" role="status" aria-live="polite" aria-atomic="true">
          {filteredCommands.length === 0
            ? 'No commands found'
            : `${filteredCommands.length} commands available. Use arrow keys to navigate.`
          }
        </div>
      </div>
    </div>
  );
}

/**
 * Hook to manage command palette state and keyboard shortcut.
 */
export function useCommandPalette() {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd+K or Ctrl+K
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return {
    isOpen,
    open: () => setIsOpen(true),
    close: () => setIsOpen(false),
    toggle: () => setIsOpen((prev) => !prev),
  };
}
