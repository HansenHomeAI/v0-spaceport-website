import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";
import os from "node:os";
import path from "node:path";
import { readFile, writeFile } from "node:fs/promises";
import ts from "typescript";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const routePath = path.resolve(scriptDir, "../app/api/sogs-proxy/[...resource]/route.ts");
const source = await readFile(routePath, "utf8");
const transpiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.ES2022,
    target: ts.ScriptTarget.ES2022,
  },
}).outputText;

const tempModulePath = path.join(os.tmpdir(), `verify-sogs-proxy-query-${process.pid}.mjs`);
await writeFile(tempModulePath, transpiled, "utf8");
const { GET } = await import(`file://${tempModulePath}`);

let fetchedUrl = null;
globalThis.fetch = async (url) => {
  fetchedUrl = url.toString();
  return new Response("ok", {
    status: 200,
    headers: { "content-type": "text/plain" },
  });
};

const query = "?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Signature=deadbeef";
const encoded = "https:/spaceport-ml-processing.s3.amazonaws.com/bundles/meta.json";
await GET(
  {
    nextUrl: new URL(`https://example.com/api/sogs-proxy/${encoded}${query}`),
    headers: new Headers({ accept: "application/json" }),
  },
  { params: { resource: [encoded] } },
);

assert.equal(
  fetchedUrl,
  `https://spaceport-ml-processing.s3.amazonaws.com/bundles/meta.json${query}`,
);

console.log("sogs proxy query passthrough ok");
