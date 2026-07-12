import json
import logging
import re
import time
from pathlib import Path

from fastapi import HTTPException

logger = logging.getLogger(__name__)

# --- Constants ---
REQUIRED_KEYS: set[str] = {
    "summary", "overall_score", "bugs", "security", "performance",
    "readability", "architecture", "best_practices", "refactoring",
    "documentation", "positive_points", "conclusion"
}

DEFAULTS: dict = {
    "summary": "No summary provided by the AI.",
    "overall_score": 0,
    "bugs": [], "security": [], "performance": [], "readability": [],
    "architecture": [], "best_practices": [], "refactoring": [],
    "documentation": [], "positive_points": [],
    "conclusion": "No conclusion provided by the AI."
}


def extract_json_string(raw_text: str) -> str:
    """Extracts the raw JSON string, stripping markdown and conversational filler."""
    logger.debug(f"Raw response length: {len(raw_text)} characters.")
    
    if not raw_text or not raw_text.strip():
        raise ValueError("The AI returned an empty response.")

    text = raw_text.strip()
    
    # 1. Remove Markdown code fences
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```\s*$", "", text)
    
    # 2. Find the actual JSON object boundaries
    start_idx = text.find('{')
    end_idx = text.rfind('}')
    
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        logger.info("Successfully extracted JSON object using brace matching.")
        return text[start_idx:end_idx + 1]
    else:
        raise ValueError("No JSON object found in the AI response.")


def fix_literal_newlines(s: str) -> str:
    """State-machine to replace literal newline characters inside JSON strings with \\n."""
    result = []
    in_string = False
    i = 0
    while i < len(s):
        c = s[i]
        if c == '\\' and in_string and i + 1 < len(s):
            result.append(c)
            result.append(s[i+1])
            i += 2
            continue
        elif c == '"':
            in_string = not in_string
            result.append(c)
        elif c in '\r\n' and in_string:
            if c == '\r' and i + 1 < len(s) and s[i+1] == '\n':
                result.append('\\n')
                i += 2
                continue
            else:
                result.append('\\n')
        else:
            result.append(c)
        i += 1
    return "".join(result)


def fix_unescaped_quotes(s: str) -> str:
    """State-machine to detect and escape unescaped double quotes inside JSON strings."""
    result = []
    in_string = False
    i = 0
    while i < len(s):
        c = s[i]
        if c == '\\' and in_string and i + 1 < len(s):
            result.append(c)
            result.append(s[i+1])
            i += 2
            continue
        elif c == '"':
            if not in_string:
                in_string = True
                result.append(c)
            else:
                # Look ahead to see if this is the actual end of the string
                j = i + 1
                while j < len(s) and s[j] in ' \t\r\n':
                    j += 1
                
                # If the next non-whitespace character is a JSON delimiter, it's the end of the string
                if j < len(s) and s[j] in ',:}]':
                    in_string = False
                    result.append(c)
                else:
                    # Otherwise, it's an unescaped quote inside the string! Escape it.
                    result.append('\\"')
            i += 1
        else:
            result.append(c)
            i += 1
    return "".join(result)


def repair_json(json_str: str) -> str:
    """Attempts to repair common JSON formatting mistakes made by LLMs."""
    logger.debug("Attempting to repair malformed JSON...")
    
    # 1. Remove BOM
    json_str = json_str.lstrip('\ufeff')
    
    # 2. Replace smart quotes
    json_str = json_str.replace('“', '"').replace('”', '"')
    json_str = json_str.replace('‘', "'").replace('’', "'")
    
    # 3. Remove literal control characters (except \n, \r, \t)
    json_str = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', json_str)
    
    # 4. Fix trailing commas: ,} or ,]
    json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
    
    # 5. Fix duplicated commas: ,,
    json_str = re.sub(r',\s*,', ',', json_str)
    
    # 6. Fix single-quoted keys: 'key': -> "key":
    json_str = re.sub(r"'\s*([a-zA-Z0-9_]+)\s*'\s*:", r'"\1":', json_str)
    
    # 7. Fix literal newlines inside strings
    json_str = fix_literal_newlines(json_str)
    
    # 8. Fix unescaped quotes inside strings
    json_str = fix_unescaped_quotes(json_str)
    
    return json_str


def validate_and_clean(data: dict) -> dict:
    """Validates the parsed dictionary against the expected schema and fixes types."""
    logger.info(f"Input to validate_and_clean: {json.dumps(data, indent=2)}")
    
    cleaned_data = {}
    missing_keys = REQUIRED_KEYS - set(data.keys())
    if missing_keys:
        logger.warning(f"AI response is missing keys: {missing_keys}. Applying defaults.")
        for key in missing_keys:
            data[key] = DEFAULTS[key]
    
    try:
        score = int(data.get("overall_score", 0))
        cleaned_data["overall_score"] = max(0, min(100, score))
    except (ValueError, TypeError):
        cleaned_data["overall_score"] = 0
        
    for key in ["summary", "conclusion"]:
        val = data.get(key)
        cleaned_data[key] = str(val) if isinstance(val, str) else DEFAULTS[key]
        
    list_keys = [
        "bugs", "security", "performance", "readability", 
        "architecture", "best_practices", "refactoring", 
        "documentation", "positive_points"
    ]
    
    for key in list_keys:
        val = data.get(key)
        if isinstance(val, list):
            # Filter out non-string items and empty strings
            cleaned_list = [str(item).strip() for item in val if isinstance(item, (str, int, float)) and str(item).strip()]
            cleaned_data[key] = cleaned_list
        elif isinstance(val, str) and val.strip():
            # CRITICAL FIX: AI returned a single string instead of a list. 
            # Wrap it in a list to prevent data loss!
            cleaned_data[key] = [val.strip()]
        else:
            cleaned_data[key] = []
            
    logger.info(f"Output from validate_and_clean: {json.dumps(cleaned_data, indent=2)}")
    return cleaned_data

def parse_review(raw_response: str) -> dict:
    """Main entry point for processing the AI response with robust error handling."""
    logger.info(f"Raw response length: {len(raw_response)} characters.")
    
    try:
        # Step 1: Extract
        json_str = extract_json_string(raw_response)
        
        # Step 2: Parse (with automatic repair)
        try:
            parsed_data = json.loads(json_str)
            logger.info("JSON parsed successfully on first attempt.")
        except json.JSONDecodeError as e:
            logger.warning(f"Initial parse failed: {e}. Attempting repairs...")
            start_repair_time = time.time()
            
            repaired_str = repair_json(json_str)
            repair_duration = time.time() - start_repair_time
            logger.info(f"Repair attempts completed in {repair_duration:.3f} seconds.")
            
            try:
                parsed_data = json.loads(repaired_str)
                logger.info("JSON parsed successfully after repairs.")
            except json.JSONDecodeError as e_final:
                logger.error(f"Final parse failed after repairs: {e_final}")
                
                # Save malformed JSON for debugging
                log_dir = Path("logs")
                log_dir.mkdir(exist_ok=True)
                failed_log_path = log_dir / "failed_response.json"
                failed_log_path.write_text(json_str, encoding="utf-8")
                logger.error(f"Malformed JSON saved to: {failed_log_path.absolute()}")
                
                # Return structured HTTPException
                raise HTTPException(
                    status_code=500,
                    detail={
                        "success": False,
                        "error": "AI returned invalid JSON that could not be repaired.",
                        "raw_preview": json_str[:500]
                    }
                )
        
        # Step 3: Validate
        if not isinstance(parsed_data, dict):
            raise HTTPException(status_code=500, detail="AI response is not a dictionary object.")
            
        cleaned_data = validate_and_clean(parsed_data)
        return cleaned_data
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"ValueError during JSON extraction: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in parse_review: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred while processing the AI review.")