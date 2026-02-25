import { PollingConfig, PollingState } from '../types/polling';

export class PollingManager {
  private intervals: Map<string, ReturnType<typeof setInterval>> = new Map();
  private configs: Map<string, PollingConfig> = new Map();
  private state: PollingState = {
    isPolling: false,
    lastPoll: null,
    nextPoll: null,
    errors: [],
    activePollers: new Set(),
  };

  startPolling(key: string, callback: () => Promise<void>, config: PollingConfig): void {
    this.stopPolling(key); // Clear existing

    this.configs.set(key, config);
    this.state.activePollers.add(key);

    const poll = async () => {
      try {
        await callback();
        this.state.lastPoll = new Date();
        this.state.nextPoll = new Date(Date.now() + config.interval);
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Unknown polling error';
        this.state.errors.push(`${key}: ${errorMessage}`);
        console.error(`Polling error for ${key}:`, error);
      }
    };

    // Initial poll
    poll();

    // Set up interval
    const interval = setInterval(poll, config.interval);
    this.intervals.set(key, interval);

    this.state.isPolling = this.state.activePollers.size > 0;
  }

  stopPolling(key: string): void {
    const interval = this.intervals.get(key);
    if (interval) {
      clearInterval(interval);
      this.intervals.delete(key);
    }

    this.configs.delete(key);
    this.state.activePollers.delete(key);
    this.state.isPolling = this.state.activePollers.size > 0;
  }

  stopAllPolling(): void {
    this.intervals.forEach((interval) => clearInterval(interval));
    this.intervals.clear();
    this.configs.clear();
    this.state.activePollers.clear();
    this.state.isPolling = false;
  }

  getState(): PollingState {
    return { ...this.state };
  }

  isPollingActive(key: string): boolean {
    return this.state.activePollers.has(key);
  }

  clearErrors(): void {
    this.state.errors = [];
  }
}

export const pollingManager = new PollingManager();
