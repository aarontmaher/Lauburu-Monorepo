/**
 * Type definitions for Marionette MCP Server.
 * Aligned with chrome-devtools-mcp 29-tool schema specification.
 */

import { CallToolResult } from '@modelcontextprotocol/sdk/types.js';

export interface PageInfo {
  pageId: number;
  url: string;
  title: string;
  windowHandle?: string;
  selected?: boolean;
  isolatedContext?: string;
  createdAt: number;
  viewport?: {
    width: number;
    height: number;
    devicePixelRatio?: number;
  };
  userAgent?: string;
  colorScheme?: 'dark' | 'light' | 'auto';
  geolocation?: string;
  networkConditions?: string;
  cpuThrottlingRate?: number;
  extraHttpHeaders?: Record<string, string>;
}

export interface ConsoleMessage {
  msgid: number;
  pageId: number;
  type:
    | 'log'
    | 'debug'
    | 'info'
    | 'error'
    | 'warn'
    | 'dir'
    | 'dirxml'
    | 'table'
    | 'trace'
    | 'clear'
    | 'startGroup'
    | 'startGroupCollapsed'
    | 'endGroup'
    | 'assert'
    | 'profile'
    | 'profileEnd'
    | 'count'
    | 'timeEnd'
    | 'verbose'
    | 'issue';
  text: string;
  timestamp: number;
  stackTrace?: string;
  serviceWorkerId?: string;
}

export interface NetworkRequest {
  reqid: number;
  pageId: number;
  url: string;
  method: string;
  resourceType:
    | 'document'
    | 'stylesheet'
    | 'image'
    | 'media'
    | 'font'
    | 'script'
    | 'texttrack'
    | 'xhr'
    | 'fetch'
    | 'prefetch'
    | 'eventsource'
    | 'websocket'
    | 'manifest'
    | 'signedexchange'
    | 'ping'
    | 'cspviolationreport'
    | 'preflight'
    | 'fedcm'
    | 'other';
  status: number;
  statusText?: string;
  headers: Record<string, string>;
  requestBody?: string;
  responseBody?: string;
  timestamp: number;
  durationMs?: number;
}

export interface AXNode {
  uid?: string;
  role: string;
  name?: string;
  value?: string;
  description?: string;
  focused?: boolean;
  disabled?: boolean;
  checked?: boolean | 'mixed';
  selected?: boolean;
  level?: number;
  url?: string;
  children?: AXNode[];
}

export interface ElementReference {
  uid: string;
  tagName: string;
  selector: string;
  xpath?: string;
  webElementId?: string;
  text?: string;
  attributes: Record<string, string>;
  boundingBox?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
}

export type ToolResult = CallToolResult;

// Tool parameter interfaces

export interface ClickParams {
  pageId: number;
  uid: string;
  dblClick?: boolean;
  includeSnapshot?: boolean;
}

export interface ClosePageParams {
  pageId: number;
}

export interface DragParams {
  pageId: number;
  from_uid: string;
  to_uid: string;
  includeSnapshot?: boolean;
}

export interface EmulateParams {
  pageId: number;
  colorScheme?: 'dark' | 'light' | 'auto';
  cpuThrottlingRate?: number;
  extraHttpHeaders?: string;
  geolocation?: string;
  networkConditions?: 'Offline' | 'Slow 3G' | 'Fast 3G' | 'Slow 4G' | 'Fast 4G';
  userAgent?: string;
  viewport?: string;
}

export interface EvaluateScriptParams {
  pageId: number;
  function: string;
  args?: string[];
  dialogAction?: 'accept' | 'dismiss' | string;
  filePath?: string;
  waitForStableDom?: boolean;
}

export interface FillParams {
  pageId: number;
  uid: string;
  value: string;
  includeSnapshot?: boolean;
}

export interface FillFormParams {
  pageId: number;
  elements: Array<{
    uid: string;
    value: string;
  }>;
  includeSnapshot?: boolean;
}

export interface GetConsoleMessageParams {
  pageId: number;
  msgid: number;
}

export interface GetNetworkRequestParams {
  pageId: number;
  reqid?: number;
  requestFilePath?: string;
  responseFilePath?: string;
}

export interface HandleDialogParams {
  pageId: number;
  action: 'accept' | 'dismiss';
  promptText?: string;
}

export interface HoverParams {
  pageId: number;
  uid: string;
  includeSnapshot?: boolean;
}

export interface LighthouseAuditParams {
  pageId: number;
  device?: 'desktop' | 'mobile';
  mode?: 'navigation' | 'snapshot';
  outputDirPath?: string;
}

export interface ListConsoleMessagesParams {
  pageId: number;
  includePreservedMessages?: boolean;
  includeStackTraces?: boolean;
  pageIdx?: number;
  pageSize?: number;
  serviceWorkerId?: string;
  types?: string[];
}

export interface ListNetworkRequestsParams {
  pageId: number;
  includePreservedRequests?: boolean;
  pageIdx?: number;
  pageSize?: number;
  resourceTypes?: string[];
}

export interface ListPagesParams {}

export interface NavigatePageParams {
  pageId: number;
  url?: string;
  type?: 'url' | 'back' | 'forward' | 'reload';
  ignoreCache?: boolean;
  initScript?: string;
  timeout?: number;
  handleBeforeUnload?: 'accept' | 'dismiss';
}

export interface NewPageParams {
  url: string;
  background?: boolean;
  isolatedContext?: string;
  timeout?: number;
}

export interface PerformanceAnalyzeInsightParams {
  pageId: number;
  insightSetId: string;
  insightName: string;
}

export interface PerformanceStartTraceParams {
  pageId: number;
  autoStop?: boolean;
  filePath?: string;
  reload?: boolean;
}

export interface PerformanceStopTraceParams {
  pageId: number;
  filePath?: string;
}

export interface PressKeyParams {
  pageId: number;
  key: string;
  includeSnapshot?: boolean;
}

export interface ResizePageParams {
  pageId: number;
  width: number;
  height: number;
}

export interface SelectPageParams {
  pageId: number;
  bringToFront?: boolean;
}

export interface TakeHeapsnapshotParams {
  pageId: number;
  filePath: string;
}

export interface TakeScreenshotParams {
  pageId: number;
  filePath?: string;
  format?: 'png' | 'jpeg' | 'webp';
  fullPage?: boolean;
  quality?: number;
  uid?: string;
}

export interface TakeSnapshotParams {
  pageId: number;
  filePath?: string;
  verbose?: boolean;
}

export interface TypeTextParams {
  pageId: number;
  text: string;
  submitKey?: string;
}

export interface UploadFileParams {
  pageId: number;
  uid: string;
  filePaths: string[];
  includeSnapshot?: boolean;
}

export interface WaitForParams {
  pageId: number;
  text: string[];
  timeout?: number;
}
