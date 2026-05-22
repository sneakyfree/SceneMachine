/**
 * Undo/Redo hook with history management.
 * Provides a generic undo/redo system for any state type.
 */

import { useCallback, useReducer, useRef } from 'react';

interface UndoRedoState<T> {
  past: T[];
  present: T;
  future: T[];
}

type UndoRedoAction<T> =
  | { type: 'SET'; payload: T; merge?: boolean }
  | { type: 'UNDO' }
  | { type: 'REDO' }
  | { type: 'RESET'; payload: T }
  | { type: 'CLEAR_HISTORY' };

function undoRedoReducer<T>(state: UndoRedoState<T>, action: UndoRedoAction<T>): UndoRedoState<T> {
  switch (action.type) {
    case 'SET': {
      // If merging, update present without adding to history
      if (action.merge && state.past.length > 0) {
        return {
          ...state,
          present: action.payload,
        };
      }
      // Normal set: add current to past, clear future
      return {
        past: [...state.past, state.present],
        present: action.payload,
        future: [],
      };
    }

    case 'UNDO': {
      if (state.past.length === 0) return state;
      const previous = state.past[state.past.length - 1];
      const newPast = state.past.slice(0, -1);
      return {
        past: newPast,
        present: previous,
        future: [state.present, ...state.future],
      };
    }

    case 'REDO': {
      if (state.future.length === 0) return state;
      const next = state.future[0];
      const newFuture = state.future.slice(1);
      return {
        past: [...state.past, state.present],
        present: next,
        future: newFuture,
      };
    }

    case 'RESET': {
      return {
        past: [],
        present: action.payload,
        future: [],
      };
    }

    case 'CLEAR_HISTORY': {
      return {
        past: [],
        present: state.present,
        future: [],
      };
    }

    default:
      return state;
  }
}

interface UseUndoRedoOptions<T> {
  maxHistorySize?: number;
  onUndo?: (state: T) => void;
  onRedo?: (state: T) => void;
  onChange?: (state: T) => void;
}

export function useUndoRedo<T>(initialState: T, options: UseUndoRedoOptions<T> = {}) {
  const { maxHistorySize = 50, onUndo, onRedo, onChange } = options;

  const [state, dispatch] = useReducer(undoRedoReducer<T>, {
    past: [],
    present: initialState,
    future: [],
  });

  // Track last action for merge detection
  const lastSetTimeRef = useRef<number>(0);
  const mergeTimeoutMs = 500; // Merge rapid changes within 500ms

  const set = useCallback(
    (newState: T | ((prev: T) => T), options?: { merge?: boolean }) => {
      const value =
        typeof newState === 'function' ? (newState as (prev: T) => T)(state.present) : newState;

      // Auto-merge rapid changes
      const now = Date.now();
      const shouldMerge = options?.merge || now - lastSetTimeRef.current < mergeTimeoutMs;
      lastSetTimeRef.current = now;

      dispatch({ type: 'SET', payload: value, merge: shouldMerge });

      // Trim history if needed
      if (state.past.length > maxHistorySize) {
        // History trimming happens automatically through the reducer
      }

      onChange?.(value);
    },
    [state.present, maxHistorySize, onChange]
  );

  const undo = useCallback(() => {
    if (state.past.length === 0) return;
    dispatch({ type: 'UNDO' });
    const previousState = state.past[state.past.length - 1];
    onUndo?.(previousState);
    onChange?.(previousState);
  }, [state.past, onUndo, onChange]);

  const redo = useCallback(() => {
    if (state.future.length === 0) return;
    dispatch({ type: 'REDO' });
    const nextState = state.future[0];
    onRedo?.(nextState);
    onChange?.(nextState);
  }, [state.future, onRedo, onChange]);

  const reset = useCallback(
    (newState: T) => {
      dispatch({ type: 'RESET', payload: newState });
      onChange?.(newState);
    },
    [onChange]
  );

  const clearHistory = useCallback(() => {
    dispatch({ type: 'CLEAR_HISTORY' });
  }, []);

  // Convenience method for batch updates
  const batch = useCallback(
    (updates: ((prev: T) => T)[]) => {
      let current = state.present;
      for (const update of updates) {
        current = update(current);
      }
      dispatch({ type: 'SET', payload: current });
      onChange?.(current);
    },
    [state.present, onChange]
  );

  return {
    state: state.present,
    set,
    undo,
    redo,
    reset,
    clearHistory,
    batch,
    canUndo: state.past.length > 0,
    canRedo: state.future.length > 0,
    historySize: state.past.length,
    futureSize: state.future.length,
  };
}

