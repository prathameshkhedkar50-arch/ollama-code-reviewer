import logging
import time

import httpx
from fastapi import HTTPException

from config.settings import settings

logger = logging.getLogger(__name__)


async def check_connection() -> bool:
    """
    Checks if the Ollama server is running and reachable.
    
    Returns:
        bool: True if the connection is successful.
        
    Raises:
        HTTPException: If the server is unreachable or times out.
    """
    logger.info(f"Attempting to connect to Ollama at {settings.OLLAMA_URL}...")
    try:
        async with httpx.AsyncClient(base_url=settings.OLLAMA_URL, timeout=settings.OLLAMA_TIMEOUT) as client:
            response = await client.get("/")
            response.raise_for_status()
            logger.info("Successfully connected to Ollama.")
            return True
    except httpx.ConnectError:
        logger.error("Failed to connect to Ollama. Is the server running?")
        raise HTTPException(
            status_code=502, 
            detail="Cannot connect to Ollama server. Please ensure it is running locally."
        )
    except httpx.TimeoutException:
        logger.error("Connection to Ollama timed out.")
        raise HTTPException(
            status_code=504, 
            detail="Connection to Ollama server timed out."
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred while checking Ollama connection: {e}")
        raise HTTPException(
            status_code=500, 
            detail="An unexpected error occurred while communicating with Ollama."
        )


async def list_models() -> list[str]:
    """
    Retrieves a list of all models currently installed in Ollama.
    
    Returns:
        list[str]: A list of model names (e.g., ['llama3:latest', 'qwen2.5-coder:7b']).
        
    Raises:
        HTTPException: If the request to fetch models fails.
    """
    try:
        async with httpx.AsyncClient(base_url=settings.OLLAMA_URL, timeout=settings.OLLAMA_TIMEOUT) as client:
            response = await client.get("/api/tags")
            response.raise_for_status()
            data = response.json()
            
            models = [model["name"] for model in data.get("models", [])]
            logger.info(f"Retrieved {len(models)} models from Ollama.")
            return models
    except httpx.ConnectError:
        logger.error("Failed to connect to Ollama while fetching models.")
        raise HTTPException(status_code=502, detail="Cannot connect to Ollama to fetch models.")
    except Exception as e:
        logger.error(f"Error fetching models from Ollama: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve models from Ollama.")


def _is_model_available(model_name: str, available_models: list[str]) -> bool:
    """
    Helper to check if a model name exists in the list of available models.
    Handles cases where the user provides a base name (e.g., 'llama3') 
    but Ollama lists it with a tag (e.g., 'llama3:latest').
    """
    if model_name in available_models:
        return True
    return any(m.startswith(f"{model_name}:") for m in available_models)


async def model_exists(model_name: str) -> bool:
    """
    Verifies if a specific model is installed in Ollama.
    
    Args:
        model_name: The name of the model to check.
        
    Returns:
        bool: True if the model is installed, False otherwise.
    """
    models = await list_models()
    return _is_model_available(model_name, models)


async def generate(prompt: str, model: str = None) -> str:
    """
    Sends a prompt to Ollama and returns the generated text.
    
    Args:
        prompt: The text prompt to send to the AI.
        model: The specific model to use. Defaults to settings.DEFAULT_MODEL.
        
    Returns:
        str: The generated text response from the AI.
        
    Raises:
        HTTPException: If generation fails, times out, or the model is not found.
    """
    model_to_use = model or settings.DEFAULT_MODEL
    
    # ==========================================
    # NEW DEBUGGING LOGS ADDED HERE
    # ==========================================
    logger.info(f"--- Starting Ollama Generation ---")
    logger.info(f"Target Model: {model_to_use}")
    logger.info(f"Prompt Length: {len(prompt)} characters")
    logger.debug(f"Prompt Preview: {prompt[:300]}...")
    
    start_time = time.time()
    
    try:
        async with httpx.AsyncClient(base_url=settings.OLLAMA_URL, timeout=settings.OLLAMA_TIMEOUT) as client:
            payload = {
                "model": model_to_use,
                "prompt": prompt,
                "stream": False,
                "format": "json"  # Force JSON mode
            }
            
            logger.info(f"Sending POST request to {settings.OLLAMA_URL}/api/generate")
            logger.debug(f"Payload snippet: {str(payload)[:200]}...")
            
            response = await client.post("/api/generate", json=payload)
            
            # ==========================================
            # NEW DEBUGGING LOGS ADDED HERE
            # ==========================================
            duration = time.time() - start_time
            logger.info(f"Ollama response received in {duration:.2f} seconds.")
            logger.info(f"HTTP Response Status: {response.status_code}")
            
            # Ollama returns 404 if the model doesn't exist
            if response.status_code == 404:
                logger.error(f"Model '{model_to_use}' not found in Ollama.")
                raise HTTPException(
                    status_code=404, 
                    detail=f"The model '{model_to_use}' is not installed in Ollama. Please pull it first."
                )
                
            response.raise_for_status()
            
            data = response.json()
            generated_text = data.get("response", "")
            
            logger.info(f"Generated text length: {len(generated_text)} characters.")
            logger.info(f"--- Ollama Generation Complete ---")
            
            return generated_text
            
    except httpx.ConnectError:
        logger.error("Lost connection to Ollama during generation.")
        raise HTTPException(status_code=502, detail="Lost connection to Ollama server during generation.")
    except httpx.TimeoutException:
        # ==========================================
        # NEW DEBUGGING LOGS ADDED HERE
        # ==========================================
        duration = time.time() - start_time
        logger.error(f"Ollama generation TIMED OUT after {duration:.2f} seconds. (Configured timeout: {settings.OLLAMA_TIMEOUT}s)")
        raise HTTPException(
            status_code=504, 
            detail=f"The AI model took too long to respond (Timeout: {settings.OLLAMA_TIMEOUT}s). Try a smaller model or increase OLLAMA_TIMEOUT in settings."
        )
    except HTTPException:
        # Re-raise our custom HTTPExceptions (like the 404 for missing model)
        raise
    except Exception as e:
        # ==========================================
        # NEW DEBUGGING LOGS ADDED HERE
        # ==========================================
        duration = time.time() - start_time
        logger.error(f"Unexpected error during Ollama generation after {duration:.2f}s: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred during AI generation.")


async def health() -> dict:
    """
    Compiles a comprehensive health status of the Ollama connection.
    
    Returns:
        dict: A dictionary containing connection status, version, default model, 
              and a list of available models.
    """
    connected = False
    models = []
    
    try:
        connected = await check_connection()
        if connected:
            models = await list_models()
    except HTTPException:
        # If check_connection fails, it raises an HTTPException. 
        # For the health endpoint, we want to catch it and return a structured JSON instead of crashing.
        connected = False
        logger.warning("Ollama health check failed: Server is unreachable.")
    except Exception as e:
        logger.error(f"Unexpected error during Ollama health check: {e}")
        connected = False

    default_model = settings.DEFAULT_MODEL
    model_installed = _is_model_available(default_model, models) if connected else False

    return {
        "connected": connected,
        "version": "N/A (Use 'ollama --version' in CLI)",
        "default_model": default_model,
        "default_model_installed": model_installed,
        "available_models": models
    }