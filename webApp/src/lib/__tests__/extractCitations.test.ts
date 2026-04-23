import { describe, it, expect } from 'vitest';
import { extractCitations } from '../extractCitations';

describe('extractCitations', () => {
  it('extracts simple [[target]] links', () => {
    const result = extractCitations('See [[meeting]] and [[project]].');
    expect(result).toEqual([
      { index: 0, target: 'meeting', display: 'meeting' },
      { index: 1, target: 'project', display: 'project' },
    ]);
  });

  it('extracts [[target|display]] links with alias', () => {
    const result = extractCitations('See [[meeting|Team Meeting]].');
    expect(result).toEqual([
      { index: 0, target: 'meeting', display: 'Team Meeting' },
    ]);
  });

  it('deduplicates by target', () => {
    const result = extractCitations('[[a]] then [[a]] again and [[a|A Link]].');
    expect(result).toHaveLength(1);
    expect(result[0].target).toBe('a');
  });

  it('handles empty string', () => {
    expect(extractCitations('')).toEqual([]);
  });

  it('handles content with no links', () => {
    expect(extractCitations('Just plain text here.')).toEqual([]);
  });

  it('handles mixed simple and aliased links', () => {
    const result = extractCitations('[[notes]] and [[docs|Documentation]] and [[notes|My Notes]].');
    expect(result).toEqual([
      { index: 0, target: 'notes', display: 'notes' },
      { index: 1, target: 'docs', display: 'Documentation' },
    ]);
  });

  it('trims whitespace from targets and display names', () => {
    const result = extractCitations('[[ spaced ]] and [[ padded | Display Name ]].');
    expect(result).toEqual([
      { index: 0, target: 'spaced', display: 'spaced' },
      { index: 1, target: 'padded', display: 'Display Name' },
    ]);
  });
});
