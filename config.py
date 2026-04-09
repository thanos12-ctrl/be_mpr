"""
Configuration management for Adaptive Learning API
"""
import os
import secrets
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/adaptive_learning"
    )
    
    # JWT
    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY",
        secrets.token_urlsafe(32)  # Auto-generate if not provided
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    
    # Models
    LSTM_MODEL_PATH: str = "student_simulator.pth"
    RL_MODEL_PATH: str = "ppo_ednet_teacher.zip"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()

# Print JWT secret on startup (for first-time setup)
if __name__ == "__main__":
    print(f"Generated JWT Secret Key: {settings.JWT_SECRET_KEY}")
    print("\nAdd this to your .env file:")
    print(f"JWT_SECRET_KEY={settings.JWT_SECRET_KEY}")
