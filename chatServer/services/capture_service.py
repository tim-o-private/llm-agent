"""CaptureService — orchestrates capture routing into the vault.

Persist -> route (rule-based for Stage 2) -> place -> confirm.
See SPEC-051 §"Technical Approach" §3.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException, status

from . import markdown_sections as md
from .activity_log_service import ActivityLogService
from .today_service import TodayService
from .vault_service import TreeNode, VaultService

logger = logging.getLogger(__name__)

_TODAY_FILE = "today.md"
_NOTES_TIMESTAMP_FMT = "%Y-%m-%dT%H:%M:%SZ"

# Maximum capture text size (10 KB per spec edge cases).
_MAX_CAPTURE_BYTES = 10 * 1024

# Confidence threshold — below this, fall back to today.md Notes.
_CONFIDENCE_THRESHOLD = 0.6

# Stage 2 rule-based routing keywords.
_TODO_PREFIXES = ("todo:", "todo ", "to-do:", "to-do ", "task:", "task ")

# Actor name for activity_log entries.
_ACTOR = "capture-router"


class CaptureService:
    """Orchestrates the capture flow: persist -> route -> place -> confirm."""

    def __init__(
        self,
        vault: VaultService,
        today: TodayService,
        system_client: Any,
        user_client: Any,
        activity_log: ActivityLogService,
    ):
        self._vault = vault
        self._today = today
        self._system = system_client
        self._user = user_client
        self._activity_log = activity_log

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def create_capture(
        self,
        user_id: str,
        text: str,
        source: str,
        context: dict | None = None,
    ) -> dict:
        """Persist capture row, route synchronously, return result.

        Stage 2: routing is rule-based and fast (< 100ms), so we do it
        inline rather than truly async. The API still returns 202 to
        match the contract for future LLM-based routing.
        """
        text = text.strip()
        if not text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Capture text required",
            )
        if len(text.encode("utf-8")) > _MAX_CAPTURE_BYTES:
            raise HTTPException(
                status_code=413,
                detail="Capture text too large (max 10 KB)",
            )
        if source not in ("today", "cmdk", "chat"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="source must be 'today', 'cmdk', or 'chat'",
            )

        # 1. Persist the capture row via system client (service role INSERT).
        now = datetime.now(timezone.utc).isoformat()
        row = {
            "user_id": user_id,
            "text": text,
            "source": source,
            "context": context,
            "status": "routing",
            "created_at": now,
        }
        resp = await self._system.table("captures").insert(row).execute()
        rows = getattr(resp, "data", None) or []
        if not rows:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to persist capture",
            )
        capture_id = rows[0]["id"]

        # 2. Route synchronously (Stage 2: rule-based, fast).
        try:
            await self.route_capture(capture_id, user_id)
        except Exception as exc:
            logger.error(
                "Capture routing failed for %s: %s", capture_id, exc, exc_info=True
            )
            # Fallback: place in today.md Notes.
            await self._fallback_to_today(
                capture_id, user_id, text, error_detail=str(exc)
            )

        # 3. Return the full capture state.
        return await self.get_capture(user_id, capture_id)

    async def route_capture(self, capture_id: str, user_id: str) -> None:
        """Determine target via rule-based routing, write to vault, update row."""
        # Read the capture row.
        capture = await self._read_capture(capture_id, user_id)
        text = capture["text"]
        context = capture.get("context") or {}

        # Read vault tree for structure context.
        tree = await self._vault.list_tree(user_id)

        # Determine routing.
        routing = self._rule_based_route(text, tree, context)

        target_path = routing["target_path"]
        target_section = routing["target_section"]
        method = routing["method"]
        reasoning = routing["reasoning"]
        confidence = routing["confidence"]
        fallback = confidence < _CONFIDENCE_THRESHOLD

        if fallback:
            target_path = _TODAY_FILE
            target_section = "Notes"
            method = "append"
            reasoning = f"Low confidence ({confidence:.2f}); falling back to today.md Notes."

        # Write to vault.
        ts = datetime.now(timezone.utc).strftime(_NOTES_TIMESTAMP_FMT)
        if method == "append":
            line = f"- [{ts}] {text}"
            try:
                body = await self._vault.read_file(user_id, target_path)
            except HTTPException as e:
                if e.status_code == 404 and target_path != _TODAY_FILE:
                    # Target file doesn't exist — create it with the capture.
                    new_body = f"# {_path_to_title(target_path)}\n\n## {target_section or 'Notes'}\n\n{line}\n"
                    await self._vault.update_body(user_id, target_path, new_body)
                    method = "create"
                else:
                    raise
            else:
                section_name = target_section or "Notes"
                new_body = md.append_to_section(body, section_name, line)
                await self._vault.update_body(user_id, target_path, new_body)
        elif method == "create":
            section_name = target_section or "Notes"
            line = f"- [{ts}] {text}"
            new_body = f"# {_path_to_title(target_path)}\n\n## {section_name}\n\n{line}\n"
            await self._vault.update_body(user_id, target_path, new_body)

        # Build confirmation string.
        section_suffix = f" under {target_section}" if target_section else ""
        confirmation = f"Added to `{target_path}`{section_suffix}"

        # Update captures row.
        placed_at = datetime.now(timezone.utc).isoformat()
        await self._update_capture(capture_id, user_id, {
            "status": "placed",
            "target_path": target_path,
            "target_section": target_section,
            "method": method,
            "reasoning": reasoning,
            "fallback": fallback,
            "confirmation": confirmation,
            "placed_at": placed_at,
        })

        # Log to activity_log.
        await self._activity_log.append(
            user_id=user_id,
            actor=_ACTOR,
            action=f"Captured: {text[:80]}",
            status="done",
            subject_path=target_path,
            reasoning=reasoning,
        )

    async def redirect_capture(
        self, user_id: str, capture_id: str, target_hint: str
    ) -> dict:
        """Move a placed capture to a new location."""
        capture = await self._read_capture(capture_id, user_id)

        if capture["status"] == "routing":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Capture is still routing; wait for placement before redirecting.",
            )
        if capture["status"] == "failed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot redirect a failed capture.",
            )
        if capture.get("redirect"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Capture has already been redirected (single redirect in Stage 2).",
            )

        text = capture["text"]
        original_path = capture["target_path"]
        original_section = capture.get("target_section")

        # 1. Remove from original location.
        await self._remove_capture_text(user_id, original_path, text)

        # 2. Interpret target_hint and determine new target.
        tree = await self._vault.list_tree(user_id)
        new_target = self._resolve_redirect_hint(target_hint, tree)
        new_path = new_target["target_path"]
        new_section = new_target["target_section"]

        # 3. Write to new target.
        ts = datetime.now(timezone.utc).strftime(_NOTES_TIMESTAMP_FMT)
        line = f"- [{ts}] {text}"
        try:
            body = await self._vault.read_file(user_id, new_path)
            new_body = md.append_to_section(body, new_section or "Notes", line)
            await self._vault.update_body(user_id, new_path, new_body)
        except HTTPException as e:
            if e.status_code == 404:
                section_name = new_section or "Notes"
                new_body = f"# {_path_to_title(new_path)}\n\n## {section_name}\n\n{line}\n"
                await self._vault.update_body(user_id, new_path, new_body)
            else:
                raise

        # 4. Update captures row.
        redirected_at = datetime.now(timezone.utc).isoformat()
        section_suffix = f" under {new_section}" if new_section else ""
        confirmation = f"Moved to `{new_path}`{section_suffix}"

        redirect_info = {
            "from_path": original_path,
            "from_section": original_section,
            "target_hint": target_hint,
            "new_target_path": new_path,
            "new_target_section": new_section,
            "redirected_at": redirected_at,
        }

        await self._update_capture(capture_id, user_id, {
            "target_path": new_path,
            "target_section": new_section,
            "redirect": redirect_info,
            "confirmation": confirmation,
        })

        # 5. Log to activity_log.
        await self._activity_log.append(
            user_id=user_id,
            actor=_ACTOR,
            action=f"Redirected capture to {new_path}",
            status="done",
            subject_path=new_path,
            reasoning=f"User requested redirect: '{target_hint}'",
        )

        return await self.get_capture(user_id, capture_id)

    async def get_capture(self, user_id: str, capture_id: str) -> dict:
        """Return current state of a capture (for polling)."""
        return await self._read_capture(capture_id, user_id)

    # ------------------------------------------------------------------
    # Rule-based routing (Stage 2)
    # ------------------------------------------------------------------

    def _rule_based_route(
        self, text: str, tree: list[TreeNode], context: dict
    ) -> dict:
        """Determine target via keyword matching + vault tree analysis.

        Priority order (per spec §5):
        1. Explicit path in text (e.g., "add to projects/foo.md: ...")
        2. Todo-like prefixes → today.md "To do" section
        3. Folder affinity from context.current_path
        4. Fallback → today.md "Notes"
        """
        text_lower = text.lower().strip()

        # Priority 1: Explicit path reference.
        explicit = self._match_explicit_path(text, tree)
        if explicit:
            return explicit

        # Priority 2: Todo-like prefixes.
        for prefix in _TODO_PREFIXES:
            if text_lower.startswith(prefix):
                return {
                    "target_path": _TODAY_FILE,
                    "target_section": "To do",
                    "method": "append",
                    "reasoning": f"Text starts with '{prefix.strip()}' — routing to To do.",
                    "confidence": 0.9,
                }

        # Priority 3: Folder affinity from context.
        current_path = context.get("current_path", "")
        if current_path:
            folder_target = self._match_folder_affinity(text, current_path, tree)
            if folder_target:
                return folder_target

        # Priority 4: Keyword match against vault file/folder names.
        keyword_match = self._match_keywords_to_tree(text, tree)
        if keyword_match:
            return keyword_match

        # Fallback: today.md Notes.
        return {
            "target_path": _TODAY_FILE,
            "target_section": "Notes",
            "method": "append",
            "reasoning": "No specific target identified; falling back to today.md Notes.",
            "confidence": 0.5,
        }

    def _match_explicit_path(
        self, text: str, tree: list[TreeNode]
    ) -> Optional[dict]:
        """Check if text contains 'add to <path>:' pattern."""
        m = re.match(
            r"^(?:add to|put in|save to|append to)\s+([^\s:]+\.md)\s*:\s*(.+)$",
            text,
            re.IGNORECASE,
        )
        if not m:
            return None
        path = m.group(1)
        # Verify the path exists in the tree (or is plausible).
        if self._path_exists_in_tree(path, tree):
            return {
                "target_path": path,
                "target_section": "Notes",
                "method": "append",
                "reasoning": f"Explicit path reference: {path}",
                "confidence": 0.95,
            }
        # Path doesn't exist — could be a new file.
        return {
            "target_path": path,
            "target_section": "Notes",
            "method": "create",
            "reasoning": f"Explicit path reference (new file): {path}",
            "confidence": 0.85,
        }

    def _match_folder_affinity(
        self, text: str, current_path: str, tree: list[TreeNode]
    ) -> Optional[dict]:
        """If user was viewing a vault folder/file, bias routing there."""
        # Normalize: strip trailing slash, find the folder.
        folder = current_path.rstrip("/")
        if folder and not folder.endswith("/"):
            # If it's a file path, get the parent folder.
            if "." in folder.split("/")[-1]:
                parts = folder.rsplit("/", 1)
                folder = parts[0] if len(parts) > 1 else ""

        if not folder:
            return None

        # Look for a notes file in the folder.
        notes_path = f"{folder}/notes.md"
        if self._path_exists_in_tree(notes_path, tree):
            return {
                "target_path": notes_path,
                "target_section": "Notes",
                "method": "append",
                "reasoning": f"Folder affinity: user was viewing {current_path}",
                "confidence": 0.7,
            }

        # Look for any .md file in the folder that might accept notes.
        folder_files = self._get_files_in_folder(folder, tree)
        if folder_files:
            # Pick the first .md file (alphabetical, as tree is sorted).
            target = folder_files[0]
            return {
                "target_path": target,
                "target_section": "Notes",
                "method": "append",
                "reasoning": f"Folder affinity: routed to first file in {folder}/",
                "confidence": 0.65,
            }

        return None

    def _match_keywords_to_tree(
        self, text: str, tree: list[TreeNode]
    ) -> Optional[dict]:
        """Match words in the capture text against vault file/folder names."""
        text_words = set(re.findall(r"[a-z]+", text.lower()))
        if not text_words:
            return None

        best_match: Optional[dict] = None
        best_score = 0

        all_files = self._flatten_tree(tree)
        for node in all_files:
            if node.type != "file" or not node.name.endswith(".md"):
                continue
            if node.path == _TODAY_FILE:
                continue
            # Score: count of text words that appear in the file name or path.
            name_words = set(re.findall(r"[a-z]+", node.name.lower()))
            path_words = set(re.findall(r"[a-z]+", node.path.lower()))
            all_words = name_words | path_words
            score = len(text_words & all_words)
            if score > best_score and score >= 2:
                best_score = score
                best_match = {
                    "target_path": node.path,
                    "target_section": "Notes",
                    "method": "append",
                    "reasoning": f"Keyword match: {score} words match {node.path}",
                    "confidence": min(0.6 + score * 0.1, 0.85),
                }

        return best_match

    # ------------------------------------------------------------------
    # Tree helpers
    # ------------------------------------------------------------------

    def _path_exists_in_tree(self, path: str, tree: list[TreeNode]) -> bool:
        for node in self._flatten_tree(tree):
            if node.path == path:
                return True
        return False

    def _get_files_in_folder(
        self, folder: str, tree: list[TreeNode]
    ) -> list[str]:
        results = []
        for node in self._flatten_tree(tree):
            if node.type == "file" and node.name.endswith(".md"):
                parent = node.path.rsplit("/", 1)[0] if "/" in node.path else ""
                if parent == folder:
                    results.append(node.path)
        return sorted(results)

    def _flatten_tree(self, tree: list[TreeNode]) -> list[TreeNode]:
        result: list[TreeNode] = []
        for node in tree:
            result.append(node)
            if node.children:
                result.extend(self._flatten_tree(node.children))
        return result

    # ------------------------------------------------------------------
    # Redirect hint resolution
    # ------------------------------------------------------------------

    def _resolve_redirect_hint(
        self, hint: str, tree: list[TreeNode]
    ) -> dict:
        """Interpret a redirect target_hint (vault path or free text)."""
        hint = hint.strip()

        # Direct vault path.
        if hint.endswith(".md"):
            return {
                "target_path": hint,
                "target_section": "Notes",
            }

        # "today" shorthand.
        if hint.lower() in ("today", "today.md", "today notes"):
            return {
                "target_path": _TODAY_FILE,
                "target_section": "Notes",
            }

        # "todo" / "to do" shorthand.
        if hint.lower() in ("todo", "to do", "to-do", "todos"):
            return {
                "target_path": _TODAY_FILE,
                "target_section": "To do",
            }

        # Try to match against tree paths/names.
        all_files = self._flatten_tree(tree)
        hint_lower = hint.lower()
        for node in all_files:
            if node.type == "file" and hint_lower in node.path.lower():
                return {
                    "target_path": node.path,
                    "target_section": "Notes",
                }
            if node.type == "folder" and hint_lower in node.path.lower():
                # Look for a notes.md or first .md in the folder.
                folder_files = self._get_files_in_folder(node.path, tree)
                if folder_files:
                    return {
                        "target_path": folder_files[0],
                        "target_section": "Notes",
                    }

        # Fallback: create a new file from the hint.
        safe_name = re.sub(r"[^a-z0-9-]", "-", hint.lower())
        safe_name = re.sub(r"-+", "-", safe_name).strip("-")
        if not safe_name:
            safe_name = "capture"
        return {
            "target_path": f"{safe_name}.md",
            "target_section": "Notes",
        }

    # ------------------------------------------------------------------
    # Internal DB helpers
    # ------------------------------------------------------------------

    async def _read_capture(self, capture_id: str, user_id: str) -> dict:
        """Read a capture row via user-scoped client."""
        resp = await (
            self._user.table("captures")
            .select("*")
            .eq("id", capture_id)
            .eq("user_id", user_id)
            .execute()
        )
        rows = getattr(resp, "data", None) or []
        if not rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Capture not found",
            )
        return rows[0]

    async def _update_capture(
        self, capture_id: str, user_id: str, data: dict
    ) -> None:
        """Update a capture row via system client (bypasses RLS for UPDATE)."""
        await (
            self._system.table("captures")
            .update(data)
            .eq("id", capture_id)
            .eq("user_id", user_id)
            .execute()
        )

    async def _fallback_to_today(
        self,
        capture_id: str,
        user_id: str,
        text: str,
        error_detail: str,
    ) -> None:
        """Place the capture in today.md Notes as a fallback."""
        try:
            await self._today.append_note(user_id, text)
        except Exception as inner:
            logger.error("Fallback append_note also failed: %s", inner, exc_info=True)

        placed_at = datetime.now(timezone.utc).isoformat()
        await self._update_capture(capture_id, user_id, {
            "status": "placed",
            "target_path": _TODAY_FILE,
            "target_section": "Notes",
            "method": "append",
            "fallback": True,
            "error_detail": error_detail[:500],
            "confirmation": "Added to `today.md` under Notes (fallback)",
            "placed_at": placed_at,
        })

        await self._activity_log.append(
            user_id=user_id,
            actor=_ACTOR,
            action=f"Captured (fallback): {text[:80]}",
            status="done",
            subject_path=_TODAY_FILE,
            reasoning=f"Routing failed: {error_detail[:200]}",
        )

    async def _remove_capture_text(
        self, user_id: str, file_path: str, text: str
    ) -> None:
        """Remove the captured text line from a vault file (best effort)."""
        try:
            body = await self._vault.read_file(user_id, file_path)
        except HTTPException:
            logger.warning("Cannot remove capture from %s: file not found", file_path)
            return

        # Find and remove the line containing the capture text.
        lines = body.split("\n")
        new_lines = []
        removed = False
        for line in lines:
            if not removed and text in line:
                removed = True
                continue
            new_lines.append(line)

        if removed:
            new_body = "\n".join(new_lines)
            await self._vault.update_body(user_id, file_path, new_body)


def _path_to_title(path: str) -> str:
    """Convert a vault path to a human title for new files."""
    name = path.rsplit("/", 1)[-1]
    if name.endswith(".md"):
        name = name[:-3]
    return name.replace("-", " ").replace("_", " ").title()
