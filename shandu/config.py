"""Configuration management module."""
import os
import json
from typing import Dict, Any, Optional
from pathlib import Path
import datetime

DEFAULT_CONFIG = {
    "api": {
        "base_url": "http://localhost:8321/v1",
        "api_key": "sctest",
        "model": "gpt-4o-2024-08-06",
        "temperature": 0.6,
        "max_tokens": 131072,
    },
    "search": {
        "engines": ["duckduckgo", "wikipedia", "bing"],  # Removed google as default to avoid rate limits
        "max_results": 8,  # Reduced to be more conservative
        "region": "wt-wt",
        "safesearch": "moderate",
        "user_agent": "ShanduResearchAgent/1.0",
        "google_rate_limit_delay": 3.0,  # Minimum delay between Google searches
        "max_retries": 3,  # Maximum retry attempts for failed searches
        "enable_google_fallback": False  # Only use Google as last resort
    },
    "research": {
        "default_depth": 2,
        "default_breadth": 4,
        "max_depth": 5,
        "max_breadth": 10,
        "max_urls_per_query": 3
    },
    "scraper": {
        "timeout": 30,
        "max_retries": 3,
        "chunk_size": 1000,
        "chunk_overlap": 200,
        "proxy": None
    },
    "display": {
        "verbose": False,
        "show_progress": True,
        "show_chain_of_thought": True
    }
}

class Config:
    """Configuration manager."""
    
    def __init__(self):
        self._config = DEFAULT_CONFIG.copy()
        self._config_path = os.path.expanduser("~/.shandu/config.json")
        self._load_config()
        self._load_env_vars()
        
    def _load_config(self):
        """Load config from file."""
        config_path = Path(self._config_path)
        if config_path.exists():
            try:
                with open(config_path) as f:
                    file_config = json.load(f)
                    self._update_nested_dict(self._config, file_config)
            except Exception as e:
                print(f"Error loading config file: {e}")
    
    def _load_env_vars(self):
        """Load config from environment variables."""
        if os.environ.get("OPENAI_API_BASE"):
            self._config["api"]["base_url"] = os.environ["OPENAI_API_BASE"]
        if os.environ.get("OPENAI_API_KEY"):
            self._config["api"]["api_key"] = os.environ["OPENAI_API_KEY"]
        if os.environ.get("OPENAI_MODEL_NAME"):
            self._config["api"]["model"] = os.environ["OPENAI_MODEL_NAME"]
        
        if os.environ.get("SHANDU_PROXY"):
            self._config["scraper"]["proxy"] = os.environ["SHANDU_PROXY"]
            
        if os.environ.get("USER_AGENT"):
            self._config["search"]["user_agent"] = os.environ["USER_AGENT"]
    
    def _update_nested_dict(self, d: Dict, u: Dict):
        """Update nested dictionary."""
        for k, v in u.items():
            if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                self._update_nested_dict(d[k], v)
            else:
                d[k] = v
    
    def save(self):
        """Save config to file."""
        config_path = Path(self._config_path)
        config_path.parent.mkdir(exist_ok=True, parents=True)
        with open(config_path, "w") as f:
            json.dump(self._config, f, indent=2)
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Get config value."""
        try:
            return self._config[section][key]
        except KeyError:
            return default
    
    def set(self, section: str, key: str, value: Any):
        """Set config value."""
        if section not in self._config:
            self._config[section] = {}
        self._config[section][key] = value
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get config section."""
        return self._config.get(section, {}).copy()
    
    def get_all(self) -> Dict[str, Any]:
        """Get all config."""
        return self._config.copy()

config = Config()

def get_current_date() -> str:
    """Get current date."""
    return datetime.datetime.now().strftime("%Y-%m-%d")

def get_current_datetime() -> str:
    """Get current date and time."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_user_agent() -> str:
    """Get user agent string."""
    configured_agent = config.get("search", "user_agent", None)
    if configured_agent and configured_agent != "Research 1.0":
        return configured_agent
    
    try:
        from fake_useragent import UserAgent
        ua = UserAgent()
        return ua.random
    except ImportError:
        import random
        fake_user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
        ]
        return random.choice(fake_user_agents)
    except Exception as e:
        print(f"Error generating user agent: {e}")
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
