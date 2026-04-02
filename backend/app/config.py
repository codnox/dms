from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List
import os
import secrets
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Distribution Management System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
    
    # Server
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = 8080
    
    # Database - SQLite
    DATABASE_PATH: str = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dms.db")
    
    # Security
    SECRET_KEY: str = secrets.token_urlsafe(64)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    CSRF_COOKIE_NAME: str = "csrftoken"
    CSRF_COOKIE_SECURE: bool = os.getenv(
        "CSRF_COOKIE_SECURE",
        "true" if os.getenv("ENVIRONMENT", "production").lower() == "production" else "false",
    ).lower() == "true"
    ENFORCE_HTTPS: bool = os.getenv("ENFORCE_HTTPS", "false").lower() == "true"
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3002"
    
    # API
    API_V1_PREFIX: str = "/api"
    
    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        if len(value) < 32 or "dms" in value.lower():
            raise ValueError(
                "SECRET_KEY must be at least 32 characters and must not contain default patterns. "
                "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
            )
        return value
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
