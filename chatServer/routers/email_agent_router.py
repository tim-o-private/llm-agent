"""Router for Email Digest Agent endpoints."""
# @docs memory-bank/patterns/api-patterns.md#pattern-11-fastapi-project-structure
# @rules memory-bank/rules/api-rules.json#api-004

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..agents.email_digest_agent import EmailDigestAgent
from ..config.constants import DEFAULT_LOG_LEVEL
from ..dependencies.auth import get_current_user

# Import existing utilities
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))

from utils.config_loader import ConfigLoader
from utils.logging_utils import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/email-agent", tags=["email-agent"])


# Request/Response Models
class EmailDigestRequest(BaseModel):
    """Request model for email digest generation."""
    hours_back: int = Field(default=24, ge=1, le=168, description="Hours to look back for emails (1-168)")
    max_threads: int = Field(default=20, ge=1, le=100, description="Maximum number of email threads to analyze")
    include_read: bool = Field(default=False, description="Whether to include read emails")


class EmailSearchRequest(BaseModel):
    """Request model for email search."""
    query: str = Field(..., description="Gmail search query")
    max_results: int = Field(default=20, ge=1, le=100, description="Maximum number of search results")


class EmailAnalysisRequest(BaseModel):
    """Request model for email analysis."""
    analysis_request: str = Field(..., description="Description of the analysis to perform")


class EmailAgentResponse(BaseModel):
    """Response model for email agent operations."""
    success: bool
    result: str
    agent_info: Dict[str, Any]
    timestamp: str


# Dependency to get Email Digest Agent
async def get_email_agent(user_id: str = Depends(get_current_user)) -> EmailDigestAgent:
    """Get Email Digest Agent instance for the current user.

    Args:
        user_id: Current user ID

    Returns:
        EmailDigestAgent instance
    """
    try:
        # Create session ID based on user and current timestamp
        import uuid
        session_id = f"{user_id}:email_digest:{uuid.uuid4().hex[:8]}"

        # Initialize config loader
        config = ConfigLoader()

        # Create agent
        agent = EmailDigestAgent(
            user_id=user_id,
            session_id=session_id,
            config_loader=config
        )

        return agent

    except Exception as e:
        logger.error(f"Failed to create email agent for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize email agent: {e}"
        )


@router.post("/digest", response_model=EmailAgentResponse)
async def generate_email_digest(
    request: EmailDigestRequest,
    agent: EmailDigestAgent = Depends(get_email_agent)
):
    """Generate an email digest using the Email Digest Agent.

    Args:
        request: Email digest request parameters
        agent: Email Digest Agent instance

    Returns:
        Email digest response

    Raises:
        HTTPException: If digest generation fails
    """
    try:
        logger.info(f"Generating email digest for user {agent.user_id}")

        # Generate digest using the agent
        result = await agent.generate_digest(
            hours_back=request.hours_back,
            max_threads=request.max_threads,
            include_read=request.include_read
        )

        # Get agent info
        agent_info = agent.get_agent_info()

        return EmailAgentResponse(
            success=True,
            result=result,
            agent_info=agent_info,
            timestamp=str(datetime.now())
        )

    except Exception as e:
        logger.error(f"Error generating email digest: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate email digest: {e}"
        )


@router.post("/search", response_model=EmailAgentResponse)
async def search_emails(
    request: EmailSearchRequest,
    agent: EmailDigestAgent = Depends(get_email_agent)
):
    """Search emails using the Email Digest Agent.

    Args:
        request: Email search request parameters
        agent: Email Digest Agent instance

    Returns:
        Email search response

    Raises:
        HTTPException: If search fails
    """
    try:
        logger.info(f"Searching emails for user {agent.user_id}: {request.query}")

        # Search emails using the agent
        result = await agent.search_emails(
            query=request.query,
            max_results=request.max_results
        )

        # Get agent info
        agent_info = agent.get_agent_info()

        return EmailAgentResponse(
            success=True,
            result=result,
            agent_info=agent_info,
            timestamp=str(datetime.now())
        )

    except Exception as e:
        logger.error(f"Error searching emails: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search emails: {e}"
        )


@router.post("/analyze", response_model=EmailAgentResponse)
async def analyze_emails(
    request: EmailAnalysisRequest,
    agent: EmailDigestAgent = Depends(get_email_agent)
):
    """Analyze emails using the Email Digest Agent.

    Args:
        request: Email analysis request parameters
        agent: Email Digest Agent instance

    Returns:
        Email analysis response

    Raises:
        HTTPException: If analysis fails
    """
    try:
        logger.info(f"Analyzing emails for user {agent.user_id}: {request.analysis_request}")

        # Analyze emails using the agent
        result = await agent.analyze_emails(request.analysis_request)

        # Get agent info
        agent_info = agent.get_agent_info()

        return EmailAgentResponse(
            success=True,
            result=result,
            agent_info=agent_info,
            timestamp=str(datetime.now())
        )

    except Exception as e:
        logger.error(f"Error analyzing emails: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze emails: {e}"
        )


@router.get("/info")
async def get_agent_info(
    agent: EmailDigestAgent = Depends(get_email_agent)
):
    """Get information about the Email Digest Agent.

    Args:
        agent: Email Digest Agent instance

    Returns:
        Agent information
    """
    try:
        agent_info = agent.get_agent_info()

        return {
            "success": True,
            "agent_info": agent_info,
            "timestamp": str(datetime.now())
        }

    except Exception as e:
        logger.error(f"Error getting agent info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent info: {e}"
        )


@router.get("/health")
async def health_check():
    """Health check endpoint for the email agent service.

    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "service": "email-digest-agent",
        "timestamp": str(datetime.now())
    }
