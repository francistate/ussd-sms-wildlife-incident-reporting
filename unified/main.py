"""
Unified Wildlife Reporting App
Combines USSD and SMS functionality in a single server
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from config import settings
from database.connection import init_database, check_connection
from database.repository import USSDReportRepository, SMSReportRepository
from sms_services.sms_service import init_sms_service
from api.routes import sms_router
from api.ussd_routes import ussd_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Suppress noisy loggers
for logger_name in ["sqlalchemy.engine", "httpx", "httpcore"]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    logger.info("Starting Unified SMS & USSD Wildlife Reporting App...")

    # Initialize database
    try:
        init_database()
        if check_connection():
            logger.info("Database connected successfully")
        else:
            logger.warning("Database connection failed - using file backup")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")

    # Initialize SMS service
    try:
        init_sms_service()
        logger.info("SMS service initialized")
    except Exception as e:
        logger.warning(f"SMS service not available: {e}")

    yield

    logger.info("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Wildlife Conservation Reporting API",
    description="Unified USSD and SMS wildlife incident reporting system",
    version="2.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ussd_router)  # /ussd endpoints
app.include_router(sms_router)   # /sms endpoints


# ============ ROOT ENDPOINTS ============

@app.get("/")
async def root():
    """Health check and service info"""
    from database.connection import get_db
    from sms_services.sms_service import get_sms_service

    db_ok = check_connection()
    sms = get_sms_service()

    ussd_stats = {}
    sms_stats = {}

    if db_ok:
        try:
            with get_db() as db:
                ussd_repo = USSDReportRepository(db)
                sms_repo = SMSReportRepository(db)
                ussd_stats = ussd_repo.get_stats()
                sms_stats = sms_repo.get_stats()
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")

    return {
        "service": "Wildlife Conservation Reporting API",
        "version": "2.0.0",
        "status": "running",
        "channels": {
            "ussd": {
                "enabled": True,
                "endpoint": "/ussd"
            },
            "sms": {
                "enabled": sms is not None,
                "endpoint": "/sms/incoming"
            }
        },
        "database": {
            "connected": db_ok,
            "ussd_stats": ussd_stats,
            "sms_stats": sms_stats
        },
        "environment": settings.environment
    }


@app.get("/health")
async def health():
    """Simple health check"""
    return {
        "status": "healthy",
        "database": check_connection()
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
