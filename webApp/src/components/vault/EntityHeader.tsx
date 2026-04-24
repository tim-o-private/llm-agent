/**
 * SPEC-053 AC-22: Entity-specific header for the file detail view.
 *
 * Renders above the editor/preview split when the current file is an
 * entity doc. Shows: entity type badge, display name, and key metadata
 * fields that vary by entity type.
 */

import React from 'react';

interface EntityHeaderProps {
  /** Parsed YAML frontmatter as a key-value map */
  frontmatter: Record<string, unknown>;
}

const TYPE_LABELS: Record<string, string> = {
  person: 'Person',
  project: 'Project',
  company: 'Company',
};

const TYPE_COLORS: Record<string, string> = {
  person:
    'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20',
  project:
    'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20',
  company:
    'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20',
};

/**
 * Render a single metadata field as "label: value".
 */
const MetaField: React.FC<{ label: string; value: unknown }> = ({
  label,
  value,
}) => {
  if (value === null || value === undefined || value === '') return null;
  const displayValue = typeof value === 'string' ? value : String(value);
  // Strip wikilink syntax for display: [[acme-corp]] → acme-corp
  const cleaned = displayValue.replace(/\[\[([^\]|]+)(?:\|[^\]]+)?\]\]/g, '$1');
  return (
    <span className="text-xs text-text-secondary">
      <span className="text-text-muted">{label}:</span>{' '}
      {cleaned}
    </span>
  );
};

/**
 * Select which metadata fields to show based on entity type.
 */
function getMetaFields(
  entityType: string,
  fm: Record<string, unknown>,
): Array<{ label: string; value: unknown }> {
  switch (entityType) {
    case 'person':
      return [
        { label: 'Role', value: fm.role },
        { label: 'Company', value: fm.company },
        { label: 'Email', value: fm.email },
      ];
    case 'project':
      return [
        { label: 'Status', value: fm.status },
        { label: 'Owner', value: fm.owner },
        { label: 'Due', value: fm.due },
      ];
    case 'company':
      return [
        { label: 'Domain', value: fm.domain },
        { label: 'Industry', value: fm.industry },
        { label: 'Relationship', value: fm.relationship },
      ];
    default:
      return [];
  }
}

export const EntityHeader: React.FC<EntityHeaderProps> = ({ frontmatter }) => {
  const entityType = String(frontmatter.entity_type ?? '');
  const name = String(frontmatter.name ?? '');
  const typeLabel = TYPE_LABELS[entityType] ?? entityType;
  const typeColor =
    TYPE_COLORS[entityType] ??
    'bg-gray-500/10 text-gray-600 dark:text-gray-400 border-gray-500/20';

  const metaFields = getMetaFields(entityType, frontmatter).filter(
    (f) => f.value !== null && f.value !== undefined && f.value !== '',
  );

  return (
    <div
      className="px-6 py-3 border-b border-ui-border bg-ui-element-bg/30 flex items-center gap-3 flex-wrap"
      data-testid="entity-header"
    >
      {/* Type badge */}
      <span
        className={`inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-semibold uppercase tracking-wider border ${typeColor}`}
      >
        {typeLabel}
      </span>

      {/* Display name */}
      <span className="text-sm font-semibold text-text-primary">{name}</span>

      {/* Separator */}
      {metaFields.length > 0 && (
        <span className="text-text-muted">|</span>
      )}

      {/* Key metadata */}
      <div className="flex items-center gap-3 flex-wrap">
        {metaFields.map((f) => (
          <MetaField key={f.label} label={f.label} value={f.value} />
        ))}
      </div>
    </div>
  );
};
