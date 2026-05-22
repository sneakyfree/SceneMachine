/**
 * Operation Progress Hook
 *
 * Tracks progress of async operations via WebSocket events.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useWebSocketEvent, EventType, WebSocketEvent } from '../lib/websocket';
import { ProgressData, ProgressStatus } from '../components/progress';

export interface OperationProgressState {
  /**
   * Unique operation ID
   */
  operationId: string | null;

  /**
   * Progress data
   */
  progress: ProgressData;

  /**
   * Start tracking an operation
   */
  startTracking: (operationId: string) => void;

  /**
   * Stop tracking
   */
  stopTracking: () => void;

  /**
   * Reset progress state
   */
  reset: () => void;
}

interface ProgressEventPayload {
  operationId: string;
  percentage: number;
  status?: ProgressStatus;
  currentStep?: string;
  totalSteps?: number;
  currentStepNumber?: number;
  etaSeconds?: number;
  elapsedSeconds?: number;
  errorMessage?: string;
}

interface CompletedEventPayload {
  operationId: string;
  result?: unknown;
}

interface FailedEventPayload {
  operationId: string;
  error: string;
}

const initialProgress: ProgressData = {
  percentage: 0,
  status: 'pending',
  cancellable: true,
};

/**
 * Hook to track operation progress via WebSocket
 */
export function useOperationProgress(
  progressEventType: EventType,
  completedEventType: EventType,
  failedEventType?: EventType
): OperationProgressState {
  const [operationId, setOperationId] = useState<string | null>(null);
  const [progress, setProgress] = useState<ProgressData>(initialProgress);
  const startTimeRef = useRef<number | null>(null);

  // Handle progress updates
  useWebSocketEvent<ProgressEventPayload>(progressEventType, (event) => {
    if (!operationId || event.payload.operationId !== operationId) {
      return;
    }

    const elapsed = startTimeRef.current
      ? Math.floor((Date.now() - startTimeRef.current) / 1000)
      : undefined;

    setProgress((prev) => ({
      ...prev,
      percentage: event.payload.percentage,
      status: event.payload.status || 'running',
      currentStep: event.payload.currentStep,
      totalSteps: event.payload.totalSteps,
      currentStepNumber: event.payload.currentStepNumber,
      etaSeconds: event.payload.etaSeconds,
      elapsedSeconds: elapsed,
    }));
  });

  // Handle completion
  useWebSocketEvent<CompletedEventPayload>(completedEventType, (event) => {
    if (!operationId || event.payload.operationId !== operationId) {
      return;
    }

    const elapsed = startTimeRef.current
      ? Math.floor((Date.now() - startTimeRef.current) / 1000)
      : undefined;

    setProgress((prev) => ({
      ...prev,
      percentage: 100,
      status: 'completed',
      elapsedSeconds: elapsed,
      etaSeconds: 0,
    }));
  });

  // Handle failure
  useWebSocketEvent<FailedEventPayload>(failedEventType || EventType.BACKEND_ERROR, (event) => {
    if (!operationId || event.payload.operationId !== operationId) {
      return;
    }

    const elapsed = startTimeRef.current
      ? Math.floor((Date.now() - startTimeRef.current) / 1000)
      : undefined;

    setProgress((prev) => ({
      ...prev,
      status: 'failed',
      errorMessage: event.payload.error,
      elapsedSeconds: elapsed,
    }));
  });

  const startTracking = useCallback((id: string) => {
    setOperationId(id);
    startTimeRef.current = Date.now();
    setProgress({
      ...initialProgress,
      status: 'running',
    });
  }, []);

  const stopTracking = useCallback(() => {
    setOperationId(null);
    startTimeRef.current = null;
  }, []);

  const reset = useCallback(() => {
    setOperationId(null);
    startTimeRef.current = null;
    setProgress(initialProgress);
  }, []);

  return {
    operationId,
    progress,
    startTracking,
    stopTracking,
    reset,
  };
}

/**
 * Hook specifically for generation progress
 */
export function useGenerationProgress() {
  return useOperationProgress(
    EventType.GENERATION_PROGRESS,
    EventType.GENERATION_COMPLETED,
    EventType.GENERATION_FAILED
  );
}

/**
 * Hook specifically for assembly/export progress
 */
