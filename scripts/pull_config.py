#!/usr/bin/env python3
"""CLI script to pull config from Supabase Storage to local disk.

Usage:
    python scripts/pull_config.py                    # pull system config
    python scripts/pull_config.py --user USER_ID     # hydrate user config
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Allow running from repo root without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional for environments where env vars are set directly

from chatServer.services.storage_sync import StorageSync  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Pull config from Supabase Storage")
    parser.add_argument("--user", type=str, help="User ID to hydrate (omit for system config)")
    parser.add_argument(
        "--data-dir",
        type=str,
        default="/data",
        help="Base data directory (default: /data)",
    )
    args = parser.parse_args()

    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not supabase_key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set", file=sys.stderr)
        sys.exit(1)

    sync = StorageSync(supabase_url, supabase_key, data_dir=Path(args.data_dir))

    if args.user:
        user_dir = asyncio.run(sync.hydrate_user(args.user))
        print(f"Hydrated user config to {user_dir}")
    else:
        asyncio.run(sync.pull_system())
        print(f"Pulled system config to {Path(args.data_dir) / 'config' / 'system'}")


if __name__ == "__main__":
    main()
