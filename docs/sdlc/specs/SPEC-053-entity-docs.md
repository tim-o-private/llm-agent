# SPEC-053: Entity Docs (Stage 4 -- Auto-maintained Entity Pages)

> **Status:** Draft (contract spec)
> **Author:** spec-writer (Claude) on behalf of Tim
> **Created:** 2026-04-21
> **Vision:** [`docs/sdlc/visions/clarity-as-vault.md`](../visions/clarity-as-vault.md) -- Stage 4
> **Directive:** [`docs/sdlc/visions/clarity-as-vault-functional.md`](../visions/clarity-as-vault-functional.md) -- S1 wikilinks in Your Day/Agent, S2 entity files in tree, S3 backlinks/citations
> **Architecture:** [`docs/sdlc/visions/clarity-as-vault-architecture.md`](../visions/clarity-as-vault-architecture.md) -- entity-refresher agent (Haiku 4.5), model routing table
> **Depends on:** SPEC-045 (VaultService, today.md), SPEC-046 (vault browser, file tree), SPEC-047 (file detail view, backlinks, remark-wiki-link, ContextRail)
> **Downstream:** SPEC-054 (orchestration proposals may create entity docs), SPEC-051 (capture routes to entity pages)
> **Stage:** Clarity-as-Vault Stage 4

---

## Goal

Ship **auto-maintained entity documents** -- person, project, and company pages that the agent keeps current. Entity docs are plain markdown files in the vault with structured YAML frontmatter. The `entity-refresher` agent extracts information from emails, calendar events, captures, and other vault activity, then writes or updates entity files. Wikilinks (`[[sarah-chen]]`) in other documents create backlinks to entity pages; the "Linked by" section in SPEC-047's ContextRail shows which files reference each entity.

This is the spec that makes the vault feel like a living graph rather than a collection of notes. Entity docs connect the dots: a meeting note mentions `[[Sarah Chen]]`, the entity page for Sarah shows the link, and the agent keeps Sarah's page current with her latest role, recent interactions, and relevant context.

Stage 4 exit criterion from the vision: **does the graph feel alive?**

### What this spec is and is not

This is a **contract spec** -- it defines the entity document format, the entity-refresher agent contract, the entity discovery mechanism, and the backlink integration with SPEC-047, with enough precision that Stages 1-3 do not make decisions that break entity docs. It does not contain FU-level PR breakdowns or detailed Playwright scripts. Implementation-level detail will be added when Stage 4 enters the build queue.

---

## Existing Infrastructure (what we reuse)

| Primitive | Source | What we use it for |
|-----------|--------|--------------------|
| VaultService | SPEC-045 `chatServer/services/vault_service.py` | All entity file reads/writes. `_resolve` is the security chokepoint. `update_body` fires StorageSync. Entity docs are vault files -- no separate storage. |
| `VaultService.find_backlinks` | SPEC-047 `chatServer/services/vault_service.py` | Backlinks computation: walks vault, greps for `[[filename]]`. Entity docs are primary producers of backlink targets. |
| ContextRail -- "Linked by" section | SPEC-047 `webApp/src/components/vault/ContextRail.tsx` | Displays backlinks for the current file. Entity docs surface here with no additional UI work. |
| ContextRail -- "Citations" section | SPEC-047 | Outgoing wikilinks from an entity doc list other entities and files it references. |
| `remark-wiki-link` in MarkdownPreview | SPEC-047 `webApp/src/components/vault/MarkdownPreview.tsx` | Renders `[[entity-name]]` as clickable links in any vault file. Already configured with `pageResolver` and `hrefTemplate`. |
| File tree | SPEC-046 `webApp/src/components/vault/FileTree.tsx` | Entity folder (`entities/`) visible in the vault browser. |
| `GET /vault/tree` | SPEC-046 `chatServer/routers/vault_router.py` | Returns recursive listing including `entities/` subdirectories. |
| `GET /vault/file` | SPEC-046 | Reads entity doc content for rendering in file detail view. |
| `PUT /vault/file` | SPEC-047 | User can edit entity docs manually. |
| Workflow engine | SPEC-036 `chatServer/workflows/run_manager.py` | Dispatches the entity-refresh workflow on schedule or trigger. |
| `activity_log` table | SPEC-045/050 | Entity refresh actions are logged. |
| `markdown_sections` parser | SPEC-045 `chatServer/services/markdown_sections.py` | Parse/patch sections within entity docs. |
| Capture routing | SPEC-051 | Captures mentioning known entities route to entity pages. |
| `suggest_cards` | SPEC-047 | Entity-refresher can propose updates via suggest cards on entity docs. |

