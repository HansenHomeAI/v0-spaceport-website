# 🛰️ EXIF GPS Processing Quick Reference

## Summary
The SfM pipeline now uses **EXIF-only GPS priors** from drone photos. CSV flight paths are **deprecated and ignored**. This anchors the reconstruction in a consistent ENU coordinate frame (East/North/Up) and stabilizes axis alignment without relying on speculative path assumptions.

## What Is Used
- **EXIF GPS**: latitude, longitude, altitude
- **EXIF timestamps** (DateTimeOriginal) for ordering (when available)
- **DJI orientation (XMP)**: FlightYaw/Pitch/Roll and GimbalYaw/Pitch/Roll (used as optional heading priors)

## Required Inputs
- A ZIP of drone images **with intact EXIF metadata**
- No CSV needed

## How It Works
1. Extract EXIF GPS from each image.
2. Compute a local origin at the GPS centroid.
3. Convert lat/lon/alt → local ENU coordinates.
4. Create OpenSfM priors:
   - `exif_overrides.json`
   - `gps_priors.json`
   - `reference_lla.json`
   - `reference.txt`

If EXIF GPS coverage is too low, the pipeline falls back to standard SfM (no priors).

## EXIF Tags of Interest
- `GPSLatitude`, `GPSLongitude`, `GPSAltitude`
- `DateTimeOriginal` (for ordering)
- DJI XMP (if present):
  - `FlightYawDegree`, `FlightPitchDegree`, `FlightRollDegree`
  - `GimbalYawDegree`, `GimbalPitchDegree`, `GimbalRollDegree`

## Troubleshooting
### "EXIF GPS coverage insufficient"
- Most images are missing GPS tags.
- **Fix**: Ensure images are original exports from the drone and not stripped by editors or messaging apps.

### "Axes rotated / model far from center"
- Common when EXIF GPS is missing or corrupted.
- **Fix**: Confirm EXIF GPS exists; run a quick check with `exiftool -gps:all <image>`.

### "Timestamp ordering skipped"
- EXIF timestamps are missing.
- Pipeline falls back to filename ordering.

## Performance Benefits
- Anchors coordinate frame → stable axis alignment
- Reduces matching search space when GPS exists
- Often improves stability over large low‑texture scenes (water, fields, snow)

---

**Note**: CSV flight path inputs are deprecated and ignored by the pipeline.
