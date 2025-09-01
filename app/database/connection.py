# app/database/connection.py
import asyncpg
import os
from typing import Optional
from dotenv import load_dotenv
import logging

# Ensure environment variables are loaded
load_dotenv()

logger = logging.getLogger(__name__)

class DatabaseConnection:
    _pool: Optional[asyncpg.Pool] = None
    
    @classmethod
    async def get_pool(cls) -> asyncpg.Pool:
        """Get or create database connection pool"""
        if cls._pool is None:
            try:
                db_url = os.getenv('DATABASE_URL')
                print(f"DEBUG: DATABASE_URL = {db_url}")
                
                if not db_url:
                    raise ValueError("DATABASE_URL environment variable not set")
                
                cls._pool = await asyncpg.create_pool(
                    db_url,
                    min_size=1,
                    max_size=10,
                    command_timeout=60
                )
                logger.info("Database connection pool created")
            except Exception as e:
                logger.error(f"Failed to create database pool: {e}")
                raise
        return cls._pool
    
    @classmethod
    async def close_pool(cls):
        """Close database connection pool"""
        if cls._pool:
            await cls._pool.close()
            cls._pool = None
            logger.info("Database connection pool closed")

async def get_db_connection():
    """Get database connection from pool"""
    pool = await DatabaseConnection.get_pool()
    return await pool.acquire()

async def release_db_connection(connection):
    """Release database connection back to pool"""
    pool = await DatabaseConnection.get_pool()
    await pool.release(connection)