---

## Entity Document Format

### Directory structure

Entity docs live under `entities/` in the user's vault root, organized by type:

```
vault/
  entities/
    people/
      sarah-chen.md
      bob-martinez.md
    projects/
      website-redesign.md
      q3-planning.md
    companies/
      acme-corp.md
      stlvr-coffee.md
  today.md
  ...
```

The `entities/` directory and its subdirectories (`people/`, `projects/`, `companies/`) are seeded on first use (AC-01). Additional entity type directories can be added by the user or agent.

### Filename convention

Entity filenames are kebab-cased from the entity name: `Sarah Chen` becomes `sarah-chen.md`. This is also the wikilink target: `[[sarah-chen]]`. The `pageResolver` in `remark-wiki-link` (already configured in SPEC-047) resolves `[[sarah-chen]]` to `/vault/entities/people/sarah-chen.md` -- see AC-06 for the resolution algorithm.

### Frontmatter schema

Every entity doc starts with YAML frontmatter declaring its type and metadata. The frontmatter is the structured data layer; the body is free-form prose.

**Person:**

```yaml
---
entity_type: person
name: Sarah Chen
aliases:
  - S. Chen
  - sarah@acme.com
role: VP Engineering
company: "[[acme-corp]]"
last_contact: 2026-04-15
email: sarah@acme.com
tags:
  - engineering
  - leadership
refreshed_at: 2026-04-21T08:30:00Z
---
```

**Project:**

```yaml
---
entity_type: project
name: Website Redesign
status: active
owner: "[[sarah-chen]]"
company: "[[acme-corp]]"
started: 2026-03-01
due: 2026-06-15
tags:
  - engineering
  - web
refreshed_at: 2026-04-21T08:30:00Z
---
```

**Company:**

```yaml
---
entity_type: company
name: Acme Corp
domain: acme.com
industry: SaaS
relationship: client
tags:
  - client
  - enterprise
refreshed_at: 2026-04-21T08:30:00Z
---
```

**Required fields (all types):** `entity_type`, `name`, `refreshed_at`.
**Optional fields:** everything else. The agent adds fields as it discovers information. Users can add arbitrary fields -- the schema is open-ended. Unknown fields are preserved on refresh (the agent reads the full frontmatter, updates known fields, and writes back without dropping unknown ones).

### Body structure

The body uses H2 sections following the same convention as `today.md`. Minimum sections per entity type:

**Person:**
```markdown
## Context
One-paragraph summary of who this person is and why they matter.

## Recent interactions
- 2026-04-15: Email thread about Q3 timeline [[q3-planning]]
- 2026-04-10: Meeting: sprint review (30min)

## Notes
User-captured notes and agent-surfaced context.
```

**Project:**
```markdown
## Overview
What this project is and its current state.

## Key people
- [[sarah-chen]] -- owner
- [[bob-martinez]] -- frontend lead

## Timeline
- 2026-03-01: Started
- 2026-06-15: Target completion

## Notes
```

**Company:**
```markdown
## About
What this company does and its relationship to the user.

## Key people
- [[sarah-chen]] -- VP Engineering
- [[bob-martinez]] -- Senior Developer

## Notes
```

The agent may add sections beyond these (e.g., `## Open questions`, `## Meeting history`). The `markdown_sections` parser preserves unknown sections.

---

## Acceptance Criteria

### Entity doc format and structure

- [ ] **AC-01:** Seed entity directory structure. On first access to any entity endpoint or on vault hydration, `VaultService` ensures `entities/people/`, `entities/projects/`, and `entities/companies/` directories exist under the user's vault root. No seed entity docs are created -- only the directory structure. [A14]

- [ ] **AC-02:** Entity docs are valid Obsidian-compatible markdown. YAML frontmatter is delimited by `---`. The `entity_type` field is one of `person`, `project`, `company`, or a user-defined string. The `name` field is a non-empty string. `refreshed_at` is an ISO 8601 timestamp set by the entity-refresher on every write. Unknown frontmatter fields are preserved across agent updates. [F1]

- [ ] **AC-03:** Entity doc filenames are derived from the `name` field via a deterministic slugifier: lowercase, spaces and non-alphanumeric characters replaced with hyphens, consecutive hyphens collapsed, leading/trailing hyphens stripped. `Sarah Chen` becomes `sarah-chen.md`. The slugifier is a pure function with unit tests. [A10]

### Entity CRUD via VaultService

