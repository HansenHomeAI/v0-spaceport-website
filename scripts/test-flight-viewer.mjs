#!/usr/bin/env node
import { chromium } from 'playwright';
import { resolve } from 'path';
import { existsSync } from 'fs';

const flightCsv = resolve('Edgewood-1.csv');
if (!existsSync(flightCsv)) {
  console.error('Flight CSV not found at', flightCsv);
  process.exit(1);
}

const url = process.env.FLIGHT_VIEWER_URL ?? 'http://localhost:3000/flight-viewer';

const stringifyArg = async (arg) => {
  try {
    const val = await arg.jsonValue();
    if (typeof val === 'object' && val !== null) {
      return JSON.stringify(val);
    }
    return String(val);
  } catch {
    try {
      return arg.toString();
    } catch {
      return '<unserializable>';
    }
  }
};

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1280, height: 720 } });
  const page = await context.newPage();

  page.on('console', async (msg) => {
    const args = await Promise.all(msg.args().map(stringifyArg));
    const payload = args.length ? ` | args=${args.join(' | ')}` : '';
    console.log(`[browser][${msg.type()}] ${msg.text()}${payload}`);
  });

  page.on('pageerror', (err) => {
    console.error('[browser][pageerror]', err);
  });

  page.on('requestfailed', (request) => {
    console.error('[browser][requestfailed]', request.url(), request.failure()?.errorText);
  });

  page.on('request', (request) => {
    if (request.url().includes('tile.googleapis.com')) {
      console.log('[browser][request]', request.method(), request.url());
    }
  });

  let sampledGlb = 0;
  const MAX_GLB_SAMPLE = 3;

  page.on('response', async (response) => {
    if (response.url().includes('tile.googleapis.com')) {
      let length = null;
      try {
        length = response.headers()['content-length'] ?? null;
      } catch (error) {
        length = `error:${error}`;
      }
      let sampleSize = null;
      if (response.url().includes('.glb') && sampledGlb < MAX_GLB_SAMPLE) {
        try {
          const buffer = await response.body();
          sampleSize = buffer?.length ?? null;
        } catch (error) {
          sampleSize = `error:${error}`;
        }
        sampledGlb += 1;
      }
      console.log('[browser][response]', response.status(), response.url(), 'length=', length, 'bodyBytes=', sampleSize);
    }
  });

  console.log('[runner] navigating to', url);
  await page.goto(url, { waitUntil: 'networkidle', timeout: 60_000 });

  const fileInput = page.locator('input[type="file"]');
  const count = await fileInput.count();
  console.log('[runner] found file inputs:', count);
  if (count === 0) {
    throw new Error('No file input found on the page');
  }

  console.log('[runner] uploading flight CSV', flightCsv);
  await fileInput.first().setInputFiles(flightCsv);

  console.log('[runner] waiting for viewer to process flight');
  await page.waitForTimeout(45_000);

  const viewer = page.locator('.flight-viewer__cesium-canvas');
  if (await viewer.count()) {
    const screenshotPath = resolve('logs/flight-viewer-playwright.png');
    await viewer.screenshot({ path: screenshotPath, fullPage: false });
    console.log('[runner] captured viewer screenshot ->', screenshotPath);
  } else {
    console.warn('[runner] viewer canvas not found for screenshot');
  }

  const diagnostics = await page.evaluate(() => {
    const diag = window.__flightViewerDiagnostics;
    if (!diag) {
      return null;
    }
    const viewer = diag.viewer;
    const tileset = diag.tileset;
    const result = {};
    if (viewer) {
      try {
        const camera = viewer.camera;
        const Cesium = window.Cesium;
        if (Cesium && camera) {
          const cartographic = Cesium.Cartographic.fromCartesian(camera.positionWC);
          if (cartographic) {
            result.cameraCartographic = {
              latitude: Cesium.Math.toDegrees(cartographic.latitude),
              longitude: Cesium.Math.toDegrees(cartographic.longitude),
              height: cartographic.height,
            };
          }
          result.cameraHeading = Cesium.Math.toDegrees(camera.heading);
          result.cameraPitch = Cesium.Math.toDegrees(camera.pitch);
          result.cameraRoll = Cesium.Math.toDegrees(camera.roll);
        }
      } catch (error) {
        result.cameraError = String(error);
      }
    }
    if (tileset) {
      try {
        const Cesium = window.Cesium;
        const info = {
          ready: tileset.ready,
          show: tileset.show,
          totalMemoryUsageInBytes: tileset.totalMemoryUsageInBytes ?? null,
          rootBoundingSphereRadius: tileset.root?.boundingSphere?.radius ?? null,
        };
        if (Cesium && tileset.root?.boundingSphere?.center) {
          const cartographic = Cesium.Cartographic.fromCartesian(tileset.root.boundingSphere.center);
          if (cartographic) {
            info.rootBoundingSphereCenterCartographic = {
              latitude: Cesium.Math.toDegrees(cartographic.latitude),
              longitude: Cesium.Math.toDegrees(cartographic.longitude),
              height: cartographic.height,
            };
          }
        }
        info.maximumScreenSpaceError = tileset.maximumScreenSpaceError;
        info.dynamicScreenSpaceError = tileset.dynamicScreenSpaceError;
        info.clippingPlanes = tileset.clippingPlanes ? true : false;
        info.stylePresent = tileset.style ? true : false;
        info.statistics = tileset.statistics ? {
          numberOfPendingRequests: tileset.statistics.numberOfPendingRequests,
          numberOfTilesWithContentReady: tileset.statistics.numberOfTilesWithContentReady,
          numberOfTilesProcessing: tileset.statistics.numberOfTilesProcessing,
        } : null;

        const sampleTiles = [];
        if (tileset.root) {
          const stack = [{ tile: tileset.root, depth: 0 }];
          while (stack.length && sampleTiles.length < 40) {
            const { tile, depth } = stack.shift();
            if (!tile) {
              continue;
            }
            const bounding = tile.boundingSphere;
            let boundingCartographic = null;
            if (Cesium && bounding?.center) {
              const cartographic = Cesium.Cartographic.fromCartesian(bounding.center);
              if (cartographic) {
                boundingCartographic = {
                  latitude: Cesium.Math.toDegrees(cartographic.latitude),
                  longitude: Cesium.Math.toDegrees(cartographic.longitude),
                  height: cartographic.height,
                };
              }
            }
            sampleTiles.push({
              depth,
              geometricError: tile.geometricError,
              contentAvailable: !!tile.content,
              boundingSphereRadius: bounding?.radius ?? null,
              boundingSphereCartographic: boundingCartographic,
            });
            if (tile.children && tile.children.length && depth < 10) {
              for (let i = 0; i < tile.children.length; i += 1) {
                stack.push({ tile: tile.children[i], depth: depth + 1 });
              }
            }
          }
        }
        info.sampleTiles = sampleTiles;
        result.tileset = info;
      } catch (error) {
        result.tilesetError = String(error);
      }
    }
    return result;
  });
  console.log('[runner] diagnostics', JSON.stringify(diagnostics, null, 2));

  await browser.close();
  console.log('[runner] completed');
})();
