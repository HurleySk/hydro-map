/**
 * Conditional logging utility that suppresses console output in production.
 * This helps keep the production console clean while maintaining full
 * debugging capabilities during development.
 */

/**
 * Check if we're in development mode
 */
const isDev = import.meta.env.DEV;

/**
 * Log level configuration
 */
export enum LogLevel {
  DEBUG = 0,
  LOG = 1,
  INFO = 2,
  WARN = 3,
  ERROR = 4,
}

/**
 * Get the current log level from environment or default
 */
function getCurrentLogLevel(): LogLevel {
  if (!isDev) {
    // In production, only show warnings and errors
    return LogLevel.WARN;
  }

  // In development, check for environment variable
  const envLevel = import.meta.env.VITE_LOG_LEVEL as string | undefined;
  switch (envLevel?.toUpperCase()) {
    case 'DEBUG':
      return LogLevel.DEBUG;
    case 'LOG':
      return LogLevel.LOG;
    case 'INFO':
      return LogLevel.INFO;
    case 'WARN':
      return LogLevel.WARN;
    case 'ERROR':
      return LogLevel.ERROR;
    default:
      return LogLevel.LOG; // Default for development
  }
}

const currentLogLevel = getCurrentLogLevel();

/**
 * Format log messages with optional context
 */
function formatMessage(level: string, context?: string, ...args: any[]): any[] {
  if (context) {
    return [`[${context}]`, ...args];
  }
  return args;
}

/**
 * Logger interface with context support
 */
export interface Logger {
  debug(...args: any[]): void;
  log(...args: any[]): void;
  info(...args: any[]): void;
  warn(...args: any[]): void;
  error(...args: any[]): void;
}

/**
 * Create a logger with an optional context prefix
 */
export function createLogger(context?: string): Logger {
  return {
    debug(...args: any[]) {
      if (currentLogLevel <= LogLevel.DEBUG) {
        console.debug(...formatMessage('DEBUG', context, ...args));
      }
    },

    log(...args: any[]) {
      if (currentLogLevel <= LogLevel.LOG) {
        console.log(...formatMessage('LOG', context, ...args));
      }
    },

    info(...args: any[]) {
      if (currentLogLevel <= LogLevel.INFO) {
        console.info(...formatMessage('INFO', context, ...args));
      }
    },

    warn(...args: any[]) {
      if (currentLogLevel <= LogLevel.WARN) {
        console.warn(...formatMessage('WARN', context, ...args));
      }
    },

    error(...args: any[]) {
      if (currentLogLevel <= LogLevel.ERROR) {
        console.error(...formatMessage('ERROR', context, ...args));
      }
    },
  };
}

/**
 * Default logger instance without context
 */
export const logger = createLogger();

/**
 * Specialized loggers for different components
 */
export const mapLogger = createLogger('Map');
export const apiLogger = createLogger('API');
export const tileLogger = createLogger('Tiles');
export const storeLogger = createLogger('Store');

/**
 * Performance timing utility (only in development)
 */
export function timeOperation<T>(
  name: string,
  operation: () => T | Promise<T>
): T | Promise<T> {
  if (!isDev) {
    return operation();
  }

  const start = performance.now();
  const result = operation();

  if (result instanceof Promise) {
    return result.finally(() => {
      const duration = performance.now() - start;
      logger.debug(`⏱ ${name}: ${duration.toFixed(2)}ms`);
    });
  } else {
    const duration = performance.now() - start;
    logger.debug(`⏱ ${name}: ${duration.toFixed(2)}ms`);
    return result;
  }
}

/**
 * Group console output (development only)
 */
export function logGroup(label: string, fn: () => void): void {
  if (!isDev) {
    fn();
    return;
  }

  console.group(label);
  try {
    fn();
  } finally {
    console.groupEnd();
  }
}

/**
 * Table logging for structured data (development only)
 */
export function logTable(data: any, columns?: string[]): void {
  if (isDev && currentLogLevel <= LogLevel.LOG) {
    console.table(data, columns);
  }
}