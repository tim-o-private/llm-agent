/**
 * SPEC-047 AC-15: Extract wiki-link citations from markdown content.
 *
 * Scans for `[[target]]` and `[[target|display]]` patterns and returns
 * a deduplicated array of citation objects.
 */

export interface Citation {
  /** Zero-based index of this citation in the document order */
  index: number;
  /** The link target (filename without extension) */
  target: string;
  /** Display text — equals target when no alias is given */
  display: string;
}

const WIKILINK_PATTERN = /\[\[([^\]|]+?)(?:\|([^\]]+?))?\]\]/g;

export function extractCitations(content: string): Citation[] {
  if (!content) return [];

  const seen = new Set<string>();
  const results: Citation[] = [];
  let match: RegExpExecArray | null;
  let index = 0;

  // Reset lastIndex for the global regex
  WIKILINK_PATTERN.lastIndex = 0;

  while ((match = WIKILINK_PATTERN.exec(content)) !== null) {
    const target = match[1].trim();
    const display = match[2]?.trim() || target;

    // Deduplicate by target
    if (!seen.has(target)) {
      seen.add(target);
      results.push({ index, target, display });
      index++;
    }
  }

  return results;
}
