import test from "node:test";
import assert from "node:assert/strict";
import { createRuleMatcher, filterPlyBuffer, parsePlyHeader } from "../../web/lib/splat-editor/ply.js";
import { createSyntheticPlyBuffer } from "./helpers.mjs";

function rowSlice(buffer, header, index) {
  const start = header.vertexDataStart + index * header.vertexStride;
  return buffer.subarray(start, start + header.vertexStride);
}

test("round-trips a SH-degree-2-style synthetic PLY with no edits", () => {
  const buffer = createSyntheticPlyBuffer({
    extraRestCount: 24,
    rows: [
      { x: 0, y: 0.2, z: 0.1, f_rest_0: 10, opacity: 0.3, rot_0: 1 },
      { x: 1, y: 1.2, z: 0.2, f_rest_0: 20, opacity: 0.4, rot_0: 1 },
    ],
  });

  const result = filterPlyBuffer(buffer, () => true);
  assert.equal(result.changed, false);
  assert.equal(result.keptCount, 2);
  assert.deepEqual(result.buffer, buffer);
});

test("filters a SH-degree-3-style synthetic PLY and preserves surviving row bytes", () => {
  const buffer = createSyntheticPlyBuffer({
    extraRestCount: 45,
    rows: [
      { x: 0, y: 0, z: 0, opacity: 0.1, rot_0: 1, f_rest_44: 4.4 },
      { x: 2, y: 1, z: 0, opacity: 0.2, rot_0: 1, f_rest_44: 5.5 },
      { x: 0, y: 3, z: 0, opacity: 0.3, rot_0: 1, f_rest_44: 6.6 },
    ],
  });
  const sourceHeader = parsePlyHeader(buffer);

  const result = filterPlyBuffer(
    buffer,
    createRuleMatcher({
      yGt: 2,
    }),
  );

  assert.equal(result.changed, true);
  assert.equal(result.removedCount, 1);
  assert.equal(result.keptCount, 2);

  const nextHeader = parsePlyHeader(result.buffer);
  assert.equal(nextHeader.vertexCount, 2);
  assert.deepEqual(rowSlice(result.buffer, nextHeader, 0), rowSlice(buffer, sourceHeader, 0));
  assert.deepEqual(rowSlice(result.buffer, nextHeader, 1), rowSlice(buffer, sourceHeader, 1));
});

test("supports radius and bounds filters", () => {
  const buffer = createSyntheticPlyBuffer({
    extraRestCount: 24,
    rows: [
      { x: 0, y: 0, z: 0 },
      { x: 2, y: 0, z: 0 },
      { x: 0.1, y: 0.1, z: 0.1 },
      { x: 0.5, y: -2, z: 0.4 },
    ],
  });

  const radiusFiltered = filterPlyBuffer(buffer, createRuleMatcher({ radiusGt: 1 }));
  assert.equal(radiusFiltered.keptCount, 2);

  const boundsFiltered = filterPlyBuffer(
    buffer,
    createRuleMatcher({
      minX: -0.2,
      maxX: 0.6,
      minY: -0.2,
      maxY: 0.6,
      minZ: -0.2,
      maxZ: 0.6,
    }),
  );
  assert.equal(boundsFiltered.keptCount, 2);
});

