import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { LayoutToggle } from '../LayoutToggle';

describe('LayoutToggle', () => {
  it('renders three radio buttons', () => {
    const onChange = vi.fn();
    render(<LayoutToggle mode="split" onChange={onChange} />);
    const buttons = screen.getAllByRole('radio');
    expect(buttons).toHaveLength(3);
  });

  it('renders with correct labels', () => {
    const onChange = vi.fn();
    render(<LayoutToggle mode="split" onChange={onChange} />);
    expect(screen.getByText('Split')).toBeDefined();
    expect(screen.getByText('Source')).toBeDefined();
    expect(screen.getByText('Preview')).toBeDefined();
  });

  it('has radiogroup with aria-label "Editor layout"', () => {
    const onChange = vi.fn();
    render(<LayoutToggle mode="split" onChange={onChange} />);
    const group = screen.getByRole('radiogroup', { name: 'Editor layout' });
    expect(group).toBeDefined();
  });

  it('marks the active button as aria-checked', () => {
    const onChange = vi.fn();
    render(<LayoutToggle mode="source" onChange={onChange} />);

    const sourceBtn = screen.getByText('Source').closest('button')!;
    const splitBtn = screen.getByText('Split').closest('button')!;
    const previewBtn = screen.getByText('Preview').closest('button')!;

    expect(sourceBtn.getAttribute('aria-checked')).toBe('true');
    expect(splitBtn.getAttribute('aria-checked')).toBe('false');
    expect(previewBtn.getAttribute('aria-checked')).toBe('false');
  });

  it('sets data-testid on the active button only', () => {
    const onChange = vi.fn();
    const { rerender } = render(
      <LayoutToggle mode="split" onChange={onChange} />,
    );
    expect(screen.getByTestId('layout-split')).toBeDefined();
    expect(screen.queryByTestId('layout-source')).toBeNull();
    expect(screen.queryByTestId('layout-preview')).toBeNull();

    rerender(<LayoutToggle mode="preview" onChange={onChange} />);
    expect(screen.queryByTestId('layout-split')).toBeNull();
    expect(screen.getByTestId('layout-preview')).toBeDefined();
  });

  it('clicking a button calls onChange with the correct mode', () => {
    const onChange = vi.fn();
    render(<LayoutToggle mode="split" onChange={onChange} />);

    fireEvent.click(screen.getByText('Source'));
    expect(onChange).toHaveBeenCalledWith('source');

    fireEvent.click(screen.getByText('Preview'));
    expect(onChange).toHaveBeenCalledWith('preview');

    fireEvent.click(screen.getByText('Split'));
    expect(onChange).toHaveBeenCalledWith('split');
  });

  it('arrow keys cycle through modes', () => {
    const onChange = vi.fn();
    render(<LayoutToggle mode="split" onChange={onChange} />);

    const group = screen.getByRole('radiogroup');

    // ArrowRight from split -> source
    fireEvent.keyDown(group, { key: 'ArrowRight' });
    expect(onChange).toHaveBeenCalledWith('source');

    // ArrowLeft from split -> preview (wraps)
    onChange.mockClear();
    fireEvent.keyDown(group, { key: 'ArrowLeft' });
    expect(onChange).toHaveBeenCalledWith('preview');
  });

  it('sets tabIndex=0 on active, tabIndex=-1 on inactive', () => {
    const onChange = vi.fn();
    render(<LayoutToggle mode="source" onChange={onChange} />);

    const buttons = screen.getAllByRole('radio');
    const splitBtn = buttons[0]; // split
    const sourceBtn = buttons[1]; // source (active)
    const previewBtn = buttons[2]; // preview

    expect(splitBtn.getAttribute('tabindex')).toBe('-1');
    expect(sourceBtn.getAttribute('tabindex')).toBe('0');
    expect(previewBtn.getAttribute('tabindex')).toBe('-1');
  });
});
