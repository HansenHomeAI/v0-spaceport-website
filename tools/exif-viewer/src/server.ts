import express from "express";
import fsp from "node:fs/promises";
import fs from "node:fs";
import path from "node:path";
import { z } from "zod";

const args = process.argv.slice(2);
function getArg(name: string) {
  const idx = args.indexOf(name);
  if (idx === -1) return undefined;
  return args[idx + 1];
}

const port = Number(getArg("--port") ?? "3177");
const dataDir = path.resolve(process.env.EXIF_VIEWER_DATA_DIR ?? ".data");

async function readCurrentSession(): Promise<string | null> {
  try {
    const p = path.join(dataDir, "current-session.txt");
    const s = (await fsp.readFile(p, "utf8")).trim();
    return s.length ? s : null;
  } catch {
    return null;
  }
}

async function readIndex() {
  const session = await readCurrentSession();
  if (!session) return null;
  const indexPath = path.join(dataDir, "sessions", session, "index.json");
  const raw = await fsp.readFile(indexPath, "utf8");
  return { session, index: JSON.parse(raw), indexPath };
}

function safeJoin(baseDir: string, rel: string) {
  const p = path.resolve(baseDir, rel);
  if (!p.startsWith(path.resolve(baseDir) + path.sep)) {
    throw new Error("Invalid path");
  }
  return p;
}

const app = express();
app.use(express.json({ limit: "10mb" }));

// If the UI has been built (`npm run build`), serve it from this process.
// In dev, Vite serves the UI and proxies /api + /data here.
const uiDist = path.resolve("ui-dist");
const uiIndex = path.join(uiDist, "index.html");
if (fs.existsSync(path.join(uiDist, "index.html"))) {
  app.use(express.static(uiDist));
}

app.get("/api/health", (_req, res) => res.json({ ok: true, port, dataDir }));

app.get("/api/index", async (_req, res) => {
  try {
    const v = await readIndex();
    if (!v) return res.status(404).json({ error: "No current session. Run `npm run ingest -- --zip ...` first." });
    return res.json({ session: v.session, index: v.index });
  } catch (e: any) {
    return res.status(500).json({ error: e?.message ?? String(e) });
  }
});

app.get("/data/file", async (req, res) => {
  try {
    const fileRel = String(req.query.rel ?? "");
    const v = await readIndex();
    if (!v) return res.status(404).end();
    const extractedDir = v.index?.source?.extractedDir;
    if (typeof extractedDir !== "string") return res.status(500).end();
    const p = safeJoin(extractedDir, fileRel);
    if (!fs.existsSync(p)) return res.status(404).end();
    return res.sendFile(p);
  } catch {
    return res.status(400).end();
  }
});

const ExportSchema = z.object({
  exportDir: z.string().min(1),
  selected: z.array(z.string().min(1))
});

app.post("/api/export", async (req, res) => {
  try {
    const body = ExportSchema.parse(req.body);
    const v = await readIndex();
    if (!v) return res.status(404).json({ error: "No current session." });
    const extractedDir = v.index?.source?.extractedDir;
    if (typeof extractedDir !== "string") return res.status(500).json({ error: "Invalid index: missing extractedDir" });

    const exportDir = path.resolve(body.exportDir);
    await fsp.mkdir(exportDir, { recursive: true });

    let copied = 0;
    const collisions = new Set<string>();
    for (const rel of body.selected) {
      const src = safeJoin(extractedDir, rel);
      const base = path.basename(rel);
      let dst = path.join(exportDir, base);
      if (fs.existsSync(dst)) {
        collisions.add(base);
        const ext = path.extname(base);
        const name = path.basename(base, ext);
        dst = path.join(exportDir, `${name}__${copied}${ext}`);
      }
      await fsp.copyFile(src, dst);
      copied++;
    }

    return res.json({ ok: true, copied, exportDir, collisions: Array.from(collisions) });
  } catch (e: any) {
    return res.status(400).json({ error: e?.message ?? String(e) });
  }
});

if (fs.existsSync(uiIndex)) {
  app.get("*", (req, res, next) => {
    if (req.path.startsWith("/api") || req.path.startsWith("/data")) return next();
    return res.sendFile(uiIndex);
  });
}

app.listen(port, () => {
  console.log(`EXIF Viewer API on http://localhost:${port}`);
  console.log(`Data dir: ${dataDir}`);
});
