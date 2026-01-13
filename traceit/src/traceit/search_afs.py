"""AFS file system search for matching files and artifacts."""

import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

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
        self.search_patterns = search_patterns or [
            ".*\\.py$",
            ".*\\.sql$",
            ".*\\.ipynb$",
        ]

        # Compile regex patterns
        self.compiled_patterns = [
            re.compile(pattern) for pattern in self.search_patterns
        ]

    def search(self, query: str, timeout: Optional[float] = None, max_depth: int = 1) -> List[Dict[str, Any]]:
        """Search for files matching the query in AFS.

        Args:
            query: Search query (file name, job name, table name)
            timeout: Maximum time in seconds to allow for search (optional)
            max_depth: Maximum directory depth for recursive search (default 1)

        Returns:
            List of file references with path and last_modified
        """
        import queue
        import threading
        references = []
        result_queue = queue.Queue()

        def _ping_afs_location(path: Path) -> bool:
            # Try to list the directory to check if reachable
            try:
                if path.exists() and path.is_dir():
                    # Try listing contents
                    _ = next(path.iterdir(), None)
                    return True
                return False
            except Exception as e:
                logger.warning(f"Ping failed for AFS location {path}: {e}")
                return False

        def search_worker():
            try:
                if not _ping_afs_location(self.root_path):
                    logger.warning(f"AFS root path is not reachable: {self.root_path}")
                    result_queue.put([])
                    return
                base_name = self._extract_base_name(query)
                matching_files = self._find_matching_files(base_name, max_depth=max_depth)
                refs = []
                for file_path in matching_files:
                    try:
                        stat_info = file_path.stat()
                        last_modified = datetime.fromtimestamp(
                            stat_info.st_mtime
                        ).isoformat()
                        refs.append(
                            {
                                "path": str(file_path),
                                "last_modified": last_modified,
                                "type": "afs",
                            }
                        )
                    except (OSError, PermissionError) as e:
                        logger.warning(f"Could not access file {file_path}: {e}")
                        continue
                result_queue.put(refs)
            except Exception as e:
                logger.error(f"Error searching AFS: {e}")
                result_queue.put([])

        import sys
        try:
            t = threading.Thread(target=search_worker)
            t.start()
            t.join(timeout)
            if t.is_alive():
                logger.error(f"AFS search timed out after {timeout} seconds.")
                return []
            return result_queue.get()
        except KeyboardInterrupt:
            logger.warning("AFS search interrupted by user (SIGINT)")
            # Optionally, clean up resources or stop thread if needed
            sys.exit(1)

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

    def _find_matching_files(self, base_name: str, max_depth: int = 1) -> List[Path]:
        """Find files matching the base name in AFS.

        Args:
            base_name: Base name to search for
            max_depth: Maximum directory depth for recursive search

        Returns:
            List of matching file paths
        """
        matching_files = []

        try:
            # Use os.walk to traverse directory tree with depth control
            root_depth = len(self.root_path.parts)
            for root, dirs, files in os.walk(self.root_path):
                current_depth = len(Path(root).parts) - root_depth
                if current_depth >= max_depth:
                    # Prevent descending further
                    dirs[:] = []
                else:
                    # Skip hidden directories
                    dirs[:] = [d for d in dirs if not d.startswith(".")]

                for file in files:
                    file_path = Path(root) / file
                    if base_name.lower() in file.lower():
                        if any(
                            pattern.search(file) for pattern in self.compiled_patterns
                        ):
                            matching_files.append(file_path)
        except (OSError, PermissionError) as e:
            logger.error(f"Error traversing AFS directory: {e}")

        return matching_files

    def _read_file_content(
        self, file_path: Path, max_size: int = 1024 * 1024
    ) -> Optional[str]:
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
