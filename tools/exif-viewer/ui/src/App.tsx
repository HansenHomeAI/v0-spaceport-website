import React, { useEffect, useMemo, useRef, useState } from "react";
import Plotly from "plotly.js-dist-min";
import { recomputeSelection, type ShapeMode, type UiShape } from "./lib/selection";

type ExifPoint = {
  id: string;
  fileRel: string;
  fileName: string;
  lat?: number;
  lon?: number;
  alt?: number;
  x?: number;
  y?: number;
  gimbalYaw?: number;
  gimbalPitch?: number;
  gimbalRoll?: number;
  cameraYaw?: number;
  cameraPitch?: number;
  cameraRoll?: number;
  dateTimeOriginal?: string;
};

type ExifIndex = {
  createdAt: string;
  origin: { lat0: number; lon0: number };
  source: { zipPath?: string; extractedDir: string };
  points: ExifPoint[];
};

async function fetchIndex(): Promise<{ session: string; index: ExifIndex }> {
  const r = await fetch("/api/index");
  if (!r.ok) throw new Error(await r.text());
  return await r.json();
}

function fmt(n?: number) {
  if (n === undefined) return "-";
  if (!Number.isFinite(n)) return "-";
  return Math.abs(n) >= 100 ? n.toFixed(1) : n.toFixed(5);
}

