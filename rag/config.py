"""
Configuration for RAG Experiment.

Manages connection parameters, notebook IDs, and authentication settings
for querying educational materials via the ExtendLM MCP protocol.
NO CACHING is used, per design directive.
"""

import os

# Default Notebook ID for Seneca CTY Year 1 (Semesters 1 and 2)
DEFAULT_NOTEBOOK_ID = "e32153b2-e906-4762-a8c3-8b96fbf093b4"
DEFAULT_NOTEBOOK_TITLE = "Semester 1 and 2 CTY"

# Additional Notebook IDs for reference or future extension
ADDITIONAL_NOTEBOOKS = {
    "semester_3": "467dc467-d492-4d50-8b20-0a157bd444db",  # Seneca CTY Semester 3 Syllabi
}

# ExtendLM MCP endpoint
EXTENDLM_MCP_URL = os.environ.get("EXTENDLM_MCP_URL", "https://mcp.extendlm.com/mcp")

# Token file location
TOKEN_FILE_PATH = os.path.expanduser("~/.gemini/config/extendlm_token.json")

# Protocol and request timeout settings
MCP_PROTOCOL_VERSION = "2025-11-25"
REQUEST_TIMEOUT_SECONDS = 180
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 3
