/**
 * SPEC-048 AC-11: Client-side validation for .flow.md workflow templates.
 *
 * Mirrors server-side template_parser.py expectations:
 *   - YAML frontmatter with `name` field required
 *   - Steps follow `### step-N: Name` pattern
 *   - Each step must have `agent` and `description` fields
 *
 * Pure function -- no server round-trip.
 */

import YAML from 'yaml';
import { extractFrontmatter } from './extractFrontmatter';

export interface ValidationResult {
  valid: boolean;
  errors: string[];
}

/**
 * Validate a .flow.md template string.
 *
 * Returns `{ valid: true, errors: [] }` when valid, or
 * `{ valid: false, errors: [...] }` with human-readable error messages.
 */
export function validateWorkflowTemplate(content: string): ValidationResult {
  const errors: string[] = [];

  const { frontmatter, body } = extractFrontmatter(content);

  // --- Frontmatter checks ---

  if (!frontmatter) {
    errors.push('Missing YAML frontmatter (must start with ---)');
    return { valid: false, errors };
  }

  let parsed: Record<string, unknown>;
  try {
    parsed = YAML.parse(frontmatter);
  } catch {
    errors.push('Invalid YAML in frontmatter');
    return { valid: false, errors };
  }

  if (!parsed || typeof parsed !== 'object') {
    errors.push('Frontmatter must be a YAML mapping');
    return { valid: false, errors };
  }

  if (!parsed.name) {
    errors.push("Missing required field 'name' in frontmatter");
  }

  // --- Step checks ---

  // Match `### step-N: Name` headers
  const stepHeaderPattern = /^###\s+step-(\d+):\s+(.+)$/gm;
  const steps: Array<{ num: number; name: string; startIndex: number }> = [];

  let match: RegExpExecArray | null;
  while ((match = stepHeaderPattern.exec(body)) !== null) {
    steps.push({
      num: parseInt(match[1], 10),
      name: match[2].trim(),
      startIndex: match.index,
    });
  }

  // For each step, extract the section until the next step header or end of body
  for (let i = 0; i < steps.length; i++) {
    const step = steps[i];
    const sectionStart = step.startIndex;
    const sectionEnd =
      i + 1 < steps.length ? steps[i + 1].startIndex : body.length;
    const section = body.slice(sectionStart, sectionEnd);

    // Check for required fields using `- **field:**` pattern
    const hasAgent = /^-\s+\*\*agent:\*\*\s+.+$/m.test(section);
    const hasDescription = /^-\s+\*\*description:\*\*\s+.+$/m.test(section);

    if (!hasAgent) {
      errors.push(`Step ${step.num} (${step.name}): missing 'agent' field`);
    }
    if (!hasDescription) {
      errors.push(
        `Step ${step.num} (${step.name}): missing 'description' field`,
      );
    }
  }

  return { valid: errors.length === 0, errors };
}
