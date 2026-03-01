import assert from "node:assert/strict";

import { NextRequest } from "next/server";

import { GET } from "../app/api/sogs-proxy/[...resource]/route";

const originalFetch = globalThis.fetch;

const presignedQuery =
  "?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=test%2F20260228%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260228T150000Z&X-Amz-Expires=300&X-Amz-SignedHeaders=host&X-Amz-Signature=abc123";
const requestUrl = `https://spaceport.test/api/sogs-proxy/https:/spaceport-ml-processing.s3.amazonaws.com/bundles/meta.json${presignedQuery}`;
let fetchedUrl = "";

globalThis.fetch = (async (input) => {
  fetchedUrl = input instanceof URL ? input.toString() : String(input);
  return new Response("ok", {
    status: 200,
    headers: {
      "content-type": "application/json",
    },
  });
}) as typeof fetch;

try {
  const response = await GET(new NextRequest(requestUrl), {
    params: {
      resource: ["https:", "spaceport-ml-processing.s3.amazonaws.com", "bundles", "meta.json"],
    },
  });

  assert.equal(response.status, 200);
  assert.equal(
    fetchedUrl,
    `https://spaceport-ml-processing.s3.amazonaws.com/bundles/meta.json${presignedQuery}`,
  );
  console.log("sogs proxy query passthrough ok");
} finally {
  globalThis.fetch = originalFetch;
}
