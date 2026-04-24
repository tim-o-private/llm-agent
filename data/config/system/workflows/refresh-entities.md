---
name: refresh-entities
description: Scan recent signals and update/propose entity docs
version: 1
default_gate_policy: none
---

# Refresh Entities

Scheduled or on-demand workflow that keeps entity docs current. The scan step
reads recent emails, calendar events, and vault activity to extract entity
mentions. The update step writes to existing entity docs. The propose step
creates suggest cards for new entities the user hasn't created yet.

Triggers: (a) daily cron per user_preferences.entity_refresh_time,
(b) on-demand via POST /workflows/run with template_name=refresh-entities,
(c) downstream of regenerate-today.

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
