/**
 * Error handling utilities for SceneMachine
 * Provides error classification, formatting, and recovery hints
 */

// ============================================================================
// Error Categories
// ============================================================================

export enum ErrorCategory {
  NETWORK = 'NETWORK',
  AUTH = 'AUTH',
  TIMEOUT = 'TIMEOUT',
  RATE_LIMIT = 'RATE_LIMIT',
  SERVER = 'SERVER',
  STORAGE = 'STORAGE',
  PROVIDER = 'PROVIDER',
  GENERATION = 'GENERATION',
  NOT_FOUND = 'NOT_FOUND',
  VALIDATION = 'VALIDATION',
  PERMISSION = 'PERMISSION',
  UNKNOWN = 'UNKNOWN',
}

export enum ErrorCode {
  // Network errors
  NETWORK_ERROR = 'NETWORK_ERROR',
  CONNECTION_REFUSED = 'CONNECTION_REFUSED',
  TIMEOUT = 'TIMEOUT',

  // Auth errors
  UNAUTHORIZED = 'UNAUTHORIZED',
  FORBIDDEN = 'FORBIDDEN',
  SESSION_EXPIRED = 'SESSION_EXPIRED',

  // Rate limiting
  RATE_LIMITED = 'RATE_LIMITED',
  QUOTA_EXCEEDED = 'QUOTA_EXCEEDED',

  // Server errors
  INTERNAL_ERROR = 'INTERNAL_ERROR',
  SERVICE_UNAVAILABLE = 'SERVICE_UNAVAILABLE',
  BAD_GATEWAY = 'BAD_GATEWAY',

  // Storage errors
  STORAGE_FULL = 'STORAGE_FULL',
  FILE_NOT_FOUND = 'FILE_NOT_FOUND',
  WRITE_FAILED = 'WRITE_FAILED',

  // Provider errors
  PROVIDER_ERROR = 'PROVIDER_ERROR',
  PROVIDER_UNAVAILABLE = 'PROVIDER_UNAVAILABLE',
  MODEL_NOT_FOUND = 'MODEL_NOT_FOUND',

  // Generation errors
  GENERATION_FAILED = 'GENERATION_FAILED',
  INVALID_INPUT = 'INVALID_INPUT',
  CONTENT_FILTERED = 'CONTENT_FILTERED',

  // Validation errors
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  INVALID_FORMAT = 'INVALID_FORMAT',

  // Not found
  NOT_FOUND = 'NOT_FOUND',
  RESOURCE_DELETED = 'RESOURCE_DELETED',

  // Unknown
  UNKNOWN = 'UNKNOWN',
}

// ============================================================================
// AppError Type
// ============================================================================

export interface AppError {
  code: ErrorCode;
  category: ErrorCategory;
  message: string;
  timestamp: Date;
  canRetry: boolean;
  retryCount: number;
  retryDelay: number;
  showTimeout: boolean;
  timeoutSeconds: number;
  helpLink?: string;
  context?: Record<string, unknown>;
  originalError?: Error;
}

// ============================================================================
// Error Classification
// ============================================================================

export function classifyError(error: unknown): AppError {
  const timestamp = new Date();
  const originalError = error instanceof Error ? error : undefined;
  const message = getErrorMessage(error);

  // Check for fetch/network errors
  if (error instanceof TypeError && message.includes('fetch')) {
    return {
      code: ErrorCode.NETWORK_ERROR,
      category: ErrorCategory.NETWORK,
      message: 'Unable to connect to the server',
      timestamp,
      canRetry: true,
      retryCount: 3,
      retryDelay: 2000,
      showTimeout: false,
      timeoutSeconds: 0,
      originalError,
    };
  }

  // Check for HTTP error responses
  if (isHttpError(error)) {
    const status = getHttpStatus(error);
    return classifyHttpError(status, message, timestamp, originalError);
  }

  // Check for timeout errors
  if (message.toLowerCase().includes('timeout') || message.toLowerCase().includes('timed out')) {
    return {
      code: ErrorCode.TIMEOUT,
      category: ErrorCategory.TIMEOUT,
      message: 'The request took too long to complete',
      timestamp,
      canRetry: true,
      retryCount: 2,
      retryDelay: 5000,
      showTimeout: true,
      timeoutSeconds: 30,
      originalError,
    };
  }

  // Check for rate limit errors
  if (
    message.toLowerCase().includes('rate limit') ||
    message.toLowerCase().includes('too many requests')
  ) {
    return {
      code: ErrorCode.RATE_LIMITED,
      category: ErrorCategory.RATE_LIMIT,
      message: 'Too many requests. Please wait before trying again.',
      timestamp,
      canRetry: true,
      retryCount: 1,
      retryDelay: 60000,
      showTimeout: true,
      timeoutSeconds: 60,
      originalError,
    };
  }

  // Default unknown error
  return {
    code: ErrorCode.UNKNOWN,
    category: ErrorCategory.UNKNOWN,
    message: message || 'An unexpected error occurred',
    timestamp,
    canRetry: true,
    retryCount: 1,
    retryDelay: 3000,
    showTimeout: false,
    timeoutSeconds: 0,
    originalError,
  };
}

