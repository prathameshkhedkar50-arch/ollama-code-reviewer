import json
import logging
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException

logger = logging.getLogger(__name__)

# --- Constants ---
HISTORY_DIR: Path = Path("history")


def _ensure_history_dir() -> None:
    """Ensures the history directory exists."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"History directory verified at: {HISTORY_DIR.absolute()}")


def save_review(filename: str, language: str, review_data: dict) -> str:
    """
    Saves a completed AI review to the history directory.
    
    Returns:
        str: The generated review ID (filename of the saved JSON).
    """
    _ensure_history_dir()
    
    # Generate unique timestamped ID
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = filename.replace("/", "_").replace("\\", "_").replace(" ", "_")
    review_id = f"{timestamp}_{safe_filename}.json"
    
    file_path = HISTORY_DIR / review_id
    
    # Construct payload
    payload = {
        "filename": filename,
        "language": language,
        "reviewed_at": datetime.now().isoformat(),
        "overall_score": review_data.get("overall_score", 0),
        "review": review_data
    }
    
    try:
        file_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        
        # Verify file was created
        if file_path.exists():
            logger.info(f"Review saved successfully: {review_id}")
            return review_id
        else:
            raise IOError("File was not created after write operation")
            
    except IOError as e:
        logger.error(f"Failed to save review {review_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to save review to history.")


def list_reviews() -> list[dict]:
    """Retrieves a summary list of all saved reviews, sorted newest first."""
    _ensure_history_dir()
    reviews = []
    
    for file_path in HISTORY_DIR.glob("*.json"):
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            reviews.append({
                "id": file_path.name,
                "filename": data.get("filename", "Unknown"),
                "language": data.get("language", "Unknown"),
                "score": data.get("overall_score", 0),
                "reviewed_at": data.get("reviewed_at", "")
            })
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Skipping corrupted file {file_path.name}: {e}")
    
    reviews.sort(key=lambda x: x["reviewed_at"], reverse=True)
    logger.info(f"Loaded {len(reviews)} reviews from history.")
    return reviews


def load_review(review_id: str) -> dict:
    """Loads the complete data for a specific review."""
    _ensure_history_dir()
    file_path = HISTORY_DIR / review_id
    
    if not file_path.resolve().is_relative_to(HISTORY_DIR.resolve()):
        raise HTTPException(status_code=400, detail="Invalid review ID.")
    
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Review not found.")
    
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        logger.info(f"Review loaded: {review_id}")
        return data
    except json.JSONDecodeError:
        logger.error(f"Corrupted JSON: {review_id}")
        raise HTTPException(status_code=500, detail="Review file is corrupted.")


def delete_review(review_id: str) -> None:
    """Deletes a specific review from the history."""
    _ensure_history_dir()
    file_path = HISTORY_DIR / review_id
    
    if not file_path.resolve().is_relative_to(HISTORY_DIR.resolve()):
        raise HTTPException(status_code=400, detail="Invalid review ID.")
    
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Review not found.")
    
    try:
        file_path.unlink()
        logger.info(f"Review deleted: {review_id}")
    except IOError as e:
        logger.error(f"Failed to delete review {review_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete review file.")


def get_review_file_path(review_id: str) -> Path:
    """Resolves and validates the file path for download."""
    _ensure_history_dir()
    file_path = HISTORY_DIR / review_id
    
    if not file_path.resolve().is_relative_to(HISTORY_DIR.resolve()):
        raise HTTPException(status_code=400, detail="Invalid review ID.")
    
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Review not found.")
    
    logger.info(f"Download requested for: {review_id}")
    return file_path