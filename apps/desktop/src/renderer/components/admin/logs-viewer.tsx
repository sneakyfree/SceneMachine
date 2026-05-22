/**
 * Logs Viewer Component
 *
 * Displays system logs with filtering, search, and auto-refresh.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import {
  Search,
  Filter,
  RefreshCw,
  AlertTriangle,
  AlertCircle,
  Info,
  Bug,
  ChevronDown,
  Pause,
  Play,
  Trash2,
  Download,
} from 'lucide-react';
import { cn } from '../../lib/utils';

export type LogLevel = 'debug' | 'info' | 'warning' | 'error';

export interface LogEntry {
  id: string;
  timestamp: Date;
  level: LogLevel;
  source: string;
  message: string;
  details?: Record<string, unknown>;
}

interface LogsViewerProps {
  /**
   * Log entries to display
   */
  logs?: LogEntry[];

  /**
   * Whether logs are loading
   */
  isLoading?: boolean;

  /**
   * Fetch logs function
   */
  onRefresh?: () => void;

  /**
   * Clear logs function
   */
  onClear?: () => void;

  /**
   * Export logs function
   */
  onExport?: () => void;

  /**
   * Auto-refresh interval in seconds (0 = disabled)
   */
  autoRefreshInterval?: number;

  /**
   * Maximum logs to display
   */
  maxLogs?: number;

  /**
   * CSS class name
   */
  className?: string;
}

const LEVEL_ICONS: Record<LogLevel, React.ComponentType<{ className?: string }>> = {
  debug: Bug,
  info: Info,
  warning: AlertTriangle,
  error: AlertCircle,
};

const LEVEL_COLORS: Record<LogLevel, string> = {
  debug: 'text-surface-400',
  info: 'text-blue-400',
  warning: 'text-yellow-400',
  error: 'text-red-400',
};

const LEVEL_BG_COLORS: Record<LogLevel, string> = {
  debug: 'bg-surface-800',
  info: 'bg-blue-500/10',
  warning: 'bg-yellow-500/10',
  error: 'bg-red-500/10',
};

