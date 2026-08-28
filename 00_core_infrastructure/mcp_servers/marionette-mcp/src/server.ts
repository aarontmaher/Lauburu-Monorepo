/**
 * Marionette MCP Server instance and request router.
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ErrorCode,
  McpError,
} from '@modelcontextprotocol/sdk/types.js';
import { SessionManager } from './driver/session-manager.js';
import { NavigationTools } from './tools/navigation.js';
import { VisualTools } from './tools/visual.js';
import { InteractionTools } from './tools/interaction.js';
import { ExecutionTools } from './tools/execution.js';
import { TelemetryTools } from './tools/telemetry.js';
import { AuditTools } from './tools/audit.js';
import { TOOL_DEFINITIONS } from './tools/tool-definitions.js';

export class MarionetteMcpServer {
  private server: Server;
  private sessionManager: SessionManager;
  private navigation: NavigationTools;
  private visual: VisualTools;
  private interaction: InteractionTools;
  private execution: ExecutionTools;
  private telemetry: TelemetryTools;
  private audit: AuditTools;

  constructor() {
    this.server = new Server(
      {
        name: 'marionette-mcp',
        version: '1.0.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.sessionManager = new SessionManager();
    this.navigation = new NavigationTools(this.sessionManager);
    this.visual = new VisualTools(this.sessionManager);
    this.interaction = new InteractionTools(this.sessionManager);
    this.execution = new ExecutionTools(this.sessionManager);
    this.telemetry = new TelemetryTools(this.sessionManager);
    this.audit = new AuditTools(this.sessionManager);

    this.setupHandlers();
  }

  public getServer(): Server {
    return this.server;
  }

  public getSessionManager(): SessionManager {
    return this.sessionManager;
  }

  private setupHandlers(): void {
    // 1. List tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: TOOL_DEFINITIONS,
      };
    });

    // 2. Call tool
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args = {} } = request.params;

      try {
        switch (name) {
          // Navigation
          case 'list_pages':
            return await this.navigation.listPages();
          case 'new_page':
            return await this.navigation.newPage(args as any);
          case 'close_page':
            return await this.navigation.closePage(args as any);
          case 'select_page':
            return await this.navigation.selectPage(args as any);
          case 'navigate_page':
            return await this.navigation.navigatePage(args as any);
          case 'resize_page':
            return await this.navigation.resizePage(args as any);
          case 'wait_for':
            return await this.navigation.waitFor(args as any);

          // Visual
          case 'take_screenshot':
            return await this.visual.takeScreenshot(args as any);
          case 'take_snapshot':
            return await this.visual.takeSnapshot(args as any);

          // Interaction
          case 'click':
            return await this.interaction.click(args as any);
          case 'hover':
            return await this.interaction.hover(args as any);
          case 'fill':
            return await this.interaction.fill(args as any);
          case 'fill_form':
            return await this.interaction.fillForm(args as any);
          case 'drag':
            return await this.interaction.drag(args as any);
          case 'press_key':
            return await this.interaction.pressKey(args as any);
          case 'type_text':
            return await this.interaction.typeText(args as any);
          case 'upload_file':
            return await this.interaction.uploadFile(args as any);
          case 'handle_dialog':
            return await this.interaction.handleDialog(args as any);

          // Execution
          case 'evaluate_script':
            return await this.execution.evaluateScript(args as any);

          // Telemetry
          case 'list_console_messages':
            return await this.telemetry.listConsoleMessages(args as any);
          case 'get_console_message':
            return await this.telemetry.getConsoleMessage(args as any);
          case 'list_network_requests':
            return await this.telemetry.listNetworkRequests(args as any);
          case 'get_network_request':
            return await this.telemetry.getNetworkRequest(args as any);
          case 'emulate':
            return await this.telemetry.emulate(args as any);

          // Audit & Performance
          case 'take_heapsnapshot':
            return await this.audit.takeHeapsnapshot(args as any);
          case 'performance_start_trace':
            return await this.audit.performanceStartTrace(args as any);
          case 'performance_stop_trace':
            return await this.audit.performanceStopTrace(args as any);
          case 'performance_analyze_insight':
            return await this.audit.performanceAnalyzeInsight(args as any);
          case 'lighthouse_audit':
            return await this.audit.lighthouseAudit(args as any);

          default:
            throw new McpError(ErrorCode.MethodNotFound, `Unknown tool: ${name}`);
        }
      } catch (err: any) {
        if (err instanceof McpError) {
          throw err;
        }
        return {
          content: [
            {
              type: 'text',
              text: `Error executing ${name}: ${err.message || String(err)}`,
            },
          ],
          isError: true,
        };
      }
    });
  }

  public async close(): Promise<void> {
    await this.sessionManager.close();
  }
}
