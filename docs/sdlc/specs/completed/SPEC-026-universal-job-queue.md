# SPEC-026: Universal Job Queue & Scheduler

> **Status:** Draft
> **Author:** Tim + Claude (Product)
> **Created:** 2026-02-25
> **Updated:** 2026-02-25

## Goal

Replace per-type job tables and per-type polling loops with two reusable primitives: a universal `jobs` table and a `JobRunnerService` that dispatches to registered handlers by `job_type`. Today, adding a new background job type (email processing, calendar sync, briefings) requires a new table, a new polling method, a new `asyncio.Task`, and registration in `start_background_tasks()`. After this spec, adding a new job type requires registering a handler function for a `job_type` string. No new tables, no new polling loops. This is the infrastructure foundation for PRD-002 (calendar, briefings, web search, draft-reply).

## Background

`BackgroundTaskService` currently manages five separate `asyncio.Task` loops:

1. `deactivate_stale_chat_session_instances` — session cleanup (housekeeping)
2. `evict_inactive_executors` — cache eviction (housekeeping)
3. `run_scheduled_agents` — cron-triggered agent execution
4. `check_due_reminders` — reminder delivery
5. `check_email_processing_jobs` — email onboarding pipeline

Each user-facing job type (#3-5) has its own polling logic, its own status tracking, and its own error handling. The `email_processing_jobs` table duplicates the lifecycle pattern (pending/processing/complete/failed) that will be needed by every future job type. The `email_digest_batches` table is orphaned — nothing writes to it.

This spec extracts the common pattern into a universal job queue with `SELECT FOR UPDATE SKIP LOCKED` for atomic claiming, JSONB input/output for type flexibility, and retry with exponential backoff. The scheduler (`agent_schedules`) creates jobs instead of directly invoking services. Reminders create jobs instead of polling a separate table.

## Acceptance Criteria

### Database

- [ ] **AC-01:** A `jobs` table exists with columns: `id` (UUID PK), `user_id` (UUID FK → auth.users ON DELETE CASCADE), `job_type` (TEXT NOT NULL), `status` (TEXT NOT NULL, CHECK IN pending/claimed/running/complete/failed), `input` (JSONB NOT NULL DEFAULT '{}'), `output` (JSONB), `error` (TEXT), `priority` (INTEGER NOT NULL DEFAULT 0), `retry_count` (INTEGER NOT NULL DEFAULT 0), `max_retries` (INTEGER NOT NULL DEFAULT 3), `scheduled_for` (TIMESTAMPTZ NOT NULL DEFAULT NOW()), `expires_at` (TIMESTAMPTZ), `claimed_at` (TIMESTAMPTZ), `started_at` (TIMESTAMPTZ), `completed_at` (TIMESTAMPTZ), `created_at` (TIMESTAMPTZ NOT NULL DEFAULT NOW()), `updated_at` (TIMESTAMPTZ NOT NULL DEFAULT NOW()). RLS enabled with `is_record_owner(user_id)` policy for user access and service_role full access. [A8, A9]
- [ ] **AC-02:** Composite index exists on `(status, scheduled_for, priority)` for efficient polling queries. Partial index on `status = 'pending'` for the common case. Index on `user_id` for user-scoped queries. [A3]
- [ ] **AC-03:** A `expire_stale_jobs()` DB function exists (modeled on `expire_pending_actions()`) that transitions `claimed` or `running` jobs older than 30 minutes to `failed` with error `'Job timed out (stale claim)'`. Returns the count of expired jobs. [A14]
- [ ] **AC-04:** The `email_digest_batches` table is dropped (orphaned, nothing writes to it). [A14]
- [ ] **AC-05:** Existing `email_processing_jobs` rows (if any) are migrated to the `jobs` table as `job_type = 'email_processing'`, with `input` containing `{connection_id, ...}` from the original row. After migration, `email_processing_jobs` table is dropped. [A11]
- [ ] **AC-06:** `jobs` table is registered in `USER_SCOPED_TABLES` in `chatServer/database/user_scoped_tables.py`. [A8]

### Backend: JobService

- [ ] **AC-07:** `JobService` class exists in `chatServer/services/job_service.py` with a constructor accepting a database connection (psycopg pool, per A3 — this is high-volume framework-level work, not user CRUD). [A1, A3, A10]
- [ ] **AC-08:** `JobService.create(job_type, input, user_id, priority=0, max_retries=3, scheduled_for=None, expires_at=None)` inserts a new job row with status `pending` and returns the job ID (UUID). If `scheduled_for` is in the future, the job is not eligible for claiming until that time. [A1]
- [ ] **AC-09:** `JobService.claim_next(job_types=None)` executes `SELECT ... FROM jobs WHERE status = 'pending' AND scheduled_for <= NOW() [AND job_type IN (...)] ORDER BY priority DESC, scheduled_for ASC LIMIT 1 FOR UPDATE SKIP LOCKED` and atomically updates the row to `status = 'claimed', claimed_at = NOW()`. Returns the job row or `None`. [A3, A11]
- [ ] **AC-10:** `JobService.mark_running(job_id)` transitions a claimed job to `status = 'running', started_at = NOW()`. [A1]
- [ ] **AC-11:** `JobService.complete(job_id, output)` transitions a running job to `status = 'complete', output = <JSONB>, completed_at = NOW()`. [A1]
- [ ] **AC-12:** `JobService.fail(job_id, error, should_retry=True)` sets `error` on the job. If `should_retry=True` and `retry_count < max_retries`, increments `retry_count`, resets status to `pending`, and sets `scheduled_for = NOW() + backoff` (exponential: `30s * 2^retry_count`, capped at 15 minutes). If retries exhausted or `should_retry=False`, sets status to `failed` and `completed_at = NOW()`. [A11, A14]
- [ ] **AC-13:** `JobService.expire_stale()` calls the `expire_stale_jobs()` DB function and returns the count. [A1]

### Backend: JobRunnerService

- [ ] **AC-14:** `JobRunnerService` class exists in `chatServer/services/job_runner_service.py` with `register_handler(job_type: str, handler: Callable)` and `run()` methods. [A1, A10, A11]
- [ ] **AC-15:** `JobRunnerService.run()` implements a single polling loop: poll every 5 seconds for available jobs (via `JobService.claim_next()`), dispatch to the registered handler for the claimed job's `job_type`, call `mark_running()` before handler invocation and `complete()` or `fail()` after. If no handler is registered for a `job_type`, the job is failed with error `'No handler registered for job_type: <type>'`. [A11]
- [ ] **AC-16:** `JobRunnerService.run()` calls `JobService.expire_stale()` every 5 minutes to clean up stale claims. [A14]
- [ ] **AC-17:** `JobRunnerService` catches all exceptions from handlers and calls `JobService.fail()` with the exception message. Handlers never crash the runner loop. [A14]

### Backend: Handler Registration & Migration

- [ ] **AC-18:** An `handle_email_processing` async handler function exists that accepts a job dict (with `input` containing `connection_id`) and calls `EmailOnboardingService.process_job()` with the appropriate shape. Registered as handler for `job_type = 'email_processing'`. [A1, A11]
- [ ] **AC-19:** An `handle_agent_invocation` async handler function exists that accepts a job dict (with `input` containing `schedule_id, user_id, agent_name, prompt, config`) and calls `ScheduledExecutionService.execute()`. Registered as handler for `job_type = 'agent_invocation'`. [A1, A11]
- [ ] **AC-20:** An `handle_reminder_delivery` async handler function exists that accepts a job dict (with `input` containing `reminder_id, user_id`) and delivers the reminder via `NotificationService.notify_user()` + `ReminderService.mark_sent()` + `ReminderService.handle_recurrence()`. Registered as handler for `job_type = 'reminder_delivery'`. [A1, A11]
- [ ] **AC-21:** `BackgroundTaskService.run_scheduled_agents()` is refactored: instead of directly calling `_execute_scheduled_agent()`, it calls `JobService.create(job_type='agent_invocation', input={schedule data}, user_id=...)`. The cron evaluation logic (`_should_run_now`, `_reload_agent_schedules`) remains in `BackgroundTaskService`. [A1, A14]
- [ ] **AC-22:** `BackgroundTaskService.check_due_reminders()` is refactored: instead of directly calling `NotificationService`/`ReminderService`, it queries due reminders and creates a job per reminder via `JobService.create(job_type='reminder_delivery', input={reminder_id, user_id}, user_id=...)`. [A1, A14]
- [ ] **AC-23:** `BackgroundTaskService.check_email_processing_jobs()` is removed entirely. Email processing jobs now go through the universal `jobs` table and `JobRunnerService`. [A11]
- [ ] **AC-24:** `BackgroundTaskService.start_background_tasks()` is updated: the `email_processing_task` is removed; a single `JobRunnerService.run()` task is added. The session cleanup loop, executor eviction loop, scheduled agents loop (cron evaluator only), and reminders loop (enqueuer only) remain as separate tasks. [A14]
- [ ] **AC-25:** `external_api_router.py` inserts into the `jobs` table (not `email_processing_jobs`) when creating email processing jobs. Job is created with `job_type='email_processing'`, `input={'connection_id': str(connection_id)}`. [A1]

### Testing

- [ ] **AC-26:** Unit tests exist for all `JobService` public methods: `create`, `claim_next`, `mark_running`, `complete`, `fail` (with retries remaining), `fail` (retries exhausted), `expire_stale`. [S1]
- [ ] **AC-27:** Unit tests exist for `JobRunnerService`: handler registration, dispatch to correct handler, unknown `job_type` handling, exception isolation (handler crash does not kill runner). [S1]
- [ ] **AC-28:** Integration-style test: create job -> claim -> mark_running -> complete lifecycle. [S1]
- [ ] **AC-29:** Test: `claim_next` with `SKIP LOCKED` correctly skips already-claimed jobs (two concurrent claims on same pending job). [S1]
- [ ] **AC-30:** Test: failed job with retries remaining is re-queued as pending with incremented `retry_count` and future `scheduled_for`. [S1]
- [ ] **AC-31:** Test: failed job at `max_retries` stays failed. [S1]
- [ ] **AC-32:** Test: expired stale jobs (claimed but not completed) get failed by `expire_stale()`. [S1]

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `supabase/migrations/2026MMDD000001_create_jobs_table.sql` | Create `jobs` table, indexes, RLS, `expire_stale_jobs()` function |
| `supabase/migrations/2026MMDD000002_migrate_email_jobs.sql` | Migrate `email_processing_jobs` data, drop `email_processing_jobs` and `email_digest_batches` |
| `chatServer/services/job_service.py` | Universal job queue CRUD service |
| `chatServer/services/job_runner_service.py` | Single polling loop + handler dispatch |
| `chatServer/services/job_handlers.py` | Handler functions: `handle_email_processing`, `handle_agent_invocation`, `handle_reminder_delivery` |
| `tests/chatServer/services/test_job_service.py` | JobService unit tests |
| `tests/chatServer/services/test_job_runner_service.py` | JobRunnerService unit tests |
| `tests/chatServer/services/test_job_handlers.py` | Handler function unit tests |

### Files to Modify

| File | Change |
|------|--------|
| `chatServer/services/background_tasks.py` | Remove `check_email_processing_jobs()` and `_process_email_job()`. Refactor `_execute_scheduled_agent()` to enqueue job. Refactor `check_due_reminders()` to enqueue jobs. Update `start_background_tasks()` to add `JobRunnerService.run()` task. Update `stop_background_tasks()`. |
| `chatServer/routers/external_api_router.py` | Change email processing job insert from `email_processing_jobs` to `jobs` table with `job_type='email_processing'` |
| `chatServer/database/user_scoped_tables.py` | Add `"jobs"` to `USER_SCOPED_TABLES` |
| `chatServer/main.py` | Wire `JobRunnerService` into the background task lifecycle (if needed beyond `BackgroundTaskService` changes) |

### Out of Scope

- **Dead-letter queue / alerting** — failed jobs stay in `jobs` table for manual inspection. Automated alerting is a future concern.
- **Web UI for job status** — users do not need to see the jobs queue. Jobs are infrastructure, not user-facing.
- **Job cancellation API** — no endpoint to cancel a pending job. Can be added later if needed.
- **Multi-worker / distributed locking** — `SKIP LOCKED` already supports this correctly, but this spec assumes a single server process. Horizontal scaling is a future concern.
- **Job chaining / DAGs** — no dependency graph between jobs. Each job is independent. Pipelines (e.g., "process email then generate briefing") are orchestrated by the handler creating a new job on completion.
- **Migrating `agent_schedules` to use `jobs` for cron storage** — `agent_schedules` stays as the cron configuration table. It creates jobs, it does not become a job.
- **Session cleanup and executor eviction** — these are infrastructure housekeeping loops, not user jobs. They stay as simple `asyncio.Task` loops in `BackgroundTaskService`.

## Technical Approach

### 1. Database: `jobs` Table (FU-1)

Per A3, the `jobs` table is high-volume framework-level data. `JobService` uses the psycopg connection pool directly (via `get_database_manager()`) for `SELECT FOR UPDATE SKIP LOCKED` — this is not possible through the Supabase REST API. RLS is still added as defense-in-depth for any direct DB access.

```sql
CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    job_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'claimed', 'running', 'complete', 'failed')),
    input JSONB NOT NULL DEFAULT '{}',
    output JSONB,
    error TEXT,
    priority INTEGER NOT NULL DEFAULT 0,
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    scheduled_for TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    claimed_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- RLS (A8: defense-in-depth)
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Enable full access for record owners on jobs"
ON jobs FOR ALL
USING (public.is_record_owner(user_id))
WITH CHECK (public.is_record_owner(user_id));

CREATE POLICY "Service role can access all jobs"
ON jobs TO service_role USING (true) WITH CHECK (true);

-- Indexes for polling query (AC-02)
CREATE INDEX idx_jobs_poll ON jobs (status, scheduled_for, priority DESC)
    WHERE status = 'pending';
CREATE INDEX idx_jobs_user ON jobs (user_id);
CREATE INDEX idx_jobs_type_status ON jobs (job_type, status);

-- Updated_at trigger (reuse existing function)
CREATE TRIGGER update_jobs_updated_at
BEFORE UPDATE ON jobs
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Stale job expiry function (AC-03)
CREATE OR REPLACE FUNCTION expire_stale_jobs() RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE
    expired_count INTEGER;
BEGIN
    UPDATE jobs
    SET status = 'failed',
        error = 'Job timed out (stale claim)',
        completed_at = now(),
        updated_at = now()
    WHERE status IN ('claimed', 'running')
      AND claimed_at < now() - interval '30 minutes';

    GET DIAGNOSTICS expired_count = ROW_COUNT;
    RETURN expired_count;
END;
$$;

COMMENT ON TABLE jobs IS 'Universal job queue for all background work types (email processing, agent invocation, reminder delivery, etc.)';
COMMENT ON COLUMN jobs.job_type IS 'Discriminator for handler dispatch (e.g., email_processing, agent_invocation, reminder_delivery)';
COMMENT ON COLUMN jobs.priority IS 'Higher priority jobs are claimed first. Default 0.';
COMMENT ON COLUMN jobs.scheduled_for IS 'Job is not eligible for claiming until this time. Supports delayed/scheduled execution.';
COMMENT ON COLUMN jobs.expires_at IS 'Optional hard expiry. Jobs past this time should not be executed.';
```

### 2. Data Migration (FU-1)

```sql
-- Migrate existing email_processing_jobs rows to jobs table
INSERT INTO jobs (id, user_id, job_type, status, input, error, created_at, started_at, completed_at, updated_at)
SELECT
    id,
    user_id,
    'email_processing',
    CASE status
        WHEN 'processing' THEN 'running'
        ELSE status
    END,
    jsonb_build_object('connection_id', connection_id::text)
        || COALESCE(result_summary, '{}'::jsonb),
    error_message,
    created_at,
    started_at,
    completed_at,
    updated_at
FROM email_processing_jobs;

-- Drop orphaned table
DROP TABLE IF EXISTS email_digest_batches;

-- Drop migrated table
DROP TABLE IF EXISTS email_processing_jobs;
```

### 3. JobService (FU-2)

Per A1, all job lifecycle logic lives in the service, not in routers or the runner. Per A3, uses psycopg directly for `SELECT FOR UPDATE SKIP LOCKED`.

```python
# chatServer/services/job_service.py
class JobService:
    """Universal job queue operations. Uses psycopg pool directly (A3)."""

    def __init__(self, db_pool):
        self.pool = db_pool

    async def create(self, job_type, input, user_id, priority=0,
                     max_retries=3, scheduled_for=None, expires_at=None) -> str:
        """Insert a pending job. Returns job ID."""
        ...

    async def claim_next(self, job_types=None) -> Optional[dict]:
        """Atomically claim the next eligible job. SELECT FOR UPDATE SKIP LOCKED."""
        ...

    async def mark_running(self, job_id: str) -> None:
        """Transition claimed -> running."""
        ...

    async def complete(self, job_id: str, output: dict) -> None:
        """Transition running -> complete."""
        ...

    async def fail(self, job_id: str, error: str, should_retry=True) -> None:
        """Fail a job. Re-queue with backoff if retries remain."""
        ...

    async def expire_stale(self) -> int:
        """Call expire_stale_jobs() DB function."""
        ...
```

**Claim query** (core of the queue):

```sql
SELECT id, user_id, job_type, status, input, priority, retry_count, max_retries,
       scheduled_for, expires_at, created_at
FROM jobs
WHERE status = 'pending'
  AND scheduled_for <= NOW()
  AND (expires_at IS NULL OR expires_at > NOW())
ORDER BY priority DESC, scheduled_for ASC
LIMIT 1
FOR UPDATE SKIP LOCKED
```

Immediately followed by:

```sql
UPDATE jobs SET status = 'claimed', claimed_at = NOW(), updated_at = NOW()
WHERE id = $1
RETURNING *
```

Both in the same transaction.

**Retry backoff formula**: `min(30 * 2^retry_count, 900)` seconds (30s, 60s, 120s, 240s, 480s, capped at 15 minutes).

### 4. JobRunnerService (FU-2)

Per A11, designed for N job types from day one. Adding a new type = registering a handler.

```python
# chatServer/services/job_runner_service.py
class JobRunnerService:
    """Single polling loop that dispatches jobs to registered handlers."""

    def __init__(self, job_service: JobService):
        self._handlers: dict[str, Callable] = {}
        self._job_service = job_service
        self._last_expiry_check = None

    def register_handler(self, job_type: str, handler: Callable) -> None:
        """Register an async handler for a job type."""
        self._handlers[job_type] = handler

    async def run(self) -> None:
        """Main loop. Poll, claim, dispatch, repeat."""
        while True:
            try:
                # Expire stale jobs every 5 minutes
                await self._maybe_expire_stale()

                # Claim next job
                job = await self._job_service.claim_next(
                    job_types=list(self._handlers.keys())
                )
                if job is None:
                    await asyncio.sleep(5)
                    continue

                # Dispatch
                await self._dispatch(job)

            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"JobRunner loop error: {e}", exc_info=True)
                await asyncio.sleep(5)

    async def _dispatch(self, job: dict) -> None:
        """Dispatch a job to its handler."""
        job_type = job["job_type"]
        handler = self._handlers.get(job_type)

        if handler is None:
            await self._job_service.fail(
                job["id"],
                f"No handler registered for job_type: {job_type}",
                should_retry=False
            )
            return

        try:
            await self._job_service.mark_running(job["id"])
            result = await handler(job)
            await self._job_service.complete(job["id"], result or {})
        except Exception as e:
            logger.error(f"Job {job['id']} ({job_type}) failed: {e}", exc_info=True)
            await self._job_service.fail(job["id"], str(e))
```

### 5. Handler Functions (FU-2)

Per A1, handlers are thin wrappers that delegate to existing services. They adapt the job's `input` JSONB to the service's expected interface.

```python
# chatServer/services/job_handlers.py

async def handle_email_processing(job: dict) -> dict:
    """Wrap EmailOnboardingService.process_job()."""
    from .email_onboarding_service import EmailOnboardingService
    service = EmailOnboardingService()
    # Adapt job shape to what process_job expects
    adapted = {
        "id": str(job["id"]),
        "user_id": str(job["user_id"]),
        "connection_id": job["input"]["connection_id"],
        "status": job["status"],
    }
    result = await service.process_job(adapted)
    if not result.get("success"):
        raise RuntimeError(result.get("error", "Email processing failed"))
    return {"output_preview": (result.get("output", ""))[:500]}


async def handle_agent_invocation(job: dict) -> dict:
    """Wrap ScheduledExecutionService.execute()."""
    from .scheduled_execution_service import ScheduledExecutionService
    service = ScheduledExecutionService()
    schedule = job["input"]  # Contains schedule_id, user_id, agent_name, prompt, config
    result = await service.execute(schedule)
    if not result.get("success"):
        raise RuntimeError(result.get("error", "Agent invocation failed"))
    return {
        "output": (result.get("output", ""))[:5000],
        "duration_ms": result.get("duration_ms"),
        "pending_actions": result.get("pending_actions_created", 0),
    }


async def handle_reminder_delivery(job: dict) -> dict:
    """Deliver a single reminder via NotificationService."""
    from ..database.supabase_client import create_system_client
    from .notification_service import NotificationService
    from .reminder_service import ReminderService

    db_client = await create_system_client()
    reminder_service = ReminderService(db_client)
    notification_service = NotificationService(db_client)

    reminder_id = job["input"]["reminder_id"]
    user_id = job["input"]["user_id"]

    # Fetch the reminder
    reminder = await reminder_service.get_reminder(reminder_id)
    if not reminder:
        return {"skipped": True, "reason": "Reminder not found"}

    await notification_service.notify_user(
        user_id=user_id,
        title=f"Reminder: {reminder['title']}",
        body=reminder.get("body") or reminder["title"],
        category="reminder",
        metadata={"reminder_id": str(reminder["id"])},
    )
    await reminder_service.mark_sent(reminder["id"])
    await reminder_service.handle_recurrence(reminder)

    return {"delivered": True, "reminder_id": str(reminder_id)}
```

### 6. BackgroundTaskService Refactoring (FU-2)

The key changes to `BackgroundTaskService`:

1. **Remove** `check_email_processing_jobs()` and `_process_email_job()` entirely.
2. **Refactor** `_execute_scheduled_agent()` to enqueue a job instead of directly calling `ScheduledExecutionService`:
   ```python
   async def _execute_scheduled_agent(self, schedule: Dict) -> None:
       job_input = {
           "id": str(schedule.get("id")),
           "user_id": schedule["user_id"],
           "agent_name": schedule["agent_name"],
           "prompt": schedule.get("prompt", ""),
           "config": schedule.get("config", {}),
       }
       await self._job_service.create(
           job_type="agent_invocation",
           input=job_input,
           user_id=schedule["user_id"],
       )
   ```
3. **Refactor** `check_due_reminders()` to create jobs instead of directly delivering:
   ```python
   # Instead of delivering inline, enqueue a job per reminder
   for reminder in due:
       await self._job_service.create(
           job_type="reminder_delivery",
           input={"reminder_id": str(reminder["id"]), "user_id": reminder["user_id"]},
           user_id=reminder["user_id"],
       )
   ```
4. **Update** `start_background_tasks()`:
   - Remove `self.email_processing_task`
   - Add `self.job_runner_task = asyncio.create_task(self._job_runner.run())`
5. **Update** `stop_background_tasks()` to cancel `job_runner_task`.

### 7. Router Change (FU-2)

In `external_api_router.py`, the email processing job creation changes from:

```python
# Old: insert into email_processing_jobs
await cur.execute(
    "INSERT INTO email_processing_jobs (user_id, connection_id) VALUES (%s, %s)",
    (user_id, connection_id),
)
```

To:

```python
# New: insert into jobs table
await cur.execute(
    """INSERT INTO jobs (user_id, job_type, input)
       VALUES (%s, 'email_processing', %s)""",
    (user_id, json.dumps({"connection_id": str(connection_id)})),
)
```

### Dependencies

- **SPEC-023 (Email Onboarding Pipeline)** — must be merged first. This spec migrates `email_processing_jobs` into `jobs`.
- **psycopg connection pool** — already exists via `get_database_manager()` in `chatServer/database/connection.py`.
- No external system dependencies.

## Testing Requirements

### Unit Tests (required)

- `test_job_service.py`: All CRUD methods on `JobService` with mocked psycopg pool
- `test_job_runner_service.py`: Registration, dispatch, error isolation with mocked `JobService`
- `test_job_handlers.py`: Each handler with mocked underlying services

### Integration Tests (required for DB changes)

- `test_job_service.py` (integration): Full lifecycle (create -> claim -> running -> complete) against real DB
- `test_job_service.py` (integration): `SKIP LOCKED` behavior with concurrent claims

### What to Test

- Happy path for each job lifecycle state transition
- Retry logic: fail with retries remaining -> re-queued as pending
- Retry logic: fail at max_retries -> stays failed permanently
- `SKIP LOCKED`: two concurrent `claim_next()` calls get different jobs
- Stale expiry: claimed jobs older than 30 min get failed
- Future `scheduled_for`: job not claimable until time arrives
- Expired `expires_at`: job not claimable after expiry time
- Unknown job_type: handler not found, job failed without retry
- Handler exception: caught by runner, job failed with retry
- Priority ordering: higher priority jobs claimed first

### AC-to-Test Mapping

| AC | Test Type | Test Function |
|----|-----------|---------------|
| AC-01 | Integration | `test_ac_01_jobs_table_exists_with_correct_schema` |
| AC-02 | Integration | `test_ac_02_polling_indexes_exist` |
| AC-03 | Unit + Integration | `test_ac_03_expire_stale_jobs_function` |
| AC-05 | Integration | `test_ac_05_email_jobs_migrated` |
| AC-08 | Unit | `test_ac_08_create_job_returns_id` |
| AC-09 | Unit + Integration | `test_ac_09_claim_next_skip_locked` |
| AC-10 | Unit | `test_ac_10_mark_running_transition` |
| AC-11 | Unit | `test_ac_11_complete_with_output` |
| AC-12 | Unit | `test_ac_12_fail_with_retry`, `test_ac_12_fail_exhausted` |
| AC-13 | Unit | `test_ac_13_expire_stale_service` |
| AC-15 | Unit | `test_ac_15_runner_poll_and_dispatch` |
| AC-17 | Unit | `test_ac_17_handler_exception_isolated` |
| AC-18 | Unit | `test_ac_18_email_processing_handler` |
| AC-19 | Unit | `test_ac_19_agent_invocation_handler` |
| AC-20 | Unit | `test_ac_20_reminder_delivery_handler` |
| AC-26-32 | Unit + Integration | `test_ac_26_*` through `test_ac_32_*` (see testing section) |

### Manual Verification (UAT)

- [ ] Start `pnpm dev`, trigger a Gmail OAuth connection. Verify job appears in `jobs` table with `job_type='email_processing'` and progresses through `pending -> claimed -> running -> complete`.
- [ ] Configure an agent schedule. Wait for cron trigger. Verify a job appears in `jobs` table with `job_type='agent_invocation'` and completes.
- [ ] Create a reminder due in 1 minute. Verify a `job_type='reminder_delivery'` job is created and the reminder notification is delivered.
- [ ] Verify `email_processing_jobs` and `email_digest_batches` tables no longer exist.
- [ ] Kill the server mid-job (simulate crash). Restart. Verify the stale job is expired and retried.

## Edge Cases

- **Concurrent claims on same job**: `SELECT FOR UPDATE SKIP LOCKED` ensures only one worker claims a job. The second concurrent claim silently skips it and moves to the next available job.
- **Handler raises exception**: Runner catches it, calls `fail()` with retry. Job re-enters queue with backoff. After `max_retries`, stays failed.
- **Job created with future `scheduled_for`**: Not eligible for claiming until `scheduled_for <= NOW()`. The claim query filters on this.
- **Job with `expires_at` in the past**: Claim query filters `expires_at IS NULL OR expires_at > NOW()`. Expired jobs are never claimed.
- **No jobs available**: Runner sleeps 5 seconds and polls again. No busy-waiting.
- **Server crash mid-execution**: Job stays in `claimed` or `running` status. `expire_stale_jobs()` (called every 5 minutes) will transition it to `failed` and retry will re-queue it if retries remain.
- **Handler returns `None`**: Treated as empty output `{}`. Job completes successfully.
- **Duplicate job creation from scheduler**: `run_scheduled_agents` tracks `last_run` in memory. If the server restarts, `last_run` resets, potentially creating a duplicate job. This is acceptable — the handler (e.g., `ScheduledExecutionService`) is idempotent (creates a new execution, which is fine for heartbeats/digests). For reminders, duplicates are prevented by `mark_sent()`.
- **Migration with active `email_processing_jobs`**: The migration copies rows as-is. In-progress jobs (`status='processing'`) are mapped to `status='running'` in the new table. They will be picked up by `expire_stale_jobs()` if not completed within 30 minutes.

## Functional Units (for PR Breakdown)

1. **FU-1: Database Migration** (`feat/SPEC-026-migration`)
   - Domain: `database-dev`
   - Complexity: Moderate
   - Create `jobs` table, indexes, RLS, `expire_stale_jobs()` function
   - Migrate `email_processing_jobs` data
   - Drop `email_processing_jobs` and `email_digest_batches` tables
   - Add `"jobs"` to `USER_SCOPED_TABLES`
   - Covers: AC-01, AC-02, AC-03, AC-04, AC-05, AC-06

2. **FU-2: Backend Services + Handlers** (`feat/SPEC-026-services`)
   - Domain: `backend-dev`
   - Complexity: Complex
   - Depends on: FU-1 merged
   - Create `JobService`, `JobRunnerService`, `job_handlers.py`
   - Refactor `BackgroundTaskService` (remove email polling, enqueue scheduled agents + reminders)
   - Update `external_api_router.py` to insert into `jobs` table
   - Wire `JobRunnerService` into `start_background_tasks()`
   - Covers: AC-07 through AC-25

3. **FU-3: Tests** (`feat/SPEC-026-tests`)
   - Domain: `backend-dev`
   - Complexity: Moderate
   - Depends on: FU-2 merged
   - Unit tests for `JobService`, `JobRunnerService`, `job_handlers`
   - Integration tests for claim/complete lifecycle, `SKIP LOCKED`, retry, expiry
   - Covers: AC-26 through AC-32

### Merge Order

```
FU-1 (migration) → FU-2 (services) → FU-3 (tests)
```

Sequential, acyclic. FU-2 depends on the `jobs` table existing. FU-3 depends on the services existing. FU-2 and FU-3 could be done by the same backend-dev agent sequentially.

## Cross-Domain Contracts

### FU-1 → FU-2: Database Schema

| Table | Key Columns | Notes |
|-------|-------------|-------|
| `jobs` | `id`, `user_id`, `job_type`, `status`, `input`, `output`, `error`, `priority`, `retry_count`, `max_retries`, `scheduled_for`, `expires_at`, `claimed_at`, `started_at`, `completed_at`, `created_at`, `updated_at` | All columns as specified in AC-01 |

### FU-2 → FU-2: Handler Contracts

| `job_type` | `input` Shape | Handler | Returns |
|------------|---------------|---------|---------|
| `email_processing` | `{"connection_id": "uuid-string"}` | `handle_email_processing` | `{"output_preview": "..."}` |
| `agent_invocation` | `{"id": "schedule-uuid", "user_id": "uuid", "agent_name": "str", "prompt": "str", "config": {...}}` | `handle_agent_invocation` | `{"output": "...", "duration_ms": N, "pending_actions": N}` |
| `reminder_delivery` | `{"reminder_id": "uuid", "user_id": "uuid"}` | `handle_reminder_delivery` | `{"delivered": true, "reminder_id": "uuid"}` |

## Effort Estimation

| FU | Domain Agent | Complexity | Estimated Effort |
|----|-------------|------------|-----------------|
| FU-1 | database-dev | Moderate | 1 migration file, schema straightforward |
| FU-2 | backend-dev | Complex | 3 new service files + refactor of background_tasks.py + router change |
| FU-3 | backend-dev | Moderate | 3 test files, mocking patterns are well-established |

**Total agents needed:** database-dev, backend-dev
**Dependencies on other specs:** SPEC-023 must be merged (for `email_processing_jobs` table to exist for migration)
**Dependencies on external systems:** None

## Completeness Checklist

- [x] Every AC has a stable ID (AC-01 through AC-32)
- [x] Every AC maps to at least one functional unit
- [x] Every cross-domain boundary has a contract (schema -> services -> handlers)
- [x] Technical decisions reference principles (A1, A3, A8, A9, A10, A11, A14)
- [x] Merge order is explicit and acyclic (FU-1 -> FU-2 -> FU-3)
- [x] Out-of-scope is explicit (no UI, no cancellation API, no multi-worker, no job chaining)
- [x] Edge cases documented with expected behavior
- [x] Testing requirements map to ACs