function formatTimestamp(date: Date): string {
  return date.toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

export function LogsViewer({
  logs = [],
  isLoading = false,
  onRefresh,
  onClear,
  onExport,
  autoRefreshInterval = 30,
  maxLogs = 100,
  className,
}: LogsViewerProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [levelFilter, setLevelFilter] = useState<LogLevel | 'all'>('all');
  const [isPaused, setIsPaused] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [expandedLogId, setExpandedLogId] = useState<string | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-refresh
  useEffect(() => {
    if (isPaused || autoRefreshInterval === 0 || !onRefresh) return;

    const interval = setInterval(() => {
      onRefresh();
    }, autoRefreshInterval * 1000);

    return () => clearInterval(interval);
  }, [isPaused, autoRefreshInterval, onRefresh]);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (!isPaused && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs.length, isPaused]);

  // Filter logs
  const filteredLogs = logs
    .filter((log) => {
      // Level filter
      if (levelFilter !== 'all' && log.level !== levelFilter) return false;

      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        return (
          log.message.toLowerCase().includes(query) || log.source.toLowerCase().includes(query)
        );
      }

      return true;
    })
    .slice(-maxLogs);

  // Toggle log expansion
  const toggleLogExpansion = useCallback((logId: string) => {
    setExpandedLogId((prev) => (prev === logId ? null : logId));
  }, []);

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Toolbar */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-surface-700 bg-surface-900/50">
        {/* Search */}
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search logs..."
            className={cn(
              'w-full pl-9 pr-3 py-2 rounded-lg',
              'bg-surface-800 border border-surface-700',
              'text-sm text-white placeholder-surface-500',
              'focus:outline-none focus:ring-2 focus:ring-primary-500/50'
            )}
          />
        </div>

        {/* Level filter */}
        <div className="relative">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={cn(
              'flex items-center gap-2 px-3 py-2 rounded-lg',
              'bg-surface-800 border border-surface-700',
              'hover:bg-surface-700 transition-colors',
              showFilters && 'ring-2 ring-primary-500/50'
            )}
          >
            <Filter className="w-4 h-4 text-surface-400" />
            <span className="text-sm capitalize">
              {levelFilter === 'all' ? 'All Levels' : levelFilter}
            </span>
            <ChevronDown className="w-3 h-3 text-surface-400" />
          </button>

          {showFilters && (
            <div className="absolute top-full mt-1 w-40 py-1 rounded-lg bg-surface-800 border border-surface-700 shadow-lg z-10">
              {(['all', 'debug', 'info', 'warning', 'error'] as const).map((level) => (
                <button
                  key={level}
                  onClick={() => {
                    setLevelFilter(level);
                    setShowFilters(false);
                  }}
                  className={cn(
                    'w-full flex items-center gap-2 px-3 py-2 text-sm text-left',
                    'hover:bg-surface-700 transition-colors',
                    levelFilter === level && 'bg-surface-700'
                  )}
                >
                  {level !== 'all' && (
                    <span className={LEVEL_COLORS[level]}>
                      {(() => {
                        const Icon = LEVEL_ICONS[level];
                        return <Icon className="w-4 h-4" />;
                      })()}
                    </span>
                  )}
                  <span className="capitalize">{level === 'all' ? 'All Levels' : level}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Pause/Play */}
        <button
          onClick={() => setIsPaused(!isPaused)}
          className={cn(
            'p-2 rounded-lg transition-colors',
            isPaused
              ? 'bg-yellow-500/20 text-yellow-400'
              : 'bg-surface-800 text-surface-400 hover:bg-surface-700'
          )}
          title={isPaused ? 'Resume auto-refresh' : 'Pause auto-refresh'}
        >
          {isPaused ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
        </button>

        {/* Refresh */}
        <button
          onClick={onRefresh}
          disabled={isLoading}
          className="p-2 rounded-lg bg-surface-800 text-surface-400 hover:bg-surface-700 transition-colors disabled:opacity-50"
          title="Refresh logs"
        >
          <RefreshCw className={cn('w-4 h-4', isLoading && 'animate-spin')} />
        </button>

        <div className="flex-1" />

        {/* Export */}
        {onExport && (
          <button
            onClick={onExport}
            className="p-2 rounded-lg bg-surface-800 text-surface-400 hover:bg-surface-700 transition-colors"
            title="Export logs"
          >
            <Download className="w-4 h-4" />
          </button>
        )}

        {/* Clear */}
        {onClear && (
          <button
            onClick={onClear}
            className="p-2 rounded-lg bg-surface-800 text-red-400 hover:bg-red-500/20 transition-colors"
            title="Clear logs"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Logs list */}
      <div ref={containerRef} className="flex-1 overflow-y-auto font-mono text-sm">
        {filteredLogs.length === 0 ? (
          <div className="flex items-center justify-center h-full text-surface-500">
            {logs.length === 0 ? 'No logs to display' : 'No logs match your filters'}
          </div>
        ) : (
          <div className="divide-y divide-surface-800">
            {filteredLogs.map((log) => {
              const Icon = LEVEL_ICONS[log.level];
              const isExpanded = expandedLogId === log.id;

              return (
                <div
                  key={log.id}
                  className={cn(
                    'px-4 py-2 hover:bg-surface-800/50 cursor-pointer transition-colors',
                    LEVEL_BG_COLORS[log.level]
                  )}
                  onClick={() => log.details && toggleLogExpansion(log.id)}
                >
                  <div className="flex items-start gap-3">
                    {/* Level icon */}
                    <Icon className={cn('w-4 h-4 mt-0.5 shrink-0', LEVEL_COLORS[log.level])} />

                    {/* Timestamp */}
                    <span className="text-surface-500 shrink-0">
                      {formatTimestamp(log.timestamp)}
                    </span>

                    {/* Source */}
                    <span className="text-surface-400 shrink-0 w-24 truncate" title={log.source}>
                      [{log.source}]
                    </span>

                    {/* Message */}
                    <span className="text-surface-200 break-words flex-1">{log.message}</span>

                    {/* Expand indicator */}
                    {log.details && (
                      <ChevronDown
                        className={cn(
                          'w-4 h-4 text-surface-500 shrink-0 transition-transform',
                          isExpanded && 'rotate-180'
                        )}
                      />
                    )}
                  </div>

                  {/* Details (expanded) */}
                  {isExpanded && log.details && (
                    <div className="mt-2 ml-7 p-3 rounded bg-surface-900/50 text-xs">
                      <pre className="text-surface-300 whitespace-pre-wrap overflow-x-auto">
                        {JSON.stringify(log.details, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
        <div ref={logsEndRef} />
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between px-4 py-2 border-t border-surface-700 bg-surface-900/50 text-xs text-surface-500">
        <span>
          Showing {filteredLogs.length} of {logs.length} logs
        </span>
        <span>{isPaused ? 'Paused' : `Auto-refresh: ${autoRefreshInterval}s`}</span>
      </div>
    </div>
  );
}

export default LogsViewer;
