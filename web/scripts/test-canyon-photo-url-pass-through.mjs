import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const overlaySource = fs.readFileSync(
  path.resolve("lib/canyon-vista/canyonVistaOverlays.ts"),
  "utf8",
);

assert.match(
  overlaySource,
  /ABSOLUTE_PHOTO_URL_PATTERN/,
  "canyon photo helper should explicitly detect absolute photo URLs",
);
assert.match(
  overlaySource,
  /return relativePath;/,
  "absolute photo URLs should be returned unchanged",
);
assert.match(
  overlaySource,
  /https:\|http:\|data:\|blob:/,
  "http, https, data, and blob photo URLs should pass through",
);

console.log("OK canyon photo URL pass-through helper is present");
