---
name: backend-patterns
description: FastAPI backend and LangChain agent patterns for chatServer/ and src/. Use when writing or modifying Python code in chatServer/, src/core/, or tests/. Covers service layer, dependency injection, Pydantic validation, RLS, auth (ES256), CRUDTool, agent loading, executor caching, and content block handling.
---

# Backend Patterns

## Architecture: Routers → Services → Database

```
chatServer/
  routers/      → HTTP handling only (request/response)
  services/     → Business logic only
  models/       → Pydantic schemas
  dependencies/ → auth.py, agent_loader.py (FastAPI Depends)
  database/     → connection.py, supabase_client.py
  config/       → settings.py
```

**Never put business logic in routers. Never put HTTP handling in services.**

## Quick Checklist

Before writing backend code, verify:
- [ ] Using `Depends(get_supabase_client)` or `Depends(get_db_connection)` — no new connections
- [ ] Business logic in services, not routers
- [ ] Pydantic models for request/response validation
- [ ] RLS handles user scoping (no manual `user_id` filtering)
- [ ] `Depends(get_current_user)` for auth — no manual header parsing
- [ ] Error handling re-raises HTTPException, logs unexpected errors
- [ ] Agent tools configured in DB, using generic CRUDTool
- [ ] Content block lists normalized to strings in chat responses

## Key Gotchas

1. **ES256 tokens** — Supabase issues ES256, not HS256. Don't revert auth.py to HS256-only.
2. **Content block lists** — Newer `langchain-anthropic` returns `[{"text": "...", "type": "text"}]`. Normalize in chat.py.
3. **Auth token source** — Frontend must use `supabase.auth.getSession()`, not Zustand.

## Detailed Reference

For full patterns with code examples, see [reference.md](reference.md).
