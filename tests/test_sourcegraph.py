"""Tests for Sourcegraph search functionality."""

import pytest
from unittest.mock import Mock, patch
from trace.search_sourcegraph import SourcegraphSearcher


def test_sourcegraph_searcher_init():
    """Test Sourcegraph searcher initialization."""
    searcher = SourcegraphSearcher(
        endpoint="https://test.sourcegraph.com/.api/graphql",
        token="test-token",
        timeout=60,
        max_retries=2,
    )
    
    assert searcher.endpoint == "https://test.sourcegraph.com/.api/graphql"
    assert searcher.token == "test-token"
    assert searcher.timeout == 60
    assert searcher.max_retries == 2


def test_build_search_query():
    """Test building Sourcegraph search queries."""
    searcher = SourcegraphSearcher(endpoint="https://test.com/.api/graphql")
    
    # File name query
    query = searcher._build_search_query("file.py")
    assert "file.py" in query
    
    # Job query
    query = searcher._build_search_query("job:daily_prices")
    assert "daily_prices" in query
    
    # Table query
    query = searcher._build_search_query("table:analytics.pnl")
    assert "analytics.pnl" in query


def test_parse_search_results():
    """Test parsing Sourcegraph API response."""
    searcher = SourcegraphSearcher(endpoint="https://test.com/.api/graphql")
    
    response = {
        "data": {
            "search": {
                "results": {
                    "results": [
                        {
                            "__typename": "FileMatch",
                            "file": {
                                "path": "test/file.py",
                                "url": "https://sourcegraph.com/test/file.py",
                            },
                            "repository": {
                                "name": "test-repo",
                            },
                        }
                    ]
                }
            }
        }
    }
    
    results = searcher._parse_search_results(response, "test")
    assert len(results) == 1
    assert results[0]["path"] == "test/file.py"
    assert results[0]["repo"] == "test-repo"


def test_parse_empty_results():
    """Test parsing empty API response."""
    searcher = SourcegraphSearcher(endpoint="https://test.com/.api/graphql")
    
    response = {"data": {}}
    results = searcher._parse_search_results(response, "test")
    assert results == []

