import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SaveStatus } from '../SaveStatus';

describe('SaveStatus', () => {
  it('renders "Saved" state with green text', () => {
    render(<SaveStatus state="saved" />);
    const savedText = screen.getByText('Saved');
    expect(savedText).toBeDefined();
    // Green text class applied
    expect(savedText.className).toMatch(/green/);
  });

  it('renders "Unsaved changes" state with amber text', () => {
    render(<SaveStatus state="unsaved" />);
    const unsavedText = screen.getByText('Unsaved changes');
    expect(unsavedText).toBeDefined();
    // Amber text class applied
    expect(unsavedText.className).toMatch(/amber/);
  });

  it('renders "Saving..." state with muted text', () => {
    render(<SaveStatus state="saving" />);
    const savingText = screen.getByText('Saving...');
    expect(savingText).toBeDefined();
  });

  it('renders a spinner SVG in saving state', () => {
    const { container } = render(<SaveStatus state="saving" />);
    const svg = container.querySelector('svg');
    expect(svg).not.toBeNull();
    // The spinner has animate-spin class
    expect(svg?.classList.contains('animate-spin')).toBe(true);
  });

  it('has aria-live="polite" on the container', () => {
    const { container } = render(<SaveStatus state="saved" />);
    const liveRegion = container.querySelector('[aria-live="polite"]');
    expect(liveRegion).not.toBeNull();
  });

  it('renders check icon in saved state', () => {
    const { container } = render(<SaveStatus state="saved" />);
    // CheckIcon from radix renders an SVG
    const svg = container.querySelector('svg');
    expect(svg).not.toBeNull();
  });

  it('renders amber dot in unsaved state', () => {
    const { container } = render(<SaveStatus state="unsaved" />);
    // The dot is a span with bg-amber-500
    const dot = container.querySelector('.bg-amber-500');
    expect(dot).not.toBeNull();
  });

  it('does not render spinner in saved state', () => {
    const { container } = render(<SaveStatus state="saved" />);
    const spinner = container.querySelector('.animate-spin');
    expect(spinner).toBeNull();
  });

  it('does not render spinner in unsaved state', () => {
    const { container } = render(<SaveStatus state="unsaved" />);
    const spinner = container.querySelector('.animate-spin');
    expect(spinner).toBeNull();
  });
});
