import test from "node:test";
import assert from "node:assert/strict";

import {
  buildSfmFileUrls,
  derivePipelineFromCompressed,
  parseImages,
  parsePoints,
} from "../lib/pipeline-viewer-utils.js";

test("derivePipelineFromCompressed supports s3 urls", () => {
  const result = derivePipelineFromCompressed(
    "s3://spaceport-ml-processing/compressed/job-123/supersplat_bundle/"
  );

  assert.equal(result?.jobId, "job-123");
  assert.equal(
    result?.compressedBundle,
    "https://spaceport-ml-processing.s3.amazonaws.com/compressed/job-123/supersplat_bundle/meta.json"
  );
  assert.equal(
    result?.colmapBase,
    "https://spaceport-ml-processing.s3.amazonaws.com/colmap/job-123/"
  );
  assert.equal(
    result?.gaussianPly,
    "https://spaceport-ml-processing.s3.amazonaws.com/3dgs/job-123/splat.ply"
  );
});

test("buildSfmFileUrls normalizes sparse path", () => {
  const urls = buildSfmFileUrls(
    "https://spaceport-ml-processing.s3.amazonaws.com/colmap/job-123",
    "/sparse/0"
  );

  assert.deepEqual(urls, {
    cameras: "https://spaceport-ml-processing.s3.amazonaws.com/colmap/job-123/sparse/0/cameras.txt",
    images: "https://spaceport-ml-processing.s3.amazonaws.com/colmap/job-123/sparse/0/images.txt",
    points: "https://spaceport-ml-processing.s3.amazonaws.com/colmap/job-123/sparse/0/points3D.txt",
  });
});

test("parsePoints enforces max point count and bounds", () => {
  const text = [
    "# header",
    "1 1 2 3 255 0 0 0.5",
    "2 -4 5 6 0 255 0 0.5",
    "3 9 10 11 0 0 255 0.5",
  ].join("\n");

  const result = parsePoints(text, 2);

  assert.equal(result.count, 2);
  assert.deepEqual(result.bounds.min, [-4, 2, 3]);
  assert.deepEqual(result.bounds.max, [1, 5, 6]);
  assert.equal(result.positions.length, 6);
  assert.equal(result.colors.length, 6);
});

test("parseImages builds camera frustums from COLMAP image rows", () => {
  const text = [
    "# images",
    "1 1 0 0 0 0 0 0 1 image-1.jpg",
    "0 0 -1",
  ].join("\n");

  const result = parseImages(text, 10);

  assert.equal(result.count, 1);
  assert.ok(result.positions.length > 0);
  assert.ok(result.bounds.min.every((value) => Math.abs(value) === 0));
  assert.ok(result.bounds.max.every((value) => Math.abs(value) === 0));
});
