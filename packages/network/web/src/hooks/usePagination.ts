/**
 * usePagination Hook
 *
 * Generic pagination state management.
 */

import { useState, useCallback, useMemo } from 'react';

export interface PaginationState {
  page: number;
  pageSize: number;
  total: number;
  hasMore: boolean;
}

export interface UsePaginationOptions {
  initialPage?: number;
  initialPageSize?: number;
}

export function usePagination<T>(options: UsePaginationOptions = {}) {
  const { initialPage = 1, initialPageSize = 20 } = options;

  const [items, setItems] = useState<T[]>([]);
  const [pagination, setPagination] = useState<PaginationState>({
    page: initialPage,
    pageSize: initialPageSize,
    total: 0,
    hasMore: true,
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const totalPages = useMemo(
    () => Math.ceil(pagination.total / pagination.pageSize),
    [pagination.total, pagination.pageSize]
  );

  const setPage = useCallback((page: number) => {
    setPagination((prev) => ({ ...prev, page }));
  }, []);

  const setPageSize = useCallback((pageSize: number) => {
    setPagination((prev) => ({ ...prev, pageSize, page: 1 }));
  }, []);

  const nextPage = useCallback(() => {
    if (pagination.hasMore) {
      setPagination((prev) => ({ ...prev, page: prev.page + 1 }));
    }
  }, [pagination.hasMore]);

  const prevPage = useCallback(() => {
    if (pagination.page > 1) {
      setPagination((prev) => ({ ...prev, page: prev.page - 1 }));
    }
  }, [pagination.page]);

  const reset = useCallback(() => {
    setItems([]);
    setPagination({
      page: initialPage,
      pageSize: initialPageSize,
      total: 0,
      hasMore: true,
    });
    setError(null);
  }, [initialPage, initialPageSize]);

  // Helper to update state from API response
  const handleResponse = useCallback(
    (response: { items: T[]; total: number; page: number; page_size: number; has_more: boolean }, append = false) => {
      setItems((prev) => (append ? [...prev, ...response.items] : response.items));
      setPagination({
        page: response.page,
        pageSize: response.page_size,
        total: response.total,
        hasMore: response.has_more,
      });
    },
    []
  );

  return {
    items,
    setItems,
    pagination,
    isLoading,
    setIsLoading,
    error,
    setError,
    totalPages,
    setPage,
    setPageSize,
    nextPage,
    prevPage,
    reset,
    handleResponse,
  };
}

export default usePagination;
