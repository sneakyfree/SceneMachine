/**
 * Hooks Tests
 *
 * Tests for custom React hooks.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useDebounce, useDebouncedCallback } from '../hooks/useDebounce';
import { usePagination } from '../hooks/usePagination';
import { useLocalStorage } from '../hooks/useLocalStorage';

describe('useDebounce', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  it('should return initial value immediately', () => {
    const { result } = renderHook(() => useDebounce('initial', 500));
    expect(result.current).toBe('initial');
  });

  it('should debounce value changes', async () => {
    const { result, rerender } = renderHook(
      ({ value }) => useDebounce(value, 500),
      { initialProps: { value: 'initial' } }
    );

    expect(result.current).toBe('initial');

    rerender({ value: 'updated' });
    expect(result.current).toBe('initial');

    act(() => {
      vi.advanceTimersByTime(500);
    });

    expect(result.current).toBe('updated');
  });

  it('should cancel pending updates on unmount', () => {
    const { result, rerender, unmount } = renderHook(
      ({ value }) => useDebounce(value, 500),
      { initialProps: { value: 'initial' } }
    );

    rerender({ value: 'updated' });
    unmount();

    // Should not throw
    act(() => {
      vi.advanceTimersByTime(500);
    });
  });
});

describe('useDebouncedCallback', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  it('should debounce callback execution', () => {
    const callback = vi.fn();
    const { result } = renderHook(() => useDebouncedCallback(callback, 500));

    result.current('arg1');
    result.current('arg2');
    result.current('arg3');

    expect(callback).not.toHaveBeenCalled();

    act(() => {
      vi.advanceTimersByTime(500);
    });

    expect(callback).toHaveBeenCalledTimes(1);
    expect(callback).toHaveBeenCalledWith('arg3');
  });
});

describe('usePagination', () => {
  it('should initialize with default values', () => {
    const { result } = renderHook(() => usePagination());

    expect(result.current.items).toEqual([]);
    expect(result.current.pagination).toEqual({
      page: 1,
      pageSize: 20,
      total: 0,
      hasMore: true,
    });
    expect(result.current.isLoading).toBe(false);
  });

  it('should handle API response correctly', () => {
    const { result } = renderHook(() => usePagination<{ id: string }>());

    const response = {
      items: [{ id: '1' }, { id: '2' }],
      total: 10,
      page: 1,
      page_size: 20,
      has_more: true,
    };

    act(() => {
      result.current.handleResponse(response);
    });

    expect(result.current.items).toEqual([{ id: '1' }, { id: '2' }]);
    expect(result.current.pagination.total).toBe(10);
    expect(result.current.pagination.hasMore).toBe(true);
  });

  it('should append items when specified', () => {
    const { result } = renderHook(() => usePagination<{ id: string }>());

    // First page
    act(() => {
      result.current.handleResponse({
        items: [{ id: '1' }],
        total: 2,
        page: 1,
        page_size: 1,
        has_more: true,
      });
    });

    // Second page with append
    act(() => {
      result.current.handleResponse(
        {
          items: [{ id: '2' }],
          total: 2,
          page: 2,
          page_size: 1,
          has_more: false,
        },
        true
      );
    });

    expect(result.current.items).toEqual([{ id: '1' }, { id: '2' }]);
  });

  it('should calculate total pages correctly', () => {
    const { result } = renderHook(() => usePagination<{ id: string }>());

    act(() => {
      result.current.handleResponse({
        items: [],
        total: 100,
        page: 1,
        page_size: 20,
        has_more: true,
      });
    });

    expect(result.current.totalPages).toBe(5);
  });

  it('should navigate pages', () => {
    const { result } = renderHook(() => usePagination<{ id: string }>());

    act(() => {
      result.current.handleResponse({
        items: [],
        total: 100,
        page: 1,
        page_size: 20,
        has_more: true,
      });
    });

    act(() => {
      result.current.nextPage();
    });

    expect(result.current.pagination.page).toBe(2);

    act(() => {
      result.current.prevPage();
    });

    expect(result.current.pagination.page).toBe(1);
  });

  it('should reset pagination', () => {
    const { result } = renderHook(() => usePagination<{ id: string }>());

    act(() => {
      result.current.handleResponse({
        items: [{ id: '1' }],
        total: 10,
        page: 3,
        page_size: 20,
        has_more: false,
      });
    });

    act(() => {
      result.current.reset();
    });

    expect(result.current.items).toEqual([]);
    expect(result.current.pagination.page).toBe(1);
  });
});

describe('useLocalStorage', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('should return initial value when no stored value', () => {
    const { result } = renderHook(() => useLocalStorage('test-key', 'default'));
    expect(result.current[0]).toBe('default');
  });

  it('should update localStorage on setValue', () => {
    const { result } = renderHook(() => useLocalStorage('test-key', 'initial'));

    act(() => {
      result.current[1]('updated');
    });

    expect(result.current[0]).toBe('updated');
    expect(localStorage.getItem('test-key')).toBe('"updated"');
  });

  it('should support function updates', () => {
    const { result } = renderHook(() => useLocalStorage('counter', 0));

    act(() => {
      result.current[1]((prev) => prev + 1);
    });

    expect(result.current[0]).toBe(1);
  });

  it('should remove value from storage', () => {
    localStorage.setItem('test-key', '"stored"');

    const { result } = renderHook(() => useLocalStorage('test-key', 'default'));

    act(() => {
      result.current[2](); // removeValue
    });

    expect(result.current[0]).toBe('default');
    expect(localStorage.getItem('test-key')).toBeNull();
  });

  it('should handle objects', () => {
    const { result } = renderHook(() =>
      useLocalStorage('object-key', { count: 0 })
    );

    act(() => {
      result.current[1]({ count: 5 });
    });

    expect(result.current[0]).toEqual({ count: 5 });
  });
});
