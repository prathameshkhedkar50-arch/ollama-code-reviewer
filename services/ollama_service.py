"""
Optimized Ollama Service with streaming, persistent connections, and performance enhancements.
"""
import asyncio
import json
import logging
import time
from functools import lru_cache
from typing import AsyncGenerator, Optional

import httpx
from fastapi import HTTPException

from config.settings import settings

logger = logging.getLogger(__name__)

# ==========================================
# PERSISTENT HTTP CLIENT (Connection Pooling)
# ==========================================

class OllamaClientPool:
    """
    Manages a persistent HTTP client for Ollama with connection pooling.
    Reuses connections across requests to reduce latency.
    """
    _client: Optional[httpx.AsyncClient] = None
    _lock = asyncio.Lock()
    
    @classmethod
    async def get_client(cls) -> httpx.AsyncClient:
        """
        Get or create a persistent HTTP client with optimized settings.
        """
        if cls._client is None or cls._client.is_closed:
            async with cls._lock:
                if cls._client is None or cls._client.is_closed:
                    limits = httpx.Limits(
                        max_connections=settings.OLLAMA_MAX_CONNECTIONS,
                        max_keepalive_connections=settings.OLLAMA_MAX_CONNECTIONS
                    )
                    timeout = httpx.Timeout(
                        timeout=settings.OLLAMA_BASE_TIMEOUT,
                        pool=settings.OLLAMA_POOL_TIMEOUT
                    )
                    cls._client = httpx.AsyncClient(
                        base_url=settings.OLLAMA_URL,
                        timeout=timeout,
                        limits=limits,
                        http2=True  # Enable HTTP/2 for better multiplexing
                    )
                    logger.info("🔗 Created persistent Ollama HTTP client with connection pooling")
        return cls._client
    
    @classmethod
    async def close(cls):
        """Close the persistent client."""
        if cls._client and not cls._client.is_closed:
            await cls._client.aclose()
            cls._client = None
            logger.info("🔗 Closed persistent Ollama HTTP client")


# ==========================================
# PROMPT & RESPONSE CACHING
# ==========================================

class PromptCache:
    """
    Simple LRU cache for prompts and responses to avoid redundant AI calls.
    """
    _cache: dict = {}
    _max_size = settings.PROMPT_CACHE_SIZE
    
    @classmethod
    def get(cls, prompt_hash: str) -> Optional[str]:
        """Retrieve cached response by prompt hash."""
        if not settings.PROMPT_CACHE_ENABLED:
            return None
        
        if prompt_hash in cls._cache:
            cached_time, cached_response = cls._cache[prompt_hash]
            # Check if cache entry is still valid
            if time.time() - cached_time < settings.CACHE_TTL:
                logger.debug(f"✓ Cache hit for prompt hash: {prompt_hash}")
                return cached_response
            else:
                # Remove expired entry
                del cls._cache[prompt_hash]
        return None
    
    @classmethod
    def set(cls, prompt_hash: str, response: str):
        """Store response in cache."""
        if not settings.PROMPT_CACHE_ENABLED:
            return
        
        # Simple LRU: remove oldest entry if cache is full
        if len(cls._cache) >= cls._max_size:
            oldest_key = min(cls._cache.keys(), key=lambda k: cls._cache[k][0])
            del cls._cache[oldest_key]
            logger.debug(f"Cache evicted oldest entry (size: {len(cls._cache)}/{cls._max_size})")
        
        cls._cache[prompt_hash] = (time.time(), response)
        logger.debug(f"✓ Cached response for prompt hash: {prompt_hash} (size: {len(cls._cache)}/{cls._max_size})")
    
    @classmethod
    def clear(cls):
        """Clear all cache entries."""
        cls._cache.clear()
        logger.info("Cache cleared")


# ==========================================
# UTILITY FUNCTIONS
# ==========================================

def _hash_prompt(prompt: str) -> str:
    """Generate a simple hash of the prompt for caching."""
    import hashlib
    return hashlib.md5(prompt.encode()).hexdigest()


