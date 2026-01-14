# Worktree Dev Server Management

Manage multiple dev servers across git worktrees to easily compare component-library outputs from different agent branches.

## Quick Start

```bash
# Start all dev servers (auto-installs deps, creates dashboard)
./scripts/worktree-dev.sh

# Or use Python directly
python3 scripts/manage_worktree_dev_servers.py
```

This will:
1. Scan all git worktrees (including main)
2. Install dependencies in each `web/` directory if needed
3. Start dev servers on sequential ports (3000, 3001, 3002, ...)
4. Create `worktree-dashboard.html` with links to all component-library pages

## Usage

### Start All Servers
```bash
./scripts/worktree-dev.sh --start
```

### Install Dependencies Only
```bash
./scripts/worktree-dev.sh --install-deps
```

### Check Status (without starting)
```bash
./scripts/worktree-dev.sh --status
```

### Stop All Servers
```bash
./scripts/worktree-dev.sh --stop
```

### Update Dashboard Only
```bash
./scripts/worktree-dev.sh --dashboard
```

### Custom Starting Port
```bash
./scripts/worktree-dev.sh --port-start 4000
```

## Dashboard

After starting servers, open `worktree-dashboard.html` in your browser. It provides:
- One-click access to each worktree's component-library page
- Visual status indicators (running/stopped/error)
- Auto-refresh every 5 seconds
- Direct links to home pages

## How It Works

1. **Worktree Detection**: Uses `git worktree list` to find all worktrees
2. **Dependency Management**: Checks for `node_modules` and runs `npm install` if missing
3. **Port Assignment**: Assigns sequential ports starting from 3000 (or custom `--port-start`)
4. **Process Management**: Tracks all server processes and cleans up on exit (Ctrl+C)

## Port Mapping

- Main worktree: `http://localhost:3000/component-library`
- First worktree: `http://localhost:3001/component-library`
- Second worktree: `http://localhost:3002/component-library`
- etc.

## Troubleshooting

### "web/ directory not found"
The script expects each worktree to have a `web/` directory. If your worktree structure differs, the script will skip it.

### "package.json not found"
Ensure each worktree has a complete `web/package.json`. The script will skip worktrees without it.

### Port Already in Use
If a port is already in use, the server for that worktree will fail to start. Either:
- Stop the conflicting process
- Use `--port-start` to start from a different port
- Manually free up ports

### Dependencies Not Installing
Check that:
- Node.js and npm are installed
- You have write permissions in each worktree's `web/` directory
- Network connectivity for npm registry access

## Integration with Cursor

While Cursor doesn't have built-in multi-worktree management, this script provides:
- **Visual Comparison**: Open dashboard in browser, click through each worktree's component-library
- **Parallel Development**: All servers run simultaneously, no manual switching needed
- **Quick Iteration**: Dependencies auto-install, servers auto-start

## Tips

1. **Keep Dashboard Open**: The dashboard auto-refreshes, making it easy to see when servers are ready
2. **Use Browser Tabs**: Open each component-library in a separate tab for side-by-side comparison
3. **Stop When Done**: Use `--stop` or Ctrl+C to clean up all processes
4. **Check Status First**: Use `--status` to see what ports will be used before starting
