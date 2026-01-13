"""Tests for AFS search functionality."""

import pytest
import tempfile
from pathlib import Path
from traceit.search_afs import AFSSearcher


def test_afs_searcher_init():
    """Test AFS searcher initialization."""
    searcher = AFSSearcher(root_path="/tmp/test", search_patterns=[".*\\.py$"])
    assert searcher.root_path == Path("/tmp/test")
    assert len(searcher.compiled_patterns) == 1


def test_extract_base_name():
    """Test extraction of base name from query."""
    searcher = AFSSearcher(root_path="/tmp/test")
    
    assert searcher._extract_base_name("file.py") == "file.py"
    assert searcher._extract_base_name("job:daily_prices") == "daily_prices"
    assert searcher._extract_base_name("table:analytics.pnl") == "pnl"


def test_afs_search_nonexistent_path():
    """Test AFS search with nonexistent path."""
    searcher = AFSSearcher(root_path="/nonexistent/path/12345")
    results = searcher.search("test.py")
    assert results == []


def test_afs_search_in_temp_dir():
    """Test AFS search in temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        test_file = Path(tmpdir) / "test_file.py"
        test_file.write_text("# Test file")
        
        searcher = AFSSearcher(root_path=tmpdir, search_patterns=[".*\\.py$"])
        results = searcher.search("test_file")
        
        assert len(results) >= 1
        assert any("test_file.py" in r["path"] for r in results)

