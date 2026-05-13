/**
 * Time estimation utilities for SceneMachine
 * Provides estimates for generation tasks
 */

// ============================================================================
// Types
// ============================================================================

export interface TimeEstimate {
    minSeconds: number;
    maxSeconds: number;
    averageSeconds: number;
    confidence: 'low' | 'medium' | 'high';
}

export interface GenerationParams {
    type: 'image' | 'video' | 'audio' | 'voice' | 'lipsync';
    duration?: number; // For video/audio in seconds
    resolution?: string; // e.g., '1920x1080'
    model?: string;
    complexity?: 'low' | 'medium' | 'high';
}

// ============================================================================
// Base estimates by type (in seconds)
// ============================================================================

const BASE_ESTIMATES: Record<string, TimeEstimate> = {
    image: {
        minSeconds: 5,
        maxSeconds: 30,
        averageSeconds: 15,
        confidence: 'high',
    },
    video: {
        minSeconds: 30,
        maxSeconds: 300,
        averageSeconds: 120,
        confidence: 'medium',
    },
    audio: {
        minSeconds: 10,
        maxSeconds: 60,
        averageSeconds: 30,
        confidence: 'high',
    },
    voice: {
        minSeconds: 5,
        maxSeconds: 30,
        averageSeconds: 15,
        confidence: 'high',
    },
    lipsync: {
        minSeconds: 60,
        maxSeconds: 600,
        averageSeconds: 180,
        confidence: 'low',
    },
};

// ============================================================================
// Estimation Functions
// ============================================================================

// ============================================================================
// Queue-level estimation helpers
// Used by components/queue-manager.tsx
// ============================================================================

type ExperienceModeName = 'story' | 'creator' | 'pro';

/**
 * Estimate total queue completion time given current pending/running counts.
 *
 * Rough heuristic: items processed in parallel groups of `concurrency`,
 * with per-item averages depending on the provider (local providers are
 * slower because they share one GPU; remote providers like Replicate/Fal
 * are faster on aggregate because they parallelize externally).
 */
export function estimateQueueTime(
    pendingCount: number,
    runningCount: number,
    provider: string,
    concurrency: number,
): TimeEstimate {
    const isLocal = provider === 'local' || provider === 'custom' || provider === 'comfyui';
    const perItem = isLocal ? 90 : 30;
    const total = Math.max(pendingCount, 0) + Math.max(runningCount, 0);
    const groups = Math.max(1, Math.ceil(total / Math.max(concurrency, 1)));
    const avg = groups * perItem;
    return {
        minSeconds: Math.round(avg * 0.6),
        maxSeconds: Math.round(avg * 1.6),
        averageSeconds: avg,
        confidence: total <= concurrency * 2 ? 'high' : total <= concurrency * 5 ? 'medium' : 'low',
    };
}

/**
 * Format a TimeEstimate as a clock-time ETA, phrased for the experience mode.
 */
export function formatCompletionTime(
    estimate: TimeEstimate,
    mode: ExperienceModeName = 'creator',
): string {
    if (estimate.averageSeconds <= 0) return mode === 'story' ? 'Right about now' : 'Now';
    const eta = new Date(Date.now() + estimate.averageSeconds * 1000);
    const time = eta.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    if (mode === 'story') return `Done around ${time}`;
    if (mode === 'creator') return `ETA ${time}`;
    return `Completion: ${time}`;
}

/**
 * Format a queue position. `position` is zero-indexed; 0 means "currently
 * first unprocessed item" or "actively running".
 */
export function formatQueuePosition(
    position: number,
    mode: ExperienceModeName = 'creator',
): string {
    if (position <= 0) return mode === 'pro' ? 'Active' : 'Up next';
    if (mode === 'story') return position === 1 ? 'One ahead' : `${position} ahead of you`;
    return `#${position + 1} in queue`;
}

/**
 * Format the elapsed time since a job started, phrased for the experience mode.
 */
export function formatElapsedTime(
    startedAt: number | string | Date,
    mode: ExperienceModeName = 'creator',
): string {
    const startMs =
        startedAt instanceof Date
            ? startedAt.getTime()
            : typeof startedAt === 'number'
              ? startedAt
              : new Date(startedAt).getTime();
    if (Number.isNaN(startMs)) return '';
    const elapsedSec = Math.max(0, Math.floor((Date.now() - startMs) / 1000));
    if (mode === 'story') {
        if (elapsedSec < 30) return 'Just now';
        if (elapsedSec < 60) return 'Under a minute';
        return `${Math.floor(elapsedSec / 60)} min`;
    }
    if (elapsedSec < 60) return `${elapsedSec}s`;
    if (elapsedSec < 3600) return `${Math.floor(elapsedSec / 60)}m ${elapsedSec % 60}s`;
    const h = Math.floor(elapsedSec / 3600);
    const m = Math.floor((elapsedSec % 3600) / 60);
    return `${h}h ${m}m`;
}

