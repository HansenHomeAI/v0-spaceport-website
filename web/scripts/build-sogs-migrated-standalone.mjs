import { mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const webRoot = path.resolve(__dirname, "..");
const entryPoint = path.join(webRoot, "standalone", "sogs-migrated-viewer", "index.tsx");
const outDir = path.join(webRoot, "public", "sogs-migrated-viewer");

await mkdir(outDir, { recursive: true });

await build({
  entryPoints: [entryPoint],
  bundle: true,
  define: {
    "process.env.NODE_ENV": JSON.stringify(process.env.NODE_ENV ?? "production"),
  },
  format: "esm",
  jsx: "automatic",
  legalComments: "none",
  logLevel: "info",
  outfile: path.join(outDir, "index.js"),
  platform: "browser",
  sourcemap: true,
  target: ["es2022"],
});
