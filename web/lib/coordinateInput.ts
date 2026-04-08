type LatLng = {
  lat: number;
  lng: number;
};

type CardinalDirection = "N" | "S" | "E" | "W";

function isValidLatLng(lat: number, lng: number): boolean {
  return Number.isFinite(lat)
    && Number.isFinite(lng)
    && Math.abs(lat) <= 90
    && Math.abs(lng) <= 180;
}

function finalizePair(first: number, second: number): LatLng | null {
  if (isValidLatLng(first, second)) {
    return { lat: first, lng: second };
  }

  // Common copy/paste source formats use lng,lat. Only swap when the ranges make that unambiguous.
  if (Math.abs(first) <= 180 && Math.abs(second) <= 90) {
    return { lat: second, lng: first };
  }

  return null;
}

function extractDecimalPair(raw: string): LatLng | null {
  const match = raw.match(/([-+]?\d+(?:\.\d+)?)\s*,\s*([-+]?\d+(?:\.\d+)?)/);
  if (!match) {
    return null;
  }

  return finalizePair(Number.parseFloat(match[1]), Number.parseFloat(match[2]));
}

function extractDegreePair(raw: string): LatLng | null {
  const match = raw.match(/(\d+(?:\.\d+)?)\s*°?\s*([NS])\s*,\s*(\d+(?:\.\d+)?)\s*°?\s*([EW])/i);
  if (!match) {
    return null;
  }

  const lat = Number.parseFloat(match[1]) * (match[2].toUpperCase() === "S" ? -1 : 1);
  const lng = Number.parseFloat(match[3]) * (match[4].toUpperCase() === "W" ? -1 : 1);
  return isValidLatLng(lat, lng) ? { lat, lng } : null;
}

function dmsToDecimal(
  degrees: string,
  minutes: string | undefined,
  seconds: string | undefined,
  direction: CardinalDirection,
): number {
  const absValue = Number.parseFloat(degrees)
    + Number.parseFloat(minutes || "0") / 60
    + Number.parseFloat(seconds || "0") / 3600;
  return direction === "S" || direction === "W" ? -absValue : absValue;
}

function extractDmsPair(raw: string): LatLng | null {
  const normalized = raw
    .replace(/[′’]/g, "'")
    .replace(/[″”]/g, '"');
  const match = normalized.match(
    /(\d+(?:\.\d+)?)\s*°\s*(\d+(?:\.\d+)?)?\s*'?\s*(\d+(?:\.\d+)?)?\s*"?\s*([NS])(?:\s*,?\s*)(\d+(?:\.\d+)?)\s*°\s*(\d+(?:\.\d+)?)?\s*'?\s*(\d+(?:\.\d+)?)?\s*"?\s*([EW])/i,
  );
  if (!match) {
    return null;
  }

  const lat = dmsToDecimal(match[1], match[2], match[3], match[4].toUpperCase() as CardinalDirection);
  const lng = dmsToDecimal(match[5], match[6], match[7], match[8].toUpperCase() as CardinalDirection);
  return isValidLatLng(lat, lng) ? { lat, lng } : null;
}

function extractKeyedPair(raw: string): LatLng | null {
  const latMatch = raw.match(/["']?(?:lat|latitude)["']?\s*[:=]\s*([-+]?\d+(?:\.\d+)?)/i);
  const lngMatch = raw.match(/["']?(?:lng|lon|longitude)["']?\s*[:=]\s*([-+]?\d+(?:\.\d+)?)/i);
  if (!latMatch || !lngMatch) {
    return null;
  }

  const lat = Number.parseFloat(latMatch[1]);
  const lng = Number.parseFloat(lngMatch[1]);
  return isValidLatLng(lat, lng) ? { lat, lng } : null;
}

function extractFromUrl(raw: string): LatLng | null {
  try {
    const url = new URL(raw);
    const candidates = [
      url.searchParams.get("q"),
      url.searchParams.get("ll"),
      url.searchParams.get("center"),
      url.searchParams.get("query"),
    ];

    for (const candidate of candidates) {
      if (!candidate) {
        continue;
      }
      const parsed = extractDecimalPair(candidate)
        ?? extractDegreePair(candidate)
        ?? extractDmsPair(candidate)
        ?? extractKeyedPair(candidate);
      if (parsed) {
        return parsed;
      }
    }

    const atMatch = `${url.pathname}${url.hash}`.match(/@([-+]?\d+(?:\.\d+)?),([-+]?\d+(?:\.\d+)?)/);
    if (atMatch) {
      return finalizePair(Number.parseFloat(atMatch[1]), Number.parseFloat(atMatch[2]));
    }
  } catch {
    return null;
  }

  return null;
}

function formatCoordinate(value: number): string {
  return value.toFixed(6);
}

export function normalizeCenterCoordinateInput(raw: string): string | null {
  const trimmed = raw.trim();
  if (!trimmed) {
    return null;
  }

  const parsed = extractFromUrl(trimmed)
    ?? extractKeyedPair(trimmed)
    ?? extractDegreePair(trimmed)
    ?? extractDmsPair(trimmed)
    ?? extractDecimalPair(trimmed);

  if (!parsed) {
    return null;
  }

  return `${formatCoordinate(parsed.lat)}, ${formatCoordinate(parsed.lng)}`;
}
