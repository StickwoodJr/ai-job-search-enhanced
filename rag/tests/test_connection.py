"""
Test connection to ExtendLM MCP and verify access to target notebook.
"""

import sys
import os

# Include parent directory in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DEFAULT_NOTEBOOK_ID, DEFAULT_NOTEBOOK_TITLE
from extendlm_bridge import ExtendLMBridge


def test_connection():
    print("[*] Running ExtendLM connection test...")
    bridge = ExtendLMBridge()
    conn, user_id = bridge.get_session_details()
    assert conn, "Failed: extension_connection is empty"
    assert user_id, "Failed: auth_user_id is empty"
    print(f"  [PASS] Active session established: connection={conn}, user_id={user_id}")

    print(f"[*] Verifying access to default notebook '{DEFAULT_NOTEBOOK_TITLE}'...")
    sources = bridge.list_sources(DEFAULT_NOTEBOOK_ID)
    assert len(sources) > 0, "Failed: No sources found in notebook"
    print(f"  [PASS] Retrieved {len(sources)} sources from notebook {DEFAULT_NOTEBOOK_ID}")
    print("[+] test_connection PASSED successfully.")


if __name__ == "__main__":
    test_connection()
