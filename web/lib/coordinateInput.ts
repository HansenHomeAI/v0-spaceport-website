type LatLng = {
  lat: number;
  lng: number;
};

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
      const parsed = extractDecimalPair(candidate) ?? extractDegreePair(candidate) ?? extractKeyedPair(candidate);
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
    ?? extractDecimalPair(trimmed);

  if (!parsed) {
    return null;
  }

  return `${formatCoordinate(parsed.lat)}, ${formatCoordinate(parsed.lng)}`;
}
