import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const modalSource = fs.readFileSync(
  path.resolve("components/NewProjectModal.tsx"),
  "utf8",
);

assert.match(
  modalSource,
  /<span className="upload-mode-label">Static Photos<\/span>/,
  "upload mode switcher should use the shortened Static Photos label",
);

assert.doesNotMatch(
  modalSource,
  /Static Property Photos/,
  "old Static Property Photos label should not be present",
);

assert.doesNotMatch(
  modalSource,
  />\s*Choose Folder\s*</,
  "static photo mode should not render an extra Choose Folder button",
);

assert.doesNotMatch(
  modalSource,
  /staticFilesInputHidden/,
  "static photo mode should not keep a second visible file/folder chooser path",
);

assert.match(
  modalSource,
  /uploadMode === 'static_photos' \? 'staticFolderInputHidden' : 'fileInputHidden'/,
  "clicking the upload zone should open the hidden folder input in static photo mode",
);

assert.match(
  modalSource,
  /webkitdirectory: '', directory: ''/,
  "static photo folder upload input should preserve folder selection support",
);

console.log("OK static photo upload UI source matches expected chooser behavior");
