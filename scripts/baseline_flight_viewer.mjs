#!/usr/bin/env node
/**
 * Baseline Flight Viewer Test - Capture current state before fixes
 */

import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js';

const MCP_URL = process.env.PLAYWRIGHT_MCP_SSE_URL || 'http://localhost:3010/sse';
const TEST_URL = process.env.TEST_URL || 'http://localhost:3000/flight-viewer';

async function baselineFlightViewer() {
  console.log('📊 Baseline Flight Viewer Test');
  console.log(`📍 Test URL: ${TEST_URL}`);
  console.log(`🔌 MCP Server: ${MCP_URL}`);

  const client = new Client(
    { name: 'flight-viewer-baseline', version: '1.0.0' },
    { capabilities: {} }
  );

  const transport = new SSEClientTransport(new URL(MCP_URL));
  await client.connect(transport);
  console.log('✅ Connected to Playwright MCP');

  try {
    console.log('\n📄 Navigating to flight viewer...');
    await client.callTool('browser_navigate', { url: TEST_URL });
    await client.callTool('browser_wait_for', { time: 3 });

    console.log('\n📸 Taking baseline screenshot...');
    const screenshot = await client.callTool('browser_take_screenshot', {
      filename: 'logs/flight-viewer-baseline.png',
      fullPage: true
    });
    console.log(`Screenshot saved: ${screenshot.filename || 'logs/flight-viewer-baseline.png'}`);

    console.log('\n🔍 Capturing page snapshot...');
    const snapshot = await client.callTool('browser_snapshot', {});
    
    // Check for canvas elements
    const canvasInfo = JSON.stringify(snapshot, null, 2);
    console.log('\n📋 Page structure:');
    console.log(canvasInfo.substring(0, 2000));

    console.log('\n📋 Console messages:');
    const consoleLogs = await client.callTool('browser_console_messages', {});
    if (consoleLogs && consoleLogs.length > 0) {
      consoleLogs.forEach((msg, i) => {
        console.log(`  [${i}] ${msg.type}: ${msg.text}`);
      });
    }

    console.log('\n✅ Baseline capture complete');

  } catch (error) {
    console.error('❌ Baseline test failed:', error);
    throw error;
  } finally {
    await client.close();
  }
}

baselineFlightViewer().catch(console.error);

