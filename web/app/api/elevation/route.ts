export const runtime = 'edge';

// Local proxy for Google Elevation API to avoid CORS in development.
// In production we typically call the backend elevation endpoint, but
// this route ensures local `npm run dev` works without AWS.

export async function POST(request: Request): Promise<Response> {
  try {
    const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || '';
    if (!apiKey) {
      return new Response(
        JSON.stringify({ error: 'Missing NEXT_PUBLIC_GOOGLE_MAPS_API_KEY' }),
        { status: 400, headers: { 'content-type': 'application/json' } }
      );
    }

    const body = await request.json().catch(() => ({}));
    const center: string = body.center || '';
    if (!center) {
      return new Response(
        JSON.stringify({ error: 'Missing center' }),
        { status: 400, headers: { 'content-type': 'application/json' } }
      );
    }

    const [latStr, lonStr] = String(center).split(',');
    const lat = Number(latStr);
    const lon = Number(lonStr);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
      return new Response(
        JSON.stringify({ error: 'Invalid center coordinates' }),
        { status: 400, headers: { 'content-type': 'application/json' } }
      );
    }

    const url = `https://maps.googleapis.com/maps/api/elevation/json?locations=${lat},${lon}&key=${apiKey}`;
    const res = await fetch(url, { cache: 'no-store' });
    if (!res.ok) {
      return new Response(
        JSON.stringify({ error: `Upstream error ${res.status}` }),
        { status: 502, headers: { 'content-type': 'application/json' } }
      );
    }
    const data = await res.json();
    if (data.status !== 'OK' || !data.results || !data.results[0]) {
      return new Response(
        JSON.stringify({ error: data.status || 'No results' }),
        { status: 502, headers: { 'content-type': 'application/json' } }
      );
    }

    const elevationMeters = Number(data.results[0].elevation) || 0;
    const elevationFeet = elevationMeters * 3.28084;

    return new Response(
      JSON.stringify({
        elevation_meters: elevationMeters,
        elevation_feet: Number(elevationFeet.toFixed(1)),
        coordinates: { lat, lon },
        source: 'google',
      }),
      {
        status: 200,
        headers: {
          'content-type': 'application/json; charset=utf-8',
          // Allow local browser to call this Next.js route
          'access-control-allow-origin': '*',
        },
      }
    );
  } catch (e: any) {
    return new Response(
      JSON.stringify({ error: 'Proxy elevation failed', detail: String(e?.message || e) }),
      { status: 500, headers: { 'content-type': 'application/json' } }
    );
  }
}


