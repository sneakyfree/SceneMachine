/**
 * Clip Context Menu component.
 * Provides right-click context menu for timeline clips.
 */

import { useCallback, useEffect, useRef } from 'react';
import {
  Play,
  Trash2,
  Lock,
  Unlock,
  Eye,
  EyeOff,
  Copy,
  Scissors,
  Mic,
} from 'lucide-react';
import { cn } from '../../lib/utils';

interface ClipContextMenuProps {
  isOpen: boolean;
  position: { x: number; y: number };
  onClose: () => void;
  clipId: string;
  isLocked: boolean;
  isVisible: boolean;
  hasVideo: boolean;
  onApplyLipSync: () => void;
  onDelete: () => void;
  onToggleLock: () => void;
  onToggleVisibility: () => void;
  onDuplicate?: () => void;
  onSplit?: () => void;
  onPreview?: () => void;
}

interface MenuItemProps {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  disabled?: boolean;
  danger?: boolean;
  shortcut?: string;
}

function MenuItem({
  icon,
  label,
  onClick,
  disabled = false,
  danger = false,
  shortcut,
}: MenuItemProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'w-full flex items-center gap-3 px-3 py-2 text-sm text-left transition-colors',
        'hover:bg-surface-700 focus:bg-surface-700 focus:outline-none',
        disabled && 'opacity-50 cursor-not-allowed',
        danger && 'text-red-400 hover:bg-red-500/10'
      )}
    >
      <span className="w-4 h-4 flex-shrink-0">{icon}</span>
      <span className="flex-1">{label}</span>
      {shortcut && (
        <span className="text-xs text-surface-500 ml-2">{shortcut}</span>
      )}
    </button>
  );
}

function MenuDivider() {
  return <div className="border-t border-surface-700 my-1" />;
}

export function ClipContextMenu({
  isOpen,
  position,
  onClose,
  clipId,
  isLocked,
  isVisible,
  hasVideo,
  onApplyLipSync,
  onDelete,
  onToggleLock,
  onToggleVisibility,
  onDuplicate,
  onSplit,
  onPreview,
}: ClipContextMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null);

  // Close on click outside
  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        onClose();
      }
    };

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEscape);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [isOpen, onClose]);

  // Adjust position to keep menu in viewport
  const adjustedPosition = useCallback(() => {
    const menuWidth = 200;
    const menuHeight = 280;
    const padding = 8;

    let x = position.x;
    let y = position.y;

    // Adjust horizontal position
    if (x + menuWidth > window.innerWidth - padding) {
      x = window.innerWidth - menuWidth - padding;
    }

    // Adjust vertical position
    if (y + menuHeight > window.innerHeight - padding) {
      y = window.innerHeight - menuHeight - padding;
    }

    return { x: Math.max(padding, x), y: Math.max(padding, y) };
  }, [position]);

  if (!isOpen) {
    return null;
  }

  const adjustedPos = adjustedPosition();

  const handleItemClick = (action: () => void) => {
    action();
    onClose();
  };

  return (
    <div
      ref={menuRef}
      className={cn(
        'fixed z-[100] min-w-[200px] py-1',
        'bg-surface-800 border border-surface-700 rounded-lg shadow-xl',
        'animate-in fade-in-0 zoom-in-95 duration-100'
      )}
      style={{
        left: adjustedPos.x,
        top: adjustedPos.y,
      }}
      role="menu"
      aria-label="Clip actions"
    >
      {/* Preview */}
      {onPreview && hasVideo && (
        <>
          <MenuItem
            icon={<Play className="w-4 h-4" />}
            label="Preview Clip"
            onClick={() => handleItemClick(onPreview)}
            shortcut="Space"
          />
          <MenuDivider />
        </>
      )}

      {/* Lip Sync - Primary action for video clips */}
      {hasVideo && (
        <>
          <MenuItem
            icon={<Mic className="w-4 h-4" />}
            label="Apply Lip Sync..."
            onClick={() => handleItemClick(onApplyLipSync)}
            disabled={isLocked}
          />
          <MenuDivider />
        </>
      )}

      {/* Editing actions */}
      {onDuplicate && (
        <MenuItem
          icon={<Copy className="w-4 h-4" />}
          label="Duplicate"
          onClick={() => handleItemClick(onDuplicate)}
          shortcut="Ctrl+D"
        />
      )}
      {onSplit && (
        <MenuItem
          icon={<Scissors className="w-4 h-4" />}
          label="Split at Playhead"
          onClick={() => handleItemClick(onSplit)}
          shortcut="S"
          disabled={isLocked}
        />
      )}

      {(onDuplicate || onSplit) && <MenuDivider />}

      {/* Visibility and lock */}
      <MenuItem
        icon={isVisible ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
        label={isVisible ? 'Hide Clip' : 'Show Clip'}
        onClick={() => handleItemClick(onToggleVisibility)}
      />
      <MenuItem
        icon={isLocked ? <Unlock className="w-4 h-4" /> : <Lock className="w-4 h-4" />}
        label={isLocked ? 'Unlock Clip' : 'Lock Clip'}
        onClick={() => handleItemClick(onToggleLock)}
      />

      <MenuDivider />

      {/* Delete */}
      <MenuItem
        icon={<Trash2 className="w-4 h-4" />}
        label="Delete Clip"
        onClick={() => handleItemClick(onDelete)}
        danger
        shortcut="Del"
        disabled={isLocked}
      />
    </div>
  );
}
