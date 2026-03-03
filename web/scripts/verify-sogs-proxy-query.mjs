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
      "https%3A%2F%2Fspaceport-ml-processing.s3.amazonaws.com%2Fbundles%2Ffully%2520encoded%2Ffile%252Bname.json%3FX-Amz-Algorithm%3DAWS4-HMAC-SHA256%26X-Amz-Signature%3Dencodedfeed",
    query: "",
    expected:
      "https://spaceport-ml-processing.s3.amazonaws.com/bundles/fully%20encoded/file%2Bname.json?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Signature=encodedfeed",
  },
  {
    encodedPath:
      "https%3A%2F%2Fspaceport-ml-processing-staging.s3.amazonaws.com%2Fbundles%2Fstaging%2520host%2Ffile%252Bname.json",
    query: "?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Signature=staginghost",
    expected:
      "https://spaceport-ml-processing-staging.s3.amazonaws.com/bundles/staging%20host/file%2Bname.json?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Signature=staginghost",
  },
  {
    encodedPath: "https:/spaceport-ml-processing-prod.s3.us-west-2.amazonaws.com/bundles/meta.json",
    query: "?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Signature=prodhost",
    expected:
      "https://spaceport-ml-processing-prod.s3.us-west-2.amazonaws.com/bundles/meta.json?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Signature=prodhost",
  },
  {
    encodedPath:
      "https%3A%2F%2Fspaceport-ml-processing.s3.amazonaws.com%2Fbundles%2Fouter-query%2520only%2Ffile%252Bname.json",
    query: "?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Signature=outeronly",
    expected:
      "https://spaceport-ml-processing.s3.amazonaws.com/bundles/outer-query%20only/file%2Bname.json?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Signature=outeronly",
  },
  {
    encodedPath:
      "https%3A%2F%2Fspaceport-ml-processing.s3.amazonaws.com%2Fbundles%2Fembedded-wins%2520case%2Ffile%252Bname.json%3FX-Amz-Algorithm%3DAWS4-HMAC-SHA256%26X-Amz-Signature%3Dembeddedsig",
    query: "?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Signature=outersig",
    expected:
      "https://spaceport-ml-processing.s3.amazonaws.com/bundles/embedded-wins%20case/file%2Bname.json?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Signature=embeddedsig",
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

fetchedUrl = null;
const malformedResponse = await GET(
  {
    url: "https://example.com/api/sogs-proxy/https%3A%2F%2Fspaceport-ml-processing.s3.amazonaws.com%2Fbroken%ZZfile",
    nextUrl: new URL(
      "https://example.com/api/sogs-proxy/https%3A%2F%2Fspaceport-ml-processing.s3.amazonaws.com%2Fbroken%ZZfile",
    ),
    headers: new Headers({ accept: "application/json" }),
  },
  { params: { resource: [] } },
);

assert.equal(malformedResponse.status, 400);
assert.equal(fetchedUrl, null);

fetchedUrl = null;
const invalidSchemeResponse = await GET(
  {
    url: "https://example.com/api/sogs-proxy/ftp://spaceport-ml-processing.s3.amazonaws.com/broken.obj",
    nextUrl: new URL(
      "https://example.com/api/sogs-proxy/ftp://spaceport-ml-processing.s3.amazonaws.com/broken.obj",
    ),
    headers: new Headers({ accept: "application/json" }),
  },
  { params: { resource: ["ftp://spaceport-ml-processing.s3.amazonaws.com/broken.obj"] } },
);

assert.equal(invalidSchemeResponse.status, 400);
assert.equal(fetchedUrl, null);

console.log("sogs proxy query passthrough ok");
