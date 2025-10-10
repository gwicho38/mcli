"""Database session management"""

from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, StaticPool

from mcli.ml.config import settings

from .models import Base

# Synchronous database setup
# Prioritize DATABASE_URL environment variable over settings
import os
database_url = os.getenv("DATABASE_URL")

# Check if DATABASE_URL has placeholder password
if database_url and "your_password" in database_url:
    database_url = None  # Treat placeholder as not set

# If no DATABASE_URL or it's SQLite from settings, try explicit configuration
if not database_url:
    try:
        # Check if settings has a non-SQLite configuration
        settings_url = settings.database.url
        if settings_url and "sqlite" not in settings_url:
            database_url = settings_url
    except (AttributeError, Exception):
        pass  # Continue with database_url=None

# If still no valid DATABASE_URL, try to use Supabase REST API via connection pooler
if not database_url:
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if supabase_url and supabase_service_key and "supabase.co" in supabase_url:
        # Extract project reference from Supabase URL
        # Format: https://PROJECT_REF.supabase.co
        project_ref = supabase_url.replace("https://", "").replace("http://", "").split(".")[0]

        # Use Supabase IPv4-only connection pooler
        # This avoids IPv6 connectivity issues on Streamlit Cloud
        # Try EU region poolers (which are verified to work for this project)
        # Session mode (port 5432) for persistent connections
        # Transaction mode (port 6543) for serverless/short-lived connections
        pooler_urls = [
            f"postgresql://postgres.{project_ref}:{supabase_service_key}@aws-1-eu-north-1.pooler.supabase.com:5432/postgres",
            f"postgresql://postgres.{project_ref}:{supabase_service_key}@aws-1-eu-north-1.pooler.supabase.com:6543/postgres",
        ]

        # Try to connect to poolers
        import logging
        logger = logging.getLogger(__name__)

        for pooler_url in pooler_urls:
            try:
                # Test connection
                test_engine = create_engine(pooler_url, pool_pre_ping=True)
                with test_engine.connect() as conn:
                    from sqlalchemy import text
                    conn.execute(text("SELECT 1"))
                database_url = pooler_url
                logger.info(f"Successfully connected via pooler: {pooler_url.split('@')[1].split(':')[0]}")
                test_engine.dispose()
                break
            except Exception as e:
                logger.warning(f"Failed to connect via {pooler_url.split('@')[1].split(':')[0]}: {e}")
                continue

        if not database_url:
            # Fallback to first pooler URL if all fail (will be handled by pool_pre_ping later)
            database_url = pooler_urls[0]

        import warnings
        warnings.warn(
            "Using Supabase connection pooler with service role key. "
            "For better performance, set DATABASE_URL with your actual database password. "
            "Find it in Supabase Dashboard → Settings → Database → Connection String"
        )
    else:
        # Default to SQLite for development/testing
        database_url = "sqlite:///./ml_system.db"
        import warnings
        warnings.warn(
            "No database credentials found. Using SQLite fallback. "
            "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY or DATABASE_URL in environment."
        )

# Debug: Log which database URL is being used
import logging
logger = logging.getLogger(__name__)

if "pooler.supabase.com" in database_url:
    logger.info(f"🔗 Using Supabase connection pooler")
elif "sqlite" in database_url:
    logger.warning("📁 Using SQLite fallback (database features limited)")
else:
    # Mask password in display
    display_url = database_url
    if "@" in display_url and ":" in display_url:
        parts = display_url.split("@")
        before_at = parts[0].split(":")
        if len(before_at) >= 3:
            before_at[2] = "***"
            display_url = ":".join(before_at) + "@" + parts[1]
    logger.info(f"🔗 Database URL: {display_url}")

# Configure connection arguments based on database type
if "sqlite" in database_url:
    connect_args = {"check_same_thread": False}
