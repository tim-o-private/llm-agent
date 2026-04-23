import { describe, it, expect } from 'vitest';
import { validateWorkflowTemplate } from '../validateWorkflowTemplate';

const VALID_TEMPLATE = [
  '---',
  'name: morning-briefing',
  'description: Compose the morning briefing.',
  'version: 1',
  'default_gate_policy: none',
  '---',
  '',
  '# Morning Briefing',
  '',
  '## Steps',
  '',
  '### step-1: Gather context',
  '- **agent:** context-gatherer',
  '- **depends_on:** []',
  '- **tools:** [web_search]',
  '- **description:** Gather calendar, email, and vault context.',
  '- **gate:** none',
].join('\n');

describe('validateWorkflowTemplate', () => {
  it('valid template passes', () => {
    const result = validateWorkflowTemplate(VALID_TEMPLATE);
    expect(result.valid).toBe(true);
    expect(result.errors).toHaveLength(0);
  });

  it('missing frontmatter fails', () => {
    const content = '# No frontmatter here\n\nJust plain markdown.';
    const result = validateWorkflowTemplate(content);
    expect(result.valid).toBe(false);
    expect(result.errors).toContain(
      'Missing YAML frontmatter (must start with ---)',
    );
  });

  it('malformed YAML fails', () => {
    const content = [
      '---',
      'name: test',
      'bad yaml: [unclosed',
      '---',
      '',
      '# Test',
    ].join('\n');
    const result = validateWorkflowTemplate(content);
    expect(result.valid).toBe(false);
    expect(
      result.errors.some((e) => e.toLowerCase().includes('yaml')),
    ).toBe(true);
  });

  it("missing 'name' field fails", () => {
    const content = [
      '---',
      'description: No name here',
      'version: 1',
      '---',
      '',
      '# Unnamed',
    ].join('\n');
    const result = validateWorkflowTemplate(content);
    expect(result.valid).toBe(false);
    expect(
      result.errors.some((e) => e.includes("'name'")),
    ).toBe(true);
  });

  it("step missing 'agent' fails", () => {
    const content = [
      '---',
      'name: test-workflow',
      '---',
      '',
      '## Steps',
      '',
      '### step-1: Do something',
      '- **description:** This step does a thing.',
      '- **gate:** none',
    ].join('\n');
    const result = validateWorkflowTemplate(content);
    expect(result.valid).toBe(false);
    expect(
      result.errors.some((e) => e.includes('agent')),
    ).toBe(true);
  });

  it("step missing 'description' fails", () => {
    const content = [
      '---',
      'name: test-workflow',
      '---',
      '',
      '## Steps',
      '',
      '### step-1: Do something',
      '- **agent:** my-agent',
      '- **gate:** none',
    ].join('\n');
    const result = validateWorkflowTemplate(content);
    expect(result.valid).toBe(false);
    expect(
      result.errors.some((e) => e.includes('description')),
    ).toBe(true);
  });

  it('empty steps section passes (valid, zero steps)', () => {
    const content = [
      '---',
      'name: empty-workflow',
      'description: A workflow with no steps.',
      '---',
      '',
      '# Empty workflow',
      '',
      '## Steps',
      '',
    ].join('\n');
    const result = validateWorkflowTemplate(content);
    expect(result.valid).toBe(true);
    expect(result.errors).toHaveLength(0);
  });
});
