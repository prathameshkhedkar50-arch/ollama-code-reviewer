from pathlib import Path

# --- Constants ---
# Centralized mapping of file extensions to programming language names.
# Keys must be lowercase and include the leading dot.
EXTENSION_TO_LANGUAGE: dict[str, str] = {
    ".py": "Python",
    ".java": "Java",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".c": "C",
    ".cpp": "C++",
    ".cs": "C#",
    ".go": "Go",
    ".rs": "Rust",
    ".php": "PHP",
    ".kt": "Kotlin",
    ".swift": "Swift",
    ".txt": "Text",
}


def detect_language(filename: str) -> str:
    """
    Detect the programming language based on the file extension.
    
    Args:
        filename: The name of the file (e.g., 'Main.java').
        
    Returns:
        str: The detected programming language name (e.g., 'Java'), 
             or 'Unknown' if the extension is not recognized.
    """
    # Extract the lowercase extension using pathlib (e.g., '.java')
    extension = Path(filename).suffix.lower()
    
    # Look up the language in the mapping, defaulting to 'Unknown'
    return EXTENSION_TO_LANGUAGE.get(extension, "Unknown")