function classifyHttpError(
  status: number,
  message: string,
  timestamp: Date,
  originalError?: Error
): AppError {
  switch (status) {
    case 400:
      return {
        code: ErrorCode.VALIDATION_ERROR,
        category: ErrorCategory.VALIDATION,
        message: 'Invalid request. Please check your input.',
        timestamp,
        canRetry: false,
        retryCount: 0,
        retryDelay: 0,
        showTimeout: false,
        timeoutSeconds: 0,
        originalError,
      };

    case 401:
      return {
        code: ErrorCode.UNAUTHORIZED,
        category: ErrorCategory.AUTH,
        message: 'Authentication required. Please log in.',
        timestamp,
        canRetry: false,
        retryCount: 0,
        retryDelay: 0,
        showTimeout: false,
        timeoutSeconds: 0,
        helpLink: '/settings',
        originalError,
      };

    case 403:
      return {
        code: ErrorCode.FORBIDDEN,
        category: ErrorCategory.PERMISSION,
        message: 'You do not have permission to perform this action.',
        timestamp,
        canRetry: false,
        retryCount: 0,
        retryDelay: 0,
        showTimeout: false,
        timeoutSeconds: 0,
        originalError,
      };

    case 404:
      return {
        code: ErrorCode.NOT_FOUND,
        category: ErrorCategory.NOT_FOUND,
        message: 'The requested resource was not found.',
        timestamp,
        canRetry: false,
        retryCount: 0,
        retryDelay: 0,
        showTimeout: false,
        timeoutSeconds: 0,
        originalError,
      };

    case 429:
      return {
        code: ErrorCode.RATE_LIMITED,
        category: ErrorCategory.RATE_LIMIT,
        message: 'Too many requests. Please wait before trying again.',
        timestamp,
        canRetry: true,
        retryCount: 1,
        retryDelay: 60000,
        showTimeout: true,
        timeoutSeconds: 60,
        originalError,
      };

    case 500:
      return {
        code: ErrorCode.INTERNAL_ERROR,
        category: ErrorCategory.SERVER,
        message: 'An internal server error occurred.',
        timestamp,
        canRetry: true,
        retryCount: 2,
        retryDelay: 5000,
        showTimeout: false,
        timeoutSeconds: 0,
        originalError,
      };

    case 502:
      return {
        code: ErrorCode.BAD_GATEWAY,
        category: ErrorCategory.SERVER,
        message: 'The server is temporarily unavailable.',
        timestamp,
        canRetry: true,
        retryCount: 3,
        retryDelay: 10000,
        showTimeout: true,
        timeoutSeconds: 30,
        originalError,
      };

    case 503:
      return {
        code: ErrorCode.SERVICE_UNAVAILABLE,
        category: ErrorCategory.SERVER,
        message: 'The service is currently unavailable.',
        timestamp,
        canRetry: true,
        retryCount: 3,
        retryDelay: 15000,
        showTimeout: true,
        timeoutSeconds: 60,
        originalError,
      };

    default:
      return {
        code: ErrorCode.UNKNOWN,
        category: ErrorCategory.UNKNOWN,
        message: message || 'An unexpected error occurred',
        timestamp,
        canRetry: true,
        retryCount: 1,
        retryDelay: 3000,
        showTimeout: false,
        timeoutSeconds: 0,
        originalError,
      };
  }
}

// ============================================================================
// Error Formatting
// ============================================================================

export interface FormattedError {
  title: string;
  message: string;
  hint: string;
  canRetry: boolean;
}

export function formatErrorForDisplay(error: unknown): FormattedError {
  const appError = classifyError(error);

  const titleMap: Record<ErrorCategory, string> = {
    [ErrorCategory.NETWORK]: 'Connection Error',
    [ErrorCategory.AUTH]: 'Authentication Error',
    [ErrorCategory.TIMEOUT]: 'Request Timeout',
    [ErrorCategory.RATE_LIMIT]: 'Rate Limited',
    [ErrorCategory.SERVER]: 'Server Error',
    [ErrorCategory.STORAGE]: 'Storage Error',
    [ErrorCategory.PROVIDER]: 'Provider Error',
    [ErrorCategory.GENERATION]: 'Generation Failed',
    [ErrorCategory.NOT_FOUND]: 'Not Found',
    [ErrorCategory.VALIDATION]: 'Validation Error',
    [ErrorCategory.PERMISSION]: 'Permission Denied',
    [ErrorCategory.UNKNOWN]: 'Error',
  };

  const hintMap: Record<ErrorCategory, string> = {
    [ErrorCategory.NETWORK]: 'Check your internet connection and make sure the backend is running.',
    [ErrorCategory.AUTH]: 'Please log in again or check your API keys in Settings.',
    [ErrorCategory.TIMEOUT]: 'The operation took too long. Try again or check your connection.',
    [ErrorCategory.RATE_LIMIT]: 'Wait a moment before making more requests.',
    [ErrorCategory.SERVER]: 'The server encountered an issue. Try again in a few moments.',
    [ErrorCategory.STORAGE]: 'Check your storage space and file permissions.',
    [ErrorCategory.PROVIDER]: 'Check your provider configuration in Settings.',
    [ErrorCategory.GENERATION]: 'Try adjusting your inputs or using a different model.',
    [ErrorCategory.NOT_FOUND]: 'The resource may have been moved or deleted.',
    [ErrorCategory.VALIDATION]: 'Please check your input and try again.',
    [ErrorCategory.PERMISSION]: 'You may need additional permissions for this action.',
    [ErrorCategory.UNKNOWN]: 'An unexpected error occurred. Try refreshing the page.',
  };

  return {
    title: titleMap[appError.category],
    message: appError.message,
    hint: hintMap[appError.category],
    canRetry: appError.canRetry,
  };
}

