#!/usr/bin/env node

import path from "node:path";
import { mutatePlyFile } from "../lib/splat-editor/ply.js";
import { createDefaultScenePayload } from "../lib/sogsViewerSceneDefaults.ts";

function usage() {
  console.error(`Usage:
  node web/scripts/soften-3dgs-ply.mjs --input <path> [--output <path>] [options]

Options:
  --radius-gt <number>          Start softening past this world-space radius. Default: 2
  --radius-full <number>        Reach full-strength softening by this radius. Default: 6
  --scale-max <number>          Max scale multiplier at full strength. Default: 1.8
  --opacity-min <number>        Min opacity multiplier at full strength. Default: 0.82
  --rest-min <number>           Min f_rest multiplier at full strength. Default: 0.45
`);
}

function parseArgs(argv) {
  const options = {};
  for (let index = 2; index < argv.length; index += 1) {
    const token = argv[index];
    const next = argv[index + 1];
    switch (token) {
      case "--input":
        options.input = next;
        index += 1;
        break;
      case "--output":
        options.output = next;
        index += 1;
        break;
      case "--radius-gt":
        options.radiusGt = Number.parseFloat(next);
        index += 1;
        break;
      case "--radius-full":
        options.radiusFull = Number.parseFloat(next);
        index += 1;
        break;
      case "--scale-max":
        options.scaleMax = Number.parseFloat(next);
        index += 1;
        break;
      case "--opacity-min":
        options.opacityMin = Number.parseFloat(next);
        index += 1;
        break;
      case "--rest-min":
        options.restMin = Number.parseFloat(next);
        index += 1;
        break;
      case "--help":
      case "-h":
        usage();
        process.exit(0);
      default:
        throw new Error(`Unknown argument: ${token}`);
    }
  }
  return options;
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function toRadians(value) {
  return (value * Math.PI) / 180;
}

function rotatePointXYZ(point, rotation) {
  const [rx, ry, rz] = rotation.map(toRadians);
  const cx = Math.cos(rx);
  const sx = Math.sin(rx);
  const cy = Math.cos(ry);
  const sy = Math.sin(ry);
  const cz = Math.cos(rz);
  const sz = Math.sin(rz);

  const y1 = point.y * cx - point.z * sx;
  const z1 = point.y * sx + point.z * cx;
  const x1 = point.x;

  const x2 = x1 * cy + z1 * sy;
  const z2 = -x1 * sy + z1 * cy;
  const y2 = y1;

  const x3 = x2 * cz - y2 * sz;
  const y3 = x2 * sz + y2 * cz;

  return { x: x3, y: y3, z: z2 };
}

function transformPoint(point, transform) {
  const scale = Number.isFinite(transform.scale) ? transform.scale : 1;
  const scaled = {
    x: point.x * scale,
    y: point.y * scale,
    z: point.z * scale,
  };
  const rotated = rotatePointXYZ(scaled, transform.rotation);
  return {
    x: rotated.x + transform.position[0],
    y: rotated.y + transform.position[1],
    z: rotated.z + transform.position[2],
  };
}

function lerp(start, end, amount) {
  return start + (end - start) * amount;
}

async function main() {
  const args = parseArgs(process.argv);
  if (!args.input) {
    usage();
    throw new Error("--input is required");
  }

  const input = path.resolve(args.input);
  const output = path.resolve(args.output ?? args.input);
  const radiusGt = Number.isFinite(args.radiusGt) ? args.radiusGt : 2;
  const radiusFull = Number.isFinite(args.radiusFull) ? args.radiusFull : 6;
  const scaleMax = Number.isFinite(args.scaleMax) ? args.scaleMax : 1.8;
  const opacityMin = Number.isFinite(args.opacityMin) ? args.opacityMin : 0.82;
  const restMin = Number.isFinite(args.restMin) ? args.restMin : 0.45;
  const scene = createDefaultScenePayload();

  const result = await mutatePlyFile(input, output, ({ x, y, z, get, set }) => {
    const world = transformPoint({ x, y, z }, scene);
    const radius = Math.sqrt(world.x * world.x + world.y * world.y + world.z * world.z);
    if (radius <= radiusGt) {
      return false;
    }

    const span = Math.max(radiusFull - radiusGt, 0.0001);
    const strength = clamp((radius - radiusGt) / span, 0, 1);
    const scaleMultiplier = lerp(1, scaleMax, strength);
    const opacityMultiplier = lerp(1, opacityMin, strength);
    const restMultiplier = lerp(1, restMin, strength);

    set("scale_0", get("scale_0") + Math.log(scaleMultiplier));
    set("scale_1", get("scale_1") + Math.log(scaleMultiplier));
    set("scale_2", get("scale_2") + Math.log(scaleMultiplier));
    set("opacity", get("opacity") + Math.log(opacityMultiplier));

    for (let index = 0; index < 45; index += 1) {
      const name = `f_rest_${index}`;
      const current = get(name);
      if (current != null) {
        set(name, current * restMultiplier);
      }
    }

    return true;
  });

  console.log(
    JSON.stringify(
      {
        input,
        output,
        changed: result.changed,
        modifiedCount: result.modifiedCount,
        vertexCount: result.vertexCount,
        radiusGt,
        radiusFull,
        scaleMax,
        opacityMin,
        restMin,
      },
      null,
      2,
    ),
  );
}

main().catch((error) => {
  console.error(error.message || String(error));
  process.exit(1);
});
