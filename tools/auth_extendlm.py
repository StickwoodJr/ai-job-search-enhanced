#!/usr/bin/env python3
"""
ExtendLM MCP Authenticator for Antigravity & AI Job Search.

Wraps Claude Code native MCP OAuth login for ExtendLM to guarantee
exact client-metadata compatibility, captures authorization links,
and automatically synchronizes fresh credentials to ~/.gemini/config/extendlm_token.json.
"""

import os
import sys
import json
import time
import shutil
import subprocess
import re
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

CLAUDE_CREDS_PATH = Path.home() / ".claude" / ".credentials.json"
GEMINI_TOKEN_PATH = Path.home() / ".gemini" / "config" / "extendlm_token.json"


def find_claude_binary() -> Optional[str]:
    """Locate the claude CLI binary."""
    which_path = shutil.which("claude")
    if which_path and os.path.exists(which_path):
        return which_path

    common_paths = [
        Path.home() / ".local" / "bin" / "claude",
        Path.home() / ".npm-global" / "bin" / "claude",
        Path("/usr/local/bin/claude"),
        Path("/usr/bin/claude"),
    ]
    for p in common_paths:
        if p.exists() and os.access(p, os.X_OK):
            return str(p)
    return None


def sync_credentials_from_claude() -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Extracts ExtendLM credentials from Claude Code credentials store
    and saves them to Antigravity ~/.gemini/config/extendlm_token.json.
    """
    if not CLAUDE_CREDS_PATH.exists():
        return False, None

    try:
        with open(CLAUDE_CREDS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[!] Could not read Claude credentials: {e}")
        return False, None

    mcp_oauth = data.get("mcpOAuth", {})
    extendlm_entry = None

    for key, val in mcp_oauth.items():
        if key.startswith("extendlm") or val.get("serverName") == "extendlm":
            extendlm_entry = val
            break

    if not extendlm_entry:
        return False, None

    access_token = extendlm_entry.get("accessToken")
    if not access_token:
        return False, None

    token_payload = {
        "access_token": access_token,
        "refresh_token": extendlm_entry.get("refreshToken", ""),
        "expires_at": extendlm_entry.get("expiresAt", 0),
        "token_type": "Bearer",
        "scope": extendlm_entry.get("scope", ""),
    }

    GEMINI_TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(GEMINI_TOKEN_PATH, "w", encoding="utf-8") as f:
        json.dump(token_payload, f, indent=2)

    return True, token_payload


def start_auth_process() -> Tuple[subprocess.Popen, Optional[str]]:
    """
    Launches claude mcp login extendlm --no-browser and returns
    (process, authorization_url).
    """
    claude_bin = find_claude_binary()
    if not claude_bin:
        raise FileNotFoundError("Could not find claude CLI binary in PATH or ~/.local/bin/claude")

    proc = subprocess.Popen(
        [claude_bin, "mcp", "login", "extendlm", "--no-browser"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    auth_url = None
    start_time = time.time()

    # Read lines until we capture the authorization URL or hit timeout
    while time.time() - start_time < 15:
        line = proc.stdout.readline()
        if not line:
            if proc.poll() is not None:
                break
            time.sleep(0.1)
            continue

        match = re.search(r"(https://api\.extendlm\.com/rest/v1/mcp/oauth/authorize\S+)", line)
        if match:
            auth_url = match.group(1).strip()
            break

    return proc, auth_url


def run_interactive_auth() -> bool:
    """Executes the complete interactive authentication flow."""
    print("=" * 75)
    print("   🔑 ExtendLM MCP Authentication for Antigravity")
    print("=" * 75)

    claude_bin = find_claude_binary()
    if not claude_bin:
        print("[✗] Error: claude CLI binary was not found.")
        print("    Install Claude Code: npm install -g @anthropic-ai/claude-code")
        return False

    print("\n[*] Starting ExtendLM OAuth authentication daemon...")
    try:
        proc, auth_url = start_auth_process()
    except Exception as e:
        print(f"[✗] Failed to launch authentication process: {e}")
        return False

    if not auth_url:
        print("[!] Warning: Could not automatically parse authorization URL from output.")
        print("    Please check the running process.")
    else:
        print("\n👉 Please click or open this link in your browser:")
        print("-" * 75)
        print(auth_url)
        print("-" * 75)
        print("\nListening for callback on port 63483...")
        print("Once authorized in Chrome, this window will automatically complete.\n")

    # Let the process finish or accept redirected URL
    try:
        stdout_remaining, _ = proc.communicate(timeout=180)
        if stdout_remaining:
            for l in stdout_remaining.splitlines():
                if any(w in l for w in ["Successfully", "connected", "authenticated"]):
                    print(f"  {l}")
    except subprocess.TimeoutExpired:
        proc.kill()
        print("\n[!] Authentication timed out after 3 minutes.")
        return False
    except KeyboardInterrupt:
        proc.kill()
        print("\n[!] Authentication cancelled.")
        return False

    # Sync fresh credentials
    success, tokens = sync_credentials_from_claude()
    if success and tokens:
        exp = tokens.get("expires_at", 0)
        from datetime import datetime, timezone
        exp_dt = datetime.fromtimestamp(exp / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC") if exp else "Unknown"
        print(f"\n[✓] SUCCESS: ExtendLM authenticated successfully!")
        print(f"    Token saved to: {GEMINI_TOKEN_PATH}")
        print(f"    Expires at: {exp_dt}\n")
        return True
    else:
        print("\n[!] Authentication completed but credentials could not be synced.")
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Authenticate ExtendLM MCP for Antigravity")
    parser.add_argument("--sync-only", action="store_true", help="Sync existing credentials from Claude Code")
    args = parser.parse_args()

    if args.sync_only:
        ok, tokens = sync_credentials_from_claude()
        if ok:
            print(f"[✓] Credentials synced successfully from {CLAUDE_CREDS_PATH} to {GEMINI_TOKEN_PATH}")
            sys.exit(0)
        else:
            print(f"[✗] No valid credentials found in {CLAUDE_CREDS_PATH}")
            sys.exit(1)

    success = run_interactive_auth()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
