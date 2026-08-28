/**
 * Telemetry tools: list_console_messages, get_console_message, list_network_requests, get_network_request, emulate.
 */

import { SessionManager } from '../driver/session-manager.js';
import {
  ListConsoleMessagesParams,
  GetConsoleMessageParams,
  ListNetworkRequestsParams,
  GetNetworkRequestParams,
  EmulateParams,
  ToolResult,
} from '../types.js';

export class TelemetryTools {
  constructor(private manager: SessionManager) {}

  public async listConsoleMessages(params: ListConsoleMessagesParams): Promise<ToolResult> {
    return this.manager.listConsoleMessages(params);
  }

  public async getConsoleMessage(params: GetConsoleMessageParams): Promise<ToolResult> {
    return this.manager.getConsoleMessage(params);
  }

  public async listNetworkRequests(params: ListNetworkRequestsParams): Promise<ToolResult> {
    return this.manager.listNetworkRequests(params);
  }

  public async getNetworkRequest(params: GetNetworkRequestParams): Promise<ToolResult> {
    return this.manager.getNetworkRequest(params);
  }

  public async emulate(params: EmulateParams): Promise<ToolResult> {
    return this.manager.emulate(params);
  }
}
