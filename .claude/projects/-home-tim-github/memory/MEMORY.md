## llm-agent Project Notes

### Database Schema
- `agent_configurations` table does NOT have `is_active` or `is_deleted` columns. Columns: `id`, `agent_name`, `soul`, `identity` (JSONB), `llm_config` (JSONB), `created_at`, `updated_at`
- `agent_tools` and `tools` tables DO have `is_active` and `is_deleted` columns
- `system_prompt` was renamed to `soul` in migration `20260219000001`

### Project Conventions
- Python venv at `.venv/bin/python` — `python` and `python3` system commands don't have project deps
- Ruff linter: line length 120, import sorting enforced
- Dual-import pattern in chatServer: try relative imports, except ImportError use absolute
- Tests: pytest with pytest-asyncio (mode=auto)