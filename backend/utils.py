"""
Utility functions for the GitHub repository indexing and Q&A system.

This module contains common utility functions used across different services
to avoid code duplication and improve maintainability.
"""

import hashlib
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional

import constants

logger = logging.getLogger(__name__)


def normalize_repo_url(repo_url: str) -> str:
    """
    Normalize repository URL for consistent caching.
    
    Args:
        repo_url: The repository URL to normalize
        
    Returns:
        Normalized repository URL
    """
    # Extract repository URL from GitHub file URLs
    if "github.com" in repo_url and "/blob/" in repo_url:
        return repo_url.split("/blob/")[0]
    
    # Remove .git suffix if present
    if repo_url.endswith(".git"):
        return repo_url[:-4]
    
    return repo_url


def generate_repo_hash(repo_url: str) -> str:
    """
    Generate a consistent hash for a repository URL.
    
    Args:
        repo_url: The repository URL to hash
        
    Returns:
        MD5 hash of the normalized repository URL
    """
    normalized_url = normalize_repo_url(repo_url)
    return hashlib.md5(normalized_url.encode()).hexdigest()


def remove_directory_if_exists(path: Path) -> None:
    """
    Remove directory if it exists.
    
    Args:
        path: Path to the directory to remove
    """
    if path.exists():
        shutil.rmtree(path)


def get_file_type(file_path: Path) -> str:
    """
    Determine file type based on extension and content.
    
    Args:
        file_path: Path to the file
        
    Returns:
        File type string
    """
    extension = file_path.suffix.lower()
    return constants.FILE_TYPE_MAPPING.get(extension, "text")


def is_text_file(file_path: Path) -> bool:
    """
    Check if a file is a text file based on extension and content.
    
    Args:
        file_path: Path to the file
        
    Returns:
        True if the file is a text file, False otherwise
    """
    # Check by extension first
    extension = file_path.suffix.lower()
    if extension in constants.INCLUDE_EXTENSIONS:
        return True
    
    # Check by filename (files without extension)
    filename = file_path.name.lower()
    if filename in constants.TEXT_FILES_WITHOUT_EXTENSION:
        return True
    
    # Check by content (first 1024 bytes)
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            # Check if it's binary by looking for null bytes
            if b'\x00' in chunk:
                return False
            # Try to decode as text
            chunk.decode('utf-8')
            return True
    except (UnicodeDecodeError, IOError):
        return False


def generate_content_hash(content: str) -> str:
    """
    Generate MD5 hash of content.
    
    Args:
        content: The content to hash
        
    Returns:
        MD5 hash of the content
    """
    return hashlib.md5(content.encode()).hexdigest()


def generate_files_hash(files: List[Dict]) -> str:
    """
    Generate hash of files list for change detection.
    
    Args:
        files: List of file dictionaries with 'path' and 'content' keys
        
    Returns:
        MD5 hash of the files list
    """
    content_hash = hashlib.md5()
    
    # Sort files by path for consistent hashing
    sorted_files = sorted(files, key=lambda f: f.get('path', ''))
    
    for file_info in sorted_files:
        path = file_info.get('path', '')
        content = file_info.get('content', '')
        content_hash.update(f"{path}:{content}".encode())
    
    return content_hash.hexdigest()


def load_json_file(file_path: Path) -> Optional[Dict]:
    """
    Load JSON data from a file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Dictionary with JSON data or None if file doesn't exist or is invalid
    """
    try:
        if not file_path.exists():
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning("Error loading JSON file %s: %s", file_path, e)
        return None


