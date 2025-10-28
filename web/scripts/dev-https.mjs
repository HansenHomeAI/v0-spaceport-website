import fs from 'node:fs';
import https from 'node:https';
import path from 'node:path';
import process from 'node:process';
import next from 'next';

const port = Number.parseInt(process.env.PORT ?? '3000', 10);
const hostname = process.env.HOSTNAME ?? 'localhost';
const certDirectory = process.env.DEV_HTTPS_CERT_DIR
  ? path.resolve(process.env.DEV_HTTPS_CERT_DIR)
  : path.resolve(process.cwd(), '..', 'certs');
const certFilename = process.env.DEV_HTTPS_CERT_FILE ?? 'localhost.pem';
const keyFilename = process.env.DEV_HTTPS_KEY_FILE ?? 'localhost-key.pem';

const certPath = path.join(certDirectory, certFilename);
const keyPath = path.join(certDirectory, keyFilename);

const missingFiles = [certPath, keyPath].filter((filePath) => !fs.existsSync(filePath));

if (missingFiles.length > 0) {
  console.error('[dev-https] Missing TLS files:');
  for (const missing of missingFiles) {
    console.error(`  - ${missing}`);
  }
  console.error('\nGenerate them with mkcert:');
  console.error('  mkcert -install');
  console.error(
    '  mkcert -key-file certs/localhost-key.pem -cert-file certs/localhost.pem localhost 127.0.0.1 ::1',
  );
  process.exit(1);
}

const app = next({
  dev: true,
  hostname,
  port,
});

const handler = app.getRequestHandler();

await app.prepare();

const server = https.createServer(
  {
    key: fs.readFileSync(keyPath),
    cert: fs.readFileSync(certPath),
  },
  (req, res) => {
    handler(req, res).catch((err) => {
      console.error('[dev-https] Request handling error:', err);
      res.statusCode = 500;
      res.end('Internal Server Error');
    });
  },
);

server.on('error', (error) => {
  console.error('[dev-https] HTTPS server failed to start:', error);
  process.exit(1);
});

server.listen(port, hostname, () => {
  console.log(`> Ready on https://${hostname}:${port}`);
});

