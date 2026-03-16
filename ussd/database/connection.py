"""
Database connection management for USSD App
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
import logging

from config import settings

logger = logging.getLogger(__name__)

# Create engine with connection pooling
engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
    connect_args={
        "sslmode": "require",
        "application_name": "ussd-backend",
    }
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db() -> Session:
    """Get database session with automatic cleanup"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db_session() -> Session:
    """Get database session (for FastAPI dependency injection)"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_connection() -> bool:
    """Check if database connection is working"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


def init_database():
    """Initialize database tables and extensions"""
    from database.models import Base

    try:
        with engine.begin() as conn:
            # Enable required extensions
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
            conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
            logger.info("Database extensions enabled")

        # Create tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created")

        # Create indexes
        _create_indexes()

        return True
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False


def _create_indexes():
    """Create additional indexes for performance"""
    try:
        with engine.begin() as conn:
            # Spatial index on location
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_ussd_reports_location_gist
                ON ussd_reports USING GIST (location);
            """))

            # Full-text search indexes
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_ussd_reports_species_fts
                ON ussd_reports USING GIN (to_tsvector('english', species));
            """))

            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_ussd_reports_location_name_fts
                ON ussd_reports USING GIN (to_tsvector('english', location_name));
            """))

            # Composite index for common queries
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_ussd_reports_status_priority
                ON ussd_reports(status, priority);
            """))

            logger.info("Database indexes created")
    except Exception as e:
        logger.warning(f"Index creation failed (non-critical): {e}")