def save_json_file(file_path: Path, data: Dict) -> bool:
    """
    Save data to a JSON file.
    
    Args:
        file_path: Path to the JSON file
        data: Dictionary to save
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        return True
    except (IOError, TypeError) as e:
        logger.warning("Error saving JSON file %s: %s", file_path, e)
        return False


def get_confidence_level(value: float, high_threshold: float, medium_threshold: float, reverse: bool = False) -> str:
    """
    Determine confidence level based on value and thresholds.
    
    Args:
        value: The value to evaluate
        high_threshold: Threshold for high confidence
        medium_threshold: Threshold for medium confidence
        reverse: If True, lower values are better (e.g., distance)
        
    Returns:
        Confidence level: 'high', 'medium', or 'low'
    """
    if reverse:
        # Lower values are better (e.g., distance)
        if value <= high_threshold:
            return "high"
        elif value <= medium_threshold:
            return "medium"
        else:
            return "low"
    else:
        # Higher values are better (e.g., score)
        if value >= high_threshold:
            return "high"
        elif value >= medium_threshold:
            return "medium"
        else:
            return "low"


def combine_confidence_levels(level1: str, level2: str) -> str:
    """
    Combine two confidence levels into a single level.
    
    Args:
        level1: First confidence level
        level2: Second confidence level
        
    Returns:
        Combined confidence level
    """
    # Priority: high > medium > low
    if level1 == "high" and level2 == "high":
        return "high"
    elif level1 == "high" or level2 == "high":
        return "medium"
    elif level1 == "medium" or level2 == "medium":
        return "medium"
    else:
        return "low"


def extract_confidence_from_text(text: str) -> str:
    """
    Extract confidence level from text response.
    
    Args:
        text: Text that may contain confidence information
        
    Returns:
        Confidence level: 'high', 'medium', 'low', or 'unknown'
    """
    text_lower = text.lower()
    
    # Look for explicit confidence markers
    if "confidence: high" in text_lower:
        return "high"
    elif "confidence: medium" in text_lower:
        return "medium"
    elif "confidence: low" in text_lower:
        return "low"
    
    # Look for confidence keywords
    if "high confidence" in text_lower or "very confident" in text_lower:
        return "high"
    elif "medium confidence" in text_lower or "somewhat confident" in text_lower:
        return "medium"
    elif "low confidence" in text_lower or "not confident" in text_lower:
        return "low"
    
    return "unknown"


def create_overlap_lines(lines: List[str], overlap_size: int) -> List[str]:
    """
    Create overlapping lines for chunking.
    
    Args:
        lines: List of lines
        overlap_size: Number of lines to overlap
        
    Returns:
        List of overlapping lines
    """
    if not lines or overlap_size <= 0:
        return []
    
    return lines[-overlap_size:] if len(lines) >= overlap_size else lines


def is_function_start(line: str, file_type: str) -> bool:
    """
    Check if a line starts a function definition.
    
    Args:
        line: The line to check
        file_type: Type of the file (python, javascript, etc.)
        
    Returns:
        True if the line starts a function definition
    """
    line = line.strip()
    
    if file_type == "python":
        return (line.startswith("def ") or 
                line.startswith("async def ") or
                line.startswith("@") and "def " in line)
    elif file_type in ["javascript", "typescript"]:
        return (line.startswith("function ") or
                line.startswith("async function ") or
                "=>" in line or
                line.startswith("const ") and "=" in line and "(" in line)
    elif file_type == "java":
        return (line.startswith("public ") and "(" in line and ")" in line) or \
               (line.startswith("private ") and "(" in line and ")" in line) or \
               (line.startswith("protected ") and "(" in line and ")" in line)
    elif file_type == "cpp":
        return (line.startswith("void ") or
                line.startswith("int ") or
                line.startswith("bool ") or
                line.startswith("string ")) and "(" in line and ")" in line
    
    return False


def is_class_start(line: str, file_type: str) -> bool:
    """
    Check if a line starts a class definition.
    
    Args:
        line: The line to check
        file_type: Type of the file (python, javascript, etc.)
        
    Returns:
        True if the line starts a class definition
    """
    line = line.strip()
    
    if file_type == "python":
        return line.startswith("class ")
    elif file_type in ["javascript", "typescript"]:
        return line.startswith("class ") or line.startswith("interface ")
    elif file_type == "java":
        return line.startswith("public class ") or line.startswith("private class ") or \
               line.startswith("protected class ") or line.startswith("class ")
    elif file_type == "cpp":
        return line.startswith("class ") or line.startswith("struct ")
    
    return False


# Session Management Functions
def load_sessions(session_file: str) -> Dict[str, Dict[str, any]]:
    """Load session data from persistent storage.

    Args:
        session_file: Path to the session file
        
    Returns:
        Dict containing session data with session_id as key.
        Returns empty dict if file doesn't exist or loading fails.
    """
    if os.path.exists(session_file):
        try:
            with open(session_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning("Failed to load sessions: %s", e)
    return {}


def save_sessions(sessions: Dict[str, Dict[str, any]], session_file: str) -> None:
    """Save session data to persistent storage.

    Args:
        sessions: Dictionary containing session data to save.
        session_file: Path to the session file
    """
    try:
        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(sessions, f, indent=2, ensure_ascii=False)
    except IOError as e:
        logger.error("Failed to save sessions: %s", e)


def update_session_status(
    session_id: str, 
    status: str, 
    message: str, 
    progress: int,
    session_status: Dict[str, Dict],
    session_file: str
) -> None:
    """Update session status and save to file.

    Args:
        session_id: Unique identifier for the session.
        status: Current status of the session.
        message: Status message.
        progress: Progress percentage (0-100).
        session_status: Dictionary containing all session statuses.
        session_file: Path to the session file.
    """
    session_status[session_id].update(
        {"status": status, "message": message, "progress": progress}
    )
    save_sessions(session_status, session_file)


async def index_repository_background(
    session_id: str, 
    repo_url: str,
    session_status: Dict[str, Dict],
    session_file: str,
    repository_service,
    rag_service
) -> None:
    """Background task for indexing repository.

    Performs the complete indexing pipeline:
    1. Clone repository
    2. Process and filter files
    3. Create vector index
    4. Update session status

    Args:
        session_id: Unique identifier for the indexing session.
        repo_url: URL or path of the repository to index.
        session_status: Dictionary containing all session statuses.
        session_file: Path to the session file.
        repository_service: Repository service instance.
        rag_service: RAG service instance.
    """
    try:
        # Define indexing steps with progress updates
        steps = [
            (
                "Cloning repository...",
                10,
                lambda: repository_service.clone_repository(repo_url, session_id),
            ),
            (
                "Processing files...",
                30,
                lambda: repository_service.process_repository_files(repo_path),
            ),
            (
                "Creating vector index...",
                60,
                lambda: rag_service.create_index(session_id, files, repo_url),
            ),
        ]

        repo_path = None
        files = None

        for message, progress, action in steps:
            update_session_status(session_id, "indexing", message, progress, session_status, session_file)
            result = await action()
            if progress == 10:  # After cloning
                repo_path = result
            elif progress == 30:  # After processing files
                files = result

        # Mark as ready
        update_session_status(
            session_id, "ready", "Repository indexed successfully!", 100, session_status, session_file
        )
        logger.info("Successfully indexed repository for session %s", session_id)

    except (ValueError, RuntimeError, OSError) as e:
        logger.error(
            "Error indexing repository for session %s: %s", session_id, e, exc_info=True
        )
        update_session_status(session_id, "error", f"Indexing failed: {str(e)}", 0, session_status, session_file)
