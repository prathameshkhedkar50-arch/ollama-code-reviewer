"""
AI Code Reviewer - Main Application Entry Point
"""
import logging
from pathlib import Path

from fastapi import FastAPI, Request  # ✅ Added Request import
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from api.review import router as review_router
from api.health import router as health_router
from config.settings import settings

# Configure logging
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

# Ensure uploads directory exists
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
logger.info(f"Uploads directory: {settings.UPLOAD_DIR.absolute()}")


# ✅ FIXED: Added 'request: Request' parameter and passed it as the first argument
@app.get("/")
async def root(request: Request):
    """Render the main application page."""
    return templates.TemplateResponse(
        request,             # ✅ First argument must be the Request object
        "index.html",
        {
            "app_name": settings.APP_NAME,
            "version": settings.VERSION
        }
    )


@app.on_event("startup")
async def startup_event():
    """Log application startup."""
    logger.info(f"🚀 {settings.APP_NAME} v{settings.VERSION} starting...")
    logger.info(f"📁 Upload directory: {settings.UPLOAD_DIR}")
    logger.info(f"🌐 Server: http://{settings.HOST}:{settings.PORT}")


@app.on_event("shutdown")
async def shutdown_event():
    """Log application shutdown."""
    logger.info(f"👋 {settings.APP_NAME} shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )