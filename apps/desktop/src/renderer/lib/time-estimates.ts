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
