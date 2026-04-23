/**
 * SPEC-053 AC-08: Enhanced wikilink anchor with entity type icon.
 *
 * Entity links show a small type indicator before the link text:
 * person icon for `person`, folder icon for `project`, building icon
 * for `company`. Non-entity wikilinks render as plain links.
 */

import React from 'react';
import { Link } from 'react-router-dom';

interface EntityWikiLinkProps {
  href: string;
  entityType?: string;
  children: React.ReactNode;
}

/**
 * Inline SVG icons for entity types. Kept minimal (14x14) so they
 * sit naturally beside link text.
 */
const PersonIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg
    className={className}
    viewBox="0 0 16 16"
    fill="currentColor"
    aria-hidden="true"
  >
    <path d="M10.5 5a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0ZM3 13c0-2.76 2.24-5 5-5s5 2.24 5 5H3Z" />
  </svg>
);

const ProjectIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg
    className={className}
    viewBox="0 0 16 16"
    fill="currentColor"
    aria-hidden="true"
  >
    <path d="M1.75 1A1.75 1.75 0 0 0 0 2.75v10.5C0 14.216.784 15 1.75 15h12.5A1.75 1.75 0 0 0 16 13.25v-8.5A1.75 1.75 0 0 0 14.25 3H7.5a.25.25 0 0 1-.2-.1l-.9-1.2A1.75 1.75 0 0 0 4.65 1H1.75Z" />
  </svg>
);

const BuildingIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg
    className={className}
    viewBox="0 0 16 16"
    fill="currentColor"
    aria-hidden="true"
  >
    <path d="M3 1a1 1 0 0 0-1 1v12h3v-3h6v3h3V2a1 1 0 0 0-1-1H3Zm1 3h2v2H4V4Zm5 0H7v2h2V4ZM4 7h2v2H4V7Zm5 0H7v2h2V7Z" />
  </svg>
);

const entityIcons: Record<string, React.FC<{ className?: string }>> = {
  person: PersonIcon,
  project: ProjectIcon,
  company: BuildingIcon,
};

export const EntityWikiLink: React.FC<EntityWikiLinkProps> = ({
  href,
  entityType,
  children,
}) => {
  const Icon = entityType ? entityIcons[entityType] : undefined;

  return (
    <Link
      to={href}
      className="text-text-accent hover:underline inline-flex items-center gap-0.5"
    >
      {Icon && (
        <Icon className="h-3.5 w-3.5 flex-shrink-0 opacity-60" />
      )}
      {children}
    </Link>
  );
};
