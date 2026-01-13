"""AFS file system search for matching files and artifacts."""

import logging
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import subprocess

logger = logging.getLogger(__name__)


class AFSSearcher:
    """Search for files in AFS storage."""
    
    def __init__(self, root_path: str, search_patterns: Optional[List[str]] = None):
        """Initialize AFS searcher.
        
        Args:
            root_path: Root path of AFS storage
            search_patterns: List of regex patterns to match files
        """
        self.root_path = Path(root_path)
        self.search_patterns = search_patterns or [".*\\.py$", ".*\\.sql$", ".*\\.ipynb$"]
        
        # Compile regex patterns
        self.compiled_patterns = [re.compile(pattern) for pattern in self.search_patterns]
    
    def search(self, query: str) -> List[Dict[str, Any]]:
        """Search for files matching the query in AFS.
        
        Args:
            query: Search query (file name, job name, table name)
        
        Returns:
            List of file references with path and last_modified
        """
        references = []
        
        if not self.root_path.exists():
            logger.warning(f"AFS root path does not exist: {self.root_path}")
            return references
        
        try:
            # Extract base name from query
            base_name = self._extract_base_name(query)
            
            # Search for files matching the query
            matching_files = self._find_matching_files(base_name)
            
            for file_path in matching_files:
                try:
                    stat_info = file_path.stat()
                    last_modified = datetime.fromtimestamp(stat_info.st_mtime).isoformat()
                    
                    references.append({
                        "path": str(file_path),
                        "last_modified": last_modified,
                        "type": "afs",
                    })
                except (OSError, PermissionError) as e:
                    logger.warning(f"Could not access file {file_path}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error searching AFS: {e}")
        
        return references
    
    def _extract_base_name(self, query: str) -> str:
        """Extract base name from query.
        
        Args:
            query: Query string (file.py, job:daily_prices, table:analytics.pnl)
        
        Returns:
            Base name to search for
        """
        if query.startswith("job:"):
            return query[4:]
        elif query.startswith("table:"):
            # Extract table name (e.g., "analytics.pnl" -> "pnl")
            table_name = query[6:]
            return table_name.split(".")[-1]
        else:
            return query
    
    def _find_matching_files(self, base_name: str) -> List[Path]:
        """Find files matching the base name in AFS.
        
        Args:
            base_name: Base name to search for
        
        Returns:
            List of matching file paths
        """
        matching_files = []
        
        try:
            # Use os.walk to traverse directory tree
            for root, dirs, files in os.walk(self.root_path):
                # Skip hidden directories
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                
                for file in files:
                    file_path = Path(root) / file
                    
                    # Check if file name contains the base name
                    if base_name.lower() in file.lower():
                        # Also check if it matches any of the search patterns
                        if any(pattern.search(file) for pattern in self.compiled_patterns):
                            matching_files.append(file_path)
        except (OSError, PermissionError) as e:
            logger.error(f"Error traversing AFS directory: {e}")
        
        return matching_files
    
    def _read_file_content(self, file_path: Path, max_size: int = 1024 * 1024) -> Optional[str]:
        """Read file content (for content-based searching).
        
        Args:
            file_path: Path to file
            max_size: Maximum file size to read (1MB default)
        
        Returns:
            File content or None if file is too large or unreadable
        """
        try:
            file_size = file_path.stat().st_size
            if file_size > max_size:
                return None
            
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception as e:
            logger.debug(f"Could not read file {file_path}: {e}")
            return None

