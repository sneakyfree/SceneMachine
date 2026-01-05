/**
 * Tabs Component
 *
 * Accessible tabbed interface with keyboard navigation.
 */

import React, { useState, useRef, useCallback } from 'react';
import clsx from 'clsx';

export interface Tab {
  id: string;
  label: string;
  icon?: React.ReactNode;
  badge?: number | string;
  disabled?: boolean;
}

export interface TabsProps {
  tabs: Tab[];
  activeTab: string;
  onTabChange: (tabId: string) => void;
  variant?: 'default' | 'pills' | 'underline';
  fullWidth?: boolean;
  className?: string;
}

export function Tabs({
  tabs,
  activeTab,
  onTabChange,
  variant = 'default',
  fullWidth = false,
  className,
}: TabsProps) {
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent, currentIndex: number) => {
      const enabledTabs = tabs.filter((t) => !t.disabled);
      const enabledIndexes = tabs
        .map((t, i) => (!t.disabled ? i : -1))
        .filter((i) => i !== -1);
      const currentEnabledIndex = enabledIndexes.indexOf(currentIndex);

      let nextIndex = -1;

      switch (event.key) {
        case 'ArrowLeft':
          nextIndex =
            enabledIndexes[
              currentEnabledIndex > 0
                ? currentEnabledIndex - 1
                : enabledIndexes.length - 1
            ];
          break;
        case 'ArrowRight':
          nextIndex =
            enabledIndexes[
              currentEnabledIndex < enabledIndexes.length - 1
                ? currentEnabledIndex + 1
                : 0
            ];
          break;
        case 'Home':
          nextIndex = enabledIndexes[0];
          break;
        case 'End':
          nextIndex = enabledIndexes[enabledIndexes.length - 1];
          break;
        default:
          return;
      }

      if (nextIndex >= 0) {
        event.preventDefault();
        tabRefs.current[nextIndex]?.focus();
        onTabChange(tabs[nextIndex].id);
      }
    },
    [tabs, onTabChange]
  );

  return (
    <>
      <div
        className={clsx('tabs', `tabs-${variant}`, { 'tabs-full': fullWidth }, className)}
        role="tablist"
      >
        {tabs.map((tab, index) => (
          <button
            key={tab.id}
            ref={(el) => {
              tabRefs.current[index] = el;
            }}
            className={clsx('tab', {
              'is-active': activeTab === tab.id,
              'is-disabled': tab.disabled,
            })}
            role="tab"
            aria-selected={activeTab === tab.id}
            aria-disabled={tab.disabled}
            tabIndex={activeTab === tab.id ? 0 : -1}
            onClick={() => !tab.disabled && onTabChange(tab.id)}
            onKeyDown={(e) => handleKeyDown(e, index)}
          >
            {tab.icon && <span className="tab-icon">{tab.icon}</span>}
            <span className="tab-label">{tab.label}</span>
            {tab.badge !== undefined && (
              <span className="tab-badge">{tab.badge}</span>
            )}
          </button>
        ))}
      </div>

      <style jsx>{`
        .tabs {
          display: flex;
          gap: 0.25rem;
        }

        .tabs-full {
          width: 100%;
        }

        .tabs-full .tab {
          flex: 1;
        }

        .tab {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.5rem;
          padding: 0.625rem 1rem;
          background: transparent;
          border: none;
          color: var(--color-text-secondary);
          font-size: var(--text-sm);
          font-weight: 500;
          cursor: pointer;
          transition: all var(--transition-fast);
          white-space: nowrap;
        }

        .tab:hover:not(.is-disabled) {
          color: var(--color-text-primary);
        }

        .tab.is-disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .tab.is-active {
          color: var(--color-accent);
        }

        /* Default variant */
        .tabs-default {
          background: var(--color-bg-secondary);
          border-radius: var(--radius-md);
          padding: 0.25rem;
        }

        .tabs-default .tab {
          border-radius: var(--radius-sm);
        }

        .tabs-default .tab.is-active {
          background: var(--color-bg-primary);
        }

        /* Pills variant */
        .tabs-pills .tab {
          border-radius: var(--radius-full);
        }

        .tabs-pills .tab.is-active {
          background: var(--gradient-primary);
          color: white;
        }

        /* Underline variant */
        .tabs-underline {
          border-bottom: 1px solid var(--color-border);
        }

        .tabs-underline .tab {
          position: relative;
          padding-bottom: 0.75rem;
          margin-bottom: -1px;
        }

        .tabs-underline .tab.is-active::after {
          content: '';
          position: absolute;
          bottom: 0;
          left: 0;
          right: 0;
          height: 2px;
          background: var(--color-accent);
          border-radius: 1px 1px 0 0;
        }

        .tab-icon {
          display: flex;
          align-items: center;
        }

        .tab-badge {
          display: flex;
          align-items: center;
          justify-content: center;
          min-width: 1.25rem;
          height: 1.25rem;
          padding: 0 0.375rem;
          background: var(--color-bg-secondary);
          border-radius: var(--radius-full);
          font-size: var(--text-xs);
          font-weight: 600;
        }

        .is-active .tab-badge {
          background: var(--color-accent);
          color: white;
        }
      `}</style>
    </>
  );
}

export default Tabs;
