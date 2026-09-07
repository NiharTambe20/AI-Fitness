import os
from typing import Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_CORS_ORIGINS = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:5500",
    "http://localhost:8000",
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5500",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:8080"
]

class Settings(BaseSettings):
    """
    Application Settings configuration using pydantic-settings.
    Supports environment variables and .env file loading.
    """
    APP_NAME: str = "AI Fitness Backend"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Database Configuration
    DATABASE_URL: str = "sqlite:///./ai_fitness.db"

    # API Keys for Gemini / Google AI
    GEMINI_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None

    # Email & SMTP Configuration
    EMAIL_PROVIDER: str = "development"
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAIL_FROM: Optional[str] = None
    FITQUEST_FRONTEND_URL: str = "http://127.0.0.1:8080"
    FITQUEST_SECRET_KEY: Optional[str] = None

    # CORS Configuration: Supports comma-separated string or list from environment
    CORS_ORIGINS: Union[list[str], str] = DEFAULT_CORS_ORIGINS

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, list[str]]) -> list[str]:
        origins = list(DEFAULT_CORS_ORIGINS)
        if isinstance(v, str):
            custom = [o.strip() for o in v.split(",") if o.strip()]
            for origin in custom:
                if origin not in origins:
                    origins.append(origin)
            return origins
        elif isinstance(v, (list, tuple)):
            for origin in v:
                if isinstance(origin, str) and origin.strip() and origin.strip() not in origins:
                    origins.append(origin.strip())
            return origins
        return origins

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def effective_api_key(self) -> Optional[str]:
        return (
            self.GEMINI_API_KEY
            or self.GOOGLE_API_KEY
            or os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
        )

settings = Settings()
