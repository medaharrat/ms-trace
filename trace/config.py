"""Configuration management for the trace tool."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class Config:
    """Configuration manager for trace tool."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration.
        
        Args:
            config_path: Path to config.yaml file. If None, looks for config.yaml
                         in current directory, then in ~/.trace/config.yaml
        """
        if config_path is None:
            # Try current directory first, then home directory
            current_dir_config = Path.cwd() / "config.yaml"
            home_config = Path.home() / ".trace" / "config.yaml"
            
            if current_dir_config.exists():
                config_path = str(current_dir_config)
            elif home_config.exists():
                config_path = str(home_config)
            else:
                # Use default config
                config_path = None
        
        if config_path and Path(config_path).exists():
            with open(config_path, "r") as f:
                self._config = yaml.safe_load(f) or {}
        else:
            self._config = {}
        
        # Set defaults
        self._set_defaults()
    
    def _set_defaults(self):
        """Set default configuration values."""
        defaults = {
            "sourcegraph": {
                "endpoint": "https://sourcegraph.example.com/.api/graphql",
                "token": "",
            },
            "afs": {
                "root_path": "/afs/project",
                "search_patterns": [".*\\.py$", ".*\\.sql$", ".*\\.ipynb$"],
            },
            "llm": {
                "enabled": False,
                "provider": "openai",
                "model": "gpt-4",
                "api_key": os.getenv("LLM_API_KEY", ""),
                "base_url": "",
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
            "performance": {
                "max_workers": 4,
                "request_timeout": 30,
                "max_retries": 3,
            },
        }
        
        # Merge defaults with user config
        for key, default_value in defaults.items():
            if key not in self._config:
                self._config[key] = default_value
            elif isinstance(default_value, dict):
                for subkey, subvalue in default_value.items():
                    if subkey not in self._config[key]:
                        self._config[key][subkey] = subvalue
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key (supports nested keys with dots).
        
        Args:
            key: Configuration key, e.g., "sourcegraph.endpoint"
            default: Default value if key not found
        
        Returns:
            Configuration value
        """
        keys = key.split(".")
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_sourcegraph_endpoint(self) -> str:
        """Get Sourcegraph API endpoint."""
        return self.get("sourcegraph.endpoint", "https://sourcegraph.example.com/.api/graphql")
    
    def get_sourcegraph_token(self) -> str:
        """Get Sourcegraph API token (optional)."""
        return self.get("sourcegraph.token", "")
    
    def get_afs_root_path(self) -> str:
        """Get AFS root path."""
        return self.get("afs.root_path", "/afs/project")
    
    def get_afs_search_patterns(self) -> list:
        """Get AFS search patterns."""
        return self.get("afs.search_patterns", [".*\\.py$", ".*\\.sql$", ".*\\.ipynb$"])
    
    def is_llm_enabled(self) -> bool:
        """Check if LLM summarization is enabled."""
        return self.get("llm.enabled", False)
    
    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration."""
        return self.get("llm", {})
    
    def get_log_level(self) -> str:
        """Get logging level."""
        return self.get("logging.level", "INFO")
    
    def get_max_workers(self) -> int:
        """Get maximum number of worker threads."""
        return self.get("performance.max_workers", 4)
    
    def get_request_timeout(self) -> int:
        """Get request timeout in seconds."""
        return self.get("performance.request_timeout", 30)
    
    def get_max_retries(self) -> int:
        """Get maximum number of retries."""
        return self.get("performance.max_retries", 3)

