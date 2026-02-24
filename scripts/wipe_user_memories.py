#!/usr/bin/env python3
"""Wipe all memories for an llm-agent user from min-memory server.

Backs up all memories to a JSON file before deleting. Refuses to operate
on google-oauth2 users (those are real users with production data).

Usage:
    python scripts/wipe_user_memories.py <user_id>

Examples:
    python scripts/wipe_user_memories.py e3fcd1d6-327d-407e-8359-b5c93ddbc670
    python scripts/wipe_user_memories.py test-user-123

Requires MEMORY_SERVER_URL and MEMORY_SERVER_BACKEND_KEY in .env
"""

import asyncio
import json
import os
import sys
from datetime import datetime

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("MEMORY_SERVER_URL", "").rstrip("/")
BACKEND_KEY = os.getenv("MEMORY_SERVER_BACKEND_KEY", "")

PROTECTED_PREFIXES = ("google-oauth2|", "auth0|", "github|")


async def call_tool(user_id: str, tool_name: str, arguments: dict) -> dict | list:
    payload = {"tool_name": tool_name, "arguments": arguments}
    headers = {
        "Content-Type": "application/json",
        "X-Backend-Key": BACKEND_KEY,
        "X-User-Id": user_id,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{BASE_URL}/api/tools/call", json=payload, headers=headers)
        if resp.status_code >= 400:
            print(f"  HTTP {resp.status_code}: {resp.text[:500]}")
            resp.raise_for_status()
    return resp.json()


async def wipe(user_id: str) -> None:
    if not BASE_URL or not BACKEND_KEY:
        print("Error: MEMORY_SERVER_URL and MEMORY_SERVER_BACKEND_KEY must be set in .env")
        sys.exit(1)

    # Guard: refuse to wipe real OAuth users
    for prefix in PROTECTED_PREFIXES:
        if user_id.startswith(prefix):
            print(f"REFUSED: Will not wipe memories for '{user_id}'.")
            print(f"This looks like a real OAuth user ({prefix}...). Only llm-agent test users allowed.")
            sys.exit(1)

    print(f"Fetching all memories for user: {user_id}")

    # retrieve_context with a broad query to get all memories
    result = await call_tool(user_id, "retrieve_context", {"query": "everything", "limit": 1000})
    memories = result if isinstance(result, list) else result.get("memories", result.get("results", []))

    if not memories:
        # Also check entities
        entities = await call_tool(user_id, "list_entities", {})
        count = entities.get("count", 0)
        if count == 0:
            print("No memories found. Already clean.")
            return
        print(f"Found {count} entities but retrieve_context returned no results.")
        print("Entities:", json.dumps(entities, indent=2))
        return

    print(f"Found {len(memories)} memories.")

    # Backup
    backup_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_uid = user_id.replace("|", "_").replace("/", "_")
    backup_path = os.path.join(backup_dir, f"memory_backup_{safe_uid}_{timestamp}.json")

    with open(backup_path, "w") as f:
        json.dump({"user_id": user_id, "timestamp": timestamp, "memories": memories}, f, indent=2)
    print(f"Backup saved to: {backup_path}")

    # Delete each memory
    deleted = 0
    errors = 0
    for mem in memories:
        mem_id = mem.get("id") or mem.get("memory_id")
        if not mem_id:
            continue
        try:
            result = await call_tool(user_id, "delete_memory", {"memory_id": mem_id})
            status = result.get("status", "unknown")
            if status in ("deleted", "already_deleted"):
                deleted += 1
            else:
                print(f"  Unexpected status for {mem_id}: {status}")
                errors += 1
        except Exception as e:
            print(f"  Error deleting {mem_id}: {e}")
            errors += 1

    print(f"Done. Deleted: {deleted}, Errors: {errors}, Total: {len(memories)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    asyncio.run(wipe(sys.argv[1]))
