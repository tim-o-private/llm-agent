export interface PollingConfig {
  interval: number;
}

export interface PollingState {
  isPolling: boolean;
  lastPoll: Date | null;
  nextPoll: Date | null;
  errors: string[];
  activePollers: Set<string>;
}
