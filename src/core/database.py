"""
Database configuration and session management.
Uses SQLAlchemy async engine for PostgreSQL.
"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from config.settings import get_settings
from src.core.exceptions import DatabaseError

logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,  # Log SQL queries in debug mode
    poolclass=NullPool if settings.is_development else None,
    pool_pre_ping=True,  # Verify connections before using
    pool_size=10 if not settings.is_development else 5,
    max_overflow=20 if not settings.is_development else 10,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for all models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI routes to get database session.
    
    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise DatabaseError(
                message="Database operation failed",
                details={"error": str(e)}
            )
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context():
    """
    Context manager for database sessions outside of FastAPI dependencies.
    
    Usage:
        async with get_db_context() as db:
            result = await db.execute(query)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database context error: {e}")
            raise DatabaseError(
                message="Database operation failed",
                details={"error": str(e)}
            )
        finally:
            await session.close()


async def init_db():
    """
    Initialize database (create all tables).
    Should only be used in development/testing.
    Use Alembic migrations in production.
    """
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise DatabaseError(
            message="Database initialization failed",
            details={"error": str(e)}
        )


async def close_db():
    """
    Close database connections.
    Call this on application shutdown.
    """
    try:
        await engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")


async def check_db_connection() -> bool:
    """
    Check if database connection is healthy.
    Used for health checks.
    """
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
