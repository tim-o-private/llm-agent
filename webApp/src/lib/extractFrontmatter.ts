/**
 * SPEC-047 AC-09 / AC-18: Extract YAML frontmatter from a markdown string.
 *
 * Splits on leading `---` delimiters. Returns the raw YAML string (without
 * delimiters) and the remaining body. If no valid frontmatter is found,
 * returns the entire string as body with `frontmatter: null`.
 */

export interface FrontmatterResult {
  frontmatter: string | null;
  body: string;
}

export function extractFrontmatter(content: string): FrontmatterResult {
  // Frontmatter must start at the very beginning of the file
  if (!content.startsWith('---')) {
    return { frontmatter: null, body: content };
  }

  // Find the closing delimiter (skip the opening "---")
  const closingIndex = content.indexOf('\n---', 3);
  if (closingIndex === -1) {
    // No closing delimiter — treat entire content as body
    return { frontmatter: null, body: content };
  }

  // Extract the YAML between delimiters (skip the opening "---\n")
  const fmStart = content.indexOf('\n', 0);
  if (fmStart === -1) {
    return { frontmatter: null, body: content };
  }

  const frontmatter = content.slice(fmStart + 1, closingIndex).trim();

  // Body starts after the closing "---" and its trailing newline
  const bodyStart = closingIndex + 4; // length of "\n---"
  const body = bodyStart < content.length ? content.slice(bodyStart).replace(/^\n/, '') : '';

  return {
    frontmatter: frontmatter || null,
    body,
  };
}
