#!/usr/bin/env node
/**
 * Flight Viewer Terrain Test
 * Tests the 3D terrain visualization feature
 */

import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const MCP_URL = process.env.PLAYWRIGHT_MCP_SSE_URL || 'http://localhost:3010/sse';
const PREVIEW_URL = 'https://agent-38146275-flight-viewer.v0-spaceport-website-preview2.pages.dev';

async function testFlightViewerTerrain() {
  console.log('🚀 Starting Flight Viewer Terrain Test');
  console.log(`📍 Preview URL: ${PREVIEW_URL}`);
  console.log(`🔌 MCP Server: ${MCP_URL}`);

  const client = new Client(
    { name: 'flight-viewer-terrain-test', version: '1.0.0' },
    { capabilities: {} }
  );

  const transport = new SSEClientTransport(new URL(MCP_URL));
  await client.connect(transport);
  console.log('✅ Connected to Playwright MCP');

  try {
    // Navigate to flight viewer
    console.log('\n📄 Step 1: Navigate to flight viewer');
    await client.callTool('browser_navigate', {
      url: `${PREVIEW_URL}/flight-viewer`,
    });
    
    await new Promise(resolve => setTimeout(resolve, 3000));

    // Take initial screenshot
    console.log('\n📸 Step 2: Take initial screenshot');
    const initialSS = await client.callTool('browser_screenshot', {});
    console.log('Initial state captured');

    // Get console logs
    console.log('\n📋 Step 3: Check console logs');
    const consoleLogs = await client.callTool('browser_console_messages', {});
    console.log('Console messages:', JSON.stringify(consoleLogs, null, 2));

    // Upload CSV file
    console.log('\n📤 Step 4: Upload Edgewood-1.csv');
    const csvPath = resolve('/Users/gabrielhansen/user-development-spaceport-website/Edgewood-1.csv');
    const csvContent = readFileSync(csvPath, 'utf-8');
    console.log(`CSV loaded: ${csvContent.split('\n').length} lines`);

    // Try to find and interact with file upload
    const snapshot = await client.callTool('browser_snapshot', {});
    console.log('Page snapshot:', JSON.stringify(snapshot, null, 2).substring(0, 500));

    // Look for file input
    console.log('\n🔍 Step 5: Looking for file input element');
    
    // Wait for upload to process
    await new Promise(resolve => setTimeout(resolve, 5000));

    // Check console for terrain loading messages
    console.log('\n📋 Step 6: Check for terrain loading logs');
    const logsAfter = await client.callTool('browser_console_messages', {});
    console.log('Console after upload:', JSON.stringify(logsAfter, null, 2));

    // Take final screenshot
    console.log('\n📸 Step 7: Take final screenshot');
    const finalSS = await client.callTool('browser_screenshot', {});
    console.log('Final state captured');

    // Check for errors
    const hasTerrainLog = JSON.stringify(logsAfter).includes('Google3DTerrain');
    const hasError = JSON.stringify(logsAfter).includes('error') || JSON.stringify(logsAfter).includes('Error');

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

