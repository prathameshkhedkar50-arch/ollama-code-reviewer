import os
import re
from pathlib import Path

# --- Constants ---
ALLOWED_EXTENSIONS: set[str] = {
    ".py", ".java", ".js", ".ts", ".cpp", ".c", 
    ".cs", ".go", ".rs", ".php", ".kt", ".swift", ".txt"
}

MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB


def is_allowed_extension(filename: str) -> bool:
    """
    Check if the file has an allowed extension.
    
    Args:
        filename: The name of the file.
        
    Returns:
        bool: True if the extension is allowed, False otherwise.
    """
    ext = get_file_extension(filename)
    return ext in ALLOWED_EXTENSIONS


def get_file_extension(filename: str) -> str:
    """
    Extract the lowercase extension from a filename.
    
    Args:
        filename: The name of the file.
        
    Returns:
        str: The file extension including the dot (e.g., '.py'), or an empty string if none.
    """
    return Path(filename).suffix.lower()


def format_file_size(size_bytes: int) -> str:
    """
    Convert file size in bytes to a human-readable string.
    
    Args:
        size_bytes: The size of the file in bytes.
        
    Returns:
        str: A formatted string (e.g., '4.2 KB', '1.5 MB').
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent directory traversal and remove unsafe characters.
    
    Args:
        filename: The original filename.
        
    Returns:
        str: A safe, sanitized filename.
    """
    safe_name = os.path.basename(filename)
    safe_name = re.sub(r'[^\w\-.]', '_', safe_name)
    
    if not safe_name or safe_name == '.':
        safe_name = "unnamed_file.txt"
        
    return safe_name


def read_file_content(file_path: Path) -> tuple[str, str]:
    """
    Reads the content of a file, attempting to detect the encoding.
    Prioritizes UTF-8, falling back to latin-1 if UTF-8 decoding fails 
    to ensure the application never crashes on weird byte sequences.
    
    Args:
        file_path: The path to the file.
        
    Returns:
        tuple: A tuple containing the file content (str) and the detected encoding (str).
        
    Raises:
        IOError: If the file cannot be read from disk.
    """
    try:
        # Attempt to read as standard UTF-8
        content = file_path.read_text(encoding="utf-8")
        return content, "utf-8"
    except UnicodeDecodeError:
        # Fallback to latin-1, which can decode any arbitrary byte sequence
        content = file_path.read_text(encoding="latin-1")
        return content, "latin-1"


def count_lines(content: str) -> int:
    """
    Counts the number of lines in a given string content.
    
    Args:
        content: The string content to analyze.
        
    Returns:
        int: The number of lines. Returns 0 for empty content.
    """
    if not content:
        return 0
    # splitlines() correctly handles different newline characters (\n, \r\n, \r)
    return len(content.splitlines())