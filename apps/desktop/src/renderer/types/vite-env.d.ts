/// <reference types="vite/client" />

interface ImportMetaEnv {
    readonly VITE_SENTRY_DSN?: string;
    readonly VITE_APP_VERSION?: string;
    readonly VITE_API_URL?: string;
    readonly MODE: string;
    readonly PROD: boolean;
    readonly DEV: boolean;
}

interface ImportMeta {
    readonly env: ImportMetaEnv;
}

// Virtual PWA register module declaration
declare module 'virtual:pwa-register' {
    export interface RegisterSWOptions {
        immediate?: boolean;
        onNeedRefresh?: () => void;
        onOfflineReady?: () => void;
        onRegistered?: (registration: ServiceWorkerRegistration | undefined) => void;
        onRegisterError?: (error: Error) => void;
    }

    export function registerSW(options?: RegisterSWOptions): (reloadPage?: boolean) => Promise<void>;
}

// Sentry module declaration
declare module '@sentry/react' {
    import { ComponentType, ReactNode } from 'react';

    export interface SentryOptions {
        dsn: string;
        environment?: string;
        release?: string;
        tracesSampleRate?: number;
        integrations?: unknown[];
        replaysSessionSampleRate?: number;
        replaysOnErrorSampleRate?: number;
    }

    export interface ReplayOptions {
        maskAllText?: boolean;
        blockAllMedia?: boolean;
    }

    export interface ErrorBoundaryProps {
        children?: ReactNode;
        fallback?: ReactNode | ComponentType<{ error: Error; componentStack: string; resetError: () => void }>;
        showDialog?: boolean;
        dialogOptions?: Record<string, unknown>;
        onError?: (error: Error, componentStack: string) => void;
        onReset?: () => void;
    }

    export function init(options: SentryOptions): void;
    export function browserTracingIntegration(): unknown;
    export function replayIntegration(options?: ReplayOptions): unknown;

    export const ErrorBoundary: ComponentType<ErrorBoundaryProps>;
}

