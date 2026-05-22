from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    API_KEY: str = "super-secret-key-12345"

    # Database Settings
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/english_to_hausa"

    # Cloud Storage (Cloudinary)
    CLOUDINARY_CLOUD_NAME: Optional[str] = None
    CLOUDINARY_API_KEY: Optional[str] = None
    CLOUDINARY_API_SECRET: Optional[str] = None

    # Paths
    STORAGE_DIR: str = "C:\\Backend\\english_to_hausa\\downloads"
    MODEL_CACHE_DIR: str = "C:\\Backend\\english_to_hausa\\models_cache"

    # Processing Limits
    MAX_VIDEO_DURATION_SECONDS: int = 7200
    MAX_TEXT_LENGTH: int = 10000
    MAX_TTS_TEXT_LENGTH: int = 5000

settings = Settings()
