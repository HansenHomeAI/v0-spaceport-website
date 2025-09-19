#!/usr/bin/env python3
"""
Playwright MCP Server Manager
Handles starting/stopping the Playwright MCP server for the agentic dev loop.
"""

import argparse
import subprocess
import time
import signal
import os
import sys
import json
from pathlib import Path

PLAYWRIGHT_MCP_PORT = 3001
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

def start_server() -> bool:
    """Start the Playwright MCP server in the background."""
    if is_server_running():
        print(f"Playwright MCP server already running on port {PLAYWRIGHT_MCP_PORT}")
        return True
    
    try:
        # Ensure .agentic directory exists
        PID_FILE.parent.mkdir(exist_ok=True)
        
        # Start server in background
        process = subprocess.Popen(
            ["playwright-mcp", "server", "--port", str(PLAYWRIGHT_MCP_PORT)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setsid  # Create new process group
        )
        
        # Save PID
        with open(PID_FILE, 'w') as f:
            f.write(str(process.pid))
        
        # Wait a moment and check if it started successfully
        time.sleep(2)
        if process.poll() is not None:
            print("Failed to start Playwright MCP server")
            return False
        
        print(f"Playwright MCP server started on port {PLAYWRIGHT_MCP_PORT} (PID: {process.pid})")
        return True
        
    except FileNotFoundError:
        print("playwright-mcp command not found. Please install Playwright MCP.")
        return False
    except Exception as e:
        print(f"Error starting Playwright MCP server: {e}")
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
