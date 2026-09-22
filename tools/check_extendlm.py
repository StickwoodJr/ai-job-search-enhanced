#!/usr/bin/env python3
"""
ExtendLM Pre-flight Health Check & Diagnostic Tool.

Verifies that ExtendLM is fully operational before attempting any RAG workflows:
1. Validates token existence and checks for expiration.
2. Tests connection to ExtendLM MCP endpoint (https://mcp.extendlm.com/mcp).
3. Verifies active Google Chrome extension connection.
4. Provides clear instructions and tools to fix authentication or connection issues.
"""

import sys
import os
import json
import time
import argparse
from datetime import datetime, timezone
from typing import Dict, Any, Tuple

REAL_FILE = os.path.realpath(__file__)
REPO_ROOT = os.path.dirname(os.path.dirname(REAL_FILE))
TOKEN_PATH = os.path.expanduser("~/.gemini/config/extendlm_token.json")
AUTH_SCRIPT = os.path.join(REPO_ROOT, "tools", "auth_extendlm.py")



def check_token_file() -> Tuple[bool, str, Dict[str, Any]]:
    """Checks whether the token file exists and is valid."""
    # First check if Claude Code credentials have a valid/newer token
    try:
        from auth_extendlm import sync_credentials_from_claude
        sync_credentials_from_claude()
    except Exception:
        pass

    if not os.path.exists(TOKEN_PATH):
        return False, "TOKEN_MISSING", {
            "error": "No token file found at ~/.gemini/config/extendlm_token.json",
            "fix": f'Run `auth-extendlm` or `python3 "{AUTH_SCRIPT}"` to authenticate.'
        }

    try:
        with open(TOKEN_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return False, "TOKEN_CORRUPT", {
            "error": f"Failed to read token file: {e}",
            "fix": f'Re-run authentication: `auth-extendlm` or `python3 "{AUTH_SCRIPT}"`'
        }

    token = data.get("access_token")
    if not token:
        return False, "TOKEN_EMPTY", {
            "error": "Token file exists but contains no access_token.",
            "fix": f'Re-run authentication: `auth-extendlm` or `python3 "{AUTH_SCRIPT}"`'
        }

    expires_at = data.get("expires_at", 0)
    current_ms = int(time.time() * 1000)

    if expires_at and current_ms > expires_at:
        diff_hours = (current_ms - expires_at) / (1000 * 3600)
        exp_dt = datetime.fromtimestamp(expires_at / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        return False, "TOKEN_EXPIRED", {
            "error": f"Access token expired on {exp_dt} (~{diff_hours:.1f} hours ago).",
            "expires_at": expires_at,
            "fix": f'Re-run authentication: `auth-extendlm` or `python3 "{AUTH_SCRIPT}"`'
        }

    return True, "TOKEN_VALID", data


def check_live_api(token_data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
    """Tests live communication with ExtendLM MCP server and verifies browser connection."""
    sys.path.insert(0, os.path.join(REPO_ROOT, "RAG Experiment"))
    try:
        from extendlm_bridge import ExtendLMBridge
    except ImportError:
        try:
            from rag.extendlm_bridge import ExtendLMBridge
        except ImportError:
            return False, "BRIDGE_MISSING", {"error": "Could not import ExtendLMBridge."}

    bridge = ExtendLMBridge(auth_token=token_data.get("access_token"))

    # Test list_notebook_users
    try:
        res = bridge.call_tool("list_notebook_users", {})
    except Exception as e:
        return False, "NETWORK_ERROR", {
            "error": f"Failed to connect to ExtendLM MCP endpoint: {e}",
            "fix": "Check your internet connection."
        }

    if "error" in res:
        err_msg = str(res["error"])
        if "401" in err_msg or "Unauthorized" in err_msg:
            return False, "UNAUTHORIZED", {
                "error": f"ExtendLM MCP returned HTTP 401 Unauthorized: {err_msg}",
                "fix": f'Your OAuth token was rejected. Run `auth-extendlm` or `python3 "{AUTH_SCRIPT}"`.'
            }
        return False, "API_ERROR", {
            "error": f"ExtendLM MCP API returned an error: {err_msg}",
            "fix": "Check the ExtendLM service status."
        }

    conns = res.get("connections", [])
    if not conns:
        return False, "NO_BROWSER_CONNECTION", {
            "error": "No active ExtendLM browser extension connection found.",
            "fix": (
                "Ensure Google Chrome is open with the ExtendLM extension enabled "
                "and an active tab open to https://notebooklm.google.com/."
            )
        }

    # Extract user details
    conn_id = conns[0].get("extension_connection")
    users = conns[0].get("users", [])
    user_email = users[0].get("email", "Unknown") if users else "Default"

    return True, "READY", {
        "status": "connected",
        "connection_id": conn_id,
        "user_email": user_email,
        "users_count": len(users)
    }


def diagnose_extendlm(verbose: bool = True) -> Dict[str, Any]:
    """Runs the full diagnostic suite and returns structured results."""
    token_ok, token_status, token_info = check_token_file()

    if not token_ok:
        result = {
            "ready": False,
            "status": token_status,
            "error": token_info.get("error"),
            "fix": token_info.get("fix"),
        }
        if verbose:
            print_diagnostic_report(result)
        return result

    api_ok, api_status, api_info = check_live_api(token_info)

    if not api_ok:
        result = {
            "ready": False,
            "status": api_status,
            "error": api_info.get("error"),
            "fix": api_info.get("fix"),
        }
        if verbose:
            print_diagnostic_report(result)
        return result

    result = {
        "ready": True,
        "status": "READY",
        "details": api_info,
    }
    if verbose:
        print_diagnostic_report(result)
    return result


def print_diagnostic_report(diag: Dict[str, Any]):
    """Prints a clear, formatted status banner."""
    print("=" * 72)
    print("   🔍 EXTENDLM PRE-FLIGHT SYSTEM HEALTH CHECK")
    print("=" * 72)

    if diag.get("ready"):
        details = diag.get("details", {})
        print("  Status: [✓] FULLY OPERATIONAL")
        print(f"  Browser Connection: Active ({details.get('connection_id', 'N/A')})")
        print(f"  Authenticated User: {details.get('user_email', 'Active')}")
        print("\n  ExtendLM is connected and ready for live RAG retrieval.")
    else:
        status = diag.get("status")
        print(f"  Status: [✗] NOT READY ({status})")
        print(f"  Detail: {diag.get('error')}")
        print("\n  👉 Action Required to Fix:")
        print(f"     {diag.get('fix')}")

    print("=" * 72)


def ensure_extendlm_ready(auto_auth: bool = True, halt_on_error: bool = True) -> bool:
    """
    Programmatic helper to be called at the start of any RAG script.
    1. Checks if ExtendLM is ready.
    2. If not ready (token missing/expired/unauthorized) and auto_auth is True:
       Automatically launches authentication, prints the click link, and waits for user.
    3. If still not ready, either raises RuntimeError (halt_on_error=True) or returns False.
    """
    diag = diagnose_extendlm(verbose=False)
    if diag.get("ready"):
        return True

    print_diagnostic_report(diag)

    if auto_auth and diag.get("status") in ("TOKEN_EXPIRED", "TOKEN_MISSING", "TOKEN_EMPTY", "UNAUTHORIZED"):
        print("\n[*] Token expired or missing. Launching ExtendLM authenticator...")
        try:
            from auth_extendlm import run_interactive_auth
            auth_ok = run_interactive_auth()
            if auth_ok:
                diag = diagnose_extendlm(verbose=True)
                if diag.get("ready"):
                    return True
        except Exception as e:
            print(f"[!] Authentication flow error: {e}")

    if halt_on_error:
        raise RuntimeError(f"ExtendLM is not ready: {diag.get('error')}")
    return False


def main():
    parser = argparse.ArgumentParser(description="Check ExtendLM MCP Status & Diagnostics")
    parser.add_argument("--json", action="store_true", help="Output JSON results")
    parser.add_argument("--auth", action="store_true", help="Launch OAuth authentication immediately if not ready")

    args = parser.parse_args()
    diag = diagnose_extendlm(verbose=not args.json)

    if args.json:
        print(json.dumps(diag, indent=2))

    if not diag.get("ready"):
        if args.auth:
            print("\n[*] Launching ExtendLM OAuth Authenticator...")
            os.system(f'python3 "{AUTH_SCRIPT}"')
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