def _calculate_timeout(model_name: str) -> int:
    """
    Calculate adaptive timeout based on model name and size.
    Larger models need more time.
    """
    # Extract model size indicator from name (e.g., "7b", "13b")
    model_lower = model_name.lower()
    
    # Simple heuristic: look for size indicators
    if "3b" in model_lower or "mini" in model_lower:
        multiplier = 1
    elif "7b" in model_lower or "medium" in model_lower:
        multiplier = 2
    elif "13b" in model_lower or "large" in model_lower:
        multiplier = 3
    elif "70b" in model_lower or "70" in model_lower:
        multiplier = 4
    else:
        multiplier = 2  # Default to medium
    
    timeout = int(settings.OLLAMA_BASE_TIMEOUT * multiplier)
    logger.debug(f"Calculated timeout for {model_name}: {timeout}s (multiplier: {multiplier})")
    return timeout


def _build_generation_payload(
    model: str,
    prompt: str,
    stream: bool = False,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    top_k: Optional[int] = None,
    num_predict: Optional[int] = None,
) -> dict:
    """
    Build optimized payload for Ollama generation request.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": stream,
    }
    
    # Add generation parameters with defaults from settings
    if temperature is not None:
        payload["temperature"] = temperature
    else:
        payload["temperature"] = settings.OLLAMA_TEMPERATURE
    
    if top_p is not None:
        payload["top_p"] = top_p
    else:
        payload["top_p"] = settings.OLLAMA_TOP_P
    
    if top_k is not None:
        payload["top_k"] = top_k
    else:
        payload["top_k"] = settings.OLLAMA_TOP_K
    
    if num_predict is not None:
        payload["num_predict"] = num_predict
    else:
        payload["num_predict"] = settings.OLLAMA_NUM_PREDICT
    
    # Force JSON format if enabled
    if settings.FORCE_JSON_FORMAT:
        payload["format"] = "json"
    
    return payload


# ==========================================
# CORE FUNCTIONS
# ==========================================

async def check_connection() -> bool:
    """
    Checks if the Ollama server is running and reachable.
    Uses persistent client for efficiency.
    
    Returns:
        bool: True if the connection is successful.
        
    Raises:
        HTTPException: If the server is unreachable or times out.
    """
    logger.info(f"🔍 Checking connection to Ollama at {settings.OLLAMA_URL}...")
    start_time = time.time()
    
    try:
        client = await OllamaClientPool.get_client()
        response = await client.get("/", timeout=settings.OLLAMA_BASE_TIMEOUT)
        response.raise_for_status()
        
        duration = time.time() - start_time
        logger.info(f"✅ Successfully connected to Ollama ({duration:.2f}s)")
        return True
        
    except httpx.ConnectError as e:
        logger.error(f"❌ Failed to connect to Ollama: {e}")
        raise HTTPException(
            status_code=502, 
            detail="Cannot connect to Ollama server. Please ensure it is running locally."
        )
    except httpx.TimeoutException:
        logger.error("⏱️  Connection to Ollama timed out")
        raise HTTPException(
            status_code=504, 
            detail="Connection to Ollama server timed out."
        )
    except Exception as e:
        logger.error(f"❌ Unexpected error checking Ollama connection: {e}")
        raise HTTPException(
            status_code=500, 
            detail="An unexpected error occurred while communicating with Ollama."
        )


async def list_models() -> list[str]:
    """
    Retrieves a list of all models currently installed in Ollama.
    Uses persistent client.
    
    Returns:
        list[str]: A list of model names (e.g., ['llama3:latest', 'qwen2.5-coder:7b']).
        
    Raises:
        HTTPException: If the request to fetch models fails.
    """
    logger.info("📋 Fetching available models from Ollama...")
    start_time = time.time()
    
    try:
        client = await OllamaClientPool.get_client()
        response = await client.get("/api/tags")
        response.raise_for_status()
        data = response.json()
        
        models = [model["name"] for model in data.get("models", [])]
        duration = time.time() - start_time
        logger.info(f"✅ Retrieved {len(models)} models from Ollama ({duration:.2f}s)")
        return models
        
    except httpx.ConnectError:
        logger.error("❌ Failed to connect to Ollama while fetching models")
        raise HTTPException(status_code=502, detail="Cannot connect to Ollama to fetch models.")
    except Exception as e:
        logger.error(f"❌ Error fetching models from Ollama: {e}")
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
    try:
        models = await list_models()
        return _is_model_available(model_name, models)
    except HTTPException:
        return False


async def generate(
    prompt: str,
    model: str = None,
    stream: bool = True,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    top_k: Optional[int] = None,
    num_predict: Optional[int] = None,
) -> str:
    """
    Sends a prompt to Ollama and returns the generated text.
    Optimized for performance with caching, streaming, and persistent connections.
    
    Args:
        prompt: The text prompt to send to the AI.
        model: The specific model to use. Defaults to settings.DEFAULT_MODEL.
        stream: Whether to stream the response. Defaults to OLLAMA_STREAM_ENABLED.
        temperature: Generation temperature (0-1).
        top_p: Nucleus sampling parameter.
        top_k: Top-k sampling parameter.
        num_predict: Max tokens to generate.
        
    Returns:
        str: The generated text response from the AI.
        
    Raises:
        HTTPException: If generation fails, times out, or the model is not found.
    """
    model_to_use = model or settings.DEFAULT_MODEL
    stream = stream and settings.OLLAMA_STREAM_ENABLED
    
    pipeline_start = time.time()
    logger.info(f"\n{'='*70}")
    logger.info(f"📝 Starting Ollama Generation")
    logger.info(f"   Model: {model_to_use}")
    logger.info(f"   Prompt Length: {len(prompt)} characters")
    logger.info(f"   Streaming: {stream}")
    
    # Check cache first
    prompt_hash = _hash_prompt(prompt)
    cached_response = PromptCache.get(prompt_hash)
    if cached_response:
        logger.info(f"✓ Retrieved from cache ({len(cached_response)} chars)")
        return cached_response
    
    try:
        # Calculate adaptive timeout
        timeout = _calculate_timeout(model_to_use)
        client = await OllamaClientPool.get_client()
        
        # Build optimized payload
        payload = _build_generation_payload(
            model_to_use, prompt, stream,
            temperature, top_p, top_k, num_predict
        )
        
        logger.debug(f"   Temperature: {payload.get('temperature')}")
        logger.debug(f"   Top-P: {payload.get('top_p')}, Top-K: {payload.get('top_k')}")
        logger.debug(f"   Max Tokens: {payload.get('num_predict')}")
        
        # Send request with adaptive timeout
        request_start = time.time()
        logger.info(f"   Sending request to Ollama (timeout: {timeout}s)...")
        
        if stream:
            # Streaming response
            generated_text = await _generate_streaming(
                client, payload, timeout, model_to_use
            )
        else:
            # Non-streaming response
            response = await client.post(
                "/api/generate",
                json=payload,
                timeout=timeout
            )
            
            request_duration = time.time() - request_start
            logger.info(f"   Response received ({request_duration:.2f}s), Status: {response.status_code}")
            
            if response.status_code == 404:
                logger.error(f"❌ Model '{model_to_use}' not found in Ollama")
                raise HTTPException(
                    status_code=404,
                    detail=f"The model '{model_to_use}' is not installed in Ollama. Please pull it first."
                )
            
            response.raise_for_status()
            data = response.json()
            generated_text = data.get("response", "")
        
        # Cache the response
        PromptCache.set(prompt_hash, generated_text)
        
        pipeline_duration = time.time() - pipeline_start
        logger.info(f"✅ Generation Complete")
        logger.info(f"   Generated Text Length: {len(generated_text)} characters")
        logger.info(f"   Total Time: {pipeline_duration:.2f}s")
        logger.info(f"{'='*70}\n")
        
        return generated_text
        
    except httpx.ConnectError:
        logger.error("❌ Lost connection to Ollama during generation")
        raise HTTPException(
            status_code=502,
            detail="Lost connection to Ollama server during generation."
        )
    except httpx.TimeoutException:
        duration = time.time() - pipeline_start
        logger.error(f"⏱️  Ollama generation TIMED OUT after {duration:.2f}s (configured: {timeout}s)")
        raise HTTPException(
            status_code=504,
            detail=f"The AI model took too long to respond. Try a smaller model or increase timeout."
        )
    except HTTPException:
        raise
    except Exception as e:
        duration = time.time() - pipeline_start
        logger.error(f"❌ Unexpected error during generation ({duration:.2f}s): {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during AI generation."
        )


async def _generate_streaming(
    client: httpx.AsyncClient,
    payload: dict,
    timeout: int,
    model_name: str
) -> str:
    """
    Handle streaming response from Ollama and accumulate into complete response.
    """
    generated_text = ""
    chunk_count = 0
    
    try:
        request_start = time.time()
        logger.debug(f"   Opening streaming connection...")
        
        async with client.stream(
            "POST",
            "/api/generate",
            json=payload,
            timeout=timeout
        ) as response:
            if response.status_code == 404:
                logger.error(f"❌ Model '{model_name}' not found")
                raise HTTPException(
                    status_code=404,
                    detail=f"The model '{model_name}' is not installed in Ollama."
                )
            
            response.raise_for_status()
            
            # Stream and accumulate response
            async for line in response.aiter_lines():
                if line.strip():
                    chunk_count += 1
                    try:
                        data = json.loads(line)
                        chunk = data.get("response", "")
                        generated_text += chunk
                        
                        # Log progress every 10 chunks
                        if chunk_count % 10 == 0:
                            elapsed = time.time() - request_start
                            logger.debug(f"   ⚡ Streamed {chunk_count} chunks ({elapsed:.1f}s, {len(generated_text)} chars)")
                    except json.JSONDecodeError:
                        logger.warning(f"   ⚠️  Skipped malformed JSON chunk: {line[:50]}")
                        continue
        
        request_duration = time.time() - request_start
        logger.info(f"   Streaming complete ({request_duration:.2f}s, {chunk_count} chunks)")
        
        return generated_text
        
    except httpx.TimeoutException:
        duration = time.time() - request_start
        logger.error(f"⏱️  Streaming timed out after {duration:.2f}s")
        raise
    except Exception as e:
        logger.error(f"❌ Error during streaming: {e}", exc_info=True)
        raise


async def health() -> dict:
    """
    Compiles a comprehensive health status of the Ollama connection
    with performance optimization details.
    
    Returns:
        dict: A dictionary containing connection status, version info, default model,
              available models, and performance settings.
    """
    logger.info("🏥 Running health check...")
    health_start = time.time()
    
    connected = False
    models = []
    
    try:
        connected = await check_connection()
        if connected:
            models = await list_models()
    except HTTPException:
        connected = False
        logger.warning("⚠️  Ollama health check failed: Server is unreachable")
    except Exception as e:
        logger.error(f"❌ Unexpected error during health check: {e}")
        connected = False
    
    default_model = settings.DEFAULT_MODEL
    model_installed = _is_model_available(default_model, models) if connected else False
    
    duration = time.time() - health_start
    
    health_status = {
        "connected": connected,
        "version": "N/A (Use 'ollama --version' in CLI)",
        "default_model": default_model,
        "default_model_installed": model_installed,
        "available_models": models,
        "performance": {
            "streaming_enabled": settings.OLLAMA_STREAM_ENABLED,
            "persistent_client": settings.USE_PERSISTENT_CLIENT,
            "caching_enabled": settings.PROMPT_CACHE_ENABLED,
            "temperature": settings.OLLAMA_TEMPERATURE,
            "timeout_base": settings.OLLAMA_BASE_TIMEOUT,
            "max_connections": settings.OLLAMA_MAX_CONNECTIONS,
        },
        "health_check_duration_ms": round(duration * 1000, 2)
    }
    
    logger.info(f"✅ Health check complete ({duration:.2f}s)")
    return health_status


async def shutdown():
    """
    Gracefully shutdown the Ollama client pool.
    Call this during application shutdown.
    """
    logger.info("🔌 Shutting down Ollama client pool...")
    await OllamaClientPool.close()
    PromptCache.clear()
    logger.info("✅ Ollama client pool closed")
