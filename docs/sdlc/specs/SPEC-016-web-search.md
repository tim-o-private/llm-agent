# SPEC-016: Web Search Tool

> **Status:** Draft
> **Author:** spec-writer agent
> **Created:** 2026-02-22
> **Updated:** 2026-02-22

## Goal

Add a web search tool to the assistant agent so it can answer questions about current events, look up documentation, and retrieve up-to-date information from the web. Uses DuckDuckGo (no API key required) via the `duckduckgo-search` Python library. This fills a confirmed gap identified during UAT — the agent currently has no way to access web information.

## Acceptance Criteria

- [ ] **AC-01:** Agent has a `search_web` tool that accepts a query string and returns up to 10 results, each with title, URL, and snippet. [A6, A10]
- [ ] **AC-02:** The tool is registered in the `tools` table with type `SearchWebTool` and linked to the `assistant` agent via `agent_tools`. [A6]
- [ ] **AC-03:** Tool approval tier is `AUTO_APPROVE` (read-only, no user data risk). [A6]
- [ ] **AC-04:** The tool returns a human-readable formatted string, not raw JSON. [A6]
- [ ] **AC-05:** When no results are found, the tool returns a clear message indicating no results. [A6]
- [ ] **AC-06:** Network errors and timeouts are caught and return a user-friendly error message (no stack traces). [A6]
- [ ] **AC-07:** Queries longer than 500 characters are rejected with a descriptive error. [A6]
- [ ] **AC-08:** The tool works on all channels (web, Telegram) — no channel-specific logic. [A7]
- [ ] **AC-09:** Agent prompt includes guidance to use `search_web` for current events, documentation, and up-to-date information. [A6]
- [ ] **AC-10:** `duckduckgo-search` is listed in both `requirements.txt` (root) and `chatServer/requirements.txt`. [Cross-domain gotcha #1]
- [ ] **AC-11:** Unit tests cover happy path, no results, network error, and query-too-long cases. [A6]

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `chatServer/services/web_search_service.py` | Service wrapping DuckDuckGo search with error handling |
| `chatServer/tools/web_search_tool.py` | `SearchWebTool` BaseTool subclass |
| `tests/chatServer/services/test_web_search_service.py` | Unit tests for WebSearchService |
| `tests/chatServer/tools/test_web_search_tool.py` | Unit tests for SearchWebTool |
| `supabase/migrations/20260222000001_register_web_search_tool.sql` | DB registration migration |

### Files to Modify

| File | Change |
|------|--------|
| `src/core/agent_loader_db.py` | Add `SearchWebTool` to `TOOL_REGISTRY` |
| `chatServer/security/approval_tiers.py` | Add `search_web` entry |
| `requirements.txt` | Add `duckduckgo-search` |
| `chatServer/requirements.txt` | Add `duckduckgo-search` |

### Out of Scope

- Web page content fetching/scraping (separate tool if needed)
- Caching search results
- Rate limiting (DuckDuckGo has no API key; rate limits are handled by the library)
- Search result ranking or re-ranking
- Image/video search (text results only)
- Frontend UI changes (tool output renders as normal agent text)

## Technical Approach

### 1. WebSearchService (`chatServer/services/web_search_service.py`)

Thin service wrapping the `duckduckgo-search` library. See `backend-patterns` skill for service layer conventions.

```python
import logging
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

class WebSearchService:
    """Service for performing web searches via DuckDuckGo."""

    def __init__(self, max_results: int = 10):
        self.max_results = max_results

    async def search(self, query: str, max_results: int | None = None) -> list[dict]:
        """
        Search DuckDuckGo and return results.

        Args:
            query: Search query string (max 500 chars).
            max_results: Override default max results (1-10).

        Returns:
            List of dicts with keys: title, href, body.

        Raises:
            ValueError: If query is empty or exceeds 500 chars.
        """
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty.")
        if len(query) > 500:
            raise ValueError("Search query must be 500 characters or fewer.")

        limit = min(max_results or self.max_results, 10)

        try:
            ddgs = DDGS()
            results = ddgs.text(query, max_results=limit)
            return results
        except Exception as e:
            logger.error(f"DuckDuckGo search failed for query '{query[:50]}...': {e}")
            raise
```

Note: `duckduckgo-search` uses `httpx` internally and its `text()` method is synchronous. We call it from `_arun` without wrapping in `asyncio.to_thread` since the HTTP call is brief (<2s typical). If latency becomes an issue, a future optimization can wrap it.

### 2. SearchWebTool (`chatServer/tools/web_search_tool.py`)

Follows the `reminder_tools.py` BaseTool pattern exactly. See `backend-patterns` skill.

```python
import logging
from typing import Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SearchWebInput(BaseModel):
    """Input schema for search_web tool."""
    query: str = Field(..., description="The search query to look up on the web", min_length=1, max_length=500)
    max_results: int = Field(5, ge=1, le=10, description="Number of results to return (1-10)")


class SearchWebTool(BaseTool):
    """Search the web using DuckDuckGo."""

    name: str = "search_web"
    description: str = (
        "Search the web for current information using DuckDuckGo. "
        "Returns titles, URLs, and snippets. Use this when the user asks about "
        "current events, documentation, recent news, or anything requiring "
        "up-to-date web information."
    )
    args_schema: Type[BaseModel] = SearchWebInput

    user_id: str
    agent_name: Optional[str] = None

    @classmethod
    def prompt_section(cls, channel: str) -> str | None:
        """Return behavioral guidance for the agent prompt."""
        return (
            "Web Search: Use search_web when the user asks about current events, "
            "documentation, recent news, product information, or anything that "
            "requires up-to-date information from the web. Do not guess at facts "
            "you are unsure about — search first."
        )

    def _run(self, query: str, max_results: int = 5) -> str:
        return "search_web requires async execution. Use _arun."

    async def _arun(self, query: str, max_results: int = 5) -> str:
        try:
            from ..services.web_search_service import WebSearchService

            service = WebSearchService()
            results = await service.search(query=query, max_results=max_results)

            if not results:
                return f'No results found for "{query}". Try rephrasing your search.'

            lines = [f"Found {len(results)} result(s) for \"{query}\":\n"]
            for i, r in enumerate(results, 1):
                title = r.get("title", "No title")
                url = r.get("href", "")
                snippet = r.get("body", "")
                lines.append(f"{i}. **{title}**")
                if url:
                    lines.append(f"   {url}")
                if snippet:
                    lines.append(f"   {snippet}")
                lines.append("")

            return "\n".join(lines)

        except ValueError as e:
            return f"Invalid search query: {e}"
        except Exception as e:
            logger.error(f"search_web failed for user {self.user_id}: {e}")
            return "Web search is temporarily unavailable. Please try again later."
```

### 3. DB Registration (Migration)

```sql
-- Add SearchWebTool to agent_tool_type enum
ALTER TYPE agent_tool_type ADD VALUE IF NOT EXISTS 'SearchWebTool';

-- Register search_web tool on assistant agent
INSERT INTO agent_tools (agent_id, tool_name, type, tool_config, is_active, "order")
SELECT
    ac.id,
    'search_web',
    'SearchWebTool'::agent_tool_type,
    '{}'::jsonb,
    true,
    (SELECT COALESCE(MAX("order"), 0) + 1 FROM agent_tools WHERE agent_id = ac.id)
FROM agent_configurations ac
WHERE ac.agent_name = 'assistant';
```

### 4. Tool Registry and Approval Tier

**`src/core/agent_loader_db.py`** — add import and registry entry:
```python
from chatServer.tools.web_search_tool import SearchWebTool

TOOL_REGISTRY: Dict[str, Type] = {
    ...
    "SearchWebTool": SearchWebTool,
}
```

**`chatServer/security/approval_tiers.py`** — add entry:
```python
TOOL_APPROVAL_DEFAULTS: dict[str, tuple[ApprovalTier, ApprovalTier]] = {
    ...
    # Web search - read-only, no user data
    "search_web": (ApprovalTier.AUTO_APPROVE, ApprovalTier.AUTO_APPROVE),
}
```

### Dependencies

- `duckduckgo-search` Python package (pip: `duckduckgo-search`)
- No database tables needed beyond the existing `agent_tools` and `tools` tables
- No new environment variables required

## Testing Requirements

### Unit Tests (required)

**`tests/chatServer/services/test_web_search_service.py`:**
- Test successful search returns list of results
- Test empty query raises ValueError
- Test query over 500 chars raises ValueError
- Test max_results capping at 10
- Test network error handling (mock DDGS to raise exception)

**`tests/chatServer/tools/test_web_search_tool.py`:**
- Test `_arun` happy path returns formatted output
- Test `_arun` with no results returns "no results" message
- Test `_arun` with network error returns user-friendly error
- Test input schema validation (min/max length, max_results bounds)
- Test `prompt_section` returns guidance string for all channels

### AC-to-Test Mapping

| AC | Test Type | Test Function |
|----|-----------|--------------|
| AC-01 | Unit | `test_search_returns_results` |
| AC-03 | Unit | `test_approval_tier_auto_approve` |
| AC-04 | Unit | `test_output_formatted_as_text` |
| AC-05 | Unit | `test_no_results_message` |
| AC-06 | Unit | `test_network_error_graceful` |
| AC-07 | Unit | `test_query_too_long_rejected` |
| AC-08 | Unit | `test_prompt_section_all_channels` |
| AC-09 | Unit | `test_prompt_section_content` |
| AC-11 | Unit | All of the above |

### Manual Verification (UAT)

- [ ] Start chatServer (`pnpm dev`)
- [ ] Ask agent: "What's the latest news about Python 3.13?"
- [ ] Verify agent uses `search_web` tool and returns formatted results with titles and URLs
- [ ] Ask agent: "Search for DuckDuckGo API documentation"
- [ ] Verify results are relevant and well-formatted
- [ ] Ask agent a factual question it should search for (e.g., "Who won the Super Bowl this year?")
- [ ] Verify agent proactively uses search rather than guessing

## Edge Cases

- **No results:** DuckDuckGo returns empty list for obscure queries. Tool returns "No results found" message with suggestion to rephrase.
- **Network error/timeout:** `duckduckgo-search` raises an exception if network is unavailable. Tool catches and returns "Web search is temporarily unavailable."
- **Query too long:** Queries over 500 characters are rejected before calling DuckDuckGo with a clear error message.
- **Empty query:** Empty or whitespace-only queries raise ValueError, caught by tool.
- **Special characters in query:** DuckDuckGo handles URL encoding internally; no special handling needed.
- **Rate limiting:** DuckDuckGo may rate-limit heavy usage. The `duckduckgo-search` library handles retries internally. If rate-limited, the exception is caught as a general network error.

## Functional Units (for PR Breakdown)

1. **FU-1: DB Registration** (`feat/SPEC-016-db`)
   - Migration: add `SearchWebTool` enum value, insert `agent_tools` row for assistant agent
   - Modify `approval_tiers.py`: add `search_web` entry
   - Assigned to: database-dev

2. **FU-2: Service + Tool** (`feat/SPEC-016-service`)
   - Create `chatServer/services/web_search_service.py`
   - Create `chatServer/tools/web_search_tool.py`
   - Modify `src/core/agent_loader_db.py`: add to `TOOL_REGISTRY`
   - Add `duckduckgo-search` to both `requirements.txt` files
   - Assigned to: backend-dev

3. **FU-3: Tests + Approval Tier** (`feat/SPEC-016-tests`)
   - Create `tests/chatServer/services/test_web_search_service.py`
   - Create `tests/chatServer/tools/test_web_search_tool.py`
   - Assigned to: backend-dev

### Merge Order

FU-1 → FU-2 → FU-3 (linear; FU-2 depends on enum from FU-1, FU-3 tests code from FU-2)

Note: FU-2 and FU-3 could be a single PR if preferred, since they're both backend-dev and tightly coupled. The split is for review clarity.

## Completeness Checklist

- [x] Every AC has a stable ID (AC-01 through AC-11)
- [x] Every AC maps to at least one functional unit
- [x] Technical decisions reference principles (A6, A7, A10)
- [x] Merge order is explicit and acyclic
- [x] Out-of-scope is explicit
- [x] Edge cases documented with expected behavior
- [x] Testing requirements map to ACs
- [x] Cross-domain gotchas addressed (dual requirements.txt)
