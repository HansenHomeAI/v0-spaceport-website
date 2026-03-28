import { createHash } from "node:crypto";
import fs from "node:fs/promises";

const SCALAR_TYPES = {
  char: { size: 1, getter: "getInt8" },
  uchar: { size: 1, getter: "getUint8" },
  int8: { size: 1, getter: "getInt8" },
  uint8: { size: 1, getter: "getUint8" },
  short: { size: 2, getter: "getInt16" },
  ushort: { size: 2, getter: "getUint16" },
  int16: { size: 2, getter: "getInt16" },
  uint16: { size: 2, getter: "getUint16" },
  int: { size: 4, getter: "getInt32" },
  uint: { size: 4, getter: "getUint32" },
  int32: { size: 4, getter: "getInt32" },
  uint32: { size: 4, getter: "getUint32" },
  float: { size: 4, getter: "getFloat32" },
  float32: { size: 4, getter: "getFloat32" },
  double: { size: 8, getter: "getFloat64" },
  float64: { size: 8, getter: "getFloat64" },
};

function decodeHeader(buffer) {
  let lineStart = 0;
  const lines = [];
  let newline = "\n";

  for (let index = 0; index < buffer.length; index += 1) {
    if (buffer[index] !== 0x0a) {
      continue;
    }
    const lineBuffer = buffer.subarray(lineStart, index);
    let line = lineBuffer.toString("utf8");
    if (line.endsWith("\r")) {
      line = line.slice(0, -1);
      newline = "\r\n";
    }
    lines.push(line);
    lineStart = index + 1;
    if (line === "end_header") {
      return { lines, headerByteLength: index + 1, newline };
    }
  }

  throw new Error("Invalid PLY: missing end_header");
}

export function parsePlyHeader(buffer) {
  const { lines, headerByteLength, newline } = decodeHeader(buffer);
  if (lines[0] !== "ply") {
    throw new Error("Invalid PLY: missing magic header");
  }

  const formatLine = lines.find((line) => line.startsWith("format "));
  if (!formatLine) {
    throw new Error("Invalid PLY: missing format line");
  }
  const [, format] = formatLine.split(/\s+/);
  if (format !== "binary_little_endian") {
    throw new Error(`Unsupported PLY format: ${format}`);
  }

  const elements = [];
  let currentElement = null;
  let vertexLineIndex = -1;

  for (let lineIndex = 0; lineIndex < lines.length; lineIndex += 1) {
    const line = lines[lineIndex];
    if (line.startsWith("element ")) {
      const [, name, countText] = line.split(/\s+/);
      const element = {
        name,
        count: Number.parseInt(countText, 10),
        properties: [],
        lineIndex,
      };
      elements.push(element);
      currentElement = element;
      if (name === "vertex") {
        vertexLineIndex = lineIndex;
      }
      continue;
    }

    if (line.startsWith("property ")) {
      if (!currentElement) {
        throw new Error("Invalid PLY: property declared before element");
      }
      const parts = line.split(/\s+/);
      if (parts[1] === "list") {
        const property = {
          kind: "list",
          countType: parts[2],
          valueType: parts[3],
          name: parts[4],
        };
        currentElement.properties.push(property);
        continue;
      }
      const property = {
        kind: "scalar",
        type: parts[1],
        name: parts[2],
      };
      currentElement.properties.push(property);
    }
  }

  const vertexElement = elements.find((element) => element.name === "vertex");
  if (!vertexElement) {
    throw new Error("Invalid PLY: missing vertex element");
  }

  let vertexStride = 0;
  const propertyOffsets = new Map();

  for (const property of vertexElement.properties) {
    if (property.kind !== "scalar") {
      throw new Error("Unsupported PLY: list properties in vertex element");
    }
    const descriptor = SCALAR_TYPES[property.type];
    if (!descriptor) {
      throw new Error(`Unsupported PLY vertex property type: ${property.type}`);
    }
    propertyOffsets.set(property.name, {
      offset: vertexStride,
      type: property.type,
      size: descriptor.size,
      getter: descriptor.getter,
    });
    vertexStride += descriptor.size;
  }

  return {
    lines,
    newline,
    format,
    elements,
    headerByteLength,
    vertexElement,
    vertexLineIndex,
    vertexCount: vertexElement.count,
    vertexStride,
    propertyOffsets,
    vertexDataStart: headerByteLength,
    vertexDataEnd: headerByteLength + vertexElement.count * vertexStride,
  };
}

