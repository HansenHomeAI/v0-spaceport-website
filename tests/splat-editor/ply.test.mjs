import test from "node:test";
import assert from "node:assert/strict";
import { createRuleMatcher, filterPlyBuffer, mutatePlyBuffer, parsePlyHeader } from "../../web/lib/splat-editor/ply.js";
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

test("supports viewer/world-space Y cuts using the applied splat transform", () => {
  const buffer = createSyntheticPlyBuffer({
    extraRestCount: 24,
    rows: [
      { x: 0, y: 0, z: 0 },
      { x: 0, y: 0, z: 0.2 },
      { x: 0, y: 0, z: -0.2 },
    ],
  });

  const result = filterPlyBuffer(
    buffer,
    createRuleMatcher({
      maxWorldY: 0.03,
      transform: {
        position: [0.03, 0.1, 0.15],
        rotation: [-100, 0, 0],
        scale: 1,
      },
    }),
  );

  assert.equal(result.changed, true);
  assert.equal(result.keptCount, 1);
  assert.equal(parsePlyHeader(result.buffer).vertexCount, 1);
});

test("mutates only rows beyond the configured world-space radius", () => {
  const buffer = createSyntheticPlyBuffer({
    extraRestCount: 45,
    rows: [
      { x: 0, y: 0, z: 0, opacity: 0, scale_0: 0, scale_1: 0, scale_2: 0, f_rest_0: 1 },
      { x: 0, y: 0, z: 3, opacity: 0, scale_0: 0, scale_1: 0, scale_2: 0, f_rest_0: 1 },
    ],
  });

  const result = mutatePlyBuffer(buffer, ({ z, get, set }) => {
    if (z <= 2) return false;
    set("scale_0", get("scale_0") + Math.log(2));
    set("f_rest_0", get("f_rest_0") * 0.5);
    return true;
  });

  assert.equal(result.changed, true);
  assert.equal(result.modifiedCount, 1);

  const header = parsePlyHeader(result.buffer);
  const view = new DataView(result.buffer.buffer, result.buffer.byteOffset, result.buffer.byteLength);
  const row0 = header.vertexDataStart;
  const row1 = row0 + header.vertexStride;
  const s0 = header.propertyOffsets.get("scale_0");
  const rest0 = header.propertyOffsets.get("f_rest_0");

  assert.equal(view.getFloat32(row0 + s0.offset, true), 0);
  assert.equal(view.getFloat32(row0 + rest0.offset, true), 1);
  assert.ok(Math.abs(view.getFloat32(row1 + s0.offset, true) - Math.log(2)) < 1e-6);
  assert.ok(Math.abs(view.getFloat32(row1 + rest0.offset, true) - 0.5) < 1e-6);
});
