import { randomUUID } from "node:crypto";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { filterPlyFile, getVertexCountFromBuffer, sha256File } from "./ply.js";

const execFileAsync = promisify(execFile);

const DEFAULT_IMPORT_SOURCE =
  "s3://spaceport-ml-processing/3dgs/manual-3dgs-1774642514/ml-job-20260327-201514-manual-3-3dgs/output/model.tar.gz";

function toS3UriFromHttps(input) {
  try {
    const url = new URL(input);
    const virtualHosted = /^([^.]+)\.s3(?:[.-][^.]+)?\.amazonaws\.com$/i.exec(url.host);
    if (virtualHosted) {
      return `s3://${virtualHosted[1]}${decodeURIComponent(url.pathname)}`;
    }
    return null;
  } catch {
    return null;
  }
}

function ensureArtifactType(source) {
  if (source.endsWith(".ply")) return "ply";
  if (source.endsWith(".tar.gz")) return "model.tar.gz";
  throw new Error("Unsupported source artifact. Expected .ply or .tar.gz");
}

function getSessionRoot() {
  return process.env.SPLAT_EDITOR_SESSION_DIR || path.join(os.tmpdir(), "spaceport-splat-editor-sessions");
}

function sessionPaths(sessionId) {
  const root = path.join(getSessionRoot(), sessionId);
  return {
    root,
    sessionFile: path.join(root, "session.json"),
    sourceDir: path.join(root, "source"),
    workingDir: path.join(root, "working"),
    exportDir: path.join(root, "export"),
    tempDir: path.join(root, "tmp"),
  };
}

async function ensureSessionDirs(paths) {
  await fs.mkdir(paths.sourceDir, { recursive: true });
  await fs.mkdir(paths.workingDir, { recursive: true });
  await fs.mkdir(paths.exportDir, { recursive: true });
  await fs.mkdir(paths.tempDir, { recursive: true });
}

async function writeJson(filePath, data) {
  await fs.writeFile(filePath, `${JSON.stringify(data, null, 2)}\n`, "utf8");
}

async function readJson(filePath) {
  return JSON.parse(await fs.readFile(filePath, "utf8"));
}

async function runAwsCopy(source, destination) {
  await execFileAsync("aws", ["s3", "cp", source, destination], {
    env: process.env,
    maxBuffer: 16 * 1024 * 1024,
  });
}

async function runTarExtract(archivePath, outputDir) {
  await execFileAsync("tar", ["-xzf", archivePath, "-C", outputDir], {
    env: process.env,
    maxBuffer: 16 * 1024 * 1024,
  });
}

async function runTarCreate(archivePath, cwd, filenames) {
  await execFileAsync("tar", ["-czf", archivePath, ...filenames], {
    cwd,
    env: process.env,
    maxBuffer: 16 * 1024 * 1024,
  });
}

async function fetchHttpsToFile(source, destination) {
  const response = await fetch(source, { cache: "no-store" });
  if (!response.ok) {
    const fallbackS3 = toS3UriFromHttps(source);
    if (fallbackS3) {
      await runAwsCopy(fallbackS3, destination);
      return;
    }
    throw new Error(`Failed to download artifact: ${response.status}`);
  }
  const arrayBuffer = await response.arrayBuffer();
  await fs.writeFile(destination, Buffer.from(arrayBuffer));
}

async function copySourceArtifact(source, destination) {
  if (source.startsWith("file://")) {
    await fs.copyFile(new URL(source), destination);
    return;
  }
  if (source.startsWith("/") || source.startsWith("./") || source.startsWith("../")) {
    await fs.copyFile(path.resolve(source), destination);
    return;
  }
  if (source.startsWith("s3://")) {
    await runAwsCopy(source, destination);
    return;
  }
  if (source.startsWith("http://") || source.startsWith("https://")) {
    await fetchHttpsToFile(source, destination);
    return;
  }
  throw new Error("Unsupported source URL. Use s3:// or https://");
}

