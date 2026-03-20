#!/usr/bin/env bash
# Unit tests + production build + E2E against a local Next server.
set -euo pipefail
cd "$(dirname "$0")/.."
PORT="${PORT:-3456}"

npm run test:camera-overlap-math
npm run build

npx next start -p "$PORT" &
PID=$!
trap 'kill $PID 2>/dev/null || true' EXIT
sleep 3

BASE_URL="http://127.0.0.1:$PORT" node scripts/e2e-camera-overlap.mjs
echo "run-camera-overlap-full-test.sh: all passed"
