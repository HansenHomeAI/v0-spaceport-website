import net from 'node:net';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { existsSync } from 'node:fs';
import { spawn, spawnSync } from 'node:child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, '..');
const webDir = path.join(repoRoot, 'web');
const host = '127.0.0.1';

function run(command, args, cwd) {
  const result = spawnSync(command, args, {
    cwd,
    stdio: 'inherit',
  });

  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

function getFreePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();

    server.on('error', reject);
    server.listen(0, host, () => {
      const address = server.address();

      if (!address || typeof address === 'string') {
        server.close(() => reject(new Error('Failed to resolve a local port.')));
        return;
      }

      const { port } = address;
      server.close((closeError) => {
        if (closeError) {
          reject(closeError);
          return;
        }
        resolve(port);
      });
    });
  });
}

async function main() {
  if (!existsSync(path.join(webDir, 'node_modules'))) {
    console.log('[local] Installing web dependencies...');
    run('npm', ['install'], webDir);
  }

  const port = process.env.PORT ? Number(process.env.PORT) : await getFreePort();

  if (!Number.isInteger(port) || port <= 0) {
    throw new Error(`Invalid port: ${String(process.env.PORT)}`);
  }

  console.log(`[local] Starting Spaceport on http://${host}:${port}`);
  console.log(`[local] Camera overlap page: http://${host}:${port}/camera-overlap`);

  const child = spawn(
    'npm',
    ['run', 'dev', '--', '--hostname', host, '--port', String(port)],
    {
      cwd: webDir,
      stdio: 'inherit',
    }
  );

  child.on('exit', (code, signal) => {
    if (signal) {
      process.kill(process.pid, signal);
      return;
    }
    process.exit(code ?? 0);
  });
}

main().catch((error) => {
  console.error(`[local] ${error instanceof Error ? error.message : String(error)}`);
  process.exit(1);
});
