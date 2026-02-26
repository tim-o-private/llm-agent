"""
UAT: SPEC-025 Approval Flow — End-to-End via Playwright

Tests the inline approval flow by asking the agent to perform an action
that requires approval, then verifying the UI renders correctly.

Run with: python tests/uat/playwright_spec025_approval.py
Requires: pnpm dev running (chatServer :3001, webApp on any port)
"""

import json
import os
import sys
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load env from project root
project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(project_root / ".env")
load_dotenv(project_root / "webApp" / ".env")

from playwright.sync_api import sync_playwright

# --- Config ---
WEBAPP_URL = os.environ.get("WEBAPP_URL", "http://localhost:3000")
API_URL = os.environ.get("API_URL", "http://localhost:3001")
SUPABASE_URL = os.environ["VITE_SUPABASE_URL"]
SUPABASE_ANON_KEY = os.environ["VITE_SUPABASE_ANON_KEY"]
DEV_USERNAME = os.environ["CLARITY_DEV_USERNAME"]
DEV_PASSWORD = os.environ["CLARITY_DEV_PASSWORD"]
SCREENSHOT_DIR = Path("/tmp/uat-spec025")
SCREENSHOT_DIR.mkdir(exist_ok=True)


def get_supabase_session():
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


def screenshot(page, name: str):
    """Take a screenshot and print the path."""
    path = SCREENSHOT_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"  Screenshot: {path}")


