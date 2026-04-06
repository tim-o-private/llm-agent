# Backend Feasibility Review: SPEC-032, SPEC-033, SPEC-034

**Reviewer:** Backend Engineer Agent
**Date:** 2026-04-06
**Scope:** Blast radius verification, feasibility analysis, risk identification

---

## SPEC-032: Config Service — Supabase Storage + Overlay Resolution

### Verdict: CONCERNS (fixable issues)

### Blast Radius Verification

The spec's blast radius analysis is **accurate and thorough**. All readers of `soul`/`identity` from `agent_configurations` and `instructions` from `user_agent_prompt_customizations` are correctly identified:

- `agent_loader_db.py` lines 725-727 (sync), 875-876 (async), 935 (SQL SELECT) — confirmed ✅
- `agent_config_cache_service.py` lines 71, 98 — confirmed ✅
- `user_instructions_cache_service.py` line 64 — confirmed ✅
- `prompt_customization.py` — confirmed ✅
- `update_instructions_tool.py` — confirmed ✅
- `schedule_service.py` reads only `id` — correctly excluded ✅
- `prompt_builder.py` receives params, source-agnostic — correctly excluded ✅

**No missed files.**

### Feasibility Analysis

**Supabase Storage async support: Confirmed working.** The `supabase-py` AsyncClient has a `storage` property that returns an `AsyncStorageClient`. The `from_("config")` pattern returns an `AsyncBucketProxy` with async `download()`, `upload()`, `list()` methods. The spec's code examples will work.

**TTL cache pattern: Confirmed.** `TTLCacheService` and `register_ttl_cache_service` exist in `chatServer/services/ttl_cache_service.py`. The spec correctly references this pattern. Three existing services use it (AgentConfig, UserInstructions, Tool).

### Issues Found

1. **CONCERN: Bucket creation via SQL migration may not work.** Supabase Storage bucket management is typically done via the Supabase Dashboard or Management API, not via raw SQL `INSERT INTO storage.buckets`. While the `storage.buckets` table exists in the schema, directly inserting may bypass Supabase's internal hooks for bucket initialization (directory structure, default policies). **Recommendation:** Verify this works on the Supabase instance first. Alternative: create bucket via `supabase.storage.create_bucket()` in the data migration script instead of SQL.

2. **CONCERN: RLS on `storage.objects` uses `LIKE` with string concatenation.** The policy `name LIKE 'users/' || auth.uid()::text || '/%'` is correct SQL but note that `LIKE` doesn't support escaping user IDs with special characters (not an issue since UUIDs are hex+hyphens, but worth documenting). Also, the `LIKE` pattern `users/{uuid}/%` requires at least one character after the slash — an exact match on `users/{uuid}/` (no filename) would fail. This is probably fine (you always have a filename) but is an edge case.

