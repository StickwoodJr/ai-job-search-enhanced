#!/usr/bin/env python3
"""
NotebookLM Manager for Educational Curriculum RAG

Helps candidates configure, discover, or create Google NotebookLM notebooks
grounded in their coursework, lab reports, code repositories, and transcripts.

Usage:
    python rag/notebook_manager.py list              # List notebooks in your account via ExtendLM
    python rag/notebook_manager.py select <id> [name] # Set active notebook for RAG
    python rag/notebook_manager.py sources [id]       # List sources in a notebook
    python rag/notebook_manager.py scan-documents    # Scan documents/ for potential RAG sources
    python rag/notebook_manager.py status            # Show current RAG notebook configuration
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

REPO_ROOT = Path(__file__).resolve().parent.parent
RAG_DIR = REPO_ROOT / "rag"
USER_CONFIG_FILE = RAG_DIR / "user_config.json"
DOCUMENTS_DIR = REPO_ROOT / "documents"


def get_bridge():
    """Import and return ExtendLMBridge instance."""
    sys.path.insert(0, str(RAG_DIR))
    from extendlm_bridge import ExtendLMBridge
    return ExtendLMBridge()


def get_current_config() -> Dict[str, Any]:
    """Read current user RAG configuration."""
    if USER_CONFIG_FILE.exists():
        try:
            with open(USER_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "enabled": True,
        "default_notebook_id": "e32153b2-e906-4762-a8c3-8b96fbf093b4",
        "default_notebook_title": "Educational Coursework & Labs",
        "additional_notebooks": {},
    }


def save_config(cfg: Dict[str, Any]) -> None:
    """Save user RAG configuration to rag/user_config.json."""
    with open(USER_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    print(f"✓ Saved notebook configuration to {USER_CONFIG_FILE}")


def cmd_status():
    """Display active RAG configuration."""
    cfg = get_current_config()
    print("=" * 60)
    print(" 🎓 Educational Curriculum RAG Configuration")
    print("=" * 60)
    print(f"  Status:          {'Enabled' if cfg.get('enabled', True) else 'Disabled'}")
    print(f"  Active Notebook: {cfg.get('default_notebook_title', 'Untitled')}")
    print(f"  Notebook ID:     {cfg.get('default_notebook_id', 'Not Set')}")
    if cfg.get("additional_notebooks"):
        print("  Additional Notebooks:")
        for k, v in cfg["additional_notebooks"].items():
            print(f"    - {k}: {v}")
    print("=" * 60)


def cmd_list():
    """List all available NotebookLM notebooks via ExtendLM MCP."""
    print("🔍 Discovering NotebookLM notebooks via ExtendLM MCP...")
    try:
        bridge = get_bridge()
        notebooks = bridge.list_notebooks()
        if not notebooks:
            print("  No notebooks found or ExtendLM connection not established.")
            print("  Tip: Ensure Chrome is running with ExtendLM extension logged into Google NotebookLM.")
            return

        print(f"\nFound {len(notebooks)} notebooks:")
        for i, nb in enumerate(notebooks, 1):
            title = nb.get("title") or nb.get("name") or "Untitled"
            nb_id = nb.get("id") or nb.get("notebook_id")
            num_sources = len(nb.get("sources", []))
            print(f"  [{i}] {title:<40} ID: {nb_id} ({num_sources} sources)")
        print()
    except Exception as e:
        print(f"  [!] ExtendLM connection note: {e}")
        print("  You can manually set a notebook ID using:")
        print("    python rag/notebook_manager.py select <NOTEBOOK_ID> \"<NOTEBOOK_TITLE>\"")


def cmd_select(notebook_id: str, title: str = None):
    """Set the active notebook ID and title."""
    cfg = get_current_config()
    cfg["default_notebook_id"] = notebook_id
    if title:
        cfg["default_notebook_title"] = title
    save_config(cfg)
    print(f"✓ Active notebook set to: '{cfg.get('default_notebook_title')}' ({notebook_id})")


def cmd_sources(notebook_id: str = None):
    """List sources attached to the active or specified notebook."""
    cfg = get_current_config()
    target_id = notebook_id or cfg.get("default_notebook_id")
    print(f"🔍 Fetching primary coursework sources for notebook {target_id}...")
    try:
        bridge = get_bridge()
        sources = bridge.list_sources(target_id)
        if not sources:
            print("  No sources returned.")
            return

        print(f"\nAttached Coursework Sources ({len(sources)} total):")
        for s in sources[:25]:
            title = s.get("title") or s.get("name") or "Untitled source"
            s_type = s.get("type", "document")
            print(f"  - [{s_type}] {title}")
        if len(sources) > 25:
            print(f"  ... and {len(sources) - 25} more sources.")
        print()
    except Exception as e:
        print(f"  [!] Could not fetch sources: {e}")


def cmd_scan_documents():
    """Scan documents/ directory for syllabi, lab guides, transcripts to add to NotebookLM."""
    print(f"📂 Scanning {DOCUMENTS_DIR} for potential Curriculum RAG materials...")
    candidates = []
    extensions = {".pdf", ".docx", ".doc", ".txt", ".md", ".pptx", ".py", ".sh", ".pkt"}

    for root, _, files in os.walk(DOCUMENTS_DIR):
        for f in files:
            p = Path(root) / f
            if p.suffix.lower() in extensions and not p.name.startswith("."):
                candidates.append(p)

    if not candidates:
        print("  No educational documents found in documents/.")
        print("  💡 Tip: Drop your course syllabi, lab reports, assignments, or code in:")
        print("     documents/diplomas/ or documents/cv/")
        return

    print(f"\nFound {len(candidates)} document(s) suitable for your NotebookLM knowledge base:")
    for c in candidates[:20]:
        rel = c.relative_to(REPO_ROOT)
        size_kb = c.stat().st_size // 1024
        print(f"  - {rel} ({size_kb} KB)")
    if len(candidates) > 20:
        print(f"  ... and {len(candidates) - 20} more files.")

    print("\n💡 How to create your Curriculum Notebook in Google NotebookLM:")
    print("  1. Go to https://notebooklm.google.com")
    print("  2. Click 'New Notebook' and title it (e.g. 'Degree Coursework & Technical Labs')")
    print("  3. Upload the documents listed above (drag & drop PDFs, docs, markdown)")
    print("  4. Copy the Notebook ID from the browser URL: https://notebooklm.google.com/notebook/<NOTEBOOK_ID>")
    print("  5. Run: python rag/notebook_manager.py select <NOTEBOOK_ID> \"<NOTEBOOK_TITLE>\"\n")


def main():
    parser = argparse.ArgumentParser(description="NotebookLM Manager for Educational Curriculum RAG")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    subparsers.add_parser("status", help="Show active RAG notebook configuration")
    subparsers.add_parser("list", help="List available NotebookLM notebooks")
    
    sel_parser = subparsers.add_parser("select", help="Set active notebook")
    sel_parser.add_argument("notebook_id", type=str, help="Target NotebookLM Notebook ID")
    sel_parser.add_argument("title", type=str, nargs="?", default="Educational Coursework & Labs", help="Notebook Title")

    src_parser = subparsers.add_parser("sources", help="List sources in a notebook")
    src_parser.add_argument("notebook_id", type=str, nargs="?", default=None, help="Optional Notebook ID")

    subparsers.add_parser("scan-documents", help="Scan documents/ directory for RAG materials")

    args = parser.parse_args()

    if args.command == "status" or not args.command:
        cmd_status()
    elif args.command == "list":
        cmd_list()
    elif args.command == "select":
        cmd_select(args.notebook_id, args.title)
    elif args.command == "sources":
        cmd_sources(args.notebook_id)
    elif args.command == "scan-documents":
        cmd_scan_documents()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
