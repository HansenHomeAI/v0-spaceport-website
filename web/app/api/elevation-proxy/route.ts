export const runtime = 'edge';

import { NextResponse } from 'next/server';

// Local dev proxy for Google Elevation API to avoid CORS
// Usage: POST { center: "lat, lon" }

export async function POST(request: Request): Promise<Response> {
  try {
    const body = await request.json().catch(() => ({}));
    const center: string | undefined = body.center;

    if (!center) {
      return NextResponse.json({ error: 'center is required ("lat, lon")' }, { status: 400 });
    }

    const [latStr, lonStr] = center.split(',').map((s: string) => s.trim());
    const lat = Number(latStr);
    const lon = Number(lonStr);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
      return NextResponse.json({ error: 'invalid center coordinates' }, { status: 400 });
    }

    const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;
    if (!apiKey) {
      return NextResponse.json({ error: 'Google Maps API key missing' }, { status: 500 });
    }

    const url = `https://maps.googleapis.com/maps/api/elevation/json?locations=${lat},${lon}&key=${apiKey}`;
    const res = await fetch(url, { cache: 'no-store' });
    if (!res.ok) {
      return NextResponse.json({ error: `elevation http ${res.status}` }, { status: 502 });
    }
    const data = await res.json();
    if (data.status !== 'OK' || !data.results || !data.results[0]) {
      return NextResponse.json({ error: data.status || 'elevation error' }, { status: 502 });
    }

    const elevationMeters: number = data.results[0].elevation;
    const elevationFeet = elevationMeters * 3.28084;

    return NextResponse.json({
      elevation_meters: elevationMeters,
      elevation_feet: elevationFeet,
      coordinates: { lat, lon },
      provider: 'google',
    });
  } catch (err: any) {
    return NextResponse.json({ error: err?.message || 'elevation proxy failed' }, { status: 500 });
  }
}