3. **CONCERN: ConfigService uses service_role for all server-side reads (AC-07).** The spec says "service_role credentials for reads (bypassing RLS for server-side operations)" while "user-facing API endpoints use the user's JWT." This is correct and safe, but the implementation must be careful: `ConfigService` must use the global `SupabaseManager` client (which authenticates with `SUPABASE_SERVICE_ROLE_KEY`), while `config_router.py` endpoints must create a user-scoped storage client. The current `UserScopedClient` wrapper in `scoped_client.py` wraps table operations — it does NOT wrap storage operations. **The spec needs a plan for user-scoped storage access in the router**, or the router should call `ConfigService` (which uses service_role) with the authenticated user_id passed through, relying on the service to enforce path scoping in code rather than via RLS. If so, RLS policies on `storage.objects` serve as defense-in-depth for direct Supabase client access from the frontend (which doesn't exist yet) rather than for the API endpoints.

4. **CONCERN: `_download()` silently catches all exceptions.** The spec's `_download()` method uses a bare `except Exception` to return `None` on 404. This will also swallow network errors, auth failures, and corrupt data. **Recommendation:** Catch the specific `StorageApiError` (from `storage3.utils`) and only treat 404-class errors as "not found". Log all other exceptions at WARNING level.

5. **MINOR: SPEC-032 numbering conflict.** The spec is numbered SPEC-032, but SPEC-033 refers to "SPEC-032 FU-1" in the context of Assistant-UI alignment / frontend streaming — that's a different SPEC-032 (the frontend/streaming spec). This creates confusion. SPEC-033 line 38 says "SPEC-032 FU-1 specs backend SSE streaming" — is that this SPEC-032 (Config Service) or another one?

6. **MINOR: No `write()` method exposed via ConfigService for system paths.** AC-02 seeds system defaults, but `ConfigService.write()` only writes to user paths (`users/{user_id}/...`). The migration script will need direct storage client access to write to `system/` paths. This is fine (migration script uses service_role directly) but should be documented.

### Risks (ranked by severity)

| # | Risk | Severity | Mitigation |
|---|------|----------|------------|
| 1 | Bucket creation via SQL fails on hosted Supabase | Medium | Test on staging first; fallback to API-based creation |
| 2 | UserScopedClient doesn't wrap storage ops | Medium | Document that router endpoints use ConfigService with user_id param, not direct storage RLS |
| 3 | Silent exception swallowing in `_download()` | Low | Catch specific StorageApiError |
| 4 | SPEC-032 numbering confusion with frontend streaming spec | Low | Renumber or clarify cross-references |

---

## SPEC-033: Conversation Handler — Replace AgentExecutor

### Verdict: CONCERNS (several fixable issues, one near-blocker)

### Blast Radius Verification

The blast radius analysis is **thorough and largely accurate** (37 files analyzed). Key verifications:

- **No existing streaming**: Confirmed. The current `/api/chat` endpoint is purely synchronous `await ainvoke()` → `ChatResponse`. No SSE, no `StreamingResponse`, no `astream_events()`. SPEC-033 introduces streaming as a green-field addition. ✅
- **Four invocation points**: Confirmed: `chat.py:302`, `telegram_bot.py:440`, `scheduled_execution_service.py:128`, `session_open_service.py:156`. ✅
- **Content block normalization**: Confirmed at 4 locations (chat.py:305-310, telegram_bot.py:443-449, scheduled_execution_service.py:137-145, session_open_service.py:174-182). ✅
- **Tool wrapping targets `_arun()`**: Confirmed at `tool_wrapper.py:61-168`. The bridge pattern will work because `wrapped_arun` replaces `tool._arun`, so calling `tool._arun(**args)` goes through approval. ✅
- **`_push_to_telegram_if_linked`**: Found at `chat.py:169-206`. The spec correctly identifies this needs extraction. ✅
- **`anthropic` package**: Only present transitively via `langchain-anthropic`. Explicit dependency needed. ✅

### Issues Found

1. **NEAR-BLOCKER: `get_approval_context()` on BaseTool subclasses.** The approval wrapper (`tool_wrapper.py:121-127`) checks for `tool.get_approval_context()` — a method on BaseTool subclasses that enriches the approval queue entry with tool-specific context (e.g., `SendEmailReplyTool` provides original email subject for the approval preview). Found in `gmail_compose_tools.py:260`. The spec's `LangChainToolBridge.execute()` calls `tool._arun(**args)` — this works because `_arun` is already wrapped. BUT the bridge stores tool references as executors by name (`tool_executors: dict[str, Callable]`). If the bridge only stores the `_arun` callable (not the tool instance), the approval wrapper's `hasattr(tool, "get_approval_context")` check will fail because `tool` is still the original BaseTool instance inside the closure — this actually works fine because the wrapper closes over the `tool` variable. **False alarm after analysis — the closure captures the tool instance.** However, this is fragile and should be explicitly tested.

2. **CONCERN: Message history format mismatch risk.** AC-06 says "Messages are converted from the stored LangChain JSON format." The actual stored format in `chat_message_history` is LangChain's `PostgresChatMessageHistory` format with `BaseMessage` serialization. This includes:
   - `HumanMessage` → `{"type": "human", "data": {"content": "...", "type": "HumanMessage"}}`
   - `AIMessage` → `{"type": "ai", "data": {"content": "...", "type": "AIMessage"}}`
   - `AIMessage` with tool calls → nested `tool_calls` array, `additional_kwargs.tool_calls`
   - `ToolMessage` → `{"type": "tool", "data": {"content": "...", "tool_call_id": "..."}}`

   The spec mentions this but the message_history_adapter must handle **all variants** — including the content-block-list format (`list[dict]` content) that newer langchain-anthropic produces. This is the same normalization problem that currently requires the hack in chat.py:305-310. The adapter needs comprehensive format-sniffing logic. **Recommendation:** Add explicit test cases for every stored message variant. Consider dumping a real `chat_message_history` row as a test fixture.

3. **CONCERN: `prompt_section()` class method migration.** The current `prompt_builder.py:148-166` calls `tool_cls.prompt_section(channel)` to collect per-tool prompt guidance. This iterates over instantiated tool objects and calls the class method. The spec doesn't address how the ConversationHandler path assembles tool guidance. It says `prompt_builder.py` is "NOT modified" — but `prompt_builder.py` currently receives `tools` (list of BaseTool instances) to call `prompt_section()` on them. If the ConversationHandler converts tools to Anthropic schemas first, the BaseTool instances still need to exist for prompt building. **This works because both paths use `load_tools_from_db()` first**, which creates BaseTool instances. The bridge then converts to Anthropic format for the API call. But this should be explicitly documented in the spec.

4. **CONCERN: Session management differs across channels.** The spec's AC-06/AC-07 describe a single message history adapter, but the four invocation points handle memory differently:
   - **chat.py**: Uses `AsyncConversationBufferWindowMemory` with k=50 (line 88)
   - **telegram_bot.py**: Same memory pattern (lines 423-434)
   - **scheduled_execution_service.py**: No memory — passes `"chat_history": []` (line 131)
   - **session_open_service.py**: No memory — passes `"chat_history": []` (line 157)

   The ConversationHandler must replicate these different memory behaviors per channel. The spec's FU-4 (Channel Adapters) acknowledges this but the AC descriptions are channel-generic ("works identically"). **Recommendation:** Add explicit ACs for memory behavior per channel: web/telegram load 50 messages, scheduled/session_open start fresh.

5. **CONCERN: `ChatService` instance state and Telegram push.** `ChatService` is a class with instance methods and holds `_agent_executor_cache` (line 48 of chat.py). The `_push_to_telegram_if_linked` method accesses `db_client` from the calling context. In the new path, this logic needs to be extracted into a standalone utility that receives `db_client` as a parameter. The spec mentions this ("extracted into a shared utility") but no AC covers it specifically. **Recommendation:** Add an AC for Telegram push extraction.

6. **CONCERN: The `CONVERSATION_HANDLER_V2` feature flag check per-request is good, but the handler construction cost matters.** `build_conversation_handler()` (spec's code example in main.py) must load tools, create BaseTool instances, wrap with approval, convert to Anthropic schemas, load history, build system prompt — all per request. The current path caches the `AgentExecutor` per `(user_id, agent_name)`. Without similar caching, the v2 path will be significantly slower on first request. **Recommendation:** Cache the ConversationHandler or at least the tool schemas + Anthropic client across requests for the same user.

7. **MINOR: SSE format divergence.** The spec acknowledges the SSE format differs from `assistant-stream` protocol (Decision #1). This will require the frontend team to handle two formats or do a format swap during SPEC-032 frontend work. Not a blocker but coordination risk.

8. **MINOR: `dispatch_workflow` stub (AC-28-30) is handler-internal but uses a tool schema.** If it's not in the DB tool registry and not in `CANONICAL_TOOL_NAMES`, the `test_tool_registry_validator.py` won't catch it — which is correct. But the stub schema must exactly match the future SPEC-035 schema to avoid a breaking change. **Recommendation:** Mark the schema as provisional in comments.

### Missed Files/Dependencies

- **`chatServer/services/langchain_auth_bridge.py`**: The spec lists this as "NOT modified" but doesn't explain what it does. It bridges Supabase Vault to Google OAuth. The ConversationHandler's tool bridge path goes `BaseTool._arun()` → tool internals → this bridge. It will work unchanged, but the spec should mention it in the blast radius as "unchanged, used transitively by OAuth tools."
- **`chatServer/tools/gmail_rate_limiter.py`**: Not mentioned in the spec. Gmail tools use `GmailRateLimiter` for rate limiting. The bridge calls `_arun()` which internally uses the rate limiter. Works unchanged but should be documented.
- **`chatServer/config/constants.py`**: Contains `CHAT_MESSAGE_HISTORY_TABLE_NAME`. The message_history_adapter will need this constant.

### Risks (ranked by severity)

| # | Risk | Severity | Mitigation |
|---|------|----------|------------|
| 1 | Message history format variants not fully covered | High | Dump real DB rows as test fixtures; test all LangChain message types |
| 2 | No handler caching → performance regression on v2 path | High | Cache tool schemas + Anthropic client per user |
| 3 | Per-channel memory differences not spec'd as ACs | Medium | Add channel-specific memory ACs |
| 4 | Telegram push extraction has no AC | Medium | Add AC for shared Telegram push utility |
| 5 | Tool guidance (`prompt_section`) assembly unclear in new path | Medium | Document that BaseTool instances are created before bridge conversion |
| 6 | SSE format coordination with frontend | Low | Resolve Decision #1 before implementation |

---

## SPEC-034: Capability Gateway — Replace BaseTool/ToolExecutionService

### Verdict: CONCERNS (significant coordination and sequencing issues)

### Blast Radius Verification

The tool migration map (29 tools) is **accurate**. Verified against `TOOL_REGISTRY` in `agent_loader_db.py:44-86`:

- Registry has 27 named entries + CRUDTool (deprecated) + 2 Gmail tool classes in `GMAIL_TOOL_CLASSES`. The spec lists 29 tools (28 canonical + the deprecated CRUDTool to delete). Count is correct. ✅
- All tool files in `chatServer/tools/` verified: `task_tools.py` (4), `reminder_tools.py` (3), `schedule_tools.py` (3), `gmail_tools.py` (2), `gmail_compose_tools.py` (2), `calendar_tools.py` (2), `memory_tools.py` (10), `web_search_tool.py` (1), `update_instructions_tool.py` (1), `briefing_tools.py` (1), `gmail_rate_limiter.py` (utility). ✅

### Issues Found

1. **BLOCKER: SPEC-034 depends on SPEC-032 ConfigService for tool definitions, but SPEC-032 might not be ready.** AC-07 says "Tool definitions are loaded from Markdown files with YAML frontmatter (via SPEC-032 ConfigService)." But SPEC-032 is building file-based config for agent identity/soul/instructions — it doesn't specifically implement tool definition storage. The gateway needs `config_service.get_tool_definition(tool_name)` — a method that doesn't exist in SPEC-032's API (`read()`, `write()`, `list_paths()` are generic file ops). The tool definition loading, parsing, and caching would need to be built in SPEC-034 on top of SPEC-032's primitives. This is fine architecturally but the dependency should be explicit: SPEC-034 FU-1 needs SPEC-032 FU-2 (ConfigService) to be complete before it can load tool definitions from storage.

   **Alternative:** For FU-1-3, hard-code tool definitions in Python (a `TOOL_DEFINITIONS` dict, similar to current `TOOL_REGISTRY`). Migrate to config files in FU-4 or a follow-up. This decouples the two specs and reduces risk. The gateway's `ToolDefinition` model stays the same; only the loading source changes.

2. **CONCERN: Gmail tools have significant internal state.** `SearchGmailTool` and `GetGmailTool` extend `BaseGmailTool` which has a cached `_provider` (`GmailToolProvider` instance, `gmail_tools.py:362-368`). `GmailToolProvider` handles:
   - Multi-account discovery (line 92: `get_all_providers()`)
   - Token refresh with retry (lines 165-200: `_refresh_if_needed()`)
   - Sync Supabase client creation for token storage (lines 143-155, 177-185, 281-285 — uses `create_client()` sync!)
   - LangChain `GmailToolkit` initialization (line 291-348)
   - Custom `MetadataGmailSearch` replacing LangChain's default (lines 340-348)

   The executor migration for Gmail isn't just "extract `_arun()` body." It requires **reimplementing the provider pattern** without LangChain's `GmailToolkit`. The `MetadataGmailSearch` subclass overrides LangChain's `GmailSearch._parse_messages()` — this logic must be preserved. This is the most complex tool migration and likely 3-4x the effort of a simple service-backed tool.

   **Additionally:** Gmail tools use `os.getenv()` directly for Supabase credentials (lines 145-146, 179-180, 283-284) rather than the async client. SPEC-034's `CredentialProvider` would need to handle this — but it should use the async client pattern, not sync `create_client()`. This is a net improvement but means the executor can't just copy-paste the `_arun()` body.

3. **CONCERN: Memory tools have deep MCP client coupling.** `_MemoryToolBase` (memory_tools.py:20-45) stores `memory_client` as a Pydantic field and uses it in `_call_mcp()`. The 10 memory tool executors would need to receive the MCP client handle via `ExecutionContext.credentials`. This works conceptually, but the MCP client is currently set at tool instantiation time (`memory_client=...` in the constructor, called from `agent_loader_db.py`). The gateway would need to set this per-session, which changes the initialization model. The spec acknowledges this (AC-12) but the implementation detail of "MCP client handle via the gateway's dependency injection" is vague. **Recommendation:** Clarify whether the MCP client is per-session (re-created for each conversation) or shared across sessions. Currently, it appears to be created during tool instantiation which is cached per `(user_id, agent_name)`.

4. **CONCERN: `prompt_section()` class methods on tools are used for prompt assembly.** The spec's `get_prompt_sections()` method on the gateway addresses this, but `prompt_builder.py:148-166` currently iterates over tool instances and calls `type(tool).prompt_section(channel)`. When BaseTool subclasses are deleted (FU-4), this code breaks. Either:
   - (a) `prompt_builder.py` must be updated to call `gateway.get_prompt_sections()` instead
   - (b) The prompt sections must be migrated to the tool definition files (the spec's `prompt_section: dict[str, str | None]` field in `ToolDefinition`)

   The spec defines `prompt_section` in `ToolDefinition` (approach b) and `get_prompt_sections()` on the gateway (approach a). But `prompt_builder.py` is listed as staying unchanged. **This is inconsistent.** `prompt_builder.py`'s `_format_tool_guidance()` function must be updated to use the gateway. This is a missed modification.

5. **CONCERN: `get_approval_context()` enrichment method.** `SendEmailReplyTool` has a `get_approval_context()` method (`gmail_compose_tools.py:260`) that the approval wrapper calls to add preview context to queued actions. In the gateway model, this enrichment logic needs to live somewhere — either in the executor, the gateway pipeline, or the tool definition. The spec doesn't mention this method. **Recommendation:** Add a `context_enricher` field to `ToolDefinition` or handle it in the gateway's tier-check step.

6. **CONCERN: FU-4 (cleanup/delete) has an ordering constraint with SPEC-033.** The spec notes this: "FU-4 can only execute after SPEC-033 (ConversationHandler) is wired to use the gateway." But if SPEC-033 is implemented with the `LangChainToolBridge` (bridging to BaseTool), deleting BaseTool subclasses in SPEC-034 FU-4 **breaks SPEC-033's bridge**. The bridge must be replaced with gateway calls before FU-4 runs. This means SPEC-033 needs a follow-up to swap the bridge for gateway integration, and SPEC-034 FU-4 depends on that follow-up. **This cross-spec dependency is not documented in either spec.**

7. **MINOR: CRUDTool in TOOL_REGISTRY.** Line 45 of `agent_loader_db.py` still has `"CRUDTool": CRUDTool` in the registry. The spec lists CRUDTool for deletion but should verify no DB rows still reference `type = 'CRUDTool'`.

8. **MINOR: `gmail_rate_limiter.py` migration.** The spec says it's "moved into `capabilities/executors/gmail.py`" — but it's a utility class (`GmailRateLimiter`) with per-instance state (rate tracking). It should be injected into the Gmail executors, not inlined. **Recommendation:** Keep it as a separate module or make it a gateway-level concern.

### Missed Files/Dependencies

- **`chatServer/services/prompt_builder.py`**: Must be modified to use gateway's `get_prompt_sections()` instead of iterating tool class methods. Currently listed as "stays unchanged" — this is wrong.
- **`chatServer/tools/__init__.py`**: Not mentioned. May have re-exports or initialization logic that needs updating.
- **`src/core/agent_loader_db.py` tool instantiation logic (lines 280-430)**: The spec mentions removing `TOOL_REGISTRY` and `load_tools_from_db()` but this function also handles tool-specific initialization (Gmail multi-account, memory client injection, tool config from DB). This initialization logic must be replicated in the gateway or executor registration. Not just a simple deletion.

### Risks (ranked by severity)

| # | Risk | Severity | Mitigation |
|---|------|----------|------------|
| 1 | Cross-spec dependency: SPEC-033 bridge must be replaced before SPEC-034 FU-4 | High | Document explicit handoff point; add SPEC-033 FU-7 for gateway integration |
| 2 | Gmail tool complexity vastly exceeds "thin executor" model | High | Budget 3-4x effort for Gmail executors; consider keeping GmailToolProvider as an internal service |
| 3 | `prompt_builder.py` must be modified (missed from spec) | Medium | Add to FU-4 modifications list |
| 4 | Hard dependency on SPEC-032 ConfigService for tool definitions | Medium | Use hardcoded definitions for FU-1-3; migrate to config files later |
| 5 | MCP client lifecycle unclear (per-session vs shared) | Medium | Clarify in spec; align with current agent_loader_db.py behavior |
| 6 | `get_approval_context()` enrichment not addressed | Medium | Add context_enricher pattern to gateway pipeline |
| 7 | Gmail tools use sync Supabase client internally | Low | Migrate to async as part of executor rewrite (net improvement) |

---

## Cross-Spec Coordination Issues

### 1. SPEC-032 ↔ SPEC-033 Numbering Conflict
SPEC-033 references "SPEC-032 FU-1" for backend SSE streaming, but the actual SPEC-032 in this review is Config Service, not streaming. Either there's a different SPEC-032 for the frontend/streaming work, or the cross-references are wrong. **Must be clarified before implementation.**

### 2. SPEC-033 ↔ SPEC-034 Bridge Lifecycle
The `LangChainToolBridge` in SPEC-033 is explicitly temporary — "removed when SPEC-034 ships." But SPEC-034 FU-4 (delete old tools) can't run until the bridge is replaced. This creates a circular dependency:
- SPEC-033 ships with bridge → BaseTool subclasses must exist
- SPEC-034 FU-1-3 ships gateway + executors → both old and new coexist
- SPEC-033 must be updated to use gateway instead of bridge → **this step is not spec'd in either document**
- SPEC-034 FU-4 can delete old tools → bridge can be removed

**Recommendation:** Add an explicit FU to one of the specs for the bridge→gateway swap. Suggested: SPEC-034 FU-3.5 "Wire ConversationHandler to CapabilityGateway" before FU-4 cleanup.

### 3. SPEC-032 ↔ SPEC-034 Tool Definition Storage
SPEC-034 says tool definitions are loaded "via SPEC-032 ConfigService." But SPEC-032's scope is agent identity/soul/instructions — tool definitions aren't mentioned in SPEC-032's ACs. Either SPEC-032's scope should expand to cover tool definition storage, or SPEC-034 should start with hardcoded definitions and migrate later.

### 4. Shared Prompt Builder Modification
Both SPEC-032 and SPEC-034 affect `prompt_builder.py` differently:
- SPEC-032: Upstream change (soul/identity source changes, but `build_agent_prompt()` signature stays the same) — transparent ✅
- SPEC-034: `_format_tool_guidance()` must switch from iterating BaseTool classes to using gateway — NOT transparent ❌

These changes should not conflict (they touch different functions), but the SPEC-034 prompt_builder modification must be added to its scope.

### 5. Implementation Order
The specs don't specify inter-spec ordering clearly. Recommended:
1. **SPEC-032 (Config Service)** — no dependencies on the others
2. **SPEC-033 (Conversation Handler)** — depends on nothing if bridge approach is used
3. **SPEC-034 FU-1-3 (Gateway + Executors)** — can depend on SPEC-032 for tool def storage, or use hardcoded defs
4. **SPEC-034 bridge swap** — depends on both SPEC-033 and SPEC-034 FU-1-3
5. **SPEC-034 FU-4 (Cleanup)** — depends on bridge swap

SPEC-032 and SPEC-033 can run in parallel. SPEC-034 should start after SPEC-032 FU-2 (if using config files) or can start immediately (if using hardcoded defs).

---

## Summary

| Spec | Verdict | Blockers | Key Action |
|------|---------|----------|------------|
| SPEC-032 | CONCERNS | 0 | Verify bucket creation via SQL; clarify user-scoped storage access |
| SPEC-033 | CONCERNS | 0 | Add caching strategy; document per-channel memory behavior; add message format test fixtures |
| SPEC-034 | CONCERNS | 1 (cross-spec) | Document bridge→gateway swap FU; budget extra time for Gmail; add prompt_builder.py to modifications |

No spec has a hard blocker that prevents implementation. The near-blocker on SPEC-034 (cross-spec bridge lifecycle) is a sequencing/documentation gap, not a technical impossibility. All three specs demonstrate strong blast radius analysis — the issues found are at the edges, not the core.
