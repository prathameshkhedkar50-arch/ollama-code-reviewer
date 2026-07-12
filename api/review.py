from typing import Any
from fastapi import APIRouter, File, UploadFile, HTTPException
from services.file_service import process_uploaded_file
from services.review_service import review_manager

router = APIRouter()

@router.post("/review")
async def start_review(file: UploadFile = File(...)) -> dict[str, Any]:
    """
    Starts a review in the background and returns a review_id immediately.
    This prevents HTTP timeouts during long-running AI analysis.
    """
    file_data = await process_uploaded_file(file)
    review_id = review_manager.create_review(file_data)
    return {"review_id": review_id, "status": "started"}

@router.get("/review/progress/{review_id}")
async def get_review_progress(review_id: str) -> dict[str, Any]:
    """
    Returns the real-time progress object for a specific review.
    """
    progress = review_manager.get_progress(review_id)
    if not progress:
        raise HTTPException(status_code=404, detail="Review not found")
    return progress