"""
Utility functions for managing file paths and data directory access.
"""
from pathlib import Path
from typing import List, Optional


def get_data_dir() -> Path:
    """
    Get the path to the data directory.
    
    Returns:
        Path to the data directory
    """
    # Get project root (where the data folder lives)
    project_root = Path(__file__).parent.parent.parent
    data_dir = project_root / "data"
    
    # Ensure data directory exists
    data_dir.mkdir(exist_ok=True)
    
    return data_dir


def list_pdf_files(subdir: Optional[str] = None) -> List[Path]:
    """
    List all PDF files in the data directory or a subdirectory.
    
    Args:
        subdir: Optional subdirectory within data folder
        
    Returns:
        List of paths to PDF files
    """
    data_dir = get_data_dir()
    
    if subdir:
        search_dir = data_dir / subdir
        search_dir.mkdir(exist_ok=True)
    else:
        search_dir = data_dir
        
    return sorted(search_dir.glob("**/*.pdf"))