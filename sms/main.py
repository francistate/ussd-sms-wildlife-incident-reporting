"""
Wildlife Conservation SMS API
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
from services.sms_service import init_sms_service, get_sms_service

# Configure logging - cleaner format
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

# Suppress noisy loggers
logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown"""
    # Startup
    logger.info("Starting Wildlife Conservation SMS API...")

    # Initialize database
    try:
        if init_database():
            logger.info("Database initialized successfully")
        else:
            logger.warning("Database initialization failed, continuing anyway")
    except Exception as e:
        logger.error(f"Database error: {e}")
        logger.warning("Continuing without database")

    # Initialize SMS service
    try:
        init_sms_service()
        logger.info("SMS Service initialized")
    except Exception as e:
        logger.error(f"SMS Service initialization failed: {e}")
        logger.warning("Continuing without SMS support")

    logger.info(f"SMS API running in {settings.environment} mode")

    yield

    # Shutdown
    logger.info("Shutting down SMS API...")


# Create FastAPI app
app = FastAPI(
    title="Wildlife Conservation SMS API",
    description="""
    SMS-based wildlife incident reporting system.

    ## Features
    - Receive and parse free-form SMS reports using NLP
    - Send incident confirmations to reporters
    - Alert rangers for high-priority incidents

    ## How it works
    1. User sends SMS describing wildlife incident
    2. System extracts: species, incident type, location, severity
    3. If confident: creates report and sends confirmation
    4. If uncertain: asks user to send clearer message
    5. Rangers alerted for high/critical priority incidents
    """,
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router)


# Additional root endpoint with more info
@app.get("/health")
async def detailed_health():
    """Detailed health check"""
    sms = get_sms_service()
    db_ok = check_connection()

    return {
        "service": "Wildlife Conservation SMS API",
        "version": "2.0.0",
        "status": "healthy" if (sms and db_ok) else "degraded",
        "components": {
            "sms_service": "up" if sms else "down",
            "database": "up" if db_ok else "down"
        },
        "config": {
            "environment": settings.environment,
            "sms_username": settings.at_username,
            "confidence_high": settings.confidence_threshold_high,
            "confidence_low": settings.confidence_threshold_low,
            "hf_model": settings.hf_model_id,
            "hf_use_api": settings.hf_use_api
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
