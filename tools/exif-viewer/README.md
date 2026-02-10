# EXIF Spatial Viewer

Local web app to:

- Ingest a ZIP of drone photos (extract + read EXIF: GPS + gimbal yaw/pitch/roll).
- View all photos spatially (top-down XY derived from lat/lon).
- Draw shapes (polygon/rectangle/oval) to include/exclude photos.
- Export the currently-selected photos to a new folder.

## Prereqs

- Node 18+

## Quick Start (Your Example ZIP)

```bash
cd tools/exif-viewer
npm install
npm run ingest -- --zip "/Users/gabrielhansen/Downloads/Red Arrow Ranch Testing/Archive.zip"
npm run dev
```

Then open the URL printed by Vite (usually `http://localhost:5173`).

## Notes

- EXIF parsing uses `exiftool-vendored` (no system `exiftool` required).
- Data is written under `tools/exif-viewer/.data/`.
- Export copies originals into the chosen export directory (flat, filenames preserved).