export function useAssemblyProgress() {
  return useOperationProgress(EventType.ASSEMBLY_PROGRESS, EventType.ASSEMBLY_COMPLETED);
}

/**
 * Hook for tracking multiple operations at once
 */
export function useMultiOperationProgress(
  progressEventType: EventType,
  completedEventType: EventType,
  failedEventType?: EventType
) {
  const [operations, setOperations] = useState<Map<string, ProgressData>>(new Map());
  const startTimesRef = useRef<Map<string, number>>(new Map());

  // Handle progress updates
  useWebSocketEvent<ProgressEventPayload>(progressEventType, (event) => {
    const { operationId, ...progressData } = event.payload;

    const startTime = startTimesRef.current.get(operationId);
    const elapsed = startTime ? Math.floor((Date.now() - startTime) / 1000) : undefined;

    setOperations((prev) => {
      const newMap = new Map(prev);
      const existing = newMap.get(operationId) || { ...initialProgress };
      newMap.set(operationId, {
        ...existing,
        percentage: progressData.percentage,
        status: progressData.status || 'running',
        currentStep: progressData.currentStep,
        totalSteps: progressData.totalSteps,
        currentStepNumber: progressData.currentStepNumber,
        etaSeconds: progressData.etaSeconds,
        elapsedSeconds: elapsed,
      });
      return newMap;
    });
  });

  // Handle completion
  useWebSocketEvent<CompletedEventPayload>(completedEventType, (event) => {
    const { operationId } = event.payload;

    const startTime = startTimesRef.current.get(operationId);
    const elapsed = startTime ? Math.floor((Date.now() - startTime) / 1000) : undefined;

    setOperations((prev) => {
      const newMap = new Map(prev);
      const existing = newMap.get(operationId);
      if (existing) {
        newMap.set(operationId, {
          ...existing,
          percentage: 100,
          status: 'completed',
          elapsedSeconds: elapsed,
          etaSeconds: 0,
        });
      }
      return newMap;
    });
  });

  // Handle failure
  useWebSocketEvent<FailedEventPayload>(failedEventType || EventType.BACKEND_ERROR, (event) => {
    const { operationId, error } = event.payload;

    const startTime = startTimesRef.current.get(operationId);
    const elapsed = startTime ? Math.floor((Date.now() - startTime) / 1000) : undefined;

    setOperations((prev) => {
      const newMap = new Map(prev);
      const existing = newMap.get(operationId);
      if (existing) {
        newMap.set(operationId, {
          ...existing,
          status: 'failed',
          errorMessage: error,
          elapsedSeconds: elapsed,
        });
      }
      return newMap;
    });
  });

  const startTracking = useCallback((operationId: string) => {
    startTimesRef.current.set(operationId, Date.now());
    setOperations((prev) => {
      const newMap = new Map(prev);
      newMap.set(operationId, {
        ...initialProgress,
        status: 'running',
      });
      return newMap;
    });
  }, []);

  const stopTracking = useCallback((operationId: string) => {
    startTimesRef.current.delete(operationId);
    setOperations((prev) => {
      const newMap = new Map(prev);
      newMap.delete(operationId);
      return newMap;
    });
  }, []);

  const getProgress = useCallback(
    (operationId: string): ProgressData | null => {
      return operations.get(operationId) || null;
    },
    [operations]
  );

  const clearCompleted = useCallback(() => {
    setOperations((prev) => {
      const newMap = new Map(prev);
      for (const [id, progress] of newMap) {
        if (progress.status === 'completed' || progress.status === 'cancelled') {
          newMap.delete(id);
          startTimesRef.current.delete(id);
        }
      }
      return newMap;
    });
  }, []);

  const reset = useCallback(() => {
    setOperations(new Map());
    startTimesRef.current.clear();
  }, []);

  return {
    operations,
    startTracking,
    stopTracking,
    getProgress,
    clearCompleted,
    reset,
  };
}

/**
 * Hook for tracking multiple generation jobs
 */
export function useMultiGenerationProgress() {
  return useMultiOperationProgress(
    EventType.GENERATION_PROGRESS,
    EventType.GENERATION_COMPLETED,
    EventType.GENERATION_FAILED
  );
}

export default useOperationProgress;
