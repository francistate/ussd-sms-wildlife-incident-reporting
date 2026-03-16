"""
Configuration management for SMS App
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Database
    database_url: str = "postgresql://localhost/wildlife"

    # Africa's Talking
    at_username: str = "sandbox"
    at_api_key: str = ""
    at_shortcode: Optional[str] = None

    # Hugging Face (for LLM fallback)
    hf_api_token: Optional[str] = None
    hf_model_id: str = "google/flan-t5-small"  # Small, fast model
    hf_use_api: bool = True  # Use API (True) or local model (False)

    # Application
    debug: bool = True
    environment: str = "development"
    host: str = "0.0.0.0"
    port: int = 8001
    log_level: str = "INFO"

    # NLP Settings
    confidence_threshold_high: float = 0.80  # Auto-create report
    confidence_threshold_low: float = 0.50   # Needs review / ask clarification
    session_timeout_minutes: int = 30

    # Notification Settings
    alert_priority_threshold: list = ["high", "critical"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Convenience access
settings = get_settings()