// ============================================================================
// Estimation Functions
// ============================================================================

/**
 * Get time estimate for a generation task
 */
export function estimateGenerationTime(params: GenerationParams): TimeEstimate {
    const base = BASE_ESTIMATES[params.type] || BASE_ESTIMATES.image;
    let multiplier = 1;

    // Adjust for duration (video/audio)
    if (params.duration && params.duration > 0) {
        if (params.type === 'video') {
            // Roughly 10-20 seconds per second of video
            multiplier *= Math.max(1, params.duration / 5);
        } else if (params.type === 'audio' || params.type === 'voice') {
            // Roughly 2-5 seconds per second of audio
            multiplier *= Math.max(1, params.duration / 10);
        } else if (params.type === 'lipsync') {
            // Lipsync is very slow, roughly 30-60 seconds per second
            multiplier *= Math.max(1, params.duration / 2);
        }
    }

    // Adjust for resolution
    if (params.resolution) {
        const [width, height] = params.resolution.split('x').map(Number);
        const pixels = (width || 1920) * (height || 1080);
        const basePixels = 1920 * 1080;
        multiplier *= Math.max(1, pixels / basePixels);
    }

    // Adjust for complexity
    if (params.complexity) {
        switch (params.complexity) {
            case 'low':
                multiplier *= 0.7;
                break;
            case 'high':
                multiplier *= 1.5;
                break;
        }
    }

    return {
        minSeconds: Math.round(base.minSeconds * multiplier),
        maxSeconds: Math.round(base.maxSeconds * multiplier),
        averageSeconds: Math.round(base.averageSeconds * multiplier),
        confidence: base.confidence,
    };
}

/**
 * Format time estimate for display
 */
export function formatTimeEstimate(estimate: TimeEstimate): string {
    const avg = estimate.averageSeconds;

    if (avg < 60) {
        return `~${avg} seconds`;
    } else if (avg < 3600) {
        const mins = Math.round(avg / 60);
        return `~${mins} minute${mins > 1 ? 's' : ''}`;
    } else {
        const hours = Math.round(avg / 3600);
        return `~${hours} hour${hours > 1 ? 's' : ''}`;
    }
}

/**
 * Format time estimate range for display
 */
export function formatTimeRange(estimate: TimeEstimate): string {
    const format = (secs: number): string => {
        if (secs < 60) return `${secs}s`;
        if (secs < 3600) return `${Math.round(secs / 60)}m`;
        return `${Math.round(secs / 3600)}h`;
    };

    return `${format(estimate.minSeconds)} - ${format(estimate.maxSeconds)}`;
}

/**
 * Get a human-readable description of the estimate
 */
export function describeEstimate(estimate: TimeEstimate): string {
    const avgFormatted = formatTimeEstimate(estimate);
    const rangeFormatted = formatTimeRange(estimate);

    const confidenceText = {
        low: 'This is a rough estimate and may vary significantly.',
        medium: 'Actual time may vary based on server load.',
        high: 'This estimate is typically accurate.',
    }[estimate.confidence];

    return `Expected: ${avgFormatted} (${rangeFormatted}). ${confidenceText}`;
}

// ============================================================================
// Progress estimation
// ============================================================================

/**
 * Estimate remaining time based on progress
 */
export function estimateRemainingTime(
    progressPercent: number,
    elapsedSeconds: number
): number {
    if (progressPercent <= 0) return 0;
    if (progressPercent >= 100) return 0;

    const totalEstimated = (elapsedSeconds / progressPercent) * 100;
    return Math.max(0, Math.round(totalEstimated - elapsedSeconds));
}

/**
 * Format remaining time for display
 */
export function formatRemainingTime(seconds: number): string {
    if (seconds <= 0) return 'Almost done';
    if (seconds < 60) return `${seconds}s remaining`;
    if (seconds < 3600) {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return secs > 0 ? `${mins}m ${secs}s remaining` : `${mins}m remaining`;
    }
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    return mins > 0 ? `${hours}h ${mins}m remaining` : `${hours}h remaining`;
}
