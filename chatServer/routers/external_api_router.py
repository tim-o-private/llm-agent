"""Router for external API connections and email digest endpoints."""
# @docs memory-bank/patterns/api-patterns.md#pattern-11-fastapi-project-structure
# @rules memory-bank/rules/api-rules.json#api-004

import logging
from typing import List

import psycopg
from fastapi import APIRouter, Depends, HTTPException, status

from ..database.connection import get_db_connection
from ..dependencies.auth import get_current_user
from ..models.external_api import (
    ExternalAPIConnectionCreate,
    ExternalAPIConnectionResponse,
    ExternalAPIConnectionUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/external", tags=["external-api"])




@router.post("/connections", response_model=ExternalAPIConnectionResponse)
async def create_api_connection(
    connection_data: ExternalAPIConnectionCreate,
    user_id: str = Depends(get_current_user),
    db_conn: psycopg.AsyncConnection = Depends(get_db_connection)
):
    """Create a new external API connection.

    Args:
        connection_data: Connection data
        user_id: Current user ID
        db_conn: Database connection

    Returns:
        Created connection response

    Raises:
        HTTPException: If connection creation fails
    """
    try:
        async with db_conn.cursor() as cur:
            # Insert connection (will update if exists due to unique constraint)
            await cur.execute(
                """
                INSERT INTO external_api_connections
                (user_id, service_name, service_user_email, access_token, refresh_token,
                 token_expires_at, scopes, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id, service_name) DO UPDATE SET
                    service_user_email = EXCLUDED.service_user_email,
                    access_token = EXCLUDED.access_token,
                    refresh_token = EXCLUDED.refresh_token,
                    token_expires_at = EXCLUDED.token_expires_at,
                    scopes = EXCLUDED.scopes,
                    is_active = EXCLUDED.is_active,
                    updated_at = NOW()
                RETURNING *
                """,
                (
                    user_id,
                    connection_data.service_name,
                    connection_data.service_user_email,
                    connection_data.access_token,
                    connection_data.refresh_token,
                    connection_data.token_expires_at,
                    connection_data.scopes,
                    True
                )
            )

            result = await cur.fetchone()
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create API connection"
                )

            # Convert row to dict
            columns = [desc[0] for desc in cur.description]
            connection_dict = dict(zip(columns, result))
            return ExternalAPIConnectionResponse(**connection_dict)

    except Exception as e:
        logger.error(f"Error creating API connection for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create API connection"
        )


@router.get("/connections", response_model=List[ExternalAPIConnectionResponse])
async def get_api_connections(
    user_id: str = Depends(get_current_user),
    db_conn: psycopg.AsyncConnection = Depends(get_db_connection)
):
    """Get all API connections for the current user.

    Args:
        user_id: Current user ID
        db_conn: Database connection

    Returns:
        List of user's API connections
    """
    try:
        async with db_conn.cursor() as cur:
            await cur.execute(
                """
                SELECT * FROM external_api_connections
                WHERE user_id = %s AND is_active = %s
                """,
                (user_id, True)
            )

            results = await cur.fetchall()
            columns = [desc[0] for desc in cur.description]

            connections = []
            for row in results:
                connection_dict = dict(zip(columns, row))
                connections.append(ExternalAPIConnectionResponse(**connection_dict))

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
    db_conn: psycopg.AsyncConnection = Depends(get_db_connection)
):
    """Get a specific API connection for the current user.

    Args:
        service_name: Name of the service
        user_id: Current user ID
        db_conn: Database connection

    Returns:
        API connection response

    Raises:
        HTTPException: If connection not found
    """
    try:
        async with db_conn.cursor() as cur:
            await cur.execute(
                """
                SELECT * FROM external_api_connections
                WHERE user_id = %s AND service_name = %s AND is_active = %s
                """,
                (user_id, service_name, True)
            )

            result = await cur.fetchone()
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No active connection found for service {service_name}"
                )

            columns = [desc[0] for desc in cur.description]
            connection_dict = dict(zip(columns, result))
            return ExternalAPIConnectionResponse(**connection_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting API connection for user {user_id}, service {service_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve API connection"
        )


@router.get("/connections/{service_name}/status")
async def get_connection_status(
    service_name: str,
    user_id: str = Depends(get_current_user),
    db_conn: psycopg.AsyncConnection = Depends(get_db_connection)
):
    """Get connection status for a specific service.

    Args:
        service_name: Name of the service (e.g., 'gmail')
        user_id: Current user ID
        db_conn: Database connection

    Returns:
        Simple connection status
    """
    try:
        async with db_conn.cursor() as cur:
            await cur.execute(
                """
                SELECT COUNT(*) FROM external_api_connections
                WHERE user_id = %s AND service_name = %s AND is_active = %s
                """,
                (user_id, service_name, True)
            )

            result = await cur.fetchone()
            is_connected = result[0] > 0 if result else False

            return {"connected": is_connected, "service": service_name}

    except Exception as e:
        logger.error(f"Error checking connection status for user {user_id}, service {service_name}: {e}")
        return {"connected": False, "service": service_name, "error": "Failed to check status"}


@router.put("/connections/{service_name}", response_model=ExternalAPIConnectionResponse)
async def update_api_connection(
    service_name: str,
    connection_update: ExternalAPIConnectionUpdate,
    user_id: str = Depends(get_current_user),
    db_conn: psycopg.AsyncConnection = Depends(get_db_connection)
):
    """Update an existing API connection.

    Args:
        service_name: Name of the service
        connection_update: Connection update data
        user_id: Current user ID
        db_conn: Database connection

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

        async with db_conn.cursor() as cur:
            # Build dynamic update query
            set_clauses = []
            values = []
            for field, value in update_data.items():
                set_clauses.append(f"{field} = %s")
                values.append(value)

            # Add updated_at
            set_clauses.append("updated_at = NOW()")
            values.extend([user_id, service_name])

            await cur.execute(
                f"""
                UPDATE external_api_connections
                SET {', '.join(set_clauses)}
                WHERE user_id = %s AND service_name = %s
                RETURNING *
                """,
                values
            )

            result = await cur.fetchone()
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No connection found for service {service_name}"
                )

            columns = [desc[0] for desc in cur.description]
            connection_dict = dict(zip(columns, result))
            return ExternalAPIConnectionResponse(**connection_dict)

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
    db_conn: psycopg.AsyncConnection = Depends(get_db_connection)
):
    """Delete (deactivate) an API connection.

    Args:
        service_name: Name of the service
        user_id: Current user ID
        db_conn: Database connection

    Returns:
        Success message

    Raises:
        HTTPException: If connection not found or deletion fails
    """
    try:
        async with db_conn.cursor() as cur:
            # Soft delete by setting is_active to False
            await cur.execute(
                """
                UPDATE external_api_connections
                SET is_active = %s, updated_at = NOW()
                WHERE user_id = %s AND service_name = %s
                RETURNING *
                """,
                (False, user_id, service_name)
            )

            result = await cur.fetchone()
            if not result:
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


