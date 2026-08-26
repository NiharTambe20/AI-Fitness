import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

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


    # CORS Configuration
    CORS_ORIGINS: list[str] = [
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
        "*"
    ]

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