export function App() {
  const plotRef = useRef<HTMLDivElement | null>(null);
  const [index, setIndex] = useState<ExifIndex | null>(null);
  const [session, setSession] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [shapes, setShapes] = useState<UiShape[]>([]);
  const [shapeModes, setShapeModes] = useState<Record<number, ShapeMode>>({});
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [activeId, setActiveId] = useState<string | null>(null);
  const [exportDir, setExportDir] = useState<string>("");
  const [exportResult, setExportResult] = useState<string>("");

  useEffect(() => {
    fetchIndex()
      .then((v) => {
        setIndex(v.index);
        setSession(v.session);
        setError(null);
      })
      .catch((e) => setError(String(e?.message ?? e)));
  }, []);

  const points = useMemo(() => {
    return (index?.points ?? []).filter((p) => typeof p.x === "number" && typeof p.y === "number") as Array<
      ExifPoint & { x: number; y: number }
    >;
  }, [index]);

  const pointById = useMemo(() => {
    const m = new Map<string, ExifPoint>();
    for (const p of index?.points ?? []) m.set(p.id, p);
    return m;
  }, [index]);

  useEffect(() => {
    if (!index) return;
    const next = recomputeSelection({ points: index.points, shapes });
    setSelectedIds(next);
    if (activeId && !next.has(activeId)) setActiveId(null);
  }, [index, shapes]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!plotRef.current) return;
    if (!index) return;

    const xs = points.map((p) => p.x);
    const ys = points.map((p) => p.y);
    const ids = points.map((p) => p.id);
    const hover = points.map((p) => {
      const parts = [
        p.fileName,
        `x=${p.x.toFixed(2)}m y=${p.y.toFixed(2)}m`,
        `lat=${fmt(p.lat)} lon=${fmt(p.lon)} alt=${p.alt ?? "-"}`,
        `gimbal yaw/pitch/roll=${p.gimbalYaw ?? "-"} / ${p.gimbalPitch ?? "-"} / ${p.gimbalRoll ?? "-"}`,
        `camera yaw/pitch/roll=${p.cameraYaw ?? "-"} / ${p.cameraPitch ?? "-"} / ${p.cameraRoll ?? "-"}`
      ];
      return parts.join("<br>");
    });

    const sel = selectedIds;
    const markerColors = points.map((p) => (sel.has(p.id) ? "rgba(141,240,194,0.92)" : "rgba(255,255,255,0.22)"));
    const markerSizes = points.map((p) => (p.id === activeId ? 9 : sel.has(p.id) ? 6 : 5));

    const trace: any = {
      type: "scattergl",
      mode: "markers",
      x: xs,
      y: ys,
      text: hover,
      customdata: ids,
      hovertemplate: "%{text}<extra></extra>",
      marker: { color: markerColors, size: markerSizes }
    };

    const layout: any = {
      margin: { l: 50, r: 20, t: 10, b: 40 },
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
      xaxis: { title: "X (meters)", zeroline: false, gridcolor: "rgba(255,255,255,0.06)" },
      yaxis: { title: "Y (meters)", zeroline: false, gridcolor: "rgba(255,255,255,0.06)", scaleanchor: "x" },
      dragmode: "pan",
      shapes: shapes.map((s) => ({
        ...s.raw,
        opacity: 0.18,
        fillcolor: s.mode === "include" ? "rgba(141,240,194,0.5)" : "rgba(255,107,107,0.5)",
        line: {
          ...(s.raw?.line ?? {}),
          color: s.mode === "include" ? "rgba(141,240,194,0.9)" : "rgba(255,107,107,0.9)",
          width: 2
        }
      }))
    };

    const config: any = {
      displaylogo: false,
      responsive: true,
      modeBarButtonsToAdd: ["drawline", "drawrect", "drawcircle", "drawclosedpath", "eraseshape"],
      toImageButtonOptions: { filename: `exif-spatial-${session ?? "session"}` }
    };

    Plotly.react(plotRef.current, [trace], layout, config);

    const el: any = plotRef.current;

    const onClick = (ev: any) => {
      const id = ev?.points?.[0]?.customdata;
      if (typeof id === "string") setActiveId(id);
    };
    const onRelayout = (ev: any) => {
      // When shapes are added/edited/removed, Plotly emits relayout events.
      // We'll read the full layout's shapes array from the graph div.
      const gd: any = plotRef.current;
      const nextShapesRaw = (gd?._fullLayout?.shapes ?? []) as any[];

      setShapes((prev) => {
        const prevModeByIdx = new Map<number, ShapeMode>();
        for (const s of prev) prevModeByIdx.set(s.plotlyIndex, s.mode);

        const next: UiShape[] = [];
        for (let i = 0; i < nextShapesRaw.length; i++) {
          const raw = nextShapesRaw[i];
          const type = String(raw?.type ?? "");
          const kind = type === "rect" ? "rect" : type === "circle" ? "circle" : type === "path" ? "path" : "line";
          const forcedMode = shapeModes[i];
          const mode = forcedMode ?? prevModeByIdx.get(i) ?? "include";
          next.push({ plotlyIndex: i, mode, kind, raw });
        }
        return next;
      });

      // Shape indices can shift when deleting; keep a best-effort mode map.
      const nextModeMap: Record<number, ShapeMode> = {};
      const gd: any = plotRef.current;
      const nextShapesRaw2 = (gd?._fullLayout?.shapes ?? []) as any[];
      for (let i = 0; i < nextShapesRaw2.length; i++) nextModeMap[i] = shapeModes[i] ?? "include";
      setShapeModes(nextModeMap);
    };

    el.on?.("plotly_click", onClick);
    el.on?.("plotly_relayout", onRelayout);

    return () => {
      el.removeListener?.("plotly_click", onClick);
      el.removeListener?.("plotly_relayout", onRelayout);
    };
  }, [index, points, selectedIds, activeId, shapes, shapeModes, session]);

  const active = activeId ? pointById.get(activeId) ?? null : null;
  const activeUrl = active ? `/data/file?rel=${encodeURIComponent(active.fileRel)}` : null;

  async function doExport() {
    setExportResult("");
    const selected = Array.from(selectedIds);
    if (!selected.length) {
      setExportResult("Nothing selected.");
      return;
    }
    if (!exportDir.trim()) {
      setExportResult("Set an export directory path first.");
      return;
    }
    const r = await fetch("/api/export", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ exportDir: exportDir.trim(), selected })
    });
    const text = await r.text();
    if (!r.ok) {
      setExportResult(text);
      return;
    }
    setExportResult(text);
  }

  function setModeForShape(idx: number, mode: ShapeMode) {
    setShapeModes((m) => ({ ...m, [idx]: mode }));
    setShapes((prev) => prev.map((s) => (s.plotlyIndex === idx ? { ...s, mode } : s)));
  }

  function clearShapes() {
    setShapes([]);
    setShapeModes({});
    const gd: any = plotRef.current;
    if (gd) Plotly.relayout(gd, { shapes: [] });
  }

  const selectedCount = selectedIds.size;
  const totalCount = index?.points?.length ?? 0;
  const gpsCount = points.length;

  return (
    <div className="wrap">
      <div className="card grid2">
        <div className="cardHeader">
          <div className="title">Spatial View</div>
          <div className="muted">
            session={session ?? "-"} selected={selectedCount}/{totalCount} gps={gpsCount}
          </div>
        </div>
        <div className="content plot" ref={plotRef} />
        <div className="content">
          <div className="row">
            <span className="pill">Draw: line/rect/oval/polygon via Plotly toolbar</span>
            <button className="danger" onClick={clearShapes}>
              Clear shapes
            </button>
            <span className="muted">
              Rule: union(include) minus union(exclude). If no include-shapes, everything is selected until excluded.
            </span>
          </div>
          {shapes.length > 0 && (
            <div className="shapeList">
              {shapes.map((s) => (
                <div key={s.plotlyIndex} className="shapeItem">
                  <span className="pill">
                    #{s.plotlyIndex} {s.kind}
                  </span>
                  <span className="muted">Affects selection</span>
                  <select value={s.mode} onChange={(e) => setModeForShape(s.plotlyIndex, e.target.value as ShapeMode)}>
                    <option value="include">include</option>
                    <option value="exclude">exclude</option>
                  </select>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="card side">
        <div className="cardHeader">
          <div className="title">Inspector</div>
          <div className="muted">{error ? "error" : active ? active.fileName : "click a point"}</div>
        </div>

        <div className="content" style={{ overflow: "auto" }}>
          {error && (
            <div className="muted" style={{ whiteSpace: "pre-wrap" }}>
              {error}
            </div>
          )}
          {index && (
            <div className="kv" style={{ marginBottom: 12 }}>
              <div>zip</div>
              <div>{index.source.zipPath ?? "-"}</div>
              <div>origin</div>
              <div>
                lat0={fmt(index.origin.lat0)} lon0={fmt(index.origin.lon0)}
              </div>
              <div>created</div>
              <div>{index.createdAt}</div>
            </div>
          )}

          {active && (
            <>
              <img className="thumb" src={activeUrl!} alt={active.fileName} />
              <div style={{ height: 10 }} />
              <div className="kv">
                <div>id</div>
                <div>{active.id}</div>
                <div>lat/lon</div>
                <div>
                  {fmt(active.lat)} / {fmt(active.lon)}
                </div>
                <div>xy</div>
                <div>
                  {active.x?.toFixed(2)} / {active.y?.toFixed(2)}
                </div>
                <div>alt</div>
                <div>{active.alt ?? "-"}</div>
                <div>time</div>
                <div>{active.dateTimeOriginal ?? "-"}</div>
                <div>gimbal y/p/r</div>
                <div>
                  {active.gimbalYaw ?? "-"} / {active.gimbalPitch ?? "-"} / {active.gimbalRoll ?? "-"}
                </div>
                <div>camera y/p/r</div>
                <div>
                  {active.cameraYaw ?? "-"} / {active.cameraPitch ?? "-"} / {active.cameraRoll ?? "-"}
                </div>
              </div>
            </>
          )}
        </div>

        <div className="content">
          <div className="row" style={{ marginBottom: 8 }}>
            <div style={{ flex: 1 }}>
              <input
                type="text"
                placeholder="Export directory (absolute path)"
                value={exportDir}
                onChange={(e) => setExportDir(e.target.value)}
              />
            </div>
            <button onClick={doExport}>Export selected</button>
          </div>
          {exportResult && (
            <div className="muted" style={{ whiteSpace: "pre-wrap" }}>
              {exportResult}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

