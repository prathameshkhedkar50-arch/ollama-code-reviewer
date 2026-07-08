import logging
from pathlib import Path

from fastapi import HTTPException

logger = logging.getLogger(__name__)

# --- Constants ---
# Dynamically resolve the path to the prompts directory relative to this file's location
PROMPTS_DIR: Path = Path(__file__).resolve().parent.parent / "prompts"

# The exact placeholders that must exist in every prompt template
REQUIRED_PLACEHOLDERS: set[str] = {"{{filename}}", "{{language}}", "{{code}}"}


def load_prompt(template_name: str) -> str:
    """
    Loads a specific prompt template from the prompts directory.
    
    Args:
        template_name: The filename of the template (e.g., 'stage1_understanding.txt').
        
    Returns:
        str: The raw prompt template string.
        
    Raises:
        HTTPException: If the prompt template file is missing or cannot be read.
    """
    template_path = PROMPTS_DIR / template_name
    
    try:
        if not template_path.exists():
            logger.error(f"Prompt template not found at: {template_path}")
            raise HTTPException(
                status_code=500, 
                detail=f"Internal server error: Prompt template '{template_name}' is missing."
            )
        
        template = template_path.read_text(encoding="utf-8")
        logger.info(f"Successfully loaded prompt template: {template_name}")
        return template
        
    except IOError as e:
        logger.error(f"Failed to read prompt template '{template_name}': {e}")
        raise HTTPException(
            status_code=500, 
            detail="Internal server error: Failed to read prompt template."
        )


def validate_prompt(template: str) -> None:
    """
    Validates that the prompt template contains all required placeholders.
    
    Args:
        template: The raw prompt template string.
        
    Raises:
        HTTPException: If any required placeholder is missing from the template.
    """
    missing_placeholders = [p for p in REQUIRED_PLACEHOLDERS if p not in template]
    
    if missing_placeholders:
        logger.error(f"Prompt template is missing required placeholders: {missing_placeholders}")
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error: Prompt template is invalid. Missing: {', '.join(missing_placeholders)}"
        )
    
    logger.info("Prompt template validation passed.")


def build_prompt(filename: str, language: str, source_code: str, template_name: str, understanding: str = "") -> str:
    """
    Builds the final prompt by validating inputs, loading the specified template, 
    and replacing placeholders with actual file data.
    
    Args:
        filename: The name of the uploaded file.
        language: The detected programming language.
        source_code: The actual source code content.
        template_name: The specific template file to use (e.g., 'stage2_bugs.txt').
        understanding: The code understanding context from Stage 1 (optional).
        
    Returns:
        str: The fully constructed prompt string ready to be sent to the AI.
        
    Raises:
        HTTPException: If any input is empty or if the prompt template is invalid.
    """
    # 1. Validate inputs
    if not filename or not filename.strip():
        raise HTTPException(status_code=400, detail="Filename cannot be empty.")
    if not language or not language.strip():
        raise HTTPException(status_code=400, detail="Language cannot be empty.")
    if not source_code or not source_code.strip():
        raise HTTPException(status_code=400, detail="Source code cannot be empty.")

    # 2. Load template
    template = load_prompt(template_name)
    
    # 3. Validate placeholders
    validate_prompt(template)
    
    # 4. Replace placeholders
    try:
        final_prompt = template.replace("{{filename}}", filename)
        final_prompt = final_prompt.replace("{{language}}", language)
        final_prompt = final_prompt.replace("{{code}}", source_code)
        
        # ✅ NEW: Replace the understanding context placeholder
        final_prompt = final_prompt.replace("{{understanding}}", understanding)
        
        logger.info(f"Successfully built prompt using '{template_name}' for file: {filename} ({language})")
        return final_prompt
        
    except Exception as e:
        logger.error(f"Failed to build prompt: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Internal server error: Failed to construct the final prompt."
        )