export interface PollingConfig {
  interval: number;           // Polling interval in milliseconds
  maxRetries: number;         // Maximum retry attempts
  backoffMultiplier: number;  // Exponential backoff multiplier
  staleThreshold: number;     // Data staleness threshold in milliseconds
}

export interface CacheEntry<T> {
  data: T;
  timestamp: Date;
  lastFetch: Date;
  isStale: boolean;
  retryCount: number;
}

export interface PollingState {
  isPolling: boolean;
  lastPoll: Date | null;
  nextPoll: Date | null;
  errors: string[];
  activePollers: Set<string>;
}

export interface StorePollingConfig {
  enabled: boolean;
  interval: number;
  staleThreshold: number;
  queryLimit: number;
} 