def run_uat():
    results = []

    def check(name, passed, note=""):
        status = "PASS" if passed else "FAIL"
        results.append((name, passed, note))
        print(f"  [{status}] {name}" + (f" — {note}" if note else ""))

    print("=" * 60)
    print("SPEC-025 UAT: Inline Approval Flow")
    print("=" * 60)

    # Step 1: Get Supabase session
    print("\n[1] Authenticating via Supabase...")
    session = get_supabase_session()
    access_token = session["access_token"]
    print(f"  Authenticated as: {session['user']['email']}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # Capture console errors
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

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

        # Step 2: Navigate to Today view
        print("\n[2] Loading app...")
        page.goto(f"{WEBAPP_URL}/today")
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        screenshot(page, "01-app-loaded")

        is_authenticated = not page.url.endswith("/login")
        check("AC-00: User authenticated and on Today view", is_authenticated)
        if not is_authenticated:
            print("  FATAL: Not authenticated. Stopping.")
            browser.close()
            sys.exit(1)

        # Step 3: Ensure chat panel is open
        print("\n[3] Ensuring chat panel is open...")
        # Check if chat panel content is visible (AI Coach header or message input)
        chat_visible = page.locator('text="AI Coach"').is_visible() or page.locator('textarea[placeholder*="message" i], input[placeholder*="message" i]').first.is_visible()  # noqa: E501

        if not chat_visible:
            # Chat is closed, click toggle to open
            chat_toggle = page.locator('button:has-text("Chat")').first
            if chat_toggle.is_visible():
                chat_toggle.click()
                time.sleep(2)
                chat_visible = True
        screenshot(page, "02-chat-panel")
        check("Chat panel is open", chat_visible)

        # Step 4: Type a message that triggers an approval-gated tool
        print("\n[4] Sending message to trigger approval flow...")
        # The chat uses assistant-ui ComposerPrimitive — need real keystrokes
        message_input = page.locator('.aui-composer-input').first

        if not message_input.is_visible():
            # Fallback: try generic selector
            message_input = page.locator('textarea[placeholder*="message" i], input[placeholder*="message" i]').first

        if not message_input.is_visible():
            print("  Chat input not visible on Today. Navigating to Coach...")
            page.goto(f"{WEBAPP_URL}/coach")
            page.wait_for_load_state("networkidle")
            time.sleep(3)
            screenshot(page, "02b-coach-page")
            message_input = page.locator('.aui-composer-input').first

        if message_input.is_visible():
            # Use click + type (not fill) to trigger React state updates
            message_input.click()
            message_input.press_sequentially(
                "Please delete the task called 'Set up work tracking system'",
                delay=20,
            )
            time.sleep(0.5)  # Let React state settle
            screenshot(page, "03a-message-typed")

            # Send via Enter key (most reliable for assistant-ui composer)
            message_input.press("Enter")
            print("  Message sent. Waiting for agent response...")
            time.sleep(15)  # Give the agent time to process and create approval
        else:
            print("  WARN: Could not find message input.")

        screenshot(page, "03-after-send")

        # Step 5: Check for approval card in timeline
        print("\n[5] Checking for approval card...")
        # Wait a bit more for polling to pick up the notification
        time.sleep(10)
        screenshot(page, "04-waiting-for-approval")

        # Look for approval cards
        approval_card = page.locator('[role="alert"]:has-text("Approval")')
        approval_count = approval_card.count()

        # Also check for the softer approval message from the agent
        agent_approval_msg = page.locator('text=/approval|approve/i')
        has_approval_reference = agent_approval_msg.count() > 0

        check(
            "AC-13: Approval card renders in chat timeline",
            approval_count > 0,
            f"Found {approval_count} approval card(s)" if approval_count > 0 else "No approval cards found. Agent may not have triggered approval.",  # noqa: E501
        )

        if approval_count == 0 and has_approval_reference:
            print("  NOTE: Agent mentioned approval but no inline card found.")
            print("  This may mean the agent discussed approval conversationally")
            print("  without actually calling the tool.")

        screenshot(page, "05-approval-check")

        # Step 6: If approval card exists, test approve button
        if approval_count > 0:
            print("\n[6] Testing approve button...")
            last_card = approval_card.last
            approve_btn = last_card.locator('button:has-text("Approve")')

            has_approve_btn = approve_btn.is_visible()
            check("AC-13: Approve button visible on pending card", has_approve_btn)

            if has_approve_btn:
                reject_btn = last_card.locator('button:has-text("Reject")')
                check("AC-13: Reject button visible on pending card", reject_btn.is_visible())

                # Check ARIA
                approve_aria = approve_btn.get_attribute("aria-label")
                check("Approve button has aria-label", approve_aria is not None, f'aria-label="{approve_aria}"')

                # Snapshot: count all role="status" + role="alert" BEFORE approve
                status_before = page.locator('[role="status"]').count()
                alert_before = page.locator('[role="alert"]').count()
                print(f"  Before approve: {alert_before} alert(s), {status_before} status(es)")

                # Click approve
                approve_btn.click()
                time.sleep(3)
                screenshot(page, "06-after-approve-immediate")

                # Verify optimistic state transition
                approved_text = last_card.locator('text=/Approved/i')
                check("AC-13: Card shows Approved state after click", approved_text.is_visible())

                # Verify buttons are removed
                approve_btn_after = last_card.locator('button:has-text("Approve")')
                check("Buttons removed after approval", approve_btn_after.count() == 0)

                # Wait for 2-3 poll cycles (5s each) to observe real behavior
                print("  Waiting for poll cycles (15s) to observe persistence...")
                time.sleep(15)
                screenshot(page, "07-after-poll-cycles")

                # Check what changed after polling
                status_after = page.locator('[role="status"]').count()
                alert_after = page.locator('[role="alert"]').count()
                print(f"  After polls:  {alert_after} alert(s), {status_after} status(es)")

                # Did the approval card persist or vanish?
                approval_cards_after = page.locator('[role="alert"]:has-text("Approval")')
                card_persisted = approval_cards_after.count() > 0
                print(f"  Approval card persisted: {card_persisted}")

                if card_persisted:
                    # Card stayed — check if it still shows approved
                    last_card_after = approval_cards_after.last
                    still_approved = last_card_after.locator('text=/Approved/i').is_visible()
                    check("Approval card persists with Approved state", still_approved)
                else:
                    print("  NOTE: Approval card vanished after poll — filter dropped it")
                    check("Approval card persists after poll", False, "Card disappeared from timeline after refetch")

                # Check for ANY new notification that appeared after approval
                new_status_count = status_after - status_before
                new_alert_count = alert_after - alert_before
                print(f"  New elements: +{new_status_count} status, +{new_alert_count} alert")

                # Dump all role="status" text for inspection
                all_status = page.locator('[role="status"]').all()
                for i, el in enumerate(all_status):
                    aria = el.get_attribute("aria-label") or ""
                    text = el.inner_text()[:100].replace("\n", " | ")
                    print(f"  status[{i}]: aria='{aria}' text='{text}'")

                all_alerts = page.locator('[role="alert"]').all()
                for i, el in enumerate(all_alerts):
                    aria = el.get_attribute("aria-label") or ""
                    text = el.inner_text()[:100].replace("\n", " | ")
                    print(f"  alert[{i}]: aria='{aria}' text='{text}'")
        else:
            print("\n[6] SKIPPED: No approval card to test.")
            print("  To manually test: ask the agent to delete a task or send an email.")

        # Step 7: General UI checks
        print("\n[7] General UI checks...")

        # AC-16: Bell dropdown removed
        bell = page.locator('[aria-label*="notification" i]:not([role="status"]):not([role="alert"])').first
        check("AC-16: Bell icon/dropdown removed from nav", not bell.is_visible())

        # AC-17: Pending actions panel removed
        pending_panel = page.locator('text="Pending Actions"')
        check("AC-17: Pending Actions panel removed", not pending_panel.is_visible())

        # Check notification inline messages exist (any notifications in timeline)
        notifications = page.locator('[role="status"][aria-label*="Notification"]')
        notification_count = notifications.count()
        print(f"  Found {notification_count} inline notification(s) in timeline.")

        # Console errors
        if console_errors:
            print(f"\n  Console errors ({len(console_errors)}):")
            for err in console_errors[:5]:
                print(f"    {err[:120]}")

        # Summary
        print("\n" + "=" * 60)
        passed = sum(1 for _, p, _ in results if p)
        failed = sum(1 for _, p, _ in results if not p)
        print(f"Results: {passed} passed, {failed} failed, {len(results)} total")
        print(f"Screenshots: {SCREENSHOT_DIR}")
        print("=" * 60)

        if failed:
            print("\nFailed checks:")
            for name, p, note in results:
                if not p:
                    print(f"  FAIL: {name}" + (f" — {note}" if note else ""))

        browser.close()
        sys.exit(1 if failed else 0)


if __name__ == "__main__":
    run_uat()
