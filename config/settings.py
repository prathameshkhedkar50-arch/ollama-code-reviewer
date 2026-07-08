from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Centralized application configuration.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

    # --- Application Metadata ---
    APP_NAME: str = "AI Code Reviewer"
    VERSION: str = "0.1.0"

    # --- Server Configuration ---
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEBUG: bool = False

    # --- Directory Paths ---
    TEMPLATE_DIR: Path = Path("templates")
    STATIC_DIR: Path = Path("static")
    UPLOAD_DIR: Path = Path("uploads")

    # --- Ollama Configuration ---
    # Make sure the : str and : int type hints are present!
    OLLAMA_URL: str = "http://localhost:11434"
    DEFAULT_MODEL: str = "qwen2.5-coder:7b"
    OLLAMA_TIMEOUT: int = 600


# Create a global settings instance
settings = Settings()