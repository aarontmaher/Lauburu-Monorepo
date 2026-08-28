/**
 * Audit & Performance tools: take_heapsnapshot, performance_start_trace, performance_stop_trace, performance_analyze_insight, lighthouse_audit.
 */

import { SessionManager } from '../driver/session-manager.js';
import {
  TakeHeapsnapshotParams,
  PerformanceStartTraceParams,
  PerformanceStopTraceParams,
  PerformanceAnalyzeInsightParams,
  LighthouseAuditParams,
  ToolResult,
} from '../types.js';

export class AuditTools {
  constructor(private manager: SessionManager) {}

  public async takeHeapsnapshot(params: TakeHeapsnapshotParams): Promise<ToolResult> {
    return this.manager.takeHeapsnapshot(params);
  }

  public async performanceStartTrace(params: PerformanceStartTraceParams): Promise<ToolResult> {
    return this.manager.performanceStartTrace(params);
  }

  public async performanceStopTrace(params: PerformanceStopTraceParams): Promise<ToolResult> {
    return this.manager.performanceStopTrace(params);
  }

  public async performanceAnalyzeInsight(params: PerformanceAnalyzeInsightParams): Promise<ToolResult> {
    return this.manager.performanceAnalyzeInsight(params);
  }

  public async lighthouseAudit(params: LighthouseAuditParams): Promise<ToolResult> {
    return this.manager.lighthouseAudit(params);
  }
}
