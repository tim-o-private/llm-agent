import { describe, it, expect, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { MarkdownPreview } from '../MarkdownPreview';
import type { SuggestCard } from '@/api/types/fileDetail';

// Wrap in MemoryRouter since MarkdownPreview renders react-router <Link>s
import type { ReactElement } from 'react';

function renderWithRouter(ui: ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe('MarkdownPreview', () => {
  it('renders markdown content as prose', () => {
    renderWithRouter(<MarkdownPreview content="# Hello world" />);
    const heading = screen.getByRole('heading', { name: 'Hello world' });
    expect(heading).toBeDefined();
  });

  it('renders paragraphs', () => {
    renderWithRouter(
      <MarkdownPreview content={'This is a paragraph.\n\nAnother one.'} />,
    );
    expect(screen.getByText('This is a paragraph.')).toBeDefined();
    expect(screen.getByText('Another one.')).toBeDefined();
  });

  it('has aria-label "Rendered preview"', () => {
    renderWithRouter(<MarkdownPreview content="" />);
    const preview = screen.getByLabelText('Rendered preview');
    expect(preview).toBeDefined();
  });

  it('renders wikilinks as router Links with /vault/ href', () => {
    renderWithRouter(
      <MarkdownPreview content="Check out [[meeting]] for details." />,
    );
    const link = screen.getByRole('link', { name: /meeting/i });
    expect(link).toBeDefined();
    expect(link.getAttribute('href')).toBe('/vault/meeting.md');
  });

  it('renders aliased wikilinks with display text', () => {
    renderWithRouter(
      <MarkdownPreview content="See [[project|My Project]] overview." />,
    );
    const link = screen.getByRole('link', { name: /My Project/i });
    expect(link).toBeDefined();
    expect(link.getAttribute('href')).toBe('/vault/project.md');
  });

  it('renders frontmatter block when present', () => {
    const content = `---
title: Test Note
tags: [test, demo]
---
# Body content here`;

    renderWithRouter(<MarkdownPreview content={content} />);
    // FrontmatterBlock renders a "Frontmatter" label
    expect(screen.getByText('Frontmatter')).toBeDefined();
    // And the YAML key-value content
    expect(screen.getByText(/title: Test Note/)).toBeDefined();
  });

  it('does not render frontmatter block when no frontmatter', () => {
    renderWithRouter(<MarkdownPreview content="# Just a heading" />);
    expect(screen.queryByText('Frontmatter')).toBeNull();
  });

  it('renders suggest cards when passed', () => {
    const cards: SuggestCard[] = [
      {
        id: 'card-1',
        file_path: 'notes/test.md',
        target_line: 5,
        label: 'Clarity suggests',
        body: 'Consider adding a summary section to this document.',
        suggested_text: '## Summary\nTBD',
        status: 'pending',
        created_at: '2026-04-21T10:00:00Z',
      },
    ];

    renderWithRouter(
      <MarkdownPreview
        content="# Test"
        suggestCards={cards}
        onSuggestAccept={vi.fn()}
        onSuggestDismiss={vi.fn()}
      />,
    );

    // Suggest card region with truncated body as aria-label
    const card = screen.getByRole('region', {
      name: /Suggestion: Consider adding a summary/,
    });
    expect(card).toBeDefined();

    // Accept and Dismiss buttons
    const acceptBtn = within(card).getByRole('button', {
      name: 'Accept suggestion',
    });
    const dismissBtn = within(card).getByRole('button', {
      name: 'Dismiss suggestion',
    });
    expect(acceptBtn).toBeDefined();
    expect(dismissBtn).toBeDefined();
  });

  it('does not render dismissed/accepted cards', () => {
    const cards: SuggestCard[] = [
      {
        id: 'card-dismissed',
        file_path: 'notes/test.md',
        target_line: 3,
        label: 'Clarity suggests',
        body: 'This card was dismissed.',
        suggested_text: null,
        status: 'dismissed',
        created_at: '2026-04-21T10:00:00Z',
      },
      {
        id: 'card-accepted',
        file_path: 'notes/test.md',
        target_line: 7,
        label: 'Clarity suggests',
        body: 'This card was accepted.',
        suggested_text: 'text',
        status: 'accepted',
        created_at: '2026-04-21T10:00:00Z',
      },
    ];

    renderWithRouter(
      <MarkdownPreview content="# Test" suggestCards={cards} />,
    );

    expect(screen.queryByText('This card was dismissed.')).toBeNull();
    expect(screen.queryByText('This card was accepted.')).toBeNull();
  });
});