export function getVertexCountFromBuffer(buffer) {
  return parsePlyHeader(buffer).vertexCount;
}

function readScalar(view, byteOffset, descriptor) {
  return view[descriptor.getter](byteOffset, true);
}

export function createRuleMatcher(options = {}) {
  const minX = Number.isFinite(options.minX) ? options.minX : null;
  const maxX = Number.isFinite(options.maxX) ? options.maxX : null;
  const minY = Number.isFinite(options.minY) ? options.minY : null;
  const maxY = Number.isFinite(options.maxY) ? options.maxY : null;
  const minZ = Number.isFinite(options.minZ) ? options.minZ : null;
  const maxZ = Number.isFinite(options.maxZ) ? options.maxZ : null;
  const yGt = Number.isFinite(options.yGt) ? options.yGt : null;
  const yLt = Number.isFinite(options.yLt) ? options.yLt : null;
  const radiusGt = Number.isFinite(options.radiusGt) ? options.radiusGt : null;
  const radiusLt = Number.isFinite(options.radiusLt) ? options.radiusLt : null;

  return ({ x, y, z }) => {
    if (yGt != null && y > yGt) return false;
    if (yLt != null && y < yLt) return false;
    if (minX != null && x < minX) return false;
    if (maxX != null && x > maxX) return false;
    if (minY != null && y < minY) return false;
    if (maxY != null && y > maxY) return false;
    if (minZ != null && z < minZ) return false;
    if (maxZ != null && z > maxZ) return false;

    if (radiusGt != null || radiusLt != null) {
      const radius = Math.sqrt(x * x + y * y + z * z);
      if (radiusGt != null && radius > radiusGt) return false;
      if (radiusLt != null && radius < radiusLt) return false;
    }

    return true;
  };
}

export function filterPlyBuffer(buffer, matcher) {
  const header = parsePlyHeader(buffer);
  const xDescriptor = header.propertyOffsets.get("x");
  const yDescriptor = header.propertyOffsets.get("y");
  const zDescriptor = header.propertyOffsets.get("z");

  if (!xDescriptor || !yDescriptor || !zDescriptor) {
    throw new Error("PLY vertex element must include x, y, and z properties");
  }

  const view = new DataView(buffer.buffer, buffer.byteOffset, buffer.byteLength);
  const rowStride = header.vertexStride;
  const keptRows = [];
  let removedCount = 0;

  for (let index = 0; index < header.vertexCount; index += 1) {
    const rowOffset = header.vertexDataStart + index * rowStride;
    const x = readScalar(view, rowOffset + xDescriptor.offset, xDescriptor);
    const y = readScalar(view, rowOffset + yDescriptor.offset, yDescriptor);
    const z = readScalar(view, rowOffset + zDescriptor.offset, zDescriptor);
    const keep = matcher({ x, y, z, index });
    if (keep) {
      keptRows.push(buffer.subarray(rowOffset, rowOffset + rowStride));
    } else {
      removedCount += 1;
    }
  }

  if (removedCount === 0) {
    return {
      changed: false,
      removedCount: 0,
      keptCount: header.vertexCount,
      buffer,
      vertexCount: header.vertexCount,
    };
  }

  const nextLines = [...header.lines];
  nextLines[header.vertexLineIndex] = `element vertex ${keptRows.length}`;
  const nextHeaderBuffer = Buffer.from(`${nextLines.join(header.newline)}${header.newline}`, "utf8");
  const tailBytes = buffer.subarray(header.vertexDataEnd);
  const nextBuffer = Buffer.concat([nextHeaderBuffer, ...keptRows, tailBytes]);

  return {
    changed: true,
    removedCount,
    keptCount: keptRows.length,
    buffer: nextBuffer,
    vertexCount: keptRows.length,
  };
}

export async function filterPlyFile(inputPath, outputPath, matcher) {
  const source = await fs.readFile(inputPath);
  const result = filterPlyBuffer(source, matcher);
  if (!result.changed && inputPath === outputPath) {
    return result;
  }
  if (!result.changed && inputPath !== outputPath) {
    await fs.copyFile(inputPath, outputPath);
    return result;
  }
  await fs.writeFile(outputPath, result.buffer);
  return result;
}

export async function sha256File(filePath) {
  const file = await fs.readFile(filePath);
  return createHash("sha256").update(file).digest("hex");
}

