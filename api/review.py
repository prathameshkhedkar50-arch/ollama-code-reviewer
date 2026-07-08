from typing import Any

from fastapi import APIRouter, File, UploadFile

from services.review_service import review_file

router = APIRouter()


@router.post("/review")
async def review_code(file: UploadFile = File(...)) -> dict[str, Any]:
    """
    Endpoint to trigger the complete AI code review pipeline.
    
    This route receives the uploaded file and delegates the entire workflow 
    (file processing, prompt building, Ollama generation, and JSON parsing) 
    to the review service layer.
    
    Args:
        file: The uploaded source code file provided in the multipart/form-data request.
        
    Returns:
        dict: A JSON object containing the success status, file metadata, 
              and the structured AI review.
    """
    return await review_file(file)