- [ ] **AC-04:** Entity docs are created, read, updated, and deleted through the existing vault endpoints (`PUT /vault/file`, `GET /vault/file`, `DELETE /vault/file` when it ships). No separate entity CRUD API. The entity-refresher agent writes entity docs via `VaultService.update_body`. Users edit entity docs via the file detail view (SPEC-047). [A1, A14]

- [ ] **AC-05:** A new `EntityService` provides entity-specific operations composed on top of VaultService:
  - `list_entities(user_id, entity_type?) -> list[EntitySummary]` -- walks `entities/` subdirectories, reads frontmatter from each `.md` file, returns structured summaries. Cached per-request.
  - `get_entity(user_id, entity_type, slug) -> EntityDoc` -- reads the file, parses frontmatter + body, returns structured data.
  - `upsert_entity(user_id, entity_type, slug, frontmatter, body) -> float` -- writes the entity doc, preserving unknown frontmatter fields. Returns new mtime.
  - `find_entity_by_alias(user_id, alias) -> EntitySummary | None` -- scans entity frontmatter `aliases` arrays for a match (email address, alternate name).
  - `search_entities(user_id, query) -> list[EntitySummary]` -- searches entity names and aliases by substring match. Stage 4: no full-text index.

### Wikilink resolution for entities

- [ ] **AC-06:** The `remark-wiki-link` `pageResolver` in `MarkdownPreview` (SPEC-047) is extended with entity-aware resolution. Resolution order:
  1. Exact match: `[[sarah-chen]]` resolves to `/vault/entities/people/sarah-chen.md` (or `projects/`, `companies/` -- whichever directory contains a matching file).
  2. Display-name match: `[[Sarah Chen]]` slugifies to `sarah-chen`, then follows step 1.
  3. Alias match: if no file matches by slug, search entity frontmatter `aliases` arrays.
  4. Fallback: resolve to `/vault/<target>.md` as today (non-entity path -- may or may not exist).
  The resolution uses a client-side entity index (AC-07) fetched on app load. No server round-trip per wikilink. [A14]

- [ ] **AC-07:** A new endpoint `GET /vault/entities/index` returns a lightweight entity index: `{ entities: Array<{ slug: string, name: string, entity_type: string, path: string, aliases: string[] }> }`. The frontend fetches this on app load and caches it in a React Query key with a 5-minute stale time. This index powers wikilink resolution (AC-06) and entity search. [A4]

- [ ] **AC-08:** Wikilinks to entities render with a distinct visual treatment in the preview pane. Entity links show a small type indicator before the link text: a person icon for `person`, a folder icon for `project`, a building icon for `company`. Non-entity wikilinks render as plain links (no icon). The type is determined by looking up the slug in the entity index. [D4]

### Backlinks -- connecting the graph

- [ ] **AC-09:** The "Linked by" section in SPEC-047's ContextRail works for entity docs with no additional backend work. `VaultService.find_backlinks` already scans all vault `.md` files for `[[slug]]` patterns. Opening `entities/people/sarah-chen.md` shows every file that contains `[[sarah-chen]]` or `[[sarah-chen|Sarah Chen]]`. [A14]

