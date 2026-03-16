"""
Wildlife Conservation USSD API
Main FastAPI Application
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from config import settings
from api.routes import router
from database.connection import init_database, check_connection

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

# Suppress noisy loggers
logging.getLogger("sqlalchemy").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    logger.info("Starting Wildlife Conservation USSD API...")

    try:
        if init_database():
            logger.info("Database initialized successfully")
        else:
            logger.warning("Database initialization failed")
    except Exception as e:
        logger.error(f"Database error: {e}")
        logger.warning("Continuing without database")

    logger.info(f"USSD API running in {settings.environment} mode")

    yield

    # Shutdown
    logger.info("Shutting down USSD API...")


# Create FastAPI app
app = FastAPI(
    title="Wildlife Conservation USSD API",
    description="""
    USSD-based wildlife incident reporting system.

    ## Features
    - Emergency incident reporting
    - Wildlife sighting logging
    - Past incident reporting
    - Multiple incident types supported

    ## How it works
    1. User dials USSD code
    2. Navigates through menu options
    3. Report is saved to database
    4. Rangers are notified for high-priority incidents
    """,
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main_new:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
