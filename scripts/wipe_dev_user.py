#!/usr/bin/env python3
"""Wipe all data for a dev/test user from Supabase and min-memory.

Deletes chat history, sessions, tasks, memories, and all other user-scoped
data. Backs up chat_message_history and memories before deletion.

Usage:
    python scripts/wipe_dev_user.py                      # uses CLARITY_DEV_USERNAME/PASSWORD
    python scripts/wipe_dev_user.py <user_id>             # explicit UUID
    python scripts/wipe_dev_user.py --dry-run
    python scripts/wipe_dev_user.py --yes

If no user_id is provided, resolves the test user UUID by signing in with
CLARITY_DEV_USERNAME and CLARITY_DEV_PASSWORD from .env.

Requires in .env:
    SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY  (Supabase wipe)
    MEMORY_SERVER_URL, MEMORY_SERVER_BACKEND_KEY  (memory wipe)
    CLARITY_DEV_USERNAME, CLARITY_DEV_PASSWORD, SUPABASE_ANON_KEY  (auto-resolve user)
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime

import httpx
from dotenv import load_dotenv

from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
MEMORY_URL = os.getenv("MEMORY_SERVER_URL", "").rstrip("/")
MEMORY_KEY = os.getenv("MEMORY_SERVER_BACKEND_KEY", "")


def resolve_dev_user_id() -> str:
    """Sign in with CLARITY_DEV_USERNAME/PASSWORD and return the user UUID."""
    url = SUPABASE_URL.rstrip("/")
    anon_key = os.getenv("SUPABASE_ANON_KEY", "")
    email = os.getenv("CLARITY_DEV_USERNAME", "")
    password = os.getenv("CLARITY_DEV_PASSWORD", "")

    if not all([url, anon_key, email, password]):
        print("Error: To auto-resolve user, set SUPABASE_URL, SUPABASE_ANON_KEY,")
        print("       CLARITY_DEV_USERNAME, and CLARITY_DEV_PASSWORD in .env")
        print("       Or pass a user UUID explicitly.")
        sys.exit(1)

    resp = httpx.post(
        f"{url}/auth/v1/token?grant_type=password",
        json={"email": email, "password": password},
        headers={"apikey": anon_key, "Content-Type": "application/json"},
        timeout=10.0,
    )
    if resp.status_code != 200:
        print(f"Error: Supabase sign-in failed ({resp.status_code}): {resp.text[:500]}")
        sys.exit(1)

    user_id = resp.json()["user"]["id"]
    print(f"Resolved dev user: {email} → {user_id}")
    return user_id

# Tables with user_id column, ordered to respect FK constraints.
# chat_message_history is handled separately (no user_id, joins via chat_sessions).
TABLES_IN_ORDER = [
    "focus_sessions",          # FK → tasks (RESTRICT)
    "tasks",                   # self-ref FK (parent_task_id), single DELETE is fine
    "agent_execution_results",
    "agent_schedules",
    "pending_actions",
    "notifications",
    "reminders",
    "notes",
    "agent_logs",
    "agent_long_term_memory",
    "agent_sessions",
    "audit_logs",
    "email_digests",
    "external_api_connections",
    "user_channels",
    "channel_linking_tokens",
    "user_tool_preferences",
    "user_agent_prompt_customizations",
    "chat_sessions",           # after chat_message_history is cleared
]


def get_supabase():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")
        sys.exit(1)
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def count_rows(sb, table: str, user_id: str) -> int:
    resp = sb.table(table).select("*", count="exact", head=True).eq("user_id", user_id).execute()
    return resp.count or 0


def count_chat_messages(sb, user_id: str) -> int:
    """Count chat_message_history rows via session_id subquery."""
    sessions = sb.table("chat_sessions").select("session_id").eq("user_id", user_id).execute()
    session_ids = [s["session_id"] for s in (sessions.data or [])]
    if not session_ids:
        return 0
    resp = (
        sb.table("chat_message_history")
        .select("*", count="exact", head=True)
        .in_("session_id", session_ids)
        .execute()
    )
    return resp.count or 0


def backup_chat_history(sb, user_id: str, backup_dir: str, timestamp: str, safe_uid: str):
    """Backup chat_message_history rows for this user."""
    sessions = sb.table("chat_sessions").select("session_id").eq("user_id", user_id).execute()
    session_ids = [s["session_id"] for s in (sessions.data or [])]
    if not session_ids:
        return []

    messages = []
    # Fetch in batches of 50 session_ids to avoid URL length limits
    for i in range(0, len(session_ids), 50):
        batch = session_ids[i : i + 50]
        resp = sb.table("chat_message_history").select("*").in_("session_id", batch).execute()
        messages.extend(resp.data or [])

    if messages:
        path = os.path.join(backup_dir, f"chat_backup_{safe_uid}_{timestamp}.json")
        with open(path, "w") as f:
            data = {"user_id": user_id, "timestamp": timestamp, "message_count": len(messages), "messages": messages}
            json.dump(data, f, indent=2, default=str)
        print(f"  Chat history backed up to: {path}")

    return session_ids


def delete_chat_messages(sb, session_ids: list[str]) -> int:
    """Delete chat_message_history rows for given session_ids."""
    deleted = 0
    for i in range(0, len(session_ids), 50):
        batch = session_ids[i : i + 50]
        resp = sb.table("chat_message_history").delete().in_("session_id", batch).execute()
        deleted += len(resp.data or [])
    return deleted


def delete_table_rows(sb, table: str, user_id: str) -> int:
    resp = sb.table(table).delete().eq("user_id", user_id).execute()
    return len(resp.data or [])


async def call_memory_tool(user_id: str, tool_name: str, arguments: dict) -> dict | list:
    payload = {"tool_name": tool_name, "arguments": arguments}
    headers = {
        "Content-Type": "application/json",
        "X-Backend-Key": MEMORY_KEY,
        "X-User-Id": user_id,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{MEMORY_URL}/api/tools/call", json=payload, headers=headers)
        if resp.status_code >= 400:
            print(f"  HTTP {resp.status_code}: {resp.text[:500]}")
            resp.raise_for_status()
    return resp.json()


async def wipe_memories(user_id: str, backup_dir: str, timestamp: str, safe_uid: str, dry_run: bool) -> int:
    """Wipe all memories from min-memory server. Returns count deleted."""
    if not MEMORY_URL or not MEMORY_KEY:
        print("  Skipping memory wipe: MEMORY_SERVER_URL / MEMORY_SERVER_BACKEND_KEY not set")
        return 0

    result = await call_memory_tool(user_id, "retrieve_context", {"query": "everything", "limit": 1000})
    memories = result if isinstance(result, list) else result.get("memories", result.get("results", []))

    if not memories:
        entities = await call_memory_tool(user_id, "list_entities", {})
        count = entities.get("count", 0)
        if count == 0:
            return 0
        print(f"  Found {count} entities but retrieve_context returned no results.")
        return 0

    # Backup
    path = os.path.join(backup_dir, f"memory_backup_{safe_uid}_{timestamp}.json")
    with open(path, "w") as f:
        json.dump({"user_id": user_id, "timestamp": timestamp, "memories": memories}, f, indent=2)
    print(f"  Memories backed up to: {path}")

    if dry_run:
        return len(memories)

    deleted = 0
    for mem in memories:
        mem_id = mem.get("id") or mem.get("memory_id")
        if not mem_id:
            continue
        try:
            result = await call_memory_tool(user_id, "delete_memory", {"memory_id": mem_id})
            status = result.get("status", "unknown")
            if status in ("deleted", "already_deleted"):
                deleted += 1
            else:
                print(f"  Unexpected status for {mem_id}: {status}")
        except Exception as e:
            print(f"  Error deleting memory {mem_id}: {e}")
    return deleted


def main():
    parser = argparse.ArgumentParser(description="Wipe all data for a dev/test user")
    parser.add_argument(
        "user_id", nargs="?", default=None,
        help="Supabase user UUID (auto-resolved from .env if omitted)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without deleting")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()

    user_id = args.user_id or resolve_dev_user_id()

    sb = get_supabase()

    # --- Scan phase ---
    print(f"Scanning data for user: {user_id}")
    summary: dict[str, int] = {}

    msg_count = count_chat_messages(sb, user_id)
    summary["chat_message_history"] = msg_count

    for table in TABLES_IN_ORDER:
        summary[table] = count_rows(sb, table, user_id)

    total = sum(summary.values())
    print()
    print(f"{'Table':<40} {'Rows':>6}")
    print("-" * 48)
    for table, count in summary.items():
        if count > 0:
            print(f"  {table:<38} {count:>6}")
    print("-" * 48)
    print(f"  {'Total (Supabase)':<38} {total:>6}")
    print(f"  {'Memories (min-memory)':<38} {'(scan at wipe time)':>6}")
    print()

    if total == 0:
        print("No Supabase data found for this user.")

    if args.dry_run:
        print("[DRY RUN] No data was deleted.")
        return

    # --- Confirmation ---
    if not args.yes:
        answer = input(f"Delete all data for {user_id}? [y/N] ")
        if answer.lower() not in ("y", "yes"):
            print("Aborted.")
            return

    # --- Backup phase ---
    backup_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_uid = user_id.replace("|", "_").replace("/", "_")

    print("Backing up and deleting...")

    # --- Delete Supabase data ---
    results: dict[str, int] = {}

    # 1. chat_message_history (via session_id join)
    session_ids = backup_chat_history(sb, user_id, backup_dir, timestamp, safe_uid)
    if session_ids:
        results["chat_message_history"] = delete_chat_messages(sb, session_ids)
    else:
        results["chat_message_history"] = 0

    # 2. All user_id tables in FK-safe order
    for table in TABLES_IN_ORDER:
        results[table] = delete_table_rows(sb, table, user_id)

    # 3. Memories
    mem_deleted = asyncio.run(wipe_memories(user_id, backup_dir, timestamp, safe_uid, dry_run=False))
    results["memories (min-memory)"] = mem_deleted

    # --- Summary ---
    print()
    print(f"{'Table':<40} {'Deleted':>8}")
    print("-" * 50)
    for table, count in results.items():
        if count > 0:
            print(f"  {table:<38} {count:>8}")
    total_deleted = sum(results.values())
    print("-" * 50)
    print(f"  {'Total':<38} {total_deleted:>8}")
    print()
    print("Done.")


if __name__ == "__main__":
    main()
