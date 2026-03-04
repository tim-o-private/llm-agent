"""
Shared Playwright helpers for UI acceptance tests.

Provides authenticated browser sessions for testing against the running
dev servers (chatServer + webApp via `pnpm dev`).

Usage in test scripts:
    from tests.uat.playwright.conftest_pw import (
        WEBAPP_URL, get_authenticated_page, screenshot, run_checks,
    )
"""

import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load env from project root
_project_root = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(_project_root / ".env")
load_dotenv(_project_root / "webApp" / ".env")

# --- Config ---
WEBAPP_URL = os.environ.get("WEBAPP_URL", "http://localhost:3000")
API_URL = os.environ.get("API_URL", "http://localhost:3001")
SUPABASE_URL = os.environ["VITE_SUPABASE_URL"]
SUPABASE_ANON_KEY = os.environ["VITE_SUPABASE_ANON_KEY"]
DEV_USERNAME = os.environ["CLARITY_DEV_USERNAME"]
DEV_PASSWORD = os.environ["CLARITY_DEV_PASSWORD"]


def get_supabase_session() -> dict:
    """Authenticate via Supabase email/password and return session."""
    resp = requests.post(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Content-Type": "application/json",
        },
        json={"email": DEV_USERNAME, "password": DEV_PASSWORD},
    )
    resp.raise_for_status()
    return resp.json()


def get_authenticated_page(playwright, headless: bool = True, viewport=None):
    """Launch browser and return a Page with Supabase session injected.

    The page is navigated to WEBAPP_URL with auth ready in localStorage.
    Caller is responsible for closing the browser.

    Returns: (page, browser) tuple
    """
    session = get_supabase_session()
    access_token = session["access_token"]

    browser = playwright.chromium.launch(headless=headless)
    context = browser.new_context(
        viewport=viewport or {"width": 1440, "height": 900}
    )
    page = context.new_page()

    # Inject Supabase session into localStorage before navigating
    storage_key = f"sb-{SUPABASE_URL.split('//')[1].split('.')[0]}-auth-token"
    page.goto(WEBAPP_URL)
    page.evaluate(
        f"""() => {{
        localStorage.setItem('{storage_key}', JSON.stringify({{
            access_token: '{access_token}',
            refresh_token: '{session["refresh_token"]}',
            expires_at: {session.get("expires_at", int(time.time()) + 3600)},
            expires_in: {session.get("expires_in", 3600)},
            token_type: 'bearer',
            user: {json.dumps(session["user"])}
        }}));
    }}"""
    )

    return page, browser


def screenshot(page, name: str, spec_id: str = "unknown"):
    """Take a screenshot and print the path."""
    directory = Path(f"/tmp/uat-{spec_id}")
    directory.mkdir(exist_ok=True)
    path = directory / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"  Screenshot: {path}")


class CheckRunner:
    """Collects pass/fail results and prints a summary."""

    def __init__(self, spec_id: str):
        self.spec_id = spec_id
        self.results: list[tuple[str, bool, str]] = []

    def check(self, name: str, passed: bool, note: str = ""):
        status = "PASS" if passed else "FAIL"
        self.results.append((name, passed, note))
        print(f"  [{status}] {name}" + (f" — {note}" if note else ""))

    def summary(self) -> int:
        """Print summary and return exit code (0 = all pass, 1 = failures)."""
        passed = sum(1 for _, p, _ in self.results if p)
        failed = sum(1 for _, p, _ in self.results if not p)
        print(f"\n{'=' * 60}")
        print(f"Results: {passed} passed, {failed} failed, {len(self.results)} total")
        print(f"Screenshots: /tmp/uat-{self.spec_id}")
        print("=" * 60)

        if failed:
            print("\nFailed checks:")
            for name, p, note in self.results:
                if not p:
                    print(f"  FAIL: {name}" + (f" — {note}" if note else ""))

        return 1 if failed else 0
