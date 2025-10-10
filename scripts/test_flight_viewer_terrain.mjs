#!/usr/bin/env node
/**
 * Flight Viewer Terrain Test
 * Exercises the 3D terrain visualisation flow with the Playwright MCP server.
 */

import { Client } from '@modelcontextprotocol/sdk/client';
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js';
import { readFileSync, writeFileSync } from 'fs';
import { resolve } from 'path';

const MCP_URL = process.env.PLAYWRIGHT_MCP_SSE_URL ?? 'http://localhost:5174/sse';
const TARGET_BASE_URL = process.argv[2] ?? 'http://localhost:3003';
const targetUrl = new URL('/flight-viewer', TARGET_BASE_URL);
if (!targetUrl.searchParams.has('debugCesium')) {
  targetUrl.searchParams.set('debugCesium', '1');
}
const FLIGHT_VIEWER_URL = targetUrl.toString();
const HOST_SLUG = FLIGHT_VIEWER_URL.replace(/^https?:\/\//, '').replace(/[^a-z0-9]+/gi, '-');

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function testFlightViewerTerrain() {
  console.log('🚀 Starting Flight Viewer Terrain Test');
  console.log(`📍 Target URL: ${FLIGHT_VIEWER_URL}`);
  console.log(`🔌 MCP Server: ${MCP_URL}`);

  const client = new Client(
    { name: 'flight-viewer-terrain-test', version: '1.0.0' },
    { capabilities: {} }
  );

  const transport = new SSEClientTransport(new URL(MCP_URL));
  await client.connect(transport);
  console.log('✅ Connected to Playwright MCP');

  const callTool = async (name, args = {}) => {
    const result = await client.callTool({ name, arguments: args });
    return result;
  };

  try {
    // Navigate to flight viewer
    console.log('\n📄 Step 1: Navigate to flight viewer');
    await callTool('browser_navigate', { url: FLIGHT_VIEWER_URL });
    await sleep(3000);

    // Snapshot page structure before upload
    console.log('\n📸 Step 2: Capture initial snapshot');
    const initialSnapshot = await callTool('browser_snapshot');
    const initialSnapshotText = initialSnapshot.content?.find((item) => item.type === 'text')?.text ?? '';
    console.log('Initial snapshot captured');
    const initialSnapshotPath = resolve(process.cwd(), `logs/flight-viewer-initial-snapshot-${HOST_SLUG}.txt`);
    writeFileSync(initialSnapshotPath, initialSnapshotText, 'utf-8');
    console.log(`Initial snapshot saved to ${initialSnapshotPath}`);

    // Get console logs
    console.log('\n📋 Step 3: Check console logs');
    const consoleLogsInitial = await callTool('browser_console_messages');
    console.log('Initial console messages:', JSON.stringify(consoleLogsInitial, null, 2));
    const initialLogsPath = resolve(process.cwd(), `logs/flight-viewer-console-initial-${HOST_SLUG}.json`);
    writeFileSync(initialLogsPath, JSON.stringify(consoleLogsInitial, null, 2), 'utf-8');

    // Upload CSV file
    console.log('\n📤 Step 4: Upload Edgewood-1.csv');
    const csvPath = resolve(process.cwd(), 'Edgewood-1.csv');
    const csvContent = readFileSync(csvPath, 'utf-8');
    console.log(`CSV loaded: ${csvContent.split('\n').length} lines`);

    console.log('Triggering input click via evaluate');
    await callTool('browser_evaluate', {
      function: "() => { const input = document.querySelector(\"input[type='file']\"); if (!input) throw new Error('Flight Viewer file input not found'); input.click(); }"
    });
    await callTool('browser_file_upload', { paths: [csvPath] });

    console.log('Waiting for flight load UI');
    await callTool('browser_wait_for', { text: 'Loaded Flights (1)', time: 10 });
    await sleep(4000);

    // Capture snapshot after upload
    const postUploadSnapshot = await callTool('browser_snapshot');
    const postUploadSnapshotText = postUploadSnapshot.content?.find((item) => item.type === 'text')?.text ?? '';
    console.log('Post-upload snapshot captured');
    const postSnapshotPath = resolve(process.cwd(), `logs/flight-viewer-post-upload-snapshot-${HOST_SLUG}.txt`);
    writeFileSync(postSnapshotPath, postUploadSnapshotText, 'utf-8');
    console.log(`Post-upload snapshot saved to ${postSnapshotPath}`);

    // Check console for terrain loading messages
    console.log('\n📋 Step 5: Check for terrain loading logs');
    const logsAfter = await callTool('browser_console_messages');
    console.log('Console after upload:', JSON.stringify(logsAfter, null, 2));
    const postLogsPath = resolve(process.cwd(), `logs/flight-viewer-console-post-upload-${HOST_SLUG}.json`);
    writeFileSync(postLogsPath, JSON.stringify(logsAfter, null, 2), 'utf-8');
    console.log(`Post-upload console logs saved to ${postLogsPath}`);

    // Capture camera debug state (requires dev instrumentation)
    console.log('\n🛰️ Step 6: Capture camera debug state');
    const cameraDebug = await callTool('browser_evaluate', {
      function: `() => {
        const viewer = (window && window.__spaceportFlightViewer) || null;
        const Cesium = (window && window.__spaceportCesium) || null;
        const lastFit = (window && window.__spaceportLastFit) || (viewer && viewer.__spaceportLastFit) || null;
        if (!viewer || !Cesium) {
          return { available: false, message: 'Viewer or Cesium debug handle missing' };
        }
        const camera = viewer.camera;
        const cartographic = camera.positionCartographic;
        const toDeg = (r) => Cesium.Math.toDegrees(r);
        const cart = camera.position;
        const magnitude = cart ? Math.sqrt((cart.x ?? 0) ** 2 + (cart.y ?? 0) ** 2 + (cart.z ?? 0) ** 2) : null;
        return {
          available: true,
          camera: {
            latitudeDeg: cartographic ? toDeg(cartographic.latitude) : null,
            longitudeDeg: cartographic ? toDeg(cartographic.longitude) : null,
            heightMeters: cartographic ? cartographic.height : null,
            headingDeg: toDeg(camera.heading),
            pitchDeg: toDeg(camera.pitch),
            rollDeg: toDeg(camera.roll),
          },
          cameraMagnitude: magnitude,
          lastFit,
        };
      }`
    });
    console.log('Camera debug:', JSON.stringify(cameraDebug, null, 2));
    const cameraDebugPath = resolve(process.cwd(), `logs/flight-viewer-camera-debug-${HOST_SLUG}.json`);
    writeFileSync(cameraDebugPath, JSON.stringify(cameraDebug, null, 2), 'utf-8');
    console.log(`Camera debug saved to ${cameraDebugPath}`);

    console.log('\n🧱 Step 6b: Capture tileset debug state');
    const tilesetDebug = await callTool('browser_evaluate', {
      function: `() => {
        const summary = (window && window.__spaceportTilesetDebug) || null;
        return summary ? { available: true, summary } : { available: false };
      }`
    });
    const tilesetDebugPath = resolve(process.cwd(), `logs/flight-viewer-tileset-debug-${HOST_SLUG}.json`);
    writeFileSync(tilesetDebugPath, JSON.stringify(tilesetDebug, null, 2), 'utf-8');
    console.log(`Tileset debug saved to ${tilesetDebugPath}`);

    // Take screenshot for visual inspection
    console.log('\n📸 Step 7: Capture screenshot');
    const screenshot = await callTool('browser_take_screenshot', {});
    const imageContent = screenshot.content?.find((item) => item.type === 'image');
    if (imageContent?.data) {
      const buffer = Buffer.from(imageContent.data, 'base64');
      const screenshotPath = resolve(process.cwd(), `logs/flight-viewer-${HOST_SLUG}.png`);
      writeFileSync(screenshotPath, buffer);
      console.log(`Screenshot saved to ${screenshotPath}`);
    } else {
      console.warn('Screenshot not available in response');
    }

    // Check for errors
    const logsText = JSON.stringify(logsAfter);
    const hasTerrainLog = logsText.includes('Google3DTerrain') || logsText.includes('Applying terrain offset');
    const hasError = /\berror\b/i.test(logsText);

    console.log('\n📊 Test Results:');
    console.log(`  Terrain logs found: ${hasTerrainLog ? '✅' : '❌'}`);
    console.log(`  Errors detected: ${hasError ? '❌' : '✅'}`);

    if (!hasTerrainLog) {
      console.log('\n⚠️  ISSUE: No terrain loading logs detected');
      console.log('Possible causes:');
      console.log('  1. API key not set in environment');
      console.log('  2. Component not rendering');
      console.log('  3. Center coordinates not calculated');
    }

  } catch (error) {
    console.error('\n❌ Test failed:', error);
    throw error;
  } finally {
    await client.close();
    console.log('\n✅ Test completed');
  }
}

testFlightViewerTerrain().catch(console.error);
