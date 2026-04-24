import { describe, it, expect } from 'vitest';
import { slugify } from '../slugify';

describe('slugify', () => {
  it('converts a simple name', () => {
    expect(slugify('Sarah Chen')).toBe('sarah-chen');
  });

  it('strips trailing punctuation', () => {
    expect(slugify('Acme Corp.')).toBe('acme-corp');
  });

  it('handles ampersands', () => {
    expect(slugify('Salt & Pepper')).toBe('salt-pepper');
  });

  it('collapses consecutive spaces', () => {
    expect(slugify('Foo   Bar   Baz')).toBe('foo-bar-baz');
  });

  it('passes through already-slugified input', () => {
    expect(slugify('sarah-chen')).toBe('sarah-chen');
  });

  it('returns empty string for empty input', () => {
    expect(slugify('')).toBe('');
  });

  it('preserves numbers', () => {
    expect(slugify('Q3 Planning 2026')).toBe('q3-planning-2026');
  });

  it('strips leading and trailing hyphens', () => {
    expect(slugify('---Hello World---')).toBe('hello-world');
  });

  it('handles accented characters via NFKD normalisation', () => {
    expect(slugify('Café')).toBe('cafe');
  });

  it('returns empty for all-special-char input', () => {
    expect(slugify('!!!')).toBe('');
  });

  it('truncates very long names', () => {
    const long = 'a'.repeat(300);
    expect(slugify(long).length).toBeLessThanOrEqual(200);
  });

  it('lowercases mixed case', () => {
    expect(slugify('CamelCaseCompany')).toBe('camelcasecompany');
  });
});
