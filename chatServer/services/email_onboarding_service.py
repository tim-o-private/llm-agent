"""Email onboarding service — processes email to store memory insights."""

import logging
from typing import Any, Dict

from ..database.connection import get_database_manager
from ..database.supabase_client import create_system_client

logger = logging.getLogger(__name__)

ONBOARDING_PROMPT_TEMPLATE = (
    "You are reading through {email}'s recent email to understand their world.\n"
    "\n"
    "Your goal: learn who they interact with, what they're working on, and how they"
    " communicate — then store those insights as memories so you can be genuinely useful.\n"
    "\n"
    "## Step 1: Search their inbox\n"
    "\n"
    "Search their recent email (up to 50 results each):\n"
    '- search_gmail(query="newer_than:7d", max_results=50, account="{email}")\n'
    '- search_gmail(query="in:sent newer_than:7d", max_results=50, account="{email}")\n'
    "\n"
    "## Step 2: Deep-read high-signal emails\n"
    "\n"
    "For emails with action items, important decisions, or recurring contacts,"
    " use get_gmail to read the full body. Focus on:\n"
    "- Emails with clear action items or deadlines\n"
    "- Messages from recurring contacts (managers, clients, close collaborators)\n"
    "- Threads that reveal ongoing projects or commitments\n"
    "\n"
    "## Step 3: Store structured memory entries\n"
    "\n"
    "Use create_memories for each insight you find. Store entries in these categories:\n"
    "\n"
    "**Key relationships** (people who matter):\n"
    '- entity=<person full name>, memory_type="core_identity", scope="global",'
    ' tags=["relationship", <domain>]\n'
    '- Example: "Alice Chen is a project manager at Acme Corp.'
    ' Communicates frequently about Q1 roadmap."\n'
    "\n"
    "**Writing style** (how they communicate):\n"
    '- entity="writing_style", memory_type="core_identity", scope="global",'
    ' tags=["communication", "style"]\n'
    '- Example: "Uses direct, concise language. Rarely uses greetings.'
    ' Prefers bullet points."\n'
    "\n"
    "**Action items** (outstanding commitments):\n"
    '- entity=<source or project>, memory_type="episodic", scope="global",'
    ' tags=["action_item", <domain>]\n'
    '- Example: "Needs to send project proposal to Bob by Friday'
    ' (from email dated 2026-02-20)."\n'
    "\n"
    "**Life context** (institutions, ongoing projects, situations):\n"
    '- entity=<institution or topic>, memory_type="core_identity", scope="global",'
    " tags=[<domain>]\n"
    '- Example: "Works at TechCorp on the mobile team. Currently in Q1 planning cycle."\n'
    "\n"
    "**Recurring patterns** (habits, regular communications):\n"
    '- entity=<source>, memory_type="project_context", scope="global",'
    ' tags=["pattern", <type>]\n'
    '- Example: "Receives weekly status reports from the engineering team every Monday."\n'
    "\n"
    "Store as many memories as are genuinely useful. Quality over quantity.\n"
    "\n"
    "## Step 4: Produce a summary\n"
    "\n"
    "End with:\n"
    "- Relationships identified: N\n"
    "- Action items found: N\n"
    "- Patterns noticed: N\n"
    "- Key context stored: <1-2 sentence summary of the most important things you learned>\n"
    "\n"
    "Does this sound right? Am I missing anything important?"
)


class EmailOnboardingService:
    """Orchestrates email onboarding: triggers agent to process email and store insights."""

    DEFAULT_MODEL = "claude-sonnet-4-5-20250514"

    async def process_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single email onboarding job.

        Args:
            job: Dict with keys: id, user_id, connection_id, status

        Returns:
            Dict with success, output, error keys
        """
        user_id = job["user_id"]
        connection_id = job["connection_id"]
        job_id = job["id"]

        try:
            # 1. Get connection details (account email)
            account_email = await self._get_account_email(connection_id)

            # 2. Build onboarding prompt
            onboarding_prompt = ONBOARDING_PROMPT_TEMPLATE.format(email=account_email)

            # 3. Call ScheduledExecutionService.execute() with synthetic schedule
            from .scheduled_execution_service import ScheduledExecutionService

            service = ScheduledExecutionService()
            schedule = {
                "id": job_id,
                "user_id": user_id,
                "agent_name": "assistant",
                "prompt": onboarding_prompt,
                "config": {
                    "model_override": self.DEFAULT_MODEL,
                    "schedule_type": "scheduled",
                    "skip_notification": True,
                },
            }
            result = await service.execute(schedule)

            output = result.get("output", "")

            # 4. Send custom onboarding notification (AC-08, AC-10)
            await self._notify(user_id, output)

            return {"success": True, "output": output}

        except Exception as e:
            logger.error(
                f"Email onboarding job {job_id} failed for user {user_id}: {e}",
                exc_info=True,
            )
            return {"success": False, "error": str(e)}

    async def _get_account_email(self, connection_id: str) -> str:
        """Fetch service_user_email for a given connection_id."""
        db_manager = get_database_manager()
        async with db_manager.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT service_user_email FROM external_api_connections WHERE id = %s",
                    (connection_id,),
                )
                row = await cur.fetchone()
                if not row or not row[0]:
                    raise ValueError(f"No email found for connection {connection_id}")
                return row[0]

    async def _notify(self, user_id: str, output: str) -> None:
        """Send onboarding completion notification."""
        try:
            from ..services.notification_service import NotificationService

            db_client = await create_system_client()
            notification_service = NotificationService(db_client)
            body = output[:2000] if output else "Email scan complete."
            await notification_service.notify_user(
                user_id=user_id,
                title="I've read through your email.",
                body=body,
                category="agent_result",
            )
        except Exception as e:
            logger.warning(
                f"Failed to send onboarding notification for user {user_id}: {e}"
            )
