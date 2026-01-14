#!/usr/bin/env python3
"""
Manage dev servers across multiple git worktrees.

Scans for all worktrees, ensures dependencies are installed,
starts dev servers on different ports, and provides a dashboard.
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import signal
import atexit
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import urllib.parse

# Global process tracking
running_servers: Dict[str, subprocess.Popen] = {}
api_server_port = 8765  # Port for the local API server
api_server = None
api_server_thread = None


def get_worktrees() -> List[Dict[str, str]]:
    """Get all git worktrees with their paths and branch names."""
    try:
        result = subprocess.run(
            ['git', 'worktree', 'list', '--porcelain'],
            capture_output=True,
            text=True,
            check=True
        )
        
        worktrees = []
        current = {}
        
        for line in result.stdout.splitlines():
            if line.startswith('worktree '):
                if current:
                    # Ensure branch exists, use head hash or path name if missing
                    if 'branch' not in current:
                        if 'head' in current:
                            current['branch'] = current['head'][:8]  # Use short hash
                        else:
                            current['branch'] = Path(current['path']).name
                    worktrees.append(current)
                current = {'path': line.split(' ', 1)[1]}
            elif line.startswith('HEAD '):
                current['head'] = line.split(' ', 1)[1]
                # Store short commit hash for display
                current['commit'] = line.split(' ', 1)[1][:8]
            elif line.startswith('branch '):
                current['branch'] = line.split(' ', 1)[1].replace('refs/heads/', '')
            elif line == 'detached':
                # Worktree is in detached HEAD state, use commit hash as branch name
                if 'head' in current:
                    current['branch'] = current['head'][:8]
                    if 'commit' not in current:
                        current['commit'] = current['head'][:8]
        
        if current:
            # Ensure branch exists for last worktree
            if 'branch' not in current:
                if 'head' in current:
                    current['branch'] = current['head'][:8]  # Use short hash
                else:
                    current['branch'] = Path(current['path']).name
            worktrees.append(current)
        
        # Get main worktree path to avoid duplicates
        main_path = subprocess.run(
            ['git', 'rev-parse', '--show-toplevel'],
            capture_output=True,
            text=True,
            check=True
        ).stdout.strip()
        
        # Remove duplicates (main worktree might already be in list)
        seen_paths = set()
        unique_worktrees = []
        for wt in worktrees:
            normalized_path = os.path.normpath(wt['path'])
            if normalized_path not in seen_paths:
                seen_paths.add(normalized_path)
                unique_worktrees.append(wt)
        
        worktrees = unique_worktrees
        
        return worktrees
    except subprocess.CalledProcessError as e:
        print(f"Error getting worktrees: {e}", file=sys.stderr)
        return []


def ensure_dependencies(worktree_path: str) -> bool:
    """Ensure node_modules exists and dependencies are installed."""
    web_dir = Path(worktree_path) / 'web'
    
    if not web_dir.exists():
        print(f"  ⚠️  web/ directory not found in {worktree_path}")
        return False
    
    node_modules = web_dir / 'node_modules'
    package_json = web_dir / 'package.json'
    
    if not package_json.exists():
        print(f"  ⚠️  package.json not found in {web_dir}")
        return False
    
    if not node_modules.exists() or not any(node_modules.iterdir()):
        print(f"  📦 Installing dependencies in {web_dir}...")
        try:
            subprocess.run(
                ['npm', 'install'],
                cwd=web_dir,
                check=True,
                capture_output=True
            )
            print(f"  ✅ Dependencies installed")
            return True
        except subprocess.CalledProcessError as e:
            print(f"  ❌ Failed to install dependencies: {e}", file=sys.stderr)
            return False
    
    return True


def get_last_commit_date(worktree_path: str, branch_name: str = None) -> Optional[datetime]:
    """Get the last commit date for a worktree.
    If branch_name is provided, gets the last commit on that branch.
    Otherwise, gets the last commit on HEAD."""
    try:
        # Try to get last commit on the branch if we have a branch name
        # Check if it's a real branch name (not a commit hash - hashes are typically 7-8 chars)
        if branch_name and len(branch_name) > 8 and '/' not in branch_name and not branch_name.startswith(('eb2a9ed', '49eb0a1', '46f1194', '935f1da', '5baad4f', '74551d7', '19a9a1f', '3d68615')):
            # It's likely a real branch name, try to get its last commit from main repo
            try:
                # Get main repo path (worktrees share the same .git)
                main_repo_result = subprocess.run(
                    ['git', 'rev-parse', '--show-toplevel'],
                    cwd=worktree_path,
                    capture_output=True,
                    text=True,
                    check=True
                )
                main_repo = main_repo_result.stdout.strip()
                
                result = subprocess.run(
                    ['git', 'log', '-1', '--format=%ct', f'refs/heads/{branch_name}'],
                    cwd=main_repo,
                    capture_output=True,
                    text=True,
                    check=True
                )
                if result.stdout.strip():
                    timestamp = int(result.stdout.strip())
                    return datetime.fromtimestamp(timestamp)
            except (subprocess.CalledProcessError, ValueError):
                pass
        
        # Fallback: get last commit on current HEAD
        result = subprocess.run(
            ['git', 'log', '-1', '--format=%ct', 'HEAD'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=True
        )
        if result.stdout.strip():
            timestamp = int(result.stdout.strip())
            return datetime.fromtimestamp(timestamp)
    except (subprocess.CalledProcessError, ValueError):
        pass
    return None


def get_recent_timestamp(worktree_path: str, branch_name: str = None) -> Optional[tuple[str, datetime]]:
    """Get formatted timestamp and commit date for worktree.
    Returns (formatted_string, datetime) or None if no commit found."""
    commit_date = get_last_commit_date(worktree_path, branch_name)
    if not commit_date:
        return None
    
    # Format as relative time
    delta = datetime.now() - commit_date
    if delta.days == 0:
        hours = delta.seconds // 3600
        if hours == 0:
            minutes = delta.seconds // 60
            formatted = f"{minutes}m ago" if minutes > 0 else "just now"
        else:
            formatted = f"{hours}h ago"
    elif delta.days == 1:
        formatted = "1 day ago"
    elif delta.days < 7:
        formatted = f"{delta.days} days ago"
    elif delta.days < 30:
        weeks = delta.days // 7
        formatted = f"{weeks} week{'s' if weeks > 1 else ''} ago"
    elif delta.days < 365:
        months = delta.days // 30
        formatted = f"{months} month{'s' if months > 1 else ''} ago"
    else:
        years = delta.days // 365
        formatted = f"{years} year{'s' if years > 1 else ''} ago"
    
    return (formatted, commit_date)


def has_uncommitted_changes(worktree_path: str) -> bool:
    """Check if worktree has uncommitted changes."""
    try:
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=True
        )
        return bool(result.stdout.strip())
    except subprocess.CalledProcessError:
        return False


def start_dev_server(worktree_path: str, port: int, branch_name: str) -> Optional[subprocess.Popen]:
    """Start a dev server for a worktree on the specified port."""
    web_dir = Path(worktree_path) / 'web'
    
    if not web_dir.exists():
        return None
    
    env = os.environ.copy()
    env['PORT'] = str(port)
    
    try:
        # Use PORT env var (Next.js supports this) and also pass -p for explicit port
        process = subprocess.Popen(
            ['npm', 'run', 'dev', '--', '-p', str(port)],
            cwd=web_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return process
    except Exception as e:
        print(f"  ❌ Failed to start server: {e}", file=sys.stderr)
        return None


def is_agent_branch(branch_name: str) -> bool:
    """Check if branch name is ONLY an 8-character code (like eb2a9eda or 49eb0a1e).
    These are agent worktrees and go in the priority section."""
    import re
    # Must be exactly 8 alphanumeric characters
    return bool(re.match(r'^[a-f0-9]{8}$', branch_name, re.IGNORECASE))


def create_dashboard(servers: List[Dict], output_path: Path):
    """Create an HTML dashboard to access all dev servers."""
    # Separate agent branches from misc
    agent_branches = [s for s in servers if is_agent_branch(s['branch'])]
    misc_branches = [s for s in servers if not is_agent_branch(s['branch'])]
    
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Worktree Dev Servers</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0a0a;
            color: #fff;
            padding: 40px 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
            text-align: center;
            font-weight: 600;
        }
        .subtitle {
            text-align: center;
            color: rgba(255, 255, 255, 0.6);
            margin-bottom: 32px;
            font-size: 1rem;
        }
        .url-input-section {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 25px;
            padding: 20px 24px;
            margin-bottom: 40px;
            display: flex;
            align-items: center;
            gap: 16px;
        }
        .url-input-label {
            font-size: 0.9rem;
            color: rgba(255, 255, 255, 0.7);
            white-space: nowrap;
        }
        .url-input-wrapper {
            flex: 1;
            display: flex;
            align-items: center;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 0 16px;
        }
        .url-input-prefix {
            color: rgba(255, 255, 255, 0.5);
            font-size: 0.9rem;
            margin-right: 8px;
        }
        .url-input {
            flex: 1;
            background: transparent;
            border: none;
            color: #fff;
            font-size: 0.95rem;
            padding: 12px 0;
            outline: none;
        }
        .url-input::placeholder {
            color: rgba(255, 255, 255, 0.3);
        }
        .section-header {
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 24px;
            margin-top: 48px;
            color: rgba(255, 255, 255, 0.9);
        }
        .section-header:first-of-type {
            margin-top: 0;
        }
        .servers-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        .server-card {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 24px;
            transition: all 0.2s;
        }
        .server-card:hover {
            background: rgba(255, 255, 255, 0.08);
            border-color: rgba(255, 255, 255, 0.2);
        }
        .server-card.running {
            border-color: #3fb27f;
        }
        .server-card.error {
            border-color: #ff4444;
        }
        .server-branch {
            font-size: 1.2rem;
            font-weight: 600;
            margin-bottom: 8px;
            word-break: break-all;
        }
        .server-path {
            font-size: 0.85rem;
            color: rgba(255, 255, 255, 0.5);
            margin-bottom: 4px;
            word-break: break-all;
        }
        .server-commit {
            font-size: 0.7rem;
            color: rgba(255, 255, 255, 0.4);
            margin-bottom: 4px;
            font-family: 'Monaco', 'Menlo', monospace;
        }
        .server-changes {
            font-size: 0.7rem;
            color: rgba(63, 178, 127, 0.9);
            margin-bottom: 8px;
            font-weight: 500;
        }
        .server-timestamp {
            font-size: 0.75rem;
            color: rgba(63, 178, 127, 0.8);
            margin-bottom: 12px;
            font-weight: 500;
        }
        .server-links {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
        }
        .server-btn {
            display: inline-block;
            padding: 9.5px 21.5px;
            border-radius: 999px;
            text-decoration: none;
            font-size: 0.95rem;
            transition: all 0.3s ease;
            cursor: pointer;
            border: 2.5px solid #fff;
            color: #fff;
            background: transparent;
            font-weight: 500;
            font-family: inherit;
            box-sizing: border-box;
        }
        .server-btn:hover {
            background: #fff;
            color: #000;
        }
        button.server-btn {
            background: transparent;
            color: #fff;
            border: 2.5px solid #fff;
        }
        button.server-btn:hover {
            background: #fff;
            color: #000;
        }
        a.server-btn {
            background: transparent;
            color: #fff;
            border: 2.5px solid #fff;
        }
        a.server-btn:hover {
            background: #fff;
            color: #000;
        }
        .status {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
            margin-bottom: 12px;
        }
        .status.running {
            background: rgba(63, 178, 127, 0.2);
            color: #3fb27f;
        }
        .status.error {
            background: rgba(255, 68, 68, 0.2);
            color: #ff4444;
        }
        .status.stopped {
            background: rgba(255, 255, 255, 0.1);
            color: rgba(255, 255, 255, 0.5);
        }
        .server-files {
            font-size: 0.75rem;
            color: rgba(255, 255, 255, 0.6);
            margin-bottom: 12px;
            background: rgba(0, 0, 0, 0.2);
            padding: 8px;
            border-radius: 6px;
            max-height: 100px;
            overflow-y: auto;
        }
        .server-files-title {
            font-weight: 600;
            margin-bottom: 4px;
            color: rgba(255, 255, 255, 0.8);
        }
        .file-item {
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            margin-bottom: 2px;
        }
        .action-button {
            display: inline-block;
            padding: 9.5px 21.5px;
            border-radius: 999px;
            border: 2.5px solid #fff;
            color: #fff;
            background: transparent;
            text-decoration: none;
            font-size: 0.95rem;
            margin: 0 8px;
            transition: all 0.3s ease;
            font-weight: 500;
        }
        .action-button:hover {
            background: #fff;
            color: #000;
        }
        .action-button.danger {
            border-color: rgba(255, 68, 68, 0.5);
            color: rgba(255, 68, 68, 0.8);
        }
        .action-button.danger:hover {
            background: rgba(255, 68, 68, 0.2);
            border-color: rgba(255, 68, 68, 0.8);
            color: #ff4444;
        }
        .refresh-info {
            text-align: center;
            color: rgba(255, 255, 255, 0.4);
            font-size: 0.85rem;
            margin-top: 20px;
        }
    </style>
</head>
    <body>
    <div class="container">
        <h1>Worktree Dev Servers</h1>
        <p class="subtitle">Click any worktree to open with your custom URL extension</p>
        
        <div class="url-input-section">
            <span class="url-input-label">URL Extension:</span>
            <div class="url-input-wrapper">
                <span class="url-input-prefix">localhost:{servers[0]['port'] if servers else 3000}</span>
                <input type="text" id="urlExtension" class="url-input" placeholder="/component-library" value="/component-library">
            </div>
        </div>
        
        <h2 class="section-header">Agent Branches</h2>
        <div class="servers-grid">
"""
    
    # Render agent branches
    for server in agent_branches:
        status_class = 'running' if server.get('running') else ('error' if server.get('error') else 'stopped')
        status_text = 'Running' if server.get('running') else ('Error' if server.get('error') else 'Stopped')
        
        timestamp_info = server.get('timestamp')
        if timestamp_info:
            timestamp_str, commit_date = timestamp_info
            # Use 'old' class if older than 7 days
            week_ago = datetime.now() - timedelta(days=7)
            old_class = ' old' if commit_date < week_ago else ''
            timestamp_html = f'<div class="server-timestamp{old_class}">Last edited: {timestamp_str}</div>'
        else:
            timestamp_html = ''
        
        # Escape for JavaScript
        worktree_path_escaped = server['path'].replace("'", "\\'").replace('"', '\\"')
        branch_escaped = server['branch'].replace("'", "\\'").replace('"', '\\"')
        port = server['port']
        
        if server.get('running'):
            button_html = f'''<a href="#" onclick="openWithExtension({port}); return false;" class="server-btn primary">Open</a>'''
        else:
            button_html = f'''<button onclick="startServer('{worktree_path_escaped}', {port}, '{branch_escaped}')" class="server-btn">Start Server</button>'''
        
        commit_hash = server.get('commit', server.get('head', '')[:8] if server.get('head') else '')
        commit_html = f'<div class="server-commit">Commit: {commit_hash}</div>' if commit_hash else ''
        has_changes = server.get('has_changes', False)
        changes_html = '<div class="server-changes">✓ Has uncommitted changes</div>' if has_changes else ''
        
        html += f"""
            <div class="server-card {status_class}" onclick="{'openWithExtension(' + str(port) + ')' if server.get('running') else ''}">
                <div class="status {status_class}">{status_text}</div>
                <div class="server-branch">{server['branch']}</div>
                <div class="server-path">{server['path']}</div>
                {commit_html}
                {changes_html}
                {timestamp_html}
                <div class="server-links">
                    {button_html}
                </div>
            </div>
"""
    
    html += """
        </div>
        
        <h2 class="section-header">Misc</h2>
        <div class="servers-grid">
"""
    
    # Render misc branches
    for server in misc_branches:
        status_class = 'running' if server.get('running') else ('error' if server.get('error') else 'stopped')
        status_text = 'Running' if server.get('running') else ('Error' if server.get('error') else 'Stopped')
        
        timestamp_info = server.get('timestamp')
        if timestamp_info:
            timestamp_str, commit_date = timestamp_info
            week_ago = datetime.now() - timedelta(days=7)
            old_class = ' old' if commit_date < week_ago else ''
            timestamp_html = f'<div class="server-timestamp{old_class}">Last edited: {timestamp_str}</div>'
        else:
            timestamp_html = ''
        
        # Escape for JavaScript
        worktree_path_escaped = server['path'].replace("'", "\\'").replace('"', '\\"')
        branch_escaped = server['branch'].replace("'", "\\'").replace('"', '\\"')
        port = server['port']
        
        if server.get('running'):
            button_html = f'''<a href="#" onclick="openWithExtension({port}); return false;" class="server-btn primary">Open</a>'''
        else:
            button_html = f'''<button onclick="startServer('{worktree_path_escaped}', {port}, '{branch_escaped}')" class="server-btn">Start Server</button>'''
        
        commit_hash = server.get('commit', server.get('head', '')[:8] if server.get('head') else '')
        commit_html = f'<div class="server-commit">Commit: {commit_hash}</div>' if commit_hash else ''
        has_changes = server.get('has_changes', False)
        changes_html = '<div class="server-changes">✓ Has uncommitted changes</div>' if has_changes else ''
        
        html += f"""
            <div class="server-card {status_class}" onclick="{'openWithExtension(' + str(port) + ')' if server.get('running') else ''}">
                <div class="status {status_class}">{status_text}</div>
                <div class="server-branch">{server['branch']}</div>
                <div class="server-path">{server['path']}</div>
                {commit_html}
                {changes_html}
                {timestamp_html}
                <div class="server-links">
                    {button_html}
                </div>
            </div>
"""
    
    html += """
        </div>
        
        </div>
        
        <div class="actions">
            <a href="#" onclick="location.reload()" class="action-button">Refresh Status</a>
            <a href="?stop=all" class="action-button danger">Stop All Servers</a>
        </div>
        
        <div class="refresh-info">
            Last updated: <span id="timestamp"></span>
        </div>
    </div>
    
    <script>
        document.getElementById('timestamp').textContent = new Date().toLocaleTimeString();
        
        function getUrlExtension() {
            const input = document.getElementById('urlExtension');
            const extension = input.value.trim();
            return extension.startsWith('/') ? extension : '/' + extension;
        }
        
        function openWithExtension(port, suggestedRoute) {
            let extension = getUrlExtension();
            // If user hasn't typed anything custom (still default), use suggested route
            if (extension === '/component-library' && suggestedRoute) {
                extension = suggestedRoute;
            }
            window.open(`http://localhost:${port}${extension}`, '_blank');
        }
        
        async function startServer(worktreePath, port, branch, suggestedRoute) {
            event.stopPropagation();
            const btn = event.target;
            btn.disabled = true;
            btn.textContent = 'Starting...';
            
            try {
                const response = await fetch('http://localhost:8765/start-server', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        path: worktreePath,
                        port: port,
                        branch: branch
                    })
                });
                
                const data = await response.json();
                
                if (response.ok && data.success) {
                    btn.textContent = 'Started!';
                    btn.classList.add('primary');
                    btn.disabled = false;
                    
                    // Open URL immediately
                    let extension = getUrlExtension();
                    if (extension === '/component-library' && suggestedRoute) {
                        extension = suggestedRoute;
                    }
                    window.open(`http://localhost:${port}${extension}`, '_blank');
                } else {
                    btn.textContent = 'Error';
                    btn.disabled = false;
                    alert(`Failed to start server: ${data.error || 'Unknown error'}`);
                }
            } catch (error) {
                btn.textContent = 'Error';
                btn.disabled = false;
                console.error('Error starting server:', error);
                alert('Failed to connect to server. Make sure the dashboard script is running with --api-server flag.');
            }
        }
        
        // Allow Enter key in URL extension input
        document.getElementById('urlExtension').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                const runningCards = document.querySelectorAll('.server-card.running');
                if (runningCards.length > 0) {
                    const onclickAttr = runningCards[0].querySelector('.server-btn').getAttribute('onclick');
                    const portMatch = onclickAttr.match(/\\d+/);
                    if (portMatch) {
                        openWithExtension(parseInt(portMatch[0]));
                    } else {
                        // Fallback: try to extract port from card's onclick
                        const cardOnclick = runningCards[0].getAttribute('onclick');
                        if (cardOnclick) {
                            const match = cardOnclick.match(/openWithExtension\\((\\d+)\\)/);
                            if (match) {
                                openWithExtension(parseInt(match[1]));
                            }
                        }
                    }
                }
            }
        });
    </script>
</body>
</html>
"""
    
    output_path.write_text(html)


