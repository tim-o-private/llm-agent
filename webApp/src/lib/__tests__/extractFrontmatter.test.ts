import { describe, it, expect } from 'vitest';
import { extractFrontmatter } from '../extractFrontmatter';

describe('extractFrontmatter', () => {
  it('splits frontmatter and body correctly', () => {
    const input = `---
title: Hello
tags: [a, b]
---
# Body here`;

    const result = extractFrontmatter(input);
    expect(result.frontmatter).toBe('title: Hello\ntags: [a, b]');
    expect(result.body).toBe('# Body here');
  });

  it('returns null frontmatter when no frontmatter present', () => {
    const input = '# Just a heading\n\nSome text.';
    const result = extractFrontmatter(input);
    expect(result.frontmatter).toBeNull();
    expect(result.body).toBe(input);
  });

  it('handles unclosed frontmatter gracefully', () => {
    const input = '---\ntitle: Broken\nNo closing delimiter';
    const result = extractFrontmatter(input);
    expect(result.frontmatter).toBeNull();
    expect(result.body).toBe(input);
  });

  it('handles frontmatter-only file', () => {
    const input = '---\ntitle: Only FM\n---';
    const result = extractFrontmatter(input);
    expect(result.frontmatter).toBe('title: Only FM');
    expect(result.body).toBe('');
  });

  it('handles empty content', () => {
    const result = extractFrontmatter('');
    expect(result.frontmatter).toBeNull();
    expect(result.body).toBe('');
  });

  it('does not treat mid-file --- as frontmatter', () => {
    const input = 'Some text\n---\ntitle: Not FM\n---\nMore text';
    const result = extractFrontmatter(input);
    expect(result.frontmatter).toBeNull();
    expect(result.body).toBe(input);
  });

  it('handles empty frontmatter block', () => {
    const input = '---\n---\n# Body';
    const result = extractFrontmatter(input);
    // Empty frontmatter string is null
    expect(result.frontmatter).toBeNull();
    expect(result.body).toBe('# Body');
  });
});
