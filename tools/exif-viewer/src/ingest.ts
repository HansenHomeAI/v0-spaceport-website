import fs from "node:fs";
import fsp from "node:fs/promises";
import path from "node:path";
import { exiftool } from "exiftool-vendored";
import fg from "fast-glob";
import unzipper from "unzipper";
import { z } from "zod";
import { lonLatToLocalMeters } from "./geo.js";
import type { ExifIndex, ExifPoint } from "./types.js";

const ArgsSchema = z.object({
  zip: z.string().optional(),
  extractedDir: z.string().optional(),
  dataDir: z.string().default(path.resolve(".data")),
  sessionName: z.string().optional()
});

function parseArgs(argv: string[]) {
  const out: Record<string, string> = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--zip") out.zip = argv[++i] ?? "";
    else if (a === "--extractedDir") out.extractedDir = argv[++i] ?? "";
    else if (a === "--dataDir") out.dataDir = argv[++i] ?? "";
    else if (a === "--session") out.sessionName = argv[++i] ?? "";
  }
  return ArgsSchema.parse(out);
}

async function ensureDir(p: string) {
  await fsp.mkdir(p, { recursive: true });
}

async function extractZip(zipPath: string, extractedDir: string) {
  await ensureDir(extractedDir);
  await new Promise<void>((resolve, reject) => {
    fs.createReadStream(zipPath)
      .pipe(unzipper.Extract({ path: extractedDir }))
      .on("close", () => resolve())
      .on("error", reject);
  });
}

function toNum(v: unknown): number | undefined {
  if (v === null || v === undefined) return undefined;
  const n = typeof v === "number" ? v : Number(String(v));
  return Number.isFinite(n) ? n : undefined;
}

function pickFirstNumber(obj: Record<string, unknown>, keys: string[]) {
  for (const k of keys) {
    const n = toNum(obj[k]);
    if (n !== undefined) return n;
  }
  return undefined;
}

async function buildIndex(extractedDir: string, zipPath?: string): Promise<ExifIndex> {
  const patterns = ["**/*.jpg", "**/*.jpeg", "**/*.JPG", "**/*.JPEG"];
  const files = await fg(patterns, {
    cwd: extractedDir,
    absolute: true,
    followSymbolicLinks: false,
    dot: false
  });

  const points: ExifPoint[] = [];
  for (const fileAbs of files) {
    const fileRel = path.relative(extractedDir, fileAbs);
    const fileName = path.basename(fileAbs);

    // Many drones store useful fields in XMP/EXIF; exiftool-vendored handles this well.
    const tags = await exiftool.read(fileAbs);

    const lat = toNum((tags as any).GPSLatitude);
    const lon = toNum((tags as any).GPSLongitude);
    const alt = pickFirstNumber(tags as any, ["GPSAltitude", "RelativeAltitude", "AbsoluteAltitude"]);

    const gimbalYaw = pickFirstNumber(tags as any, [
      "GimbalYawDegree",
      "GimbalYaw",
      "GimbalYawDegreeOriginal",
      "GimbalYawDegree_1"
    ]);
    const gimbalPitch = pickFirstNumber(tags as any, ["GimbalPitchDegree", "GimbalPitch"]);
    const gimbalRoll = pickFirstNumber(tags as any, ["GimbalRollDegree", "GimbalRoll"]);

    // Some DJI variants expose camera attitude fields differently.
    const cameraYaw = pickFirstNumber(tags as any, ["Yaw", "FlightYawDegree", "CameraYaw"]);
    const cameraPitch = pickFirstNumber(tags as any, ["Pitch", "FlightPitchDegree", "CameraPitch"]);
    const cameraRoll = pickFirstNumber(tags as any, ["Roll", "FlightRollDegree", "CameraRoll"]);

    const dateTimeOriginal = (tags as any).DateTimeOriginal
      ? String((tags as any).DateTimeOriginal)
      : undefined;

    points.push({
      id: fileRel,
      fileAbs,
      fileRel,
      fileName,
      dateTimeOriginal,
      lat,
      lon,
      alt,
      gimbalYaw,
      gimbalPitch,
      gimbalRoll,
      cameraYaw,
      cameraPitch,
      cameraRoll
    });
  }

  const withGps = points.filter((p) => typeof p.lat === "number" && typeof p.lon === "number") as Array<
    ExifPoint & { lat: number; lon: number }
  >;
  if (withGps.length === 0) {
    throw new Error(`No images with GPS found under: ${extractedDir}`);
  }

  const lat0 = withGps.reduce((s, p) => s + p.lat, 0) / withGps.length;
  const lon0 = withGps.reduce((s, p) => s + p.lon, 0) / withGps.length;

  for (const p of points) {
    if (typeof p.lat === "number" && typeof p.lon === "number") {
      const { x, y } = lonLatToLocalMeters({ lon: p.lon, lat: p.lat, lon0, lat0 });
      p.x = x;
      p.y = y;
    }
  }

  return {
    createdAt: new Date().toISOString(),
    source: { zipPath, extractedDir },
    origin: { lat0, lon0 },
    points
  };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const dataDir = path.resolve(args.dataDir);
  const session =
    args.sessionName ??
    `${new Date().toISOString().replace(/[:.]/g, "-")}-${Math.random().toString(16).slice(2, 8)}`;
  const sessionDir = path.join(dataDir, "sessions", session);
  const extractedDir = args.extractedDir ? path.resolve(args.extractedDir) : path.join(sessionDir, "extracted");

  await ensureDir(sessionDir);

  if (args.zip) {
    const zipAbs = path.resolve(args.zip);
    const zipCopy = path.join(sessionDir, path.basename(zipAbs));
    await fsp.copyFile(zipAbs, zipCopy);
    await extractZip(zipCopy, extractedDir);
    const index = await buildIndex(extractedDir, zipAbs);
    await fsp.writeFile(path.join(sessionDir, "index.json"), JSON.stringify(index, null, 2), "utf8");
    await fsp.writeFile(path.join(dataDir, "current-session.txt"), session, "utf8");
    console.log(`Session: ${session}`);
    console.log(`Index: ${path.join(sessionDir, "index.json")}`);
    return;
  }

  if (args.extractedDir) {
    const index = await buildIndex(extractedDir);
    await fsp.writeFile(path.join(sessionDir, "index.json"), JSON.stringify(index, null, 2), "utf8");
    await fsp.writeFile(path.join(dataDir, "current-session.txt"), session, "utf8");
    console.log(`Session: ${session}`);
    console.log(`Index: ${path.join(sessionDir, "index.json")}`);
    return;
  }

  throw new Error("Provide --zip <path> or --extractedDir <path>");
}

main()
  .catch((err) => {
    console.error(err?.stack || String(err));
    process.exitCode = 1;
  })
  .finally(async () => {
    // Ensure the exiftool child process is terminated.
    await exiftool.end();
  });

