#!/usr/bin/env node

import path from "node:path";
import { createRuleMatcher, filterPlyFile, parsePlyHeader } from "../lib/splat-editor/ply.js";
import { parseRuleOptions } from "../lib/splat-editor/session-store.js";

function usage() {
  console.error(`Usage:
  node web/scripts/edit-3dgs-ply.mjs --input <path> [--output <path>] [rules]

Rules:
  --y-gt <number>
  --y-lt <number>
  --radius-gt <number>
  --radius-lt <number>
  --bounds <minX,maxX,minY,maxY,minZ,maxZ>
  --min-x <number> --max-x <number> --min-y <number> --max-y <number> --min-z <number> --max-z <number>
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
      case "--y-gt":
        options.yGt = next;
        index += 1;
        break;
      case "--y-lt":
        options.yLt = next;
        index += 1;
        break;
      case "--radius-gt":
        options.radiusGt = next;
        index += 1;
        break;
      case "--radius-lt":
        options.radiusLt = next;
        index += 1;
        break;
      case "--bounds":
        options.bounds = next;
        index += 1;
        break;
      case "--min-x":
        options.minX = next;
        index += 1;
        break;
      case "--max-x":
        options.maxX = next;
        index += 1;
        break;
      case "--min-y":
        options.minY = next;
        index += 1;
        break;
      case "--max-y":
        options.maxY = next;
        index += 1;
        break;
      case "--min-z":
        options.minZ = next;
        index += 1;
        break;
      case "--max-z":
        options.maxZ = next;
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

async function main() {
  const args = parseArgs(process.argv);
  if (!args.input) {
    usage();
    throw new Error("--input is required");
  }

  const input = path.resolve(args.input);
  const output = path.resolve(args.output ?? args.input);
  const matcher = createRuleMatcher(parseRuleOptions(args));
  const result = await filterPlyFile(input, output, matcher);

  const sourceHeader = parsePlyHeader(result.buffer);
  console.log(
    JSON.stringify(
      {
        input,
        output,
        changed: result.changed,
        removedCount: result.removedCount,
        keptCount: result.keptCount,
        vertexCount: sourceHeader.vertexCount,
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
