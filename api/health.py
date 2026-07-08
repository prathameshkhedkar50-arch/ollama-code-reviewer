from fastapi import APIRouter

from config.settings import settings
from services.ollama_service import generate as ollama_generate
from services.ollama_service import health as ollama_health_status

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """
    Basic application health check endpoint.
    
    Returns:
        dict: A simple status message indicating the API is running.
    """
    return {"status": "healthy"}


@router.get("/ollama/health")
async def ollama_health() -> dict:
    """
    Endpoint to check the status of the Ollama connection.
    
    Returns:
        dict: Contains connection status, version info, default model, 
              and a list of available models.
    """
    return await ollama_health_status()


@router.post("/ollama/test")
async def ollama_test() -> dict:
    """
    Endpoint to send a test prompt to the configured Ollama model.
    This verifies that the AI generation pipeline is working correctly.
    
    Returns:
        dict: Contains success status, the model used, and the AI response.
    """
    test_prompt = "Reply with exactly: Ollama connection successful."
    
    # Generate response using the default model
    response_text = await ollama_generate(prompt=test_prompt)
    
    return {
        "success": True,
        "model": settings.DEFAULT_MODEL,
        "response": response_text.strip()
    }