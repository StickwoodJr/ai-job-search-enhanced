"""
ExtendLM MCP Bridge for RAG Experiment.

Handles low-level JSON-RPC communication with the ExtendLM MCP server
(https://mcp.extendlm.com/mcp) over HTTP Server-Sent Events (SSE).
Exposes methods for notebook discovery, source listing, and live source-grounded querying.
"""

import json
import os
import time
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional, Tuple

try:
    from .config import (
        EXTENDLM_MCP_URL,
        TOKEN_FILE_PATH,
        MCP_PROTOCOL_VERSION,
        REQUEST_TIMEOUT_SECONDS,
        MAX_RETRIES,
        RETRY_BACKOFF_SECONDS,
    )
except ImportError:
    from config import (
        EXTENDLM_MCP_URL,
        TOKEN_FILE_PATH,
        MCP_PROTOCOL_VERSION,
        REQUEST_TIMEOUT_SECONDS,
        MAX_RETRIES,
        RETRY_BACKOFF_SECONDS,
    )


class ExtendLMBridge:
    """Client for querying Gemini NotebookLM via ExtendLM MCP."""

    def __init__(self, base_url: str = EXTENDLM_MCP_URL, auth_token: Optional[str] = None):
        self.base_url = base_url
        file_token = ""
        if os.path.exists(TOKEN_FILE_PATH):
            try:
                with open(TOKEN_FILE_PATH, "r", encoding="utf-8") as tf:
                    t_data = json.load(tf)
                    file_token = t_data.get("access_token", "")
            except Exception:
                pass
        self.auth_token = auth_token or os.environ.get("EXTENDLM_AUTH_TOKEN", "") or file_token
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": MCP_PROTOCOL_VERSION,
            "User-Agent": "Antigravity-RAG-Experiment/1.0",
        }
        if self.auth_token:
            self.headers["Authorization"] = f"Bearer {self.auth_token}"
        self._connection: Optional[str] = None
        self._user_id: Optional[str] = None

    def call_mcp(
        self,
        method: str,
        params: Dict[str, Any],
        rpc_id: int = 1,
        retries: int = MAX_RETRIES,
        timeout: int = REQUEST_TIMEOUT_SECONDS,
    ) -> Dict[str, Any]:
        """Sends a JSON-RPC request to the MCP endpoint and parses the SSE/JSON response."""
        payload = {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "method": method,
            "params": params,
        }

        last_err = None
        for attempt in range(1, retries + 1):
            req = urllib.request.Request(
                self.base_url,
                data=json.dumps(payload).encode("utf-8"),
                headers=self.headers,
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    raw = resp.read().decode("utf-8")
                    for line in raw.splitlines():
                        if line.startswith("data: "):
                            data = json.loads(line[6:])
                            res = data.get("result", {})
                            if "content" in res and isinstance(res["content"], list):
                                first = res["content"][0]
                                if first.get("type") == "text":
                                    try:
                                        return json.loads(first.get("text", "{}"))
                                    except Exception:
                                        return {"text": first.get("text", "")}
                            return res
                    return {}
            except Exception as e:
                last_err = e
                if attempt < retries:
                    time.sleep(RETRY_BACKOFF_SECONDS * attempt)

        return {"error": str(last_err), "status": "failed"}

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Executes a named MCP tool."""
        return self.call_mcp("tools/call", {"name": tool_name, "arguments": arguments})

    def get_session_details(self) -> Tuple[str, str]:
        """Discovers active extension_connection and auth_user_id."""
        if self._connection and self._user_id:
            return self._connection, self._user_id

        res = self.call_tool("list_notebook_users", {})
        if "error" in res:
            err_msg = str(res["error"])
            if "401" in err_msg or "Unauthorized" in err_msg:
                raise RuntimeError(
                    f"ExtendLM authentication failed (HTTP 401 Unauthorized). "
                    "Your OAuth Bearer token in ~/.gemini/config/extendlm_token.json is expired or invalid. "
                    "Please re-authenticate ExtendLM."
                )
            raise RuntimeError(f"ExtendLM API error: {err_msg}")

        conns = res.get("connections", [])
        if not conns:
            raise RuntimeError(
                "No active ExtendLM browser extension connection found. "
                "Ensure Chrome is running with ExtendLM extension active."
            )

        self._connection = conns[0]["extension_connection"]
        users = conns[0].get("users", [])
        for u in users:
            if u.get("is_selected"):
                self._user_id = u.get("auth_user_id")
                break
        if not self._user_id and users:
            self._user_id = users[0].get("auth_user_id")
        return self._connection, self._user_id or "0"

    def list_notebooks(self) -> List[Dict[str, Any]]:
        """Lists all available Gemini Notebooks."""
        conn, user_id = self.get_session_details()
        res = self.call_tool("list_notebooks", {
            "extension_connection": conn,
            "auth_user_id": user_id,
        })
        return res.get("items", []) or res.get("notebooks", [])

    def list_sources(self, notebook_id: str) -> List[Dict[str, Any]]:
        """Lists all attached sources in a target notebook."""
        conn, user_id = self.get_session_details()
        res = self.call_tool("list_notebook_sources", {
            "extension_connection": conn,
            "auth_user_id": user_id,
            "notebook_id": notebook_id,
        })
        return res.get("items", [])

    def ask_notebook(
        self,
        notebook_id: str,
        question: str,
        source_ids: Optional[List[str]] = None,
    ) -> str:
        """
        Executes a live query against Gemini NotebookLM.
        Zero caching is applied; every invocation performs a fresh source-grounded query.
        """
        conn, user_id = self.get_session_details()
        args: Dict[str, Any] = {
            "extension_connection": conn,
            "auth_user_id": user_id,
            "notebook_id": notebook_id,
            "question": question,
        }
        if source_ids:
            args["source_ids"] = source_ids

        for attempt in range(1, MAX_RETRIES + 1):
            res = self.call_tool("ask_notebook", args)
            if isinstance(res, dict):
                if res.get("code") == "chat_failed" or res.get("retryable"):
                    if attempt < MAX_RETRIES:
                        time.sleep(RETRY_BACKOFF_SECONDS * attempt + 2)
                        continue
                if "answer" in res:
                    return res["answer"]
                if "text" in res:
                    return res["text"]
                if "error" in res:
                    raise RuntimeError(f"ExtendLM Error: {res['error']}")
                return json.dumps(res, indent=2)
            return str(res)

        return json.dumps(res, indent=2) if isinstance(res, dict) else str(res)
