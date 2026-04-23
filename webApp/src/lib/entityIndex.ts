/**
 * SPEC-053 AC-06: Client-side entity index for wikilink resolution.
 *
 * The entity index is fetched once on app load (via useEntityIndex) and
 * used to resolve `[[target]]` wikilinks to entity doc paths.
 *
 * Resolution order:
 *   1. Exact slug match in entity index
 *   2. Display-name slugify → slug match
 *   3. Alias match (slug or case-insensitive string)
 *   4. Fallback: non-entity vault path `/vault/<target>.md`
 */

import { slugify } from './slugify';
import type { EntitySummary } from '@/api/types/entity';

export type EntityIndexEntry = EntitySummary;

/**
 * Resolve a wikilink target to a vault path using the entity index.
 *
 * Returns a path like `/vault/entities/people/sarah-chen.md` for entity
 * matches, or `/vault/<target>.md` as a fallback for non-entity links.
 */
export function resolveWikiLink(
  target: string,
  entityIndex: EntityIndexEntry[],
): string {
  const slug = slugify(target);

  // 1. Exact slug match
  const exactMatch = entityIndex.find((e) => e.slug === slug);
  if (exactMatch) return `/vault/${exactMatch.path}`;

  // 2. Already handled by step 1 (slugify normalises display names)

  // 3. Alias match: slugified alias or case-insensitive string
  const aliasMatch = entityIndex.find((e) =>
    e.aliases.some(
      (a) =>
        slugify(a) === slug || a.toLowerCase() === target.toLowerCase(),
    ),
  );
  if (aliasMatch) return `/vault/${aliasMatch.path}`;

  // 4. Fallback: non-entity vault path
  return `/vault/${target}.md`;
}

/**
 * Look up an entity by slug in the index.
 * Returns undefined if no match is found.
 */
export function findEntityBySlug(
  slug: string,
  entityIndex: EntityIndexEntry[],
): EntityIndexEntry | undefined {
  return entityIndex.find((e) => e.slug === slug);
}
