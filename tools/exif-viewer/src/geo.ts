const R = 6378137; // meters

export function lonLatToLocalMeters(args: {
  lon: number;
  lat: number;
  lon0: number;
  lat0: number;
}) {
  const { lon, lat, lon0, lat0 } = args;
  const degToRad = Math.PI / 180;
  const x = (lon - lon0) * degToRad * R * Math.cos(lat0 * degToRad);
  const y = (lat - lat0) * degToRad * R;
  return { x, y };
}

