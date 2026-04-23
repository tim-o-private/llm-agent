export function relativeTime(iso: string): string {
  try {
    const then = new Date(iso).getTime();
    const diff = Date.now() - then;
    if (Number.isNaN(diff)) return iso;
    const mins = Math.round(diff / 60_000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins} min ago`;
    const hrs = Math.round(mins / 60);
    if (hrs < 24) return `${hrs} hr ago`;
    const days = Math.round(hrs / 24);
    if (days < 7) return `${days} day${days === 1 ? '' : 's'} ago`;
    return new Date(iso).toISOString().slice(0, 10);
  } catch {
    return iso;
  }
}

export function relativeTimeFromDate(timestamp: Date): string {
  return relativeTime(timestamp.toISOString());
}
