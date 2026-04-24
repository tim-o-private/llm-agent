/**
 * SPEC-053 AC-03: Deterministic name-to-slug converter for entity doc filenames.
 *
 * Mirrors the Python implementation in `chatServer/lib/slugify.py`.
 * Used for wikilink resolution and UI previews.
 *
 * "Sarah Chen" → "sarah-chen"
 * "Acme Corp." → "acme-corp"
 */

const MAX_SLUG_LEN = 200;

/**
 * Convert a display name to a kebab-case filename slug.
 *
 * Unicode is normalised to NFKD and non-ASCII characters are stripped.
 * Non-alphanumeric characters become hyphens; consecutive hyphens are
 * collapsed; leading/trailing hyphens are removed.
 */
export function slugify(name: string): string {
  if (!name) return '';
  // NFKD normalise and strip non-ASCII
  const normalised = name
    .normalize('NFKD')
    .split('')
    .filter((c) => c.charCodeAt(0) <= 127)
    .join('');
  return normalised
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, MAX_SLUG_LEN);
}
