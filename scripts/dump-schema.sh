#!/usr/bin/env bash
# dump-schema.sh — Pull current DDL from Supabase and prune for agent consumption
#
# Usage: ./scripts/dump-schema.sh
#
# Output: supabase/schema.sql (the single source of truth for current DDL)
#
# Run this before any database work so agents have an accurate, token-efficient
# view of the schema. The output strips pg_dump noise (SET statements, OWNER,
# GRANT, ALTER DEFAULT PRIVILEGES) and keeps only what matters:
#   - ENUMs, functions, tables, views
#   - Constraints, indexes, triggers
#   - RLS enablement and policies
#   - COMMENTs

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT="$REPO_ROOT/supabase/schema.sql"
RAW_DUMP=$(mktemp)

trap 'rm -f "$RAW_DUMP"' EXIT

echo "Dumping schema from linked Supabase project..."
supabase db dump --linked -s public > "$RAW_DUMP" 2>/dev/null

echo "Pruning for agent consumption..."

{
    echo "-- ============================================"
    echo "-- llm-agent: Current Production Schema"
    echo "-- Generated: $(date -u '+%Y-%m-%d %H:%M UTC')"
    echo "-- Source: supabase db dump --linked -s public"
    echo "-- "
    echo "-- This file is AUTO-GENERATED. Do not edit manually."
    echo "-- Re-generate: ./scripts/dump-schema.sh"
    echo "-- ============================================"
    echo ""
} > "$OUTPUT"

# Filter out noise, keep meaningful DDL
sed -E \
    -e '/^SET /d' \
    -e '/^SELECT pg_catalog/d' \
    -e '/^ALTER .* OWNER TO/d' \
    -e '/^GRANT /d' \
    -e '/^REVOKE /d' \
    -e '/^ALTER DEFAULT PRIVILEGES/d' \
    -e '/^CREATE SCHEMA IF NOT EXISTS "public"/d' \
    -e '/^ALTER SCHEMA/d' \
    -e "/^COMMENT ON SCHEMA .public./d" \
    "$RAW_DUMP" >> "$OUTPUT"

# Collapse runs of 3+ blank lines into 2
awk 'NF{blank=0} !NF{blank++} blank<=2' "$OUTPUT" > "${OUTPUT}.tmp" && mv "${OUTPUT}.tmp" "$OUTPUT"

LINES=$(wc -l < "$OUTPUT")
TABLES=$(grep -c '^CREATE TABLE' "$OUTPUT" || true)
FUNCTIONS=$(grep -c '^CREATE OR REPLACE FUNCTION' "$OUTPUT" || true)
INDEXES=$(grep -c '^CREATE INDEX' "$OUTPUT" || true)
POLICIES=$(grep -c '^CREATE POLICY' "$OUTPUT" || true)

echo ""
echo "Written to: $OUTPUT"
echo "  Lines:     $LINES (raw dump was $(wc -l < "$RAW_DUMP"))"
echo "  Tables:    $TABLES"
echo "  Functions: $FUNCTIONS"
echo "  Indexes:   $INDEXES"
echo "  Policies:  $POLICIES"
