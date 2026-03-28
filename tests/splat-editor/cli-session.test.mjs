import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import {
  buildExportArtifact,
  createSessionFromSource,
  getSessionPublicState,
} from "../../web/lib/splat-editor/session-store.js";
import { createTempDir, createSyntheticTarGz, writeSyntheticPly } from "./helpers.mjs";

const execFileAsync = promisify(execFile);

test("imports local tar.gz sessions, applies CLI edits, and exports tar.gz", async () => {
  const tempRoot = await createTempDir("splat-editor-session-");
  process.env.SPLAT_EDITOR_SESSION_DIR = path.join(tempRoot, "sessions");

  const sourceDir = path.join(tempRoot, "source");
  await fs.mkdir(sourceDir, { recursive: true });

  const plyPath = path.join(sourceDir, "fixture.ply");
  await writeSyntheticPly(plyPath, {
    extraRestCount: 45,
    rows: [
      { x: 0, y: 0.1, z: 0 },
      { x: 0, y: 2.5, z: 0 },
      { x: 0, y: 1.5, z: 0 },
    ],
  });

  const tarPath = path.join(sourceDir, "fixture.tar.gz");
  await createSyntheticTarGz({
    tarPath,
    plyPath,
    metadata: {
      output_file: "splat.ply",
      file_size_mb: 0.1,
      training_completed: true,
      sh_degree: 3,
    },
  });

  const session = await createSessionFromSource(tarPath);
  assert.equal(session.sourceArtifactType, "model.tar.gz");
  await execFileAsync("node", ["web/scripts/edit-3dgs-ply.mjs", "--input", session.workingPlyPath, "--y-gt", "2"], {
    cwd: path.resolve("."),
  });

  const updated = await getSessionPublicState(session.sessionId);
  assert.equal(updated.vertexCount, 2);

  const exportArtifact = await buildExportArtifact(session.sessionId);
  assert.equal(exportArtifact.fileName, "edited-model.tar.gz");
  const { stdout } = await execFileAsync("tar", ["-tzf", exportArtifact.filePath]);
  assert.match(stdout, /training_metadata\.json/);
  assert.match(stdout, /splat\.ply/);
});

test("imports local bare PLY sessions and exports a bare edited PLY", async () => {
  const tempRoot = await createTempDir("splat-editor-ply-session-");
  process.env.SPLAT_EDITOR_SESSION_DIR = path.join(tempRoot, "sessions");

  const plyPath = path.join(tempRoot, "source.ply");
  await writeSyntheticPly(plyPath, {
    extraRestCount: 24,
    rows: [
      { x: 0, y: -1, z: 0 },
      { x: 0, y: 0, z: 0 },
      { x: 0, y: 1, z: 0 },
    ],
  });

  const session = await createSessionFromSource(plyPath);
  assert.equal(session.sourceArtifactType, "ply");
  await execFileAsync("node", ["web/scripts/edit-3dgs-ply.mjs", "--input", session.workingPlyPath, "--y-lt", "-0.5"], {
    cwd: path.resolve("."),
  });

  const updated = await getSessionPublicState(session.sessionId);
  assert.equal(updated.vertexCount, 2);

  const exportArtifact = await buildExportArtifact(session.sessionId);
  assert.equal(exportArtifact.fileName, "edited-splat.ply");
  const stat = await fs.stat(exportArtifact.filePath);
  assert.ok(stat.size > 0);
});

