#!/usr/bin/env python3
"""
Playwright MCP Server Manager
Handles starting/stopping the Playwright MCP server for the agentic dev loop.
"""

import argparse
import json
import os
import shlex
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import List

PLAYWRIGHT_MCP_PORT = int(os.environ.get("PLAYWRIGHT_MCP_PORT", "5174"))
PID_FILE = Path.home() / ".agentic" / "playwright-mcp.pid"

def is_server_running() -> bool:
    """Check if Playwright MCP server is already running."""
    if not PID_FILE.exists():
        return False
    
    try:
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        
        # Check if process is still running
        os.kill(pid, 0)  # This will raise OSError if process doesn't exist
        return True
    except (OSError, ValueError):
        # Process doesn't exist or PID file is invalid
        PID_FILE.unlink(missing_ok=True)
        return False

def _is_port_available(port: int) -> bool:
    """Return True if the TCP port can be bound on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def _candidate_commands() -> List[List[str]]:
    """Compute launch command candidates for the MCP server."""
    commands: List[List[str]] = []

    override = os.environ.get("PLAYWRIGHT_MCP_COMMAND")
    if override:
        commands.append(shlex.split(override))

    headless_cmd = ["npx", "@playwright/mcp@latest", "--headless"]
    if _is_port_available(PLAYWRIGHT_MCP_PORT):
        headless_cmd += ["--port", str(PLAYWRIGHT_MCP_PORT)]
    commands.append(headless_cmd)

    legacy_cmd = ["playwright-mcp", "server", "--port", str(PLAYWRIGHT_MCP_PORT)]
    commands.append(legacy_cmd)

    return commands


def start_server() -> bool:
    """Start the Playwright MCP server in the background."""
    if is_server_running():
        print(f"Playwright MCP server already running on port {PLAYWRIGHT_MCP_PORT}")
        return True

    # Ensure .agentic directory exists so we can persist the PID.
    PID_FILE.parent.mkdir(exist_ok=True)

    last_error: Exception | None = None
    for command in _candidate_commands():
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid
            )
        except FileNotFoundError as exc:
            last_error = exc
            continue
        except Exception as exc:  # pylint: disable=broad-except
            last_error = exc
            continue

        time.sleep(2)
        if process.poll() is not None:
            last_error = RuntimeError(f"Command {' '.join(command)} exited with code {process.returncode}")
            continue

        with open(PID_FILE, 'w') as f:
            f.write(str(process.pid))

        print(f"Playwright MCP server started via {' '.join(command)} (PID: {process.pid})")
        return True

    if last_error:
        print(f"Failed to start Playwright MCP server: {last_error}")
    else:
        print("Failed to start Playwright MCP server: unknown error")
    return False

def stop_server() -> bool:
    """Stop the Playwright MCP server."""
    if not PID_FILE.exists():
        print("No Playwright MCP server PID file found")
        return True
    
    try:
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        
        # Kill the process group
        os.killpg(os.getpgid(pid), signal.SIGTERM)
        
        # Wait for termination
        time.sleep(1)
        
        # Clean up PID file
        PID_FILE.unlink()
        
        print(f"Playwright MCP server stopped (PID: {pid})")
        return True
        
    except (OSError, ValueError) as e:
        print(f"Error stopping server: {e}")
        PID_FILE.unlink(missing_ok=True)
        return False

def status() -> bool:
    """Check and report server status."""
    if is_server_running():
        with open(PID_FILE, 'r') as f:
            pid = f.read().strip()
        print(f"Playwright MCP server is running on port {PLAYWRIGHT_MCP_PORT} (PID: {pid})")
        return True
    else:
        print("Playwright MCP server is not running")
        return False

def ensure_running() -> bool:
    """Ensure the server is running, start if needed."""
    if is_server_running():
        return True
    return start_server()

def main():
    parser = argparse.ArgumentParser(description="Manage Playwright MCP server for agentic dev loop")
    parser.add_argument("action", choices=["start", "stop", "status", "ensure"], 
                       help="Action to perform")
    
    args = parser.parse_args()
    
    if args.action == "start":
        success = start_server()
    elif args.action == "stop":
        success = stop_server()
    elif args.action == "status":
        success = status()
    elif args.action == "ensure":
        success = ensure_running()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