- [ ] **AC-10:** Entity docs themselves produce outgoing wikilinks (e.g., a person's `company` frontmatter field contains `"[[acme-corp]]"`, and the body may reference `[[website-redesign]]`). These appear in the "Citations" section of the ContextRail. The `extractCitations` function (SPEC-047) already handles this -- wikilinks in both frontmatter and body are extracted. [A14]

### Entity-refresher agent

- [ ] **AC-11:** A new agent markdown file ships at `data/config/system/agents/clarity/entity-refresher.md` with frontmatter: `name: entity-refresher`, `model: haiku-4.5`, `tools: [read_file, write_file, search_gmail, list_calendar_events]`, `description: Extracts entity information from vault activity and keeps entity docs current`. The model is Haiku 4.5 per the architecture doc's model routing table -- this is extraction/summarization work, not judgment. [A2]

- [ ] **AC-12:** A new workflow file ships at `data/config/system/workflows/refresh-entities.md` defining the entity refresh workflow. The workflow has two steps:
  1. **Scan signals:** Read recent activity (emails, calendar events, captures, recently modified vault files) and extract entity mentions -- names, email addresses, roles, companies.
  2. **Update entities:** For each entity mentioned, either update the existing entity doc or propose creation of a new one.
  The workflow is triggered by: (a) scheduled cron (daily, configurable in `user_preferences`), (b) on-demand via `POST /workflows/run` with `template_name=refresh-entities`, (c) as a downstream step after the `regenerate-today` workflow completes. [A2, A14]

- [ ] **AC-13:** Entity refresh behavior rules:
  - **Existing entity:** The agent reads the current doc, updates `refreshed_at`, appends new interactions to `## Recent interactions` (prepending to the list, most recent first), updates frontmatter fields if new information is found (e.g., role change detected in email signature). The agent never deletes user-written content from the body -- it appends to sections or updates frontmatter only.
  - **New entity detected:** The agent does not create entity docs directly. Instead, it creates a `suggest_cards` entry (SPEC-047) on `today.md` proposing the new entity: "Clarity suggests: Create entity page for Sarah Chen (VP Engineering at Acme Corp, seen in 3 recent emails). Accept to create." Accepting the suggest card triggers entity doc creation. This is the approval lane for entity creation. [A12]
  - **Ambiguous entity:** When the agent cannot confidently match a mention to an existing entity (e.g., "Sarah" could be Sarah Chen or Sarah Miller), it does not update either. It may surface the ambiguity as a suggest card: "Clarity suggests: 'Sarah' in the email from Bob likely refers to [[sarah-chen]]. Confirm?" [A12]

- [ ] **AC-14:** The entity-refresher preserves the full existing frontmatter when updating. Implementation: read the file, parse YAML frontmatter into a dict, merge new keys over existing keys (never drop unknown keys), serialize back. The `yaml` library (SPEC-047 dependency, round-trips comments) handles this. Unit tests confirm round-trip preservation of unknown fields. [A14]

### Entity discovery and indexing

- [ ] **AC-15:** Entity discovery is frontmatter-based. A file is an entity doc if and only if: (a) it lives under `entities/` in the vault, and (b) its YAML frontmatter contains an `entity_type` field. The `EntityService.list_entities` method walks `entities/` and reads frontmatter from each `.md` file. There is no separate entity registry table in Postgres -- the vault is the source of truth. [A14, F1]

- [ ] **AC-16:** The entity index endpoint (AC-07) derives its response from `EntityService.list_entities`. For a vault with <500 entity files, the full walk + frontmatter parse completes within 2 seconds. If this becomes a bottleneck, a later spec adds a materialized index (a JSON sidecar file at `entities/.index.json` maintained by the entity-refresher, with the walk as a fallback). Stage 4 does not build the sidecar. [A14]

### Cold start -- bootstrapping entities from an empty vault

- [ ] **AC-17:** When a user has no entity docs, the entity-refresher's first run scans available signals (Gmail history, calendar events) and proposes a batch of entity suggestions via `suggest_cards`. Each card proposes a single entity with a preview of the entity doc the agent would create. The user drains the approval lane to build their initial entity graph. The agent does not flood the lane -- it proposes at most 10 entities per cold-start run, prioritized by interaction frequency. [A12, A14]

- [ ] **AC-18:** The regenerate-today workflow (SPEC-045) includes wikilinks to entity docs in the "Your day" section when it recognizes entities in calendar events or email threads. Before entity docs exist, these wikilinks resolve to 404 pages ("File not found in vault" from SPEC-047 AC-15). The 404 page includes a prompt: "This entity doesn't exist yet. The agent may propose creating it, or you can create it manually." This is standard wikilink behavior (link first, page later) and requires no special-casing. [A14]

### Integration with Today and Capture

- [ ] **AC-19:** The `regenerate-today` workflow's composer step (SPEC-045 `data/config/system/workflows/regenerate-today.md`) uses entity docs as context. When composing "Your day," it reads relevant entity docs to provide background on meeting participants and email correspondents. For example: "10:00 Sprint review with [[sarah-chen]] (VP Engineering, Acme Corp) -- see [[q3-planning]] for context." The entity name in the wikilink is the display name; the slug is the href target. [A14]

- [ ] **AC-20:** SPEC-051 capture routing is entity-aware. When a capture mentions a known entity (matched by name or alias), the capture-router agent considers routing the capture to that entity's `## Notes` section as one of its placement options. This is not forced routing -- the capture-router uses its existing heuristics, with entity match as an additional signal. [A14]

### Frontend entity enhancements

- [ ] **AC-21:** The file tree (SPEC-046) shows the `entities/` folder with a distinct icon and label "Entities." Subfolders (`people/`, `projects/`, `companies/`) show their respective type icons matching AC-08. Entity files in the tree show the entity `name` from frontmatter as the display name (not the filename slug), with the slug shown in JetBrains Mono below or on hover. [D4]

- [ ] **AC-22:** The file detail view (SPEC-047) renders entity docs with an entity-specific header that shows: entity type badge, display name (from frontmatter `name`), and key metadata fields (role + company for people, status + owner for projects, domain + relationship for companies). This header renders above the standard editor/preview split and is derived from the parsed frontmatter. [D4, D5]

### Auth and isolation

- [ ] **AC-23:** All entity operations inherit the existing VaultService access control model. Entity docs live in the user's vault sandbox. User A cannot read or modify User B's entities. The entity index endpoint uses `get_current_user_id` and scopes the walk to the authenticated user's vault. [A8]

---

## Scope

### What Stage 1-3 specs must preserve for entity docs to work

These are the **contract constraints** that earlier specs must not violate. Each constraint references the spec and AC that establishes the prerequisite.

| Constraint | Established by | Why entity docs need it |
|------------|---------------|------------------------|
| `remark-wiki-link` in the preview pipeline | SPEC-047 AC-09 | Entity wikilinks render as clickable links. |
| `pageResolver` accepts pluggable resolution | SPEC-047 AC-09 | AC-06 extends resolution with entity-aware lookup. |
| `VaultService.find_backlinks` scans for `[[slug]]` | SPEC-047 AC-20 | Backlinks connect entity docs to the rest of the vault. |
| `extractCitations` scans `[[...]]` in both frontmatter and body | SPEC-047 AC-15 | Outgoing links from entity docs appear in Citations rail. |
| `entities/` not excluded from `VaultService._walk_recent` | SPEC-045 | Entity docs appear in the Recent section when modified. |
| `entities/` not excluded from `GET /vault/tree` | SPEC-046 AC-21 | Entity files appear in the file tree. |
| `markdown_sections` parser preserves unknown sections | SPEC-045 | Agent can add sections to entity docs without losing user-written ones. |
| `yaml` library preserves unknown keys on round-trip | SPEC-047 (dependency) | Entity-refresher does not drop user-added frontmatter fields. |
| `suggest_cards` table exists | SPEC-047 | Entity creation proposals use suggest cards. |
| `activity_log` table exists | SPEC-045 | Entity refresh actions are logged. |
| Workflow engine dispatches by template_name | SPEC-036 | `refresh-entities` workflow runs on schedule or demand. |
| `user_preferences` table accepts new columns | SPEC-045 pattern | Entity refresh scheduling adds preference columns. |

### Files to create

| File | Purpose |
|------|---------|
| `chatServer/services/entity_service.py` | Entity-specific operations: list, get, upsert, find-by-alias, search. Composes VaultService. |
| `chatServer/routers/entity_router.py` | `GET /vault/entities/index`, `GET /vault/entities/search?q=`. Thin router over EntityService. [A1] |
| `chatServer/lib/slugify.py` | Pure function: name to kebab-case slug. Deterministic, unit-tested. |
| `data/config/system/agents/clarity/entity-refresher.md` | Agent markdown: model, tools, description. |
| `data/config/system/workflows/refresh-entities.md` | Workflow: scan signals, update/propose entities. |
| `data/config/system/templates/entity-person.md` | Seed template for person entity docs. |
| `data/config/system/templates/entity-project.md` | Seed template for project entity docs. |
| `data/config/system/templates/entity-company.md` | Seed template for company entity docs. |
| `webApp/src/lib/entityIndex.ts` | Client-side entity index: fetch, cache, resolve wikilinks. |
| `webApp/src/components/vault/EntityHeader.tsx` | Entity-specific header for the file detail view (type badge, name, key metadata). |
| `webApp/src/components/vault/EntityWikiLink.tsx` | Enhanced wikilink anchor with entity type icon. |
| `webApp/src/api/hooks/useEntityHooks.ts` | `useEntityIndex`, `useEntitySearch`. [A4] |
| `webApp/src/api/types/entity.ts` | `EntitySummary`, `EntityDoc`, `EntityIndex` types. |
| `supabase/migrations/YYYYMMDD_user_prefs_entity_refresh.sql` | Add `entity_refresh_enabled` (BOOL, default false) and `entity_refresh_time` (TEXT, default '07:00') to `user_preferences`. |
| `tests/unit/services/test_entity_service.py` | Entity list, get, upsert, alias search, frontmatter preservation. |
| `tests/unit/lib/test_slugify.py` | Slugifier edge cases: unicode, special chars, consecutive hyphens, empty string. |
| `tests/integration/test_entity_api.py` | Entity index endpoint, auth, cross-user isolation. |
| `webApp/src/lib/slugify.ts` | Client-side slugifier (same algorithm as Python, for UI previews). |
| `webApp/src/lib/slugify.test.ts` | Client-side slugifier tests. |

### Files to modify

| File | Change |
|------|--------|
| `webApp/src/components/vault/MarkdownPreview.tsx` | Extend `pageResolver` to use entity index for resolution (AC-06). Use `EntityWikiLink` component for entity links (AC-08). |
| `webApp/src/components/vault/FileDetailView.tsx` | Detect entity docs by path + frontmatter, render `EntityHeader` when applicable (AC-22). |
| `webApp/src/components/vault/FileTree.tsx` | Entity-specific display names and icons for `entities/` subtree (AC-21). |
| `chatServer/main.py` | Register `entity_router`. |
| `chatServer/services/vault_service.py` | Add `ensure_dirs(user_id, dirs)` method for seeding empty directories (AC-01). |
| `data/config/system/workflows/regenerate-today.md` | Composer step references entity docs for meeting participant context (AC-19). |

### Out of scope

- **Entity merging/deduplication UI** -- manual only in Stage 4. Agent surfaces ambiguity; user resolves.
- **Full-text search across entity docs** -- substring match on name/alias in Stage 4. Full-text index is a later spec.
- **Entity relationship graph visualization** -- deferred. Power users get this via Obsidian.
- **Entity doc versioning / change history** -- git-backed in the vault; UI for viewing history is a SPEC-047 deferred item.
- **Bulk entity import** -- no CSV/vCard import. Entities are built incrementally from signals.
- **Entity deletion workflow** -- users delete via vault file operations. No special entity-specific deletion flow.
- **Real-time entity index updates** -- index has a 5-minute stale time. After entity creation, the user refreshes or waits for cache invalidation. Acceptable for Stage 4 volumes.
- **Non-text entity types** -- no images, attachments, or binary data in entity docs. Links to external resources are plain URLs.
- **Cross-user entity sharing** -- entities are per-user vault files. No sharing mechanism.
- **Agent-initiated entity graph restructuring** -- the agent proposes new entities but does not reorganize the `entities/` directory structure. That is Stage 5 orchestration-proposal territory.

---

## Technical Approach

### 1. EntityService -- entity operations on top of VaultService

`EntityService` is a thin layer that knows about entity semantics (frontmatter schema, directory conventions, slug generation) while delegating all file I/O to `VaultService`. This follows A1 (thin routers, fat services) and keeps VaultService as the single security chokepoint.

```python
class EntityService:
    def __init__(self, vault: VaultService):
        self._vault = vault

    async def list_entities(
        self, user_id: str, entity_type: str | None = None
    ) -> list[EntitySummary]:
        """Walk entities/ subdirectories, read frontmatter from each .md file."""
        ...

    async def get_entity(
        self, user_id: str, entity_type: str, slug: str
    ) -> EntityDoc:
        """Read entities/{entity_type}/{slug}.md, parse frontmatter + body."""
        rel_path = f"entities/{entity_type}/{slug}.md"
        content = await self._vault.read_file(user_id, rel_path)
        frontmatter, body = parse_frontmatter(content)
        return EntityDoc(frontmatter=frontmatter, body=body, path=rel_path)

    async def upsert_entity(
        self, user_id: str, entity_type: str, slug: str,
        frontmatter: dict, body: str
    ) -> float:
        """Write entity doc, preserving unknown frontmatter fields."""
        rel_path = f"entities/{entity_type}/{slug}.md"
        existing_fm = {}
        try:
            existing_content = await self._vault.read_file(user_id, rel_path)
            existing_fm, _ = parse_frontmatter(existing_content)
        except HTTPException:
            pass  # new entity
        merged_fm = {**existing_fm, **frontmatter}
        merged_fm["refreshed_at"] = datetime.now(timezone.utc).isoformat()
        content = serialize_entity_doc(merged_fm, body)
        return await self._vault.update_body(user_id, rel_path, content)

    async def find_entity_by_alias(
        self, user_id: str, alias: str
    ) -> EntitySummary | None:
        """Scan entity frontmatter aliases for a match."""
        for entity in await self.list_entities(user_id):
            if alias.lower() in [a.lower() for a in entity.aliases]:
                return entity
        return None
```

### 2. Slugifier -- deterministic name-to-filename mapping

A pure function used by both Python (entity-refresher, EntityService) and TypeScript (wikilink resolution, UI previews):

```python
# chatServer/lib/slugify.py
import re
import unicodedata

def slugify(name: str) -> str:
    """Convert a display name to a kebab-case filename slug.

    'Sarah Chen' -> 'sarah-chen'
    'Acme Corp.' -> 'acme-corp'
    'O'Brien & Associates' -> 'obrien-associates'
    """
    s = unicodedata.normalize("NFKD", name)
    s = s.encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-")
```

The TypeScript version is byte-for-byte equivalent in behavior. Unit tests for both include: unicode names, apostrophes, ampersands, consecutive spaces, empty string, already-slugified input.

### 3. Entity-aware wikilink resolution

The `remark-wiki-link` `pageResolver` in SPEC-047 currently resolves `[[target]]` to `/vault/<target>.md`. Entity-aware resolution wraps this with an index lookup:

```typescript
// webApp/src/lib/entityIndex.ts

export interface EntityIndexEntry {
  slug: string;
  name: string;
  entity_type: string;
  path: string;
  aliases: string[];
}

export function resolveWikiLink(
  target: string,
  entityIndex: EntityIndexEntry[]
): string {
  const slug = slugify(target);

  // 1. Exact slug match in entity index
  const exactMatch = entityIndex.find(e => e.slug === slug);
  if (exactMatch) return `/${exactMatch.path}`;

  // 2. Alias match
  const aliasMatch = entityIndex.find(e =>
    e.aliases.some(a => slugify(a) === slug || a.toLowerCase() === target.toLowerCase())
  );
  if (aliasMatch) return `/${aliasMatch.path}`;

  // 3. Fallback: non-entity vault path
  return `/vault/${target}.md`;
}
```

The `MarkdownPreview` component passes a custom `pageResolver` that calls `resolveWikiLink` with the cached entity index. The entity index is fetched once on app load via `useEntityIndex` (React Query, 5-minute stale time) and provided to `MarkdownPreview` via props or context.

### 4. Entity-refresher workflow

The `refresh-entities.md` workflow:

```markdown
---
name: refresh-entities
description: Scan recent signals and update/propose entity docs
version: 1
default_gate_policy: none
---

## Parameters
| Parameter | Required | Description |
|-----------|----------|-------------|
| scope | no | 'full' (scan all signals) or 'incremental' (since last refresh). Default: incremental. |
| max_proposals | no | Maximum new entity proposals per run. Default: 10. |

## Steps

### step-1: Scan signals
- **agent:** entity-refresher
- **depends_on:** []
- **tools:** [read_file, search_gmail, list_calendar_events]
- **description:** Read recent emails (last 24h for incremental, last 30 days for full), calendar events (next 7 days + last 7 days), and recently modified vault files. Extract entity mentions: person names, email addresses, company names, project references. Cross-reference against existing entity docs. Output: list of (entity_slug, entity_type, update_data) tuples for existing entities; list of (name, entity_type, evidence) tuples for proposed new entities.
- **gate:** none

### step-2: Update existing entities
- **agent:** entity-refresher
- **depends_on:** [step-1]
- **tools:** [read_file, write_file]
- **description:** For each existing entity with new information: read the current doc, update frontmatter fields (role, last_contact, etc.), prepend new interactions to Recent interactions section. Preserve all existing content. Write back via write_file. Log each update to activity_log.
- **gate:** none

### step-3: Propose new entities
- **agent:** entity-refresher
- **depends_on:** [step-1]
- **tools:** [write_file]
- **description:** For each proposed new entity (up to max_proposals): create a suggest_card on today.md with a preview of the entity doc. Do not create the entity doc directly. The suggest card body shows: entity name, type, evidence (which emails/events mention this entity), and a preview of the proposed doc. Accepting the card triggers entity creation.
- **gate:** none
```

### 5. Suggest card integration for entity creation

When the user accepts a suggest card proposing a new entity (from step-3 above), the accept handler creates the entity doc. This extends SPEC-047's suggest card accept flow:

The suggest card for entity creation has a `suggested_text` payload containing the full entity doc content (frontmatter + body). The `target_line` is 0 (not a line insertion -- it is a file creation). A new field `action_type: 'create_entity'` in the suggest card's metadata distinguishes entity creation cards from inline text suggestions.

The accept endpoint detects `action_type: 'create_entity'` and calls `EntityService.upsert_entity` instead of inserting text at a line number. This is a small extension to SPEC-047 AC-22's accept handler.

### 6. Performance considerations

- **Entity index (`GET /vault/entities/index`):** For a vault with <500 entity files (~2KB frontmatter each), a full walk + parse takes ~200ms. Acceptable for a 5-minute cached endpoint. At scale, the materialized `.index.json` sidecar optimizes this to a single file read.
- **Backlinks on entity docs:** `VaultService.find_backlinks` walks the entire vault. For <500 total files, this is <2s (SPEC-047 estimate). Entity docs are likely to be heavily linked, so their backlink lists may be long -- the ContextRail should paginate or truncate at 20 entries with a "Show all" toggle.
- **Entity-refresher workflow:** Haiku 4.5 is cheap per the architecture doc's model routing table. A full scan of 30 days of email + calendar is bounded by the Gmail/Calendar API pagination, not by model cost. Incremental scans (last 24h) are the default and complete in seconds.

---

## Edge Cases

- **Entity with same name as a non-entity vault file:** The slugifier produces the same filename. Resolution order (AC-06) checks `entities/` first. A file at `vault/sarah-chen.md` and `vault/entities/people/sarah-chen.md` coexist without conflict -- `[[sarah-chen]]` resolves to the entity.
- **Two entities with the same slug:** Entities in different type directories can share a slug (`entities/people/acme.md` and `entities/companies/acme.md`). Wikilink `[[acme]]` resolves to the first match in type priority order: `person` > `project` > `company`. To disambiguate, users write `[[acme-corp]]` or use the full path: link text in `[[entities/companies/acme|Acme]]`.
- **Entity doc with missing frontmatter:** If a file under `entities/` lacks `entity_type` in frontmatter, it is excluded from the entity index (AC-15). It still renders normally in the file detail view -- just without the entity header (AC-22). The entity-refresher does not touch files without proper frontmatter.
- **Entity doc manually moved out of `entities/`:** The file disappears from the entity index. Backlinks to it still resolve (the file still exists at the new path, but the wikilink resolver falls through to the non-entity fallback). The entity-refresher may propose re-creating the entity if it still detects signals for that person/project/company.
- **Very long entity name:** The slugifier truncates to 200 characters (filesystem limit safety). Names that collide after truncation get a numeric suffix (`sarah-chen-2`).
- **Unicode names:** The slugifier normalizes to NFKD and strips non-ASCII. `Muller` and `Mueller` produce different slugs. The alias system (frontmatter `aliases`) handles display-name variants.
- **Agent updates entity while user is editing:** Same as SPEC-047's concurrent edit handling: `VaultService.update_body` with `expected_mtime` catches the race. The second write gets 409. The entity-refresher retries once with the fresh content; on second failure, it logs the conflict and skips the update (the entity is not stale enough to warrant forcing).
- **Entity-refresher proposes an entity that already exists:** The suggest card creation logic checks the entity index before proposing. If a match exists, the agent updates the existing entity instead of proposing a new one.
- **No email/calendar signals available (BYOK not configured):** The entity-refresher gracefully handles missing tool access. It falls back to scanning vault content only (recently modified files, captures). Entity docs can still be created manually or from vault-only signals.
- **First run with large email history:** Full scan is bounded by `max_proposals` (default 10). The agent prioritizes entities by interaction frequency. Subsequent incremental scans are much cheaper.

---

## Resolved Questions (2026-04-21, Tim approved all recommendations)

### 1. Entity type extensibility — **RESOLVED: fixed set with extensible code**

Three known types (person, project, company) get icon/header treatment. `entity_type` is a free string; unknown types get generic treatment. Custom types emerge organically rather than being explicitly documented in Stage 4.

### 2. Entity creation mechanism — **RESOLVED: suggest cards**

Suggest cards (SPEC-047) for entity proposals. Lighter-weight than approval cards. Entity creation is non-destructive (creates a new file); the approval lane is reserved for world-facing actions.

### 3. Wikilink resolution scope — **RESOLVED: entity-only in Stage 4, designed for vault-wide upgrade**

Stage 4 ships entity index only. `pageResolver` designed to accept a broader index later. Fallback `/vault/<target>.md` covers non-entity files. Upgrading to vault-wide is a one-line change to the index endpoint.

---

## Completeness Checklist

- [x] Every AC has a stable ID (AC-01 through AC-23)
- [x] Entity doc format defined (frontmatter schema, body structure, filename convention)
- [x] Entity-refresher agent contract defined (triggers, data sources, behavior rules)
- [x] Backlink mechanism defined (reuses SPEC-047 infrastructure)
- [x] Entity CRUD path defined (VaultService, no separate API)
- [x] Entity discovery mechanism defined (frontmatter-based, no separate registry)
- [x] Wikilink resolution algorithm specified with fallback chain
- [x] Cold-start bootstrapping defined (suggest cards, max 10 proposals)
- [x] Stage 1-3 preservation constraints enumerated in a table
- [x] Integration points with SPEC-045, 046, 047, 051 documented
- [x] Edge cases documented with expected behavior
- [x] Out-of-scope explicit and enumerates what is deferred
- [x] Technical decisions cite principles (A1, A2, A4, A8, A10, A12, A14; D4, D5; F1)
- [x] Decisions requiring input called out with options and recommendations
