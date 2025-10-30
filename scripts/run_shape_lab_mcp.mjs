#!/usr/bin/env node
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js';

const MCP_URL = process.env.PLAYWRIGHT_MCP_SSE_URL || 'http://localhost:5174/sse';
const PREVIEW_URL = process.env.SHAPE_LAB_URL || 'http://127.0.0.1:3000';

async function runShapeLabFlow() {
  console.log('🧪 Shape Lab MCP Smoke Test');
  console.log(`🔌 MCP: ${MCP_URL}`);
  console.log(`🌐 URL: ${PREVIEW_URL}/shape-lab`);

  const client = new Client({ name: 'shape-lab-smoke', version: '1.0.0' }, { capabilities: {} });
  const transport = new SSEClientTransport(new URL(MCP_URL));
  await client.connect(transport);
  console.log('✅ Connected to MCP server');
  const tools = await client.listTools();
  console.log('🧰 Tools available:', tools.tools?.map((t) => t.name).join(', '));

  try {
    await client.callTool({ name: 'browser_navigate', arguments: { url: `${PREVIEW_URL}/shape-lab` } });
    console.log('📄 Navigated to Shape Lab');

    await new Promise((resolve) => setTimeout(resolve, 2000));

    const snapshot = await client.callTool({ name: 'browser_snapshot', arguments: {} });
    console.log('🪟 Snapshot summary:', JSON.stringify(snapshot, null, 2).slice(0, 400));

    const screenshot = await client.callTool({ name: 'browser_screenshot', arguments: {} });
    console.log('📸 Screenshot captured (base64 length):', screenshot?.base64?.length ?? 0);

    const consoleMessages = await client.callTool({ name: 'browser_console_messages', arguments: {} });
    console.log('🪵 Console messages:', JSON.stringify(consoleMessages, null, 2).slice(0, 400));

  } finally {
    await client.close();
    console.log('🏁 Shape Lab MCP smoke test complete');
  }
}

runShapeLabFlow().catch((error) => {
  console.error('❌ Shape Lab MCP smoke test failed', error);
  process.exitCode = 1;
});
