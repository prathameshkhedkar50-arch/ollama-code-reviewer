"""
AI Code Reviewer - Main Application Entry Point
"""
import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from api.review import router as review_router
from api.health import router as health_router
from config.settings import settings
from services import ollama_service

# Configure logging with more detailed format for performance tracking
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Offline AI-powered code reviewer using Ollama"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")

# Configure templates
templates = Jinja2Templates(directory=settings.TEMPLATE_DIR)

# Include API routers
app.include_router(health_router)
app.include_router(review_router)

# Ensure required directories exist
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.HISTORY_DIR.mkdir(parents=True, exist_ok=True)
logger.info(f"📁 Upload directory: {settings.UPLOAD_DIR.absolute()}")
logger.info(f"📁 History directory: {settings.HISTORY_DIR.absolute()}")


@app.get("/")
async def root(request: Request):
    """Render the main application page."""
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "app_name": settings.APP_NAME,
            "version": settings.VERSION
        }
    )


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info(f"\n{'='*70}")
    logger.info(f"🚀 {settings.APP_NAME} v{settings.VERSION} Starting")
    logger.info(f"{'='*70}")
    
    # Log configuration
    logger.info(f"🌐 Server: http://{settings.HOST}:{settings.PORT}")
    logger.info(f"🧠 Default Model: {settings.DEFAULT_MODEL}")
    
    # Log performance settings
    logger.info(f"⚡ Performance Configuration:")
    logger.info(f"   - Streaming: {'✓ Enabled' if settings.OLLAMA_STREAM_ENABLED else '✗ Disabled'}")
    logger.info(f"   - Persistent Client: {'✓ Enabled' if settings.USE_PERSISTENT_CLIENT else '✗ Disabled'}")
    logger.info(f"   - Caching: {'✓ Enabled' if settings.PROMPT_CACHE_ENABLED else '✗ Disabled'}")
    logger.info(f"   - Max Connections: {settings.OLLAMA_MAX_CONNECTIONS}")
    logger.info(f"   - Temperature: {settings.OLLAMA_TEMPERATURE}")
    logger.info(f"   - Top-P: {settings.OLLAMA_TOP_P}")
    logger.info(f"   - Max Tokens: {settings.OLLAMA_NUM_PREDICT}")
    logger.info(f"   - Base Timeout: {settings.OLLAMA_BASE_TIMEOUT}s")
    
    logger.info(f"{'='*70}\n")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    logger.info(f"\n{'='*70}")
    logger.info(f"👋 {settings.APP_NAME} Shutting Down")
    logger.info(f"{'='*70}")
    
    # Shutdown Ollama client pool
    try:
        await ollama_service.shutdown()
        logger.info("✅ Ollama client pool closed")
    except Exception as e:
        logger.error(f"❌ Error during Ollama shutdown: {e}")
    
    logger.info(f"{'='*70}\n")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
