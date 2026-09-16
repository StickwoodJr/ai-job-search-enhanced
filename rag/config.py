"""
Configuration for Curriculum RAG & Educational Grounding.

Manages connection parameters, notebook IDs, and authentication settings
for querying educational materials via the ExtendLM MCP protocol.
NO CACHING is used, per design directive.
"""

import json
import os
from pathlib import Path

# Paths
CONFIG_DIR = Path(__file__).resolve().parent
USER_CONFIG_FILE = CONFIG_DIR / "user_config.json"

# Default Notebook ID & Title (can be overridden by user_config.json or ENV)
DEFAULT_NOTEBOOK_ID = os.environ.get("NOTEBOOKLM_NOTEBOOK_ID", "[YOUR_NOTEBOOKLM_NOTEBOOK_ID]")
DEFAULT_NOTEBOOK_TITLE = os.environ.get("NOTEBOOKLM_NOTEBOOK_TITLE", "Personal Knowledge & Career Evidence")
ADDITIONAL_NOTEBOOKS = {}
RAG_ENABLED = True

# Load user-specific notebook configuration if present
if USER_CONFIG_FILE.exists():
    try:
        with open(USER_CONFIG_FILE, "r", encoding="utf-8") as f:
            u_cfg = json.load(f)
            DEFAULT_NOTEBOOK_ID = u_cfg.get("default_notebook_id", DEFAULT_NOTEBOOK_ID)
            DEFAULT_NOTEBOOK_TITLE = u_cfg.get("default_notebook_title", DEFAULT_NOTEBOOK_TITLE)
            ADDITIONAL_NOTEBOOKS = u_cfg.get("additional_notebooks", ADDITIONAL_NOTEBOOKS)
            RAG_ENABLED = u_cfg.get("enabled", True)
    except Exception:
        pass

# ExtendLM MCP endpoint
EXTENDLM_MCP_URL = os.environ.get("EXTENDLM_MCP_URL", "https://mcp.extendlm.com/mcp")

# Token file location
TOKEN_FILE_PATH = os.path.expanduser("~/.gemini/config/extendlm_token.json")

# Protocol and request timeout settings
MCP_PROTOCOL_VERSION = "2025-11-25"
REQUEST_TIMEOUT_SECONDS = 180
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 3
