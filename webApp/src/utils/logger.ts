/**
 * Global Logging Manager
 * 
 * This module provides a centralized logging system with configurable log levels.
 * 
 * ## Usage:
 * 
 * ### Component Logging:
 * ```typescript
 * import { createComponentLogger } from '@/utils/logger';
 * 
 * const log = createComponentLogger('MyComponent');
 * 
 * log.debug('Debug message', { data: 'value' });
 * log.info('Info message');
 * log.warn('Warning message');
 * log.error('Error message', error);
 * ```
 * 
 * ### Global Logger:
 * ```typescript
 * import { logger } from '@/utils/logger';
 * 
 * logger.debug('ComponentName', 'Debug message', { data: 'value' });
 * ```
 * 
 * ### Runtime Control:
 * ```typescript
 * import { setLogLevel, getLogLevel } from '@/utils/logger';
 * 
 * setLogLevel('debug'); // Enable all logs
 * setLogLevel('warn');  // Only warnings and errors
 * setLogLevel('silent'); // Disable all logs
 * ```
 * 
 * ### Browser Console Control:
 * ```javascript
 * // In browser console:
 * __logger.setLevel('debug');
 * __logger.getLevel();
 * ```
 * 
 * ## Environment Configuration:
 * Set `VITE_LOG_LEVEL` environment variable to control default log level:
 * - Development default: 'debug'
 * - Production default: 'warn'
 * 
 * ## Log Levels (in order):
 * - debug: Detailed debugging information
 * - info: General information
 * - warn: Warning messages
 * - error: Error messages
 * - silent: No logging
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error' | 'silent';

interface LoggerConfig {
  level: LogLevel;
  prefix?: string;
  enableTimestamp?: boolean;
}

class Logger {
  private config: LoggerConfig;
  private static instance: Logger;

  constructor(config: LoggerConfig = { level: 'info' }) {
    this.config = {
      enableTimestamp: true,
      ...config,
    };
  }

  static getInstance(): Logger {
    if (!Logger.instance) {
      // Check environment variables for log level
      const envLogLevel = import.meta.env.VITE_LOG_LEVEL as LogLevel;
      const isDev = import.meta.env.DEV;
      
      // Default to 'debug' in development, 'warn' in production
      const defaultLevel: LogLevel = isDev ? 'debug' : 'warn';
      const level = envLogLevel || defaultLevel;

      Logger.instance = new Logger({ level });
    }
    return Logger.instance;
  }

  static setLevel(level: LogLevel): void {
    Logger.getInstance().config.level = level;
  }

  static getLevel(): LogLevel {
    return Logger.getInstance().config.level;
  }

  private shouldLog(level: LogLevel): boolean {
    const levels: LogLevel[] = ['debug', 'info', 'warn', 'error', 'silent'];
    const currentLevelIndex = levels.indexOf(this.config.level);
    const messageLevelIndex = levels.indexOf(level);
    
    if (this.config.level === 'silent') return false;
    return messageLevelIndex >= currentLevelIndex;
  }

  private formatMessage(level: LogLevel, component: string, message: string, ...args: any[]): [string, ...any[]] {
    const timestamp = this.config.enableTimestamp ? new Date().toISOString().slice(11, 23) : '';
    const prefix = this.config.prefix ? `[${this.config.prefix}]` : '';
    const levelStr = level.toUpperCase().padEnd(5);
    
    const formattedMessage = [
      timestamp && `[${timestamp}]`,
      prefix,
      `[${levelStr}]`,
      `[${component}]`,
      message
    ].filter(Boolean).join(' ');

    return [formattedMessage, ...args];
  }

  debug(component: string, message: string, ...args: any[]): void {
    if (this.shouldLog('debug')) {
      console.debug(...this.formatMessage('debug', component, message, ...args));
    }
  }

  info(component: string, message: string, ...args: any[]): void {
    if (this.shouldLog('info')) {
      console.info(...this.formatMessage('info', component, message, ...args));
    }
  }

  warn(component: string, message: string, ...args: any[]): void {
    if (this.shouldLog('warn')) {
      console.warn(...this.formatMessage('warn', component, message, ...args));
    }
  }

  error(component: string, message: string, ...args: any[]): void {
    if (this.shouldLog('error')) {
      console.error(...this.formatMessage('error', component, message, ...args));
    }
  }
}

// Export singleton instance and convenience functions
export const logger = Logger.getInstance();

// Convenience functions for common usage patterns
export const createComponentLogger = (componentName: string) => ({
  debug: (message: string, ...args: any[]) => logger.debug(componentName, message, ...args),
  info: (message: string, ...args: any[]) => logger.info(componentName, message, ...args),
  warn: (message: string, ...args: any[]) => logger.warn(componentName, message, ...args),
  error: (message: string, ...args: any[]) => logger.error(componentName, message, ...args),
});

// Global functions for runtime control
export const setLogLevel = (level: LogLevel) => Logger.setLevel(level);
export const getLogLevel = () => Logger.getLevel();

// Make logger available globally for debugging
if (typeof window !== 'undefined') {
  (window as any).__logger = {
    setLevel: setLogLevel,
    getLevel: getLogLevel,
    instance: logger,
  };
} 