def cleanup_servers():
    """Stop all running servers."""
    for branch, process in running_servers.items():
        if process and process.poll() is None:
            print(f"Stopping server for {branch}...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


class APIRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for starting servers via API."""
    
    def do_POST(self):
        """Handle POST requests to start servers."""
        if self.path == '/start-server':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                worktree_path = data.get('path')
                port = data.get('port')
                branch = data.get('branch')
                
                if not worktree_path or not port:
                    self.send_response(400)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'Missing path or port'}).encode())
                    return
                
                # Ensure dependencies
                if not ensure_dependencies(worktree_path):
                    self.send_response(500)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'Failed to install dependencies'}).encode())
                    return
                
                # Start server
                process = start_dev_server(worktree_path, port, branch or 'unknown')
                
                if process:
                    running_servers[branch or worktree_path] = process
                    # Poll to check if server is ready (max 5 seconds)
                    import socket
                    ready = False
                    for _ in range(10):  # Check 10 times over 5 seconds
                        time.sleep(0.5)
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(0.1)
                        result = sock.connect_ex(('localhost', port))
                        sock.close()
                        if result == 0:
                            ready = True
                            break
                    
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({'success': True, 'port': port, 'ready': ready}).encode())
                else:
                    self.send_response(500)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'Failed to start server'}).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def log_message(self, format, *args):
        """Suppress HTTP server logs."""
        pass


def start_api_server():
    """Start the local API server in a background thread."""
    global api_server, api_server_thread
    
    def run_server():
        global api_server
        try:
            api_server = HTTPServer(('localhost', api_server_port), APIRequestHandler)
            api_server.serve_forever()
        except OSError:
            pass  # Port already in use or server stopped
    
    api_server_thread = threading.Thread(target=run_server, daemon=True)
    api_server_thread.start()
    time.sleep(0.5)  # Give server time to start


def stop_api_server():
    """Stop the API server."""
    global api_server
    if api_server:
        api_server.shutdown()
        api_server.server_close()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Manage dev servers across git worktrees')
    parser.add_argument('--start', action='store_true', help='Start all dev servers')
    parser.add_argument('--stop', action='store_true', help='Stop all dev servers')
    parser.add_argument('--status', action='store_true', help='Show status of all servers')
    parser.add_argument('--dashboard', action='store_true', help='Create/update dashboard HTML')
    parser.add_argument('--port-start', type=int, default=3000, help='Starting port number (default: 3000)')
    parser.add_argument('--install-deps', action='store_true', help='Install dependencies in all worktrees')
    parser.add_argument('--dashboard-path', type=str, default='worktree-dashboard.html', help='Path for dashboard HTML')
    parser.add_argument('--start-one', type=str, help='Start server for a specific worktree path')
    parser.add_argument('--api-server', action='store_true', help='Start API server for dashboard interactions')
    
    args = parser.parse_args()
    
    # Register cleanup on exit
    atexit.register(cleanup_servers)
    atexit.register(stop_api_server)
    signal.signal(signal.SIGINT, lambda s, f: (cleanup_servers(), stop_api_server(), sys.exit(0)))
    signal.signal(signal.SIGTERM, lambda s, f: (cleanup_servers(), stop_api_server(), sys.exit(0)))
    
    # Start API server if requested or if dashboard is being created
    if args.api_server or args.dashboard:
        start_api_server()
        if args.api_server:
            print(f"API server started on http://localhost:{api_server_port}")
            print("Press Ctrl+C to stop")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                cleanup_servers()
                stop_api_server()
                return 0
    
    worktrees = get_worktrees()
    
    if not worktrees:
        print("No worktrees found", file=sys.stderr)
        return 1
    
    print(f"Found {len(worktrees)} worktree(s)")
    
    if args.start_one:
        # Start server for a specific worktree
        worktree_path = args.start_one
        # Find the worktree
        matching_wt = None
        for wt in worktrees:
            if os.path.normpath(wt['path']) == os.path.normpath(worktree_path):
                matching_wt = wt
                break
        
        if not matching_wt:
            print(f"Worktree not found: {worktree_path}", file=sys.stderr)
            return 1
        
        branch = matching_wt.get('branch', matching_wt.get('head', Path(matching_wt['path']).name)[:8])
        port = args.port_start
        
        print(f"Starting server for {branch} on port {port}...")
        if not ensure_dependencies(worktree_path):
            print(f"Failed to install dependencies", file=sys.stderr)
            return 1
        
        process = start_dev_server(worktree_path, port, branch)
        if process:
            print(f"Server started: http://localhost:{port}/component-library")
            print("Press Ctrl+C to stop")
            try:
                process.wait()
            except KeyboardInterrupt:
                process.terminate()
                process.wait()
            return 0
        else:
            print("Failed to start server", file=sys.stderr)
            return 1
    
    if args.install_deps:
        for wt in worktrees:
            print(f"\n📦 Checking {wt['branch']} ({wt['path']})...")
            ensure_dependencies(wt['path'])
    
    if args.stop:
        cleanup_servers()
        print("All servers stopped")
        return 0
    
    if args.status:
        for i, wt in enumerate(worktrees):
            port = args.port_start + i
            url = f"http://localhost:{port}/component-library"
            print(f"{wt['branch']:30} -> {url}")
        return 0
    
    if args.start or not (args.stop or args.status or args.dashboard):
        # Default action: start servers
        servers_info = []
        
        # First, collect all worktree info with timestamps
        worktree_data = []
        for wt in worktrees:
            branch = wt.get('branch', wt.get('head', Path(wt['path']).name)[:8])
            timestamp = get_recent_timestamp(wt['path'], branch)
            commit_date = timestamp[1] if timestamp else datetime.min
            worktree_data.append({
                'worktree': wt,
                'branch': branch,
                'timestamp': timestamp,
                'commit_date': commit_date
            })
        
        # Sort by commit date (most recent first)
        worktree_data.sort(key=lambda x: x['commit_date'], reverse=True)
        
        for i, data in enumerate(worktree_data):
            wt = data['worktree']
            branch = data['branch']
            port = args.port_start + i
            
            # Recalculate timestamp with branch name
            timestamp = get_recent_timestamp(wt['path'], branch)
            commit_date = timestamp[1] if timestamp else datetime.min
            
            print(f"\n🚀 Starting server for {branch} on port {port}...")
            
            if not ensure_dependencies(wt['path']):
                print(f"  ⚠️  Skipping {branch} due to missing dependencies")
                servers_info.append({
                    'branch': branch,
                    'path': wt['path'],
                    'port': port,
                    'running': False,
                    'error': True,
                    'timestamp': timestamp,
                    'commit': wt.get('commit', wt.get('head', '')[:8] if wt.get('head') else ''),
                    'head': wt.get('head', '')
                })
                continue
            
            process = start_dev_server(wt['path'], port, branch)
            
            if process:
                running_servers[branch] = process
                servers_info.append({
                    'branch': branch,
                    'path': wt['path'],
                    'port': port,
                    'running': True,
                    'timestamp': timestamp,
                    'commit': wt.get('commit', wt.get('head', '')[:8] if wt.get('head') else ''),
                    'head': wt.get('head', '')
                })
                print(f"  ✅ Server started: http://localhost:{port}/component-library")
                time.sleep(2)  # Give server time to start
            else:
                servers_info.append({
                    'branch': branch,
                    'path': wt['path'],
                    'port': port,
                    'running': False,
                    'error': True,
                    'timestamp': timestamp,
                    'commit': wt.get('commit', wt.get('head', '')[:8] if wt.get('head') else ''),
                    'head': wt.get('head', '')
                })
        
        # Create dashboard
        dashboard_path = Path(args.dashboard_path)
        create_dashboard(servers_info, dashboard_path)
        print(f"\n📊 Dashboard created: {dashboard_path.absolute()}")
        print(f"   Open it in your browser to access all servers")
        
        print("\n" + "="*60)
        print("Servers running. Press Ctrl+C to stop all servers.")
        print("="*60)
        
        # Keep running
        try:
            while True:
                time.sleep(1)
                # Check if any process died
                for branch, process in list(running_servers.items()):
                    if process.poll() is not None:
                        print(f"⚠️  Server for {branch} stopped unexpectedly")
                        del running_servers[branch]
        except KeyboardInterrupt:
            print("\n\nStopping all servers...")
            cleanup_servers()
            return 0
    
    if args.dashboard:
        servers_info = []
        for i, wt in enumerate(worktrees):
            port = args.port_start + i
            # Check if server is actually running
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            is_running = sock.connect_ex(('localhost', port)) == 0
            sock.close()
            
            branch = wt.get('branch', wt.get('head', Path(wt['path']).name)[:8])
            timestamp = get_recent_timestamp(wt['path'], branch)
            
            has_changes = has_uncommitted_changes(wt['path'])
            servers_info.append({
                'branch': branch,
                'path': wt['path'],
                'port': port,
                'running': is_running,
                'timestamp': timestamp,
                'commit_date': timestamp[1] if timestamp else datetime.min,
                'commit': wt.get('commit', wt.get('head', '')[:8] if wt.get('head') else ''),
                'head': wt.get('head', ''),
                'has_changes': has_changes
            })
        
        # Sort by commit date (most recent first)
        servers_info.sort(key=lambda x: x['commit_date'], reverse=True)
        # Reassign ports based on sorted order
        for i, server in enumerate(servers_info):
            server['port'] = args.port_start + i
        
        dashboard_path = Path(args.dashboard_path)
        create_dashboard(servers_info, dashboard_path)
        print(f"Dashboard updated: {dashboard_path.absolute()}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
