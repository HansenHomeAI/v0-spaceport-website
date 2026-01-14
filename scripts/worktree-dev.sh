#!/usr/bin/env bash
# Quick wrapper for managing worktree dev servers

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/manage_worktree_dev_servers.py" "$@"
