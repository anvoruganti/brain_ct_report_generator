"""Utility functions for DICOM file handling."""

from pathlib import Path
from typing import List


def collect_all_files_recursively(root: Path) -> List[Path]:
    """
    Recursively collect all files from a directory tree.
    
    Useful for KHEOPS folder structures like DICOM/0/* where files
    are nested in subdirectories.
    
    Args:
        root: Root directory path
        
    Returns:
        List of file paths found recursively
    """
    return [p for p in root.rglob("*") if p.is_file()]


def looks_like_dicom(b: bytes) -> bool:
    """
    Check if bytes look like a DICOM file by checking for DICM signature.
    
    Args:
        b: File bytes to check
        
    Returns:
        True if bytes appear to be DICOM format
    """
    if b is None or len(b) < 132:
        return False
    
    # Check for DICM signature at offset 128 (Part-10 DICOM)
    return b[128:132] == b"DICM" or b[:4] == b"DICM"