// Command pattern for more complex undo/redo scenarios
export interface Command<T> {
  execute: (state: T) => T;
  undo: (state: T) => T;
  description?: string;
}

export function useCommandHistory<T>(initialState: T) {
  const [state, setState] = useReducer(
    (s: { value: T; commands: Command<T>[]; index: number }, action: any) => {
      switch (action.type) {
        case 'EXECUTE': {
          const newValue = action.command.execute(s.value);
          const newCommands = [...s.commands.slice(0, s.index + 1), action.command];
          return {
            value: newValue,
            commands: newCommands,
            index: newCommands.length - 1,
          };
        }
        case 'UNDO': {
          if (s.index < 0) return s;
          const command = s.commands[s.index];
          const newValue = command.undo(s.value);
          return {
            ...s,
            value: newValue,
            index: s.index - 1,
          };
        }
        case 'REDO': {
          if (s.index >= s.commands.length - 1) return s;
          const command = s.commands[s.index + 1];
          const newValue = command.execute(s.value);
          return {
            ...s,
            value: newValue,
            index: s.index + 1,
          };
        }
        case 'RESET': {
          return {
            value: action.payload,
            commands: [],
            index: -1,
          };
        }
        default:
          return s;
      }
    },
    { value: initialState, commands: [], index: -1 }
  );

  const execute = useCallback((command: Command<T>) => {
    setState({ type: 'EXECUTE', command });
  }, []);

  const undo = useCallback(() => {
    setState({ type: 'UNDO' });
  }, []);

  const redo = useCallback(() => {
    setState({ type: 'REDO' });
  }, []);

  const reset = useCallback((value: T) => {
    setState({ type: 'RESET', payload: value });
  }, []);

  return {
    state: state.value,
    execute,
    undo,
    redo,
    reset,
    canUndo: state.index >= 0,
    canRedo: state.index < state.commands.length - 1,
    commandHistory: state.commands.slice(0, state.index + 1).map((c) => c.description),
  };
}

// Pre-built commands for common operations
export const createMoveCommand = <T extends { id: string; x?: number; y?: number }>(
  itemId: string,
  dx: number,
  dy: number
): Command<T[]> => ({
  execute: (items) =>
    items.map((item) =>
      item.id === itemId ? { ...item, x: (item.x || 0) + dx, y: (item.y || 0) + dy } : item
    ),
  undo: (items) =>
    items.map((item) =>
      item.id === itemId ? { ...item, x: (item.x || 0) - dx, y: (item.y || 0) - dy } : item
    ),
  description: `Move item ${itemId}`,
});

export const createDeleteCommand = <T extends { id: string }>(item: T): Command<T[]> => ({
  execute: (items) => items.filter((i) => i.id !== item.id),
  undo: (items) => [...items, item],
  description: `Delete item ${item.id}`,
});

export const createAddCommand = <T extends { id: string }>(item: T): Command<T[]> => ({
  execute: (items) => [...items, item],
  undo: (items) => items.filter((i) => i.id !== item.id),
  description: `Add item ${item.id}`,
});

export const createUpdateCommand = <T extends { id: string }>(
  itemId: string,
  oldProps: Partial<T>,
  newProps: Partial<T>
): Command<T[]> => ({
  execute: (items) => items.map((item) => (item.id === itemId ? { ...item, ...newProps } : item)),
  undo: (items) => items.map((item) => (item.id === itemId ? { ...item, ...oldProps } : item)),
  description: `Update item ${itemId}`,
});
