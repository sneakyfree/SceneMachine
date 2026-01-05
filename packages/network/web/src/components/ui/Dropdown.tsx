/**
 * Dropdown Component
 *
 * Accessible dropdown menu with keyboard navigation.
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';
import clsx from 'clsx';

export interface DropdownItem {
  id: string;
  label: string;
  icon?: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  danger?: boolean;
  divider?: boolean;
}

export interface DropdownProps {
  trigger: React.ReactNode;
  items: DropdownItem[];
  align?: 'left' | 'right';
  className?: string;
}

export function Dropdown({
  trigger,
  items,
  align = 'left',
  className,
}: DropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [focusedIndex, setFocusedIndex] = useState(-1);
  const containerRef = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  const close = useCallback(() => {
    setIsOpen(false);
    setFocusedIndex(-1);
  }, []);

  // Close on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        close();
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen, close]);

  // Keyboard navigation
  const handleKeyDown = (event: React.KeyboardEvent) => {
    const selectableItems = items.filter((item) => !item.divider && !item.disabled);

    switch (event.key) {
      case 'Enter':
      case ' ':
        if (!isOpen) {
          setIsOpen(true);
          setFocusedIndex(0);
        } else if (focusedIndex >= 0) {
          const item = selectableItems[focusedIndex];
          if (item?.onClick) {
            item.onClick();
            close();
          }
        }
        event.preventDefault();
        break;

      case 'ArrowDown':
        if (!isOpen) {
          setIsOpen(true);
          setFocusedIndex(0);
        } else {
          setFocusedIndex((prev) =>
            prev < selectableItems.length - 1 ? prev + 1 : 0
          );
        }
        event.preventDefault();
        break;

      case 'ArrowUp':
        if (isOpen) {
          setFocusedIndex((prev) =>
            prev > 0 ? prev - 1 : selectableItems.length - 1
          );
        }
        event.preventDefault();
        break;

      case 'Escape':
        close();
        event.preventDefault();
        break;

      case 'Tab':
        close();
        break;
    }
  };

  const handleItemClick = (item: DropdownItem) => {
    if (item.disabled || item.divider) return;
    item.onClick?.();
    close();
  };

  return (
    <>
      <div
        ref={containerRef}
        className={clsx('dropdown', className)}
        onKeyDown={handleKeyDown}
      >
        <div
          className="dropdown-trigger"
          onClick={() => setIsOpen(!isOpen)}
          role="button"
          tabIndex={0}
          aria-haspopup="menu"
          aria-expanded={isOpen}
        >
          {trigger}
        </div>

        {isOpen && (
          <div
            ref={menuRef}
            className={clsx('dropdown-menu', `align-${align}`)}
            role="menu"
          >
            {items.map((item, index) =>
              item.divider ? (
                <div key={item.id} className="dropdown-divider" role="separator" />
              ) : (
                <div
                  key={item.id}
                  className={clsx('dropdown-item', {
                    'is-disabled': item.disabled,
                    'is-danger': item.danger,
                    'is-focused': index === focusedIndex,
                  })}
                  role="menuitem"
                  tabIndex={-1}
                  aria-disabled={item.disabled}
                  onClick={() => handleItemClick(item)}
                  onMouseEnter={() => setFocusedIndex(index)}
                >
                  {item.icon && <span className="item-icon">{item.icon}</span>}
                  <span className="item-label">{item.label}</span>
                </div>
              )
            )}
          </div>
        )}
      </div>

      <style jsx>{`
        .dropdown {
          position: relative;
          display: inline-block;
        }

        .dropdown-trigger {
          cursor: pointer;
        }

        .dropdown-menu {
          position: absolute;
          top: calc(100% + 0.5rem);
          z-index: 50;
          min-width: 12rem;
          padding: 0.375rem;
          background: var(--color-bg-primary);
          border: 1px solid var(--color-border);
          border-radius: var(--radius-md);
          box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
          animation: dropdown-enter 0.15s ease-out;
        }

        @keyframes dropdown-enter {
          from {
            opacity: 0;
            transform: translateY(-0.5rem);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .align-left {
          left: 0;
        }

        .align-right {
          right: 0;
        }

        .dropdown-item {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          padding: 0.5rem 0.75rem;
          border-radius: var(--radius-sm);
          color: var(--color-text-primary);
          cursor: pointer;
          transition: background-color var(--transition-fast);
        }

        .dropdown-item:hover,
        .dropdown-item.is-focused {
          background: var(--color-bg-secondary);
        }

        .dropdown-item.is-disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .dropdown-item.is-disabled:hover {
          background: transparent;
        }

        .dropdown-item.is-danger {
          color: var(--color-error);
        }

        .item-icon {
          display: flex;
          align-items: center;
          color: var(--color-text-secondary);
        }

        .is-danger .item-icon {
          color: inherit;
        }

        .dropdown-divider {
          height: 1px;
          margin: 0.375rem 0;
          background: var(--color-border);
        }
      `}</style>
    </>
  );
}

export default Dropdown;