// ============================================================================
// Helper Functions
// ============================================================================

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  if (typeof error === 'string') {
    return error;
  }
  if (error && typeof error === 'object' && 'message' in error) {
    return String((error as { message: unknown }).message);
  }
  return 'An unknown error occurred';
}

function isHttpError(error: unknown): boolean {
  if (!error || typeof error !== 'object') return false;
  return 'status' in error || 'statusCode' in error || 'response' in error;
}

function getHttpStatus(error: unknown): number {
  if (!error || typeof error !== 'object') return 0;

  if ('status' in error && typeof (error as { status: unknown }).status === 'number') {
    return (error as { status: number }).status;
  }
  if ('statusCode' in error && typeof (error as { statusCode: unknown }).statusCode === 'number') {
    return (error as { statusCode: number }).statusCode;
  }
  if ('response' in error) {
    const response = (error as { response: unknown }).response;
    if (response && typeof response === 'object' && 'status' in response) {
      return (response as { status: number }).status;
    }
  }
  return 0;
}

// ============================================================================
// Error Creation Helpers
// ============================================================================

export function createAppError(
  code: ErrorCode,
  message: string,
  options: Partial<AppError> = {}
): AppError {
  const category = getDefaultCategory(code);

  return {
    code,
    category,
    message,
    timestamp: new Date(),
    canRetry: options.canRetry ?? true,
    retryCount: options.retryCount ?? 1,
    retryDelay: options.retryDelay ?? 3000,
    showTimeout: options.showTimeout ?? false,
    timeoutSeconds: options.timeoutSeconds ?? 0,
    ...options,
  };
}

function getDefaultCategory(code: ErrorCode): ErrorCategory {
  const categoryMap: Partial<Record<ErrorCode, ErrorCategory>> = {
    [ErrorCode.NETWORK_ERROR]: ErrorCategory.NETWORK,
    [ErrorCode.CONNECTION_REFUSED]: ErrorCategory.NETWORK,
    [ErrorCode.TIMEOUT]: ErrorCategory.TIMEOUT,
    [ErrorCode.UNAUTHORIZED]: ErrorCategory.AUTH,
    [ErrorCode.FORBIDDEN]: ErrorCategory.PERMISSION,
    [ErrorCode.SESSION_EXPIRED]: ErrorCategory.AUTH,
    [ErrorCode.RATE_LIMITED]: ErrorCategory.RATE_LIMIT,
    [ErrorCode.QUOTA_EXCEEDED]: ErrorCategory.RATE_LIMIT,
    [ErrorCode.INTERNAL_ERROR]: ErrorCategory.SERVER,
    [ErrorCode.SERVICE_UNAVAILABLE]: ErrorCategory.SERVER,
    [ErrorCode.BAD_GATEWAY]: ErrorCategory.SERVER,
    [ErrorCode.STORAGE_FULL]: ErrorCategory.STORAGE,
    [ErrorCode.FILE_NOT_FOUND]: ErrorCategory.STORAGE,
    [ErrorCode.WRITE_FAILED]: ErrorCategory.STORAGE,
    [ErrorCode.PROVIDER_ERROR]: ErrorCategory.PROVIDER,
    [ErrorCode.PROVIDER_UNAVAILABLE]: ErrorCategory.PROVIDER,
    [ErrorCode.MODEL_NOT_FOUND]: ErrorCategory.PROVIDER,
    [ErrorCode.GENERATION_FAILED]: ErrorCategory.GENERATION,
    [ErrorCode.INVALID_INPUT]: ErrorCategory.VALIDATION,
    [ErrorCode.CONTENT_FILTERED]: ErrorCategory.GENERATION,
    [ErrorCode.VALIDATION_ERROR]: ErrorCategory.VALIDATION,
    [ErrorCode.INVALID_FORMAT]: ErrorCategory.VALIDATION,
    [ErrorCode.NOT_FOUND]: ErrorCategory.NOT_FOUND,
    [ErrorCode.RESOURCE_DELETED]: ErrorCategory.NOT_FOUND,
  };

  return categoryMap[code] ?? ErrorCategory.UNKNOWN;
}
