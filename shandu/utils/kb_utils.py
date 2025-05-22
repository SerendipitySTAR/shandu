import os
import json
import hashlib
from typing import List, Dict, Any

# Moved from shandu/cli.py - need to handle console & sanitize_error if used
# For now, utils will be more library-like, raising errors or returning status.
# Callers (CLI, nodes) will handle user-facing messages.

LOCAL_KB_DIR = os.path.expanduser("~/.shandu")
LOCAL_KB_PATH = os.path.join(LOCAL_KB_DIR, "local_kb.json")

def _ensure_kb_dir_exists():
    """Ensures the local KB directory exists."""
    os.makedirs(LOCAL_KB_DIR, exist_ok=True)

def load_local_kb() -> List[Dict[str, Any]]:
    """
    Reads LOCAL_KB_PATH, returns list of stored SourceInfo-like dicts.
    Returns empty list if file not found or error occurs.
    """
    _ensure_kb_dir_exists()
    if not os.path.exists(LOCAL_KB_PATH):
        return []
    try:
        with open(LOCAL_KB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, IOError) as e:
        # In a library function, it's often better to raise an error
        # or return a specific error indicator rather than printing.
        # For this iteration, we'll return empty list on error to match
        # the original intent of the CLI's load_local_kb.
        print(f"Error loading local knowledge base from {LOCAL_KB_PATH}: {e}") # Temporary print for debugging
        return []

def save_local_kb(kb_data: List[Dict[str, Any]]) -> bool:
    """
    Writes the list to LOCAL_KB_PATH.
    Returns True on success, False on failure.
    """
    _ensure_kb_dir_exists()
    try:
        with open(LOCAL_KB_PATH, "w", encoding="utf-8") as f:
            json.dump(kb_data, f, indent=2)
        return True
    except IOError as e:
        print(f"Error saving local knowledge base to {LOCAL_KB_PATH}: {e}") # Temporary print for debugging
        return False

def generate_kb_id(file_path: str) -> str:
    """Creates a unique ID for a knowledge base item based on its file path."""
    return hashlib.md5(file_path.encode()).hexdigest()[:10]
