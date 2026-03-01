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

const cases = [
  {
    encodedPath:
      "https%3A%2F%2Fspaceport-ml-processing.s3.amazonaws.com%2Fbundles%2Ffully%2520encoded%2Ffile%252Bname.json",
    query: "?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Signature=encodedfeed",
    expected:
      "https://spaceport-ml-processing.s3.amazonaws.com/bundles/fully%20encoded/file%2Bname.json?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Signature=encodedfeed",
  },
  {
    encodedPath: "https:/spaceport-ml-processing.s3.amazonaws.com/bundles/meta.json",
    query: "?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Signature=deadbeef",
    expected:
      "https://spaceport-ml-processing.s3.amazonaws.com/bundles/meta.json?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Signature=deadbeef",
  },
  {
    // Using request.url preserves the raw encoded object key. Rebuilding from decoded
    // params.resource would turn this into a different path and break S3 signatures.
    encodedPath:
      "https:/spaceport-ml-processing.s3.amazonaws.com/bundles/folder%20name/file%2Bname.json",
    query: "?X-Amz-Expires=300&X-Amz-Signature=beadfeed",
    expected:
      "https://spaceport-ml-processing.s3.amazonaws.com/bundles/folder%20name/file%2Bname.json?X-Amz-Expires=300&X-Amz-Signature=beadfeed",
  },
  {
    encodedPath:
      "https:/spaceport-ml-processing.s3.amazonaws.com/bundles/base%20path/file%2Bname.json",
    query: "?X-Amz-Date=20260301T000000Z&X-Amz-Signature=feedface",
    requestPath:
      "/preview/api/sogs-proxy/https:/spaceport-ml-processing.s3.amazonaws.com/bundles/base%20path/file%2Bname.json",
    basePath: "/preview",
    expected:
      "https://spaceport-ml-processing.s3.amazonaws.com/bundles/base%20path/file%2Bname.json?X-Amz-Date=20260301T000000Z&X-Amz-Signature=feedface",
  },
];

for (const testCase of cases) {
  fetchedUrl = null;
  const requestPath = testCase.requestPath ?? `/api/sogs-proxy/${testCase.encodedPath}`;
  const nextUrl = new URL(`https://example.com${requestPath}${testCase.query}`);
  nextUrl.basePath = testCase.basePath ?? "";
  await GET(
    {
      url: `https://example.com${requestPath}${testCase.query}`,
      nextUrl,
      headers: new Headers({ accept: "application/json" }),
    },
    { params: { resource: [testCase.encodedPath] } },
  );

  assert.equal(fetchedUrl, testCase.expected);
}

console.log("sogs proxy query passthrough ok");
