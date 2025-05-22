#!/usr/bin/env python
import os
import sys
import asyncio
import uuid
import logging
import time

# Import both psycopg and asyncpg for comparative testing
import psycopg
from psycopg_pool import AsyncConnectionPool

try:
    import asyncpg
    HAVE_ASYNCPG = True
except ImportError:
    HAVE_ASYNCPG = False

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("db_connection_test")

# Get connection params from environment - same as chatServer/main.py
DB_USER = os.getenv("SUPABASE_DB_USER")
DB_PASSWORD = os.getenv("SUPABASE_DB_PASSWORD")
DB_HOST = os.getenv("SUPABASE_DB_HOST")
DB_NAME = os.getenv("SUPABASE_DB_NAME", "postgres")
DB_PORT = os.getenv("SUPABASE_DB_PORT", "5432")

# Check required parameters
if not all([DB_USER, DB_PASSWORD, DB_HOST]):
    logger.error("Missing required database parameters. Ensure SUPABASE_DB_USER, SUPABASE_DB_PASSWORD, and SUPABASE_DB_HOST are set.")
    sys.exit(1)

# Generate connection strings
def get_base_connection_params():
    return {
        "user": DB_USER,
        "password": DB_PASSWORD,
        "host": DB_HOST,
        "port": DB_PORT,
        "dbname": DB_NAME,
    }

# Basic psycopg direct connection test
async def test_psycopg_direct():
    logger.info("=== TEST 1: Basic psycopg direct connection ===")
    connection_string = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    masked_string = connection_string.replace(DB_PASSWORD, "[REDACTED]")
    logger.info(f"Connecting with: {masked_string}")
    
    try:
        conn = await psycopg.AsyncConnection.connect(
            connection_string,
            connect_timeout=10.0
        )
        logger.info("DIRECT CONNECTION SUCCESSFUL!")
        
        # Try a simple query
        async with conn.cursor() as cur:
            await cur.execute("SELECT 1 AS test")
            result = await cur.fetchone()
            logger.info(f"Query result: {result}")
        
        await conn.close()
        return True
    except Exception as e:
        logger.error(f"Direct connection failed: {e}")
        return False

# Test psycopg pool with transaction
async def test_psycopg_pool_with_transaction():
    logger.info("=== TEST 2: psycopg AsyncConnectionPool with transaction ===")
    connection_string = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    masked_string = connection_string.replace(DB_PASSWORD, "[REDACTED]")
    logger.info(f"Connecting pool with: {masked_string}")
    
    try:
        # Create a minimal connection pool
        pool = AsyncConnectionPool(
            conninfo=connection_string,
            min_size=1,
            max_size=2,
            timeout=30.0,  # Longer pool connection timeout
            kwargs={
                "connect_timeout": 10.0,  # Connection timeout in seconds
                "application_name": "test-psycopg-app",  # Helps identify in logs
            }
        )
        
        logger.info("Opening pool...")
        await pool.open()
        logger.info("Pool opened successfully!")
        
        # Wrap operations in a transaction
        logger.info("Testing pool connection with transaction...")
        conn = await pool.getconn()
        try:
            async with conn.transaction():
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1 AS test")
                    result = await cur.fetchone()
                    logger.info(f"Transaction query result: {result}")
            logger.info("Transaction completed successfully")
        finally:
            await pool.putconn(conn)
        
        await pool.close()
        logger.info("Pool closed successfully")
        return True
    except Exception as e:
        logger.error(f"Pool with transaction test failed: {e}")
        return False

# Test session mode connection
async def test_session_mode():
    logger.info("=== TEST 3: Session mode connection ===")
    
    # Extract project ID from DB_HOST
    if "supabase.co" in DB_HOST:
        # Original format: db.dsyakikfxlhjszyhlmaa.supabase.co
        # We need: dsyakikfxlhjszyhlmaa
        project_id = DB_HOST.replace("db.", "").replace(".supabase.co", "")
        
        # Session mode format: postgres.PROJECT_ID:PASSWORD@aws-0-REGION.pooler.supabase.com
        # We'll need to guess the region - often us-east-1 or us-west-1
        regions = ["us-east-1", "us-west-1", "eu-west-1", "ap-southeast-1"]
        
        for region in regions:
            session_host = f"aws-0-{region}.pooler.supabase.com"
            session_user = f"postgres.{project_id}"
            session_conn_str = f"postgresql://{session_user}:{DB_PASSWORD}@{session_host}:{DB_PORT}/{DB_NAME}"
            masked_str = session_conn_str.replace(DB_PASSWORD, "[REDACTED]")
            
            logger.info(f"Trying session mode region {region}: {masked_str}")
            
            try:
                conn = await psycopg.AsyncConnection.connect(
                    session_conn_str,
                    connect_timeout=10.0
                )
                logger.info(f"SESSION MODE CONNECTION SUCCESSFUL with region {region}!")
                
                # Try a simple query
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1 AS test")
                    result = await cur.fetchone()
                    logger.info(f"Query result: {result}")
                
                await conn.close()
                return True
            except Exception as e:
                logger.error(f"Session mode connection failed for region {region}: {e}")
        
        logger.error("All session mode connection attempts failed")
        return False
    else:
        logger.error(f"Host format '{DB_HOST}' doesn't appear to be a Supabase host")
        return False

# Test asyncpg if available (for comparison)
async def test_asyncpg():
    if not HAVE_ASYNCPG:
        logger.warning("asyncpg not installed, skipping comparison test")
        return False
    
    logger.info("=== TEST 4: asyncpg connection test ===")
    try:
        # Create the SQLAlchemy-compatible DSN that works with asyncpg
        dsn = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        
        # Connect with settings that should work with connection poolers
        conn = await asyncpg.connect(
            dsn,
            statement_cache_size=0,
            prepared_statement_cache_size=0,  # SQLAlchemy 2.0 setting
            command_timeout=10,
        )
        
        logger.info("ASYNCPG CONNECTION SUCCESSFUL!")
        
        # Try a simple query
        result = await conn.fetchrow("SELECT 1 AS test")
        logger.info(f"Query result: {result}")
        
        await conn.close()
        return True
    except Exception as e:
        logger.error(f"asyncpg connection failed: {e}")
        return False

async def main():
    logger.info("Starting database connection tests")
    
    results = {}
    
    # Run tests with timing
    for test_func in [
        test_psycopg_direct,
        test_psycopg_pool_with_transaction,
        test_session_mode,
        test_asyncpg
    ]:
        start_time = time.time()
        try:
            success = await test_func()
            elapsed = time.time() - start_time
            results[test_func.__name__] = {"success": success, "time": elapsed}
        except Exception as e:
            logger.error(f"Unexpected error in {test_func.__name__}: {e}")
            results[test_func.__name__] = {"success": False, "error": str(e)}
    
    # Print summary
    logger.info("\n=== TEST RESULTS SUMMARY ===")
    for name, result in results.items():
        success = result.get("success", False)
        time_taken = result.get("time", 0)
        error = result.get("error", "")
        
        status = "✅ PASSED" if success else f"❌ FAILED: {error}"
        logger.info(f"{name}: {status} ({time_taken:.2f}s)")

if __name__ == "__main__":
    asyncio.run(main()) 