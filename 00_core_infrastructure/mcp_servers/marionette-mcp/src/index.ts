#!/usr/bin/env node
/**
 * Main entrypoint for Marionette MCP Server over stdio.
 */

import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { MarionetteMcpServer } from './server.js';

async function main() {
  const serverInstance = new MarionetteMcpServer();
  const transport = new StdioServerTransport();

  const cleanup = async () => {
    try {
      await serverInstance.close();
    } catch {
      // ignore
    }
    process.exit(0);
  };

  process.on('SIGINT', cleanup);
  process.on('SIGTERM', cleanup);

  await serverInstance.getServer().connect(transport);
}

main().catch((error) => {
  console.error('Fatal error starting Marionette MCP server:', error);
  process.exit(1);
});
