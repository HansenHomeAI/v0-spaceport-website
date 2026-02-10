export type ShapeMode = "include" | "exclude";

export type UiShape = {
  plotlyIndex: number;
  mode: ShapeMode;
  kind: "rect" | "circle" | "path" | "line";
  raw: any;
};

export type Point2 = { x: number; y: number };

function pointInPoly(p: Point2, poly: Point2[]) {
  // Ray casting; polygon assumed closed (first != last is fine).
  let inside = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const xi = poly[i].x,
      yi = poly[i].y;
    const xj = poly[j].x,
      yj = poly[j].y;
    const intersect = yi > p.y !== yj > p.y && p.x < ((xj - xi) * (p.y - yi)) / (yj - yi + 0.0) + xi;
    if (intersect) inside = !inside;
  }
  return inside;
}

function parseSvgPathToPoints(pathStr: string): Point2[] {
  // Plotly "path" shape uses an SVG path string like: "M x,y L x,y ... Z"
  // We parse numbers in order and treat them as (x,y) pairs.
  const nums = pathStr
    .replace(/[A-Za-z]/g, " ")
    .trim()
    .split(/[\s,]+/)
    .map((s) => Number(s))
    .filter((n) => Number.isFinite(n));
  const pts: Point2[] = [];
  for (let i = 0; i + 1 < nums.length; i += 2) pts.push({ x: nums[i], y: nums[i + 1] });
  return pts;
}

export function pointInShape(p: Point2, shape: any) {
  const type = String(shape?.type ?? "");
  if (type === "rect") {
    const x0 = Number(shape.x0),
      x1 = Number(shape.x1),
      y0 = Number(shape.y0),
      y1 = Number(shape.y1);
    if (![x0, x1, y0, y1].every(Number.isFinite)) return false;
    const xmin = Math.min(x0, x1);
    const xmax = Math.max(x0, x1);
    const ymin = Math.min(y0, y1);
    const ymax = Math.max(y0, y1);
    return p.x >= xmin && p.x <= xmax && p.y >= ymin && p.y <= ymax;
  }
  if (type === "circle") {
    // Plotly stores circle as bounding box corners; treat it as ellipse.
    const x0 = Number(shape.x0),
      x1 = Number(shape.x1),
      y0 = Number(shape.y0),
      y1 = Number(shape.y1);
    if (![x0, x1, y0, y1].every(Number.isFinite)) return false;
    const cx = (x0 + x1) / 2;
    const cy = (y0 + y1) / 2;
    const rx = Math.abs(x1 - x0) / 2;
    const ry = Math.abs(y1 - y0) / 2;
    if (rx === 0 || ry === 0) return false;
    const dx = (p.x - cx) / rx;
    const dy = (p.y - cy) / ry;
    return dx * dx + dy * dy <= 1;
  }
  if (type === "path") {
    const pathStr = String(shape.path ?? "");
    const pts = parseSvgPathToPoints(pathStr);
    if (pts.length < 3) return false;
    return pointInPoly(p, pts);
  }
  if (type === "line") {
    // Treat as a thin corridor around the line; useful for "photos on a line".
    const x0 = Number(shape.x0),
      x1 = Number(shape.x1),
      y0 = Number(shape.y0),
      y1 = Number(shape.y1);
    const w = Number(shape.line?.width ?? 6); // px-ish; plot units vary but OK for quick use
    if (![x0, x1, y0, y1, w].every(Number.isFinite)) return false;
    const vx = x1 - x0;
    const vy = y1 - y0;
    const len2 = vx * vx + vy * vy;
    if (len2 === 0) return false;
    const t = ((p.x - x0) * vx + (p.y - y0) * vy) / len2;
    const tt = Math.max(0, Math.min(1, t));
    const projx = x0 + tt * vx;
    const projy = y0 + tt * vy;
    const dx = p.x - projx;
    const dy = p.y - projy;
    return dx * dx + dy * dy <= (w * w) / 4;
  }
  return false;
}

export function recomputeSelection(args: {
  points: Array<{ x?: number; y?: number; id: string }>;
  shapes: UiShape[];
}) {
  const { points, shapes } = args;
  const include = shapes.filter((s) => s.mode === "include");
  const exclude = shapes.filter((s) => s.mode === "exclude");

  // Behavior:
  // - If there are include-shapes, select union(include) minus union(exclude)
  // - If there are no include-shapes, start with "all" and only subtract excludes
  const selected = new Set<string>();
  if (include.length === 0) {
    for (const p of points) selected.add(p.id);
  } else {
    for (const p of points) {
      if (p.x === undefined || p.y === undefined) continue;
      for (const s of include) {
        if (pointInShape({ x: p.x, y: p.y }, s.raw)) {
          selected.add(p.id);
          break;
        }
      }
    }
  }

  for (const p of points) {
    if (!selected.has(p.id)) continue;
    if (p.x === undefined || p.y === undefined) continue;
    for (const s of exclude) {
      if (pointInShape({ x: p.x, y: p.y }, s.raw)) {
        selected.delete(p.id);
        break;
      }
    }
  }

  return selected;
}

