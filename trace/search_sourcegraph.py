"""Sourcegraph API integration for code reference search."""

import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
import requests
from requests_kerberos import HTTPKerberosAuth

logger = logging.getLogger(__name__)


class SourcegraphSearcher:
    """Search for code references using Sourcegraph API."""
    
    def __init__(self, endpoint: str, token: Optional[str] = None, timeout: int = 30, max_retries: int = 3):
        """Initialize Sourcegraph searcher.
        
        Args:
            endpoint: Sourcegraph GraphQL API endpoint
            token: Optional API token (Kerberos will be used primarily)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries on failure
        """
        self.endpoint = endpoint
        self.token = token
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Set up authentication (Kerberos SSO)
        self.auth = HTTPKerberosAuth(mutual_authentication="OPTIONAL")
        self.headers = {
            "Content-Type": "application/json",
        }
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"
    
    def search_references(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Search for code references.
        
        Args:
            query: Search query (file name, job name, table name, etc.)
            limit: Maximum number of results to return
        
        Returns:
            List of reference dictionaries with path, repo, last_modified, author
        """
        # GraphQL query for code search
        graphql_query = """
        query SearchReferences($query: String!, $first: Int!) {
            search(query: $query, first: $first) {
                results {
                    results {
                        __typename
                        ... on FileMatch {
                            file {
                                path
                                url
                            }
                            repository {
                                name
                            }
                            lineMatches {
                                lineNumber
                                offsetAndLengths
                                preview
                            }
                        }
                        ... on Repository {
                            name
                        }
                    }
                }
            }
        }
        """
        
        # Alternative: Use Search query type for more flexible searching
        search_query = self._build_search_query(query)
        
        variables = {
            "query": search_query,
            "first": limit,
        }
        
        payload = {
            "query": graphql_query,
            "variables": variables,
        }
        
        try:
            response = self._make_request(payload)
            return self._parse_search_results(response, query)
        except Exception as e:
            logger.error(f"Error searching Sourcegraph: {e}")
            return []
    
    def _build_search_query(self, query: str) -> str:
        """Build Sourcegraph search query from input.
        
        Args:
            query: Original query (file name, job:daily_prices, table:analytics.pnl)
        
        Returns:
            Sourcegraph search query string
        """
        # Handle different query types
        if query.startswith("job:"):
            job_name = query[4:]
            return f'type:file "{job_name}" (lang:python OR lang:yaml OR lang:json)'
        elif query.startswith("table:"):
            table_name = query[6:]
            return f'type:file "{table_name}" (lang:sql OR lang:python)'
        else:
            # File name search
            return f'type:file "{query}"'
    
    def _make_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make HTTP request to Sourcegraph API with retries.
        
        Args:
            payload: Request payload
        
        Returns:
            Response JSON data
        
        Raises:
            requests.RequestException: If request fails after retries
        """
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self.endpoint,
                    json=payload,
                    headers=self.headers,
                    auth=self.auth,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Request failed after {self.max_retries} attempts: {e}")
                    raise
        
        return {}
    
    def _parse_search_results(self, response: Dict[str, Any], original_query: str) -> List[Dict[str, Any]]:
        """Parse Sourcegraph API response into reference list.
        
        Args:
            response: API response JSON
            original_query: Original search query
        
        Returns:
            List of reference dictionaries
        """
        references = []
        
        try:
            search_results = response.get("data", {}).get("search", {}).get("results", {}).get("results", [])
            
            for result in search_results:
                if result.get("__typename") == "FileMatch":
                    file_info = result.get("file", {})
                    repo_info = result.get("repository", {})
                    
                    references.append({
                        "path": file_info.get("path", ""),
                        "repo": repo_info.get("name", ""),
                        "url": file_info.get("url", ""),
                        "last_modified": None,  # Sourcegraph API doesn't provide this directly
                        "author": None,  # Would need separate API call for git blame
                        "type": "code",
                    })
        except Exception as e:
            logger.error(f"Error parsing search results: {e}")
        
        return references
    
    def get_file_blame_info(self, repo: str, file_path: str) -> Dict[str, Any]:
        """Get git blame information for a file (last modified, author).
        
        Note: This requires additional Sourcegraph API calls and may not be available
        in all Sourcegraph instances.
        
        Args:
            repo: Repository name
            file_path: File path in repository
        
        Returns:
            Dictionary with last_modified and author
        """
        # This would require additional GraphQL queries to get commit history
        # For now, return placeholder
        return {
            "last_modified": None,
            "author": None,
        }

