/**
 * SPEC-053: Entity types matching the backend entity_router.py response models.
 */

export interface EntitySummary {
  slug: string;
  name: string;
  entity_type: string;
  path: string;
  aliases: string[];
}

export interface EntityIndexResponse {
  entities: EntitySummary[];
}

export interface EntitySearchResponse {
  results: EntitySummary[];
}

/**
 * Full entity document with parsed frontmatter and body.
 * Used when rendering entity-specific views.
 */
export interface EntityDoc {
  frontmatter: Record<string, unknown>;
  body: string;
  path: string;
}

/**
 * Client-side entity index: a lookup-optimised structure built from
 * the EntityIndexResponse for wikilink resolution and entity type badges.
 */
export type EntityIndex = EntitySummary[];
