import os
from pathlib import Path


class Config:
    """Base application configuration."""
    BASE_DIR = Path(__file__).resolve().parent
    SOURCES_DIR = os.getenv("SOURCES_DIR", str(BASE_DIR / "sources"))
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 32 * 1024 * 1024))  # 32 MB
    WEB_SEARCH_TIMEOUT = int(os.getenv("WEB_SEARCH_TIMEOUT", 4))
    PORT = int(os.getenv("PORT", 5001))
    HOST = os.getenv("HOST", "127.0.0.1")
    DEBUG = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")
    SECRET_KEY = os.getenv("SECRET_KEY", "plagiarism-pro-secret-key-2026")
    ADMIN_PIN = os.getenv("ADMIN_PIN", "1234")


class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True


class TestingConfig(Config):
    """Testing environment configuration."""
    TESTING = True
    DEBUG = False
    WEB_SEARCH_TIMEOUT = 2


class ProductionConfig(Config):
    """Production environment configuration."""
    DEBUG = False
