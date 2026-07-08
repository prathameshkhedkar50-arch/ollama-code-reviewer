from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Centralized application configuration with performance optimization settings.
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
    HISTORY_DIR: Path = Path("history")

    # --- Ollama Configuration ---
    OLLAMA_URL: str = "http://localhost:11434"
    DEFAULT_MODEL: str = "qwen2.5-coder:7b"
    
    # --- Timeout Configuration (in seconds) ---
    # Adaptive timeout: base timeout + (model_size * multiplier)
    # Small models (3B): ~30s, Medium (7B): ~60s, Large (13B+): ~120s
    OLLAMA_BASE_TIMEOUT: int = 30
    OLLAMA_TIMEOUT_MULTIPLIER: float = 10.0  # Extra time per GB of model size
    
    # --- Ollama Generation Parameters ---
    # These are passed to Ollama's /api/generate endpoint
    OLLAMA_TEMPERATURE: float = 0.3  # Lower = more deterministic, better for code
    OLLAMA_TOP_P: float = 0.9  # Nucleus sampling
    OLLAMA_TOP_K: int = 40  # Top-k sampling
    OLLAMA_NUM_PREDICT: int = 2048  # Max tokens to generate per request
    OLLAMA_NUM_CONTEXT: int = 4096  # Context window size
    
    # --- Connection Pool Settings ---
    OLLAMA_POOL_TIMEOUT: int = 30  # HTTP pool timeout
    OLLAMA_KEEP_ALIVE: int = 30  # Keep-alive timeout for persistent connections
    OLLAMA_MAX_CONNECTIONS: int = 10  # Max concurrent connections
    
    # --- Streaming Settings ---
    OLLAMA_STREAM_ENABLED: bool = True  # Enable streaming responses
    OLLAMA_STREAM_CHUNK_SIZE: int = 8192  # Size of streaming chunks
    
    # --- Caching Settings ---
    PROMPT_CACHE_ENABLED: bool = True
    PROMPT_CACHE_SIZE: int = 100  # Number of prompts to cache
    RESPONSE_CACHE_ENABLED: bool = True
    RESPONSE_CACHE_SIZE: int = 50  # Number of responses to cache
    CACHE_TTL: int = 3600  # Cache TTL in seconds
    
    # --- Performance Optimization ---
    CONCURRENT_REQUESTS: int = 4  # Max concurrent Ollama requests
    USE_PERSISTENT_CLIENT: bool = True  # Reuse HTTP client across requests
    
    # --- JSON Format Settings ---
    FORCE_JSON_FORMAT: bool = True  # Force Ollama to output valid JSON
    JSON_REPAIR_ENABLED: bool = True  # Attempt to repair malformed JSON


# Create a global settings instance
settings = Settings()
