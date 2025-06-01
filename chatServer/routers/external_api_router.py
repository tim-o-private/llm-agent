"""Router for external API connections and email digest endpoints."""
# @docs memory-bank/patterns/api-patterns.md#pattern-11-fastapi-project-structure
# @rules memory-bank/rules/api-rules.json#api-004

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import AsyncClient

try:
    from ..dependencies.auth import get_current_user
    from ..database.supabase_client import get_supabase_client
    from ..models.external_api import (
        ExternalAPIConnectionCreate, ExternalAPIConnectionUpdate, 
        ExternalAPIConnectionResponse, EmailDigestRequest, EmailDigestResponse
    )
    from ..services.email_digest_service import EmailDigestService
except ImportError:
    from chatServer.dependencies.auth import get_current_user
    from chatServer.database.supabase_client import get_supabase_client
    from chatServer.models.external_api import (
        ExternalAPIConnectionCreate, ExternalAPIConnectionUpdate,
        ExternalAPIConnectionResponse, EmailDigestRequest, EmailDigestResponse
    )
    from chatServer.services.email_digest_service import EmailDigestService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/external", tags=["external-api"])


def get_email_digest_service(db: AsyncClient = Depends(get_supabase_client)) -> EmailDigestService:
    """Get email digest service instance.
    
    Args:
        db: Supabase client
        
    Returns:
        EmailDigestService instance
    """
    return EmailDigestService(db)


@router.post("/connections", response_model=ExternalAPIConnectionResponse)
async def create_api_connection(
    connection_data: ExternalAPIConnectionCreate,
    user_id: str = Depends(get_current_user),
    db: AsyncClient = Depends(get_supabase_client)
):
    """Create a new external API connection.
    
    Args:
        connection_data: Connection data
        user_id: Current user ID
        db: Supabase client
        
    Returns:
        Created connection response
        
    Raises:
        HTTPException: If connection creation fails
    """
    try:
        # Prepare connection data
        insert_data = connection_data.model_dump()
        insert_data['user_id'] = user_id
        
        # Insert connection (will update if exists due to unique constraint)
        result = await db.table('external_api_connections').upsert(
            insert_data,
            on_conflict='user_id,service_name'
        ).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create API connection"
            )
        
        connection_response = result.data[0]
        return ExternalAPIConnectionResponse(**connection_response)
        
    except Exception as e:
        logger.error(f"Error creating API connection for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create API connection"
        )


@router.get("/connections", response_model=List[ExternalAPIConnectionResponse])
async def get_api_connections(
    user_id: str = Depends(get_current_user),
    db: AsyncClient = Depends(get_supabase_client)
):
    """Get all API connections for the current user.
    
    Args:
        user_id: Current user ID
        db: Supabase client
        
    Returns:
        List of user's API connections
    """
    try:
        result = await db.table('external_api_connections').select('*').eq(
            'user_id', user_id
        ).eq('is_active', True).execute()
        
        connections = []
        for connection_data in result.data:
            connections.append(ExternalAPIConnectionResponse(**connection_data))
        
        return connections
        
    except Exception as e:
        logger.error(f"Error getting API connections for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve API connections"
        )


@router.get("/connections/{service_name}", response_model=ExternalAPIConnectionResponse)
async def get_api_connection(
    service_name: str,
    user_id: str = Depends(get_current_user),
    db: AsyncClient = Depends(get_supabase_client)
):
    """Get a specific API connection for the current user.
    
    Args:
        service_name: Name of the service
        user_id: Current user ID
        db: Supabase client
        
    Returns:
        API connection response
        
    Raises:
        HTTPException: If connection not found
    """
    try:
        result = await db.table('external_api_connections').select('*').eq(
            'user_id', user_id
        ).eq('service_name', service_name).eq('is_active', True).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No active connection found for service {service_name}"
            )
        
        connection_data = result.data[0]
        return ExternalAPIConnectionResponse(**connection_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting API connection for user {user_id}, service {service_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve API connection"
        )


@router.put("/connections/{service_name}", response_model=ExternalAPIConnectionResponse)
async def update_api_connection(
    service_name: str,
    connection_update: ExternalAPIConnectionUpdate,
    user_id: str = Depends(get_current_user),
    db: AsyncClient = Depends(get_supabase_client)
):
    """Update an existing API connection.
    
    Args:
        service_name: Name of the service
        connection_update: Connection update data
        user_id: Current user ID
        db: Supabase client
        
    Returns:
        Updated connection response
        
    Raises:
        HTTPException: If connection not found or update fails
    """
    try:
        # Only update fields that are provided
        update_data = connection_update.model_dump(exclude_unset=True)
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No update data provided"
            )
        
        result = await db.table('external_api_connections').update(
            update_data
        ).eq('user_id', user_id).eq('service_name', service_name).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No connection found for service {service_name}"
            )
        
        connection_data = result.data[0]
        return ExternalAPIConnectionResponse(**connection_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating API connection for user {user_id}, service {service_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update API connection"
        )


@router.delete("/connections/{service_name}")
async def delete_api_connection(
    service_name: str,
    user_id: str = Depends(get_current_user),
    db: AsyncClient = Depends(get_supabase_client)
):
    """Delete (deactivate) an API connection.
    
    Args:
        service_name: Name of the service
        user_id: Current user ID
        db: Supabase client
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If connection not found or deletion fails
    """
    try:
        # Soft delete by setting is_active to False
        result = await db.table('external_api_connections').update(
            {'is_active': False}
        ).eq('user_id', user_id).eq('service_name', service_name).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No connection found for service {service_name}"
            )
        
        return {"message": f"API connection for {service_name} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting API connection for user {user_id}, service {service_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete API connection"
        )


@router.get("/connections/{service_name}/test")
async def test_api_connection(
    service_name: str,
    user_id: str = Depends(get_current_user),
    email_digest_service: EmailDigestService = Depends(get_email_digest_service)
):
    """Test an API connection.
    
    Args:
        service_name: Name of the service
        user_id: Current user ID
        email_digest_service: Email digest service
        
    Returns:
        Test result
        
    Raises:
        HTTPException: If service not supported or test fails
    """
    try:
        if service_name == "gmail":
            async with email_digest_service:
                is_working = await email_digest_service.test_gmail_connection(user_id)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Testing not supported for service {service_name}"
            )
        
        return {
            "service_name": service_name,
            "is_working": is_working,
            "message": "Connection is working" if is_working else "Connection failed"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing API connection for user {user_id}, service {service_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test API connection"
        )


@router.post("/email/digest", response_model=EmailDigestResponse)
async def generate_email_digest(
    digest_request: EmailDigestRequest,
    user_id: str = Depends(get_current_user),
    email_digest_service: EmailDigestService = Depends(get_email_digest_service)
):
    """Generate an email digest for the current user.
    
    Args:
        digest_request: Email digest request parameters
        user_id: Current user ID
        email_digest_service: Email digest service
        
    Returns:
        Generated email digest
        
    Raises:
        HTTPException: If digest generation fails
    """
    try:
        async with email_digest_service:
            digest = await email_digest_service.generate_digest(user_id, digest_request)
        
        if not digest:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate email digest"
            )
        
        return digest
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating email digest for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate email digest"
        ) 