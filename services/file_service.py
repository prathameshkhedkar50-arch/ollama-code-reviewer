import logging
from pathlib import Path

from fastapi import HTTPException, UploadFile

from config.settings import settings
from utils.file_utils import (
    MAX_FILE_SIZE_BYTES,
    count_lines,
    format_file_size,
    get_file_extension,
    is_allowed_extension,
    read_file_content,
    sanitize_filename,
)
from utils.language_detector import detect_language

logger = logging.getLogger(__name__)


async def process_uploaded_file(file: UploadFile) -> dict:
    """
    Processes an uploaded file: validates, sanitizes, saves, reads content, 
    detects language, and returns comprehensive metadata.
    
    Args:
        file: The UploadFile object received from the FastAPI request.
        
    Returns:
        dict: A dictionary containing upload success status, filename, 
              extension, language, formatted size, line count, encoding, 
              and the full source code content.
              
    Raises:
        HTTPException: If the file is empty, too large, has an unsupported 
                       extension, or if an I/O error occurs.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    # 1. Read file content to check size and prepare for saving
    content_bytes = await file.read()
    file_size_bytes = len(content_bytes)

    # 2. Validate file size
    if file_size_bytes == 0:
        raise HTTPException(status_code=400, detail="Cannot upload an empty file.")
    
    if file_size_bytes > MAX_FILE_SIZE_BYTES:
        max_size_formatted = format_file_size(MAX_FILE_SIZE_BYTES)
        raise HTTPException(
            status_code=413, 
            detail=f"File size exceeds the maximum limit of {max_size_formatted}."
        )

    # 3. Validate file extension
    if not is_allowed_extension(file.filename):
        raise HTTPException(
            status_code=400, 
            detail="Unsupported file type. Please upload a supported source code or text file."
        )

    # 4. Sanitize filename and determine save path
    safe_filename = sanitize_filename(file.filename)
    file_extension = get_file_extension(file.filename)
    save_path = settings.UPLOAD_DIR / safe_filename

    # Ensure the upload directory exists (safety check)
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # 5. Save the file to disk
    try:
        save_path.write_bytes(content_bytes)
        logger.info(f"File saved successfully at: {save_path}")
    except IOError as e:
        logger.error(f"Failed to save file {safe_filename}: {e}")
        raise HTTPException(status_code=500, detail="Failed to save the file to the server.")

    # 6. Read file content from disk and detect encoding
    try:
        file_content, detected_encoding = read_file_content(save_path)
    except IOError as e:
        logger.error(f"Failed to read saved file {safe_filename}: {e}")
        raise HTTPException(status_code=500, detail="Failed to read the file from the server.")

    # 7. Detect language and count lines
    language = detect_language(file.filename)
    line_count = count_lines(file_content)
    formatted_size = format_file_size(file_size_bytes)

    # 8. Build and return response
    return {
        "success": True,
        "filename": safe_filename,
        "extension": file_extension,
        "language": language,
        "size": formatted_size,
        "lines": line_count,
        "encoding": detected_encoding,
        "content": file_content
    }