function buildExportName(artifactType) {
  return artifactType === "ply" ? "edited-splat.ply" : "edited-model.tar.gz";
}

async function buildWorkingStatus(filePath, previous) {
  const stat = await fs.stat(filePath);
  const fileSignature = `${stat.size}:${stat.mtimeMs}`;
  if (previous?.fileSignature === fileSignature) {
    return {
      hash: previous.hash,
      fileSignature,
      mtimeMs: stat.mtimeMs,
      sizeBytes: stat.size,
      vertexCount: previous.vertexCount,
    };
  }
  const hash = await sha256File(filePath);
  const buffer = await fs.readFile(filePath);
  const vertexCount = getVertexCountFromBuffer(buffer);
  return {
    hash,
    fileSignature,
    mtimeMs: stat.mtimeMs,
    sizeBytes: stat.size,
    vertexCount,
  };
}

function publicSession(session, workingStatus) {
  return {
    sessionId: session.sessionId,
    sourceUrl: session.sourceUrl,
    sourceArtifactType: session.sourceArtifactType,
    sourceArtifactPath: session.sourceArtifactPath,
    workingPlyPath: session.workingPlyPath,
    exportTargetName: session.exportTargetName,
    trainingMetadataPath: session.trainingMetadataPath,
    autoRefreshEnabled: true,
    revisionHash: workingStatus.hash,
    lastModifiedMs: workingStatus.mtimeMs,
    sizeBytes: workingStatus.sizeBytes,
    vertexCount: workingStatus.vertexCount,
  };
}

async function initializeSession(sourceUrl) {
  const sessionId = randomUUID();
  const paths = sessionPaths(sessionId);
  await ensureSessionDirs(paths);

  const sourceArtifactType = ensureArtifactType(sourceUrl);
  const sourceArtifactName = sourceArtifactType === "ply" ? "source-splat.ply" : "source-model.tar.gz";
  const sourceArtifactPath = path.join(paths.sourceDir, sourceArtifactName);

  await copySourceArtifact(sourceUrl, sourceArtifactPath);

  let workingPlyPath = path.join(paths.workingDir, "splat.ply");
  let trainingMetadataPath = null;

  if (sourceArtifactType === "ply") {
    await fs.copyFile(sourceArtifactPath, workingPlyPath);
  } else {
    await runTarExtract(sourceArtifactPath, paths.tempDir);
    const extractedPly = path.join(paths.tempDir, "splat.ply");
    const extractedMetadata = path.join(paths.tempDir, "training_metadata.json");
    try {
      await fs.access(extractedPly);
    } catch {
      throw new Error("Imported tar.gz is missing splat.ply");
    }
    try {
      await fs.access(extractedMetadata);
      trainingMetadataPath = path.join(paths.workingDir, "training_metadata.json");
      await fs.copyFile(extractedMetadata, trainingMetadataPath);
    } catch {
      throw new Error("Imported tar.gz is missing training_metadata.json");
    }
    await fs.copyFile(extractedPly, workingPlyPath);
  }

  const session = {
    sessionId,
    sourceUrl,
    sourceArtifactType,
    sourceArtifactPath,
    workingPlyPath,
    trainingMetadataPath,
    exportTargetName: buildExportName(sourceArtifactType),
    createdAt: new Date().toISOString(),
    workingStatus: null,
  };

  const workingStatus = await buildWorkingStatus(workingPlyPath, null);
  session.workingStatus = workingStatus;
  await writeJson(paths.sessionFile, session);

  return publicSession(session, workingStatus);
}

export async function createSessionFromSource(sourceUrl = DEFAULT_IMPORT_SOURCE) {
  return initializeSession(sourceUrl);
}

export async function loadSession(sessionId) {
  const paths = sessionPaths(sessionId);
  const session = await readJson(paths.sessionFile);
  const workingStatus = await buildWorkingStatus(session.workingPlyPath, session.workingStatus);
  if (session.workingStatus?.hash !== workingStatus.hash || session.workingStatus?.mtimeMs !== workingStatus.mtimeMs) {
    session.workingStatus = workingStatus;
    await writeJson(paths.sessionFile, session);
  }
  return { session, workingStatus };
}

export async function getSessionPublicState(sessionId) {
  const { session, workingStatus } = await loadSession(sessionId);
  return publicSession(session, workingStatus);
}

export async function getSessionWorkingPlyPath(sessionId) {
  const { session } = await loadSession(sessionId);
  return session.workingPlyPath;
}

function updateMetadataForExport(metadata, workingStatus) {
  const next = { ...metadata };
  next.output_file = "splat.ply";
  next.file_size_mb = workingStatus.sizeBytes / (1024 * 1024);
  next.timestamp = Date.now() / 1000;
  next.edited_locally = true;
  return next;
}

export async function buildExportArtifact(sessionId) {
  const { session, workingStatus } = await loadSession(sessionId);
  const paths = sessionPaths(sessionId);
  const exportPath = path.join(paths.exportDir, session.exportTargetName);

  if (session.sourceArtifactType === "ply") {
    await fs.copyFile(session.workingPlyPath, exportPath);
    return {
      filePath: exportPath,
      fileName: session.exportTargetName,
      contentType: "application/octet-stream",
    };
  }

  const bundleDir = path.join(paths.exportDir, "bundle");
  await fs.rm(bundleDir, { recursive: true, force: true });
  await fs.mkdir(bundleDir, { recursive: true });
  await fs.copyFile(session.workingPlyPath, path.join(bundleDir, "splat.ply"));

  const originalMetadata = session.trainingMetadataPath
    ? JSON.parse(await fs.readFile(session.trainingMetadataPath, "utf8"))
    : {};
  const nextMetadata = updateMetadataForExport(originalMetadata, workingStatus);
  await writeJson(path.join(bundleDir, "training_metadata.json"), nextMetadata);
  await runTarCreate(exportPath, bundleDir, ["training_metadata.json", "splat.ply"]);

  return {
    filePath: exportPath,
    fileName: session.exportTargetName,
    contentType: "application/gzip",
  };
}

function parseNumericOption(value) {
  if (value == null || value === "") return null;
  const parsed = Number.parseFloat(value);
  if (!Number.isFinite(parsed)) {
    throw new Error(`Expected numeric rule value, received "${value}"`);
  }
  return parsed;
}

export function parseRuleOptions(raw = {}) {
  const [minX, maxX, minY, maxY, minZ, maxZ] =
    typeof raw.bounds === "string"
      ? raw.bounds.split(",").map((part) => Number.parseFloat(part.trim()))
      : [null, null, null, null, null, null];

  return {
    yGt: parseNumericOption(raw.yGt),
    yLt: parseNumericOption(raw.yLt),
    radiusGt: parseNumericOption(raw.radiusGt),
    radiusLt: parseNumericOption(raw.radiusLt),
    minX: Number.isFinite(minX) ? minX : parseNumericOption(raw.minX),
    maxX: Number.isFinite(maxX) ? maxX : parseNumericOption(raw.maxX),
    minY: Number.isFinite(minY) ? minY : parseNumericOption(raw.minY),
    maxY: Number.isFinite(maxY) ? maxY : parseNumericOption(raw.maxY),
    minZ: Number.isFinite(minZ) ? minZ : parseNumericOption(raw.minZ),
    maxZ: Number.isFinite(maxZ) ? maxZ : parseNumericOption(raw.maxZ),
  };
}

export async function applyRulesToSession(sessionId, matcher) {
  const { session } = await loadSession(sessionId);
  const result = await filterPlyFile(session.workingPlyPath, session.workingPlyPath, matcher);
  await getSessionPublicState(sessionId);
  return result;
}

export { DEFAULT_IMPORT_SOURCE, getSessionRoot, sessionPaths };
