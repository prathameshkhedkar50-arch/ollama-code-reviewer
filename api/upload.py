from typing import Any

from fastapi import APIRouter, File, UploadFile

from services.file_service import process_uploaded_file

router = APIRouter()


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)) -> dict[str, Any]:
    """
    Endpoint to handle single file uploads.
    
    This route receives the uploaded file and delegates all validation, 
    sanitization, saving, reading, and language detection logic to the 
    file service layer.
    
    Args:
        file: The uploaded file provided in the multipart/form-data request.
        
    Returns:
        dict: A JSON object containing the upload status, file metadata, 
              and the full source code content.
    """
    return await process_uploaded_file(file)