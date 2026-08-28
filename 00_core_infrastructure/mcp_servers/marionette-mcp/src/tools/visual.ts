/**
 * Visual & Screenshot tools: take_screenshot, take_snapshot.
 */

import { SessionManager } from '../driver/session-manager.js';
import { TakeScreenshotParams, TakeSnapshotParams, ToolResult } from '../types.js';

export class VisualTools {
  constructor(private manager: SessionManager) {}

  public async takeScreenshot(params: TakeScreenshotParams): Promise<ToolResult> {
    return this.manager.takeScreenshot(params);
  }

  public async takeSnapshot(params: TakeSnapshotParams): Promise<ToolResult> {
    return this.manager.takeSnapshot(params);
  }
}