elif "postgresql" in database_url:
    # Force IPv4 for PostgreSQL to avoid IPv6 connection issues
    connect_args = {
        "connect_timeout": 10,
        "options": "-c statement_timeout=30000",  # 30 second query timeout
    }
else:
    connect_args = {}

engine = create_engine(
    database_url,
    connect_args=connect_args,
    pool_pre_ping=True,  # Verify connections before using them
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_size=5,  # Smaller pool for Streamlit Cloud
    max_overflow=10,
    pool_timeout=30,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


# Asynchronous database setup
try:
    async_engine = create_async_engine(
        settings.database.async_url,
        pool_size=settings.database.pool_size,
        max_overflow=settings.database.max_overflow,
        pool_timeout=settings.database.pool_timeout,
        pool_pre_ping=True,
        echo=settings.debug,
    )
except (AttributeError, Exception):
    # Fallback for async engine
    import os
    async_database_url = os.getenv("ASYNC_DATABASE_URL")
    if not async_database_url:
        # Convert sync URL to async if possible
        if "sqlite" in database_url:
            async_database_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
        else:
            async_database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")

    async_engine = create_async_engine(
        async_database_url,
        pool_pre_ping=True,
    )

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for getting database session.

    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Async dependency for getting database session.

    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_async_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Context manager for database session with improved error handling.

    Usage:
        with get_session() as session:
            user = session.query(User).first()

    Raises:
        ConnectionError: If database connection cannot be established
        Exception: For other database errors
    """
    session = None
    try:
        session = SessionLocal()
        # Test the connection
        from sqlalchemy import text
        session.execute(text("SELECT 1"))
        yield session
        session.commit()
    except Exception as e:
        if session:
            session.rollback()
        # Provide more helpful error messages
        error_msg = str(e).lower()
        if "cannot assign requested address" in error_msg or "ipv6" in error_msg:
            raise ConnectionError(
                "Database connection failed due to network issues. "
                "This may be an IPv6 connectivity problem. "
                "Please ensure DATABASE_URL uses connection pooler (pooler.supabase.com) instead of direct connection (db.supabase.co). "
                f"Original error: {e}"
            )
        elif "authentication failed" in error_msg or "password" in error_msg:
            raise ConnectionError(
                "Database authentication failed. Please check your database credentials. "
                f"Original error: {e}"
            )
        else:
            raise
    finally:
        if session:
            session.close()


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager for database session.

    Usage:
        async with get_async_session() as session:
            result = await session.execute(select(User))
            users = result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def init_db() -> None:
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)

    # Create additional indexes
    from .models import create_indexes

    create_indexes(engine)


async def init_async_db() -> None:
    """Initialize database tables asynchronously"""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def drop_db() -> None:
    """Drop all database tables (use with caution!)"""
    Base.metadata.drop_all(bind=engine)


async def drop_async_db() -> None:
    """Drop all database tables asynchronously"""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# Test database setup (for unit tests)
def get_test_engine():
    """Create test database engine with in-memory SQLite"""
    from sqlalchemy import create_engine

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(bind=engine)
    return engine


def get_test_session():
    """Create test database session"""
    engine = get_test_engine()
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return TestSessionLocal()


# Database health check
async def check_database_health() -> bool:
    """Check if database is accessible and healthy"""
    try:
        async with get_async_session() as session:
            await session.execute("SELECT 1")
            return True
    except Exception as e:
        print(f"Database health check failed: {e}")
        return False


# Utility functions for bulk operations
async def bulk_insert(model_class, data: list) -> None:
    """Bulk insert data into database"""
    async with get_async_session() as session:
        session.add_all([model_class(**item) for item in data])
        await session.commit()


async def bulk_update(model_class, data: list, key_field: str = "id") -> None:
    """Bulk update data in database"""
    async with get_async_session() as session:
        for item in data:
            key_value = item.pop(key_field)
            await session.execute(
                model_class.__table__.update()
                .where(getattr(model_class, key_field) == key_value)
                .values(**item)
            )
        await session.commit()
