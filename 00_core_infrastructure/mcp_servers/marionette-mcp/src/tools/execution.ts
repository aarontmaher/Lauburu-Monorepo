/**
 * Execution tools: evaluate_script.
 */

import { SessionManager } from '../driver/session-manager.js';
import { EvaluateScriptParams, ToolResult } from '../types.js';

export class ExecutionTools {
  constructor(private manager: SessionManager) {}

  public async evaluateScript(params: EvaluateScriptParams): Promise<ToolResult> {
    return this.manager.evaluateScript(params);
  }
}
