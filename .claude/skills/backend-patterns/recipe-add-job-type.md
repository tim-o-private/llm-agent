# Recipe: Add a New Job Type

Prescriptive guide for adding a new background job type to the universal job queue (SPEC-026).

> **Stub:** This recipe will be completed when SPEC-026 is implemented. The structure below reflects the spec's design.

## Prerequisites

- SPEC-026 merged (universal job queue infrastructure exists)
- Job type name chosen: `{job_type}` (snake_case — e.g., `email_processing`, `calendar_sync`, `briefing_generation`)
- Input/output JSONB contracts defined

## Step 1: Handler Function — `chatServer/services/job_handlers.py`

Add an async handler function to the existing `job_handlers.py`:

```python
async def handle_{job_type}(job: dict) -> dict:
    """Handle {job_type} jobs.

    Input contract: {describe input JSONB shape}
    Output contract: {describe output JSONB shape}
    """
    # Import the service that does the actual work
    from .{domain}_service import {Domain}Service

    # Extract typed input from job's JSONB
    {field} = job["input"]["{field}"]

    # Delegate to existing service
    service = {Domain}Service(...)
    result = await service.do_work(...)

    # Raise on failure — JobRunnerService will catch and call fail() with retry
    if not result.get("success"):
        raise RuntimeError(result.get("error", "{job_type} failed"))

    # Return output dict — stored in jobs.output JSONB
    return {"key": "value", ...}
```

**Rules:**
- Handler receives the full job dict (including `id`, `user_id`, `input`, `status`, etc.).
- Handler returns a dict (stored in `jobs.output` JSONB) or raises an exception.
- Exceptions are caught by `JobRunnerService` — the job is failed with retry by default.
- Raise `RuntimeError` with `should_retry=False` semantics by returning vs. raising.
- Keep handlers thin — delegate to existing services. The handler adapts the job shape, nothing more.

## Step 2: Register Handler

In the `JobRunnerService` setup (in `background_tasks.py` or wherever the runner is initialized):

```python
from chatServer.services.job_handlers import handle_{job_type}

job_runner.register_handler("{job_type}", handle_{job_type})
```

## Step 3: Create Jobs from Trigger Source

Wherever the trigger originates (router, scheduler, another handler, agent tool):

```python
await job_service.create(
    job_type="{job_type}",
    input={"{field}": value, ...},
    user_id=user_id,
    priority=0,           # default; increase for urgent work
    max_retries=3,        # default; set 0 for no-retry jobs
    scheduled_for=None,   # default=NOW; set future time for deferred work
)
```

## Step 4: Tests — `tests/chatServer/services/test_job_handlers.py`

Add tests for the new handler to the existing test file:

```python
@pytest.mark.asyncio
async def test_handle_{job_type}_success():
    job = {
        "id": "job-1",
        "user_id": "user-1",
        "job_type": "{job_type}",
        "input": {"{field}": "value"},
        "status": "running",
    }
    with patch("chatServer.services.job_handlers.{Domain}Service") as mock_svc:
        mock_svc.return_value.do_work = AsyncMock(return_value={"success": True})
        result = await handle_{job_type}(job)
    assert result["key"] == "value"


@pytest.mark.asyncio
async def test_handle_{job_type}_failure_raises():
    job = {"id": "job-1", "user_id": "user-1", "input": {"{field}": "value"}, ...}
    with patch("chatServer.services.job_handlers.{Domain}Service") as mock_svc:
        mock_svc.return_value.do_work = AsyncMock(return_value={"success": False, "error": "boom"})
        with pytest.raises(RuntimeError, match="boom"):
            await handle_{job_type}(job)
```

## Step 5: Document the Contract

Add to the cross-domain contracts section of the relevant spec:

| `job_type` | `input` Shape | Handler | Returns |
|------------|---------------|---------|---------|
| `{job_type}` | `{"field": "value"}` | `handle_{job_type}` | `{"key": "value"}` |

## Checklist

- [ ] Handler function in `chatServer/services/job_handlers.py`
- [ ] Handler registered in runner setup
- [ ] Job creation wired from trigger source
- [ ] Handler tests in `tests/chatServer/services/test_job_handlers.py`
- [ ] Input/output JSONB contract documented in spec
- [ ] No new tables created (use `jobs` table — see Platform Primitives in product-architecture)
- [ ] No new polling loops created (handler dispatched by `JobRunnerService`)
