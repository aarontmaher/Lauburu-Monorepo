/**
 * Navigation tools: navigate_page, new_page, close_page, select_page, list_pages, resize_page, wait_for.
 */

import { SessionManager } from '../driver/session-manager.js';
import {
  NavigatePageParams,
  NewPageParams,
  ClosePageParams,
  SelectPageParams,
  ResizePageParams,
  WaitForParams,
  ToolResult,
} from '../types.js';

export class NavigationTools {
  constructor(private manager: SessionManager) {}

  public async listPages(): Promise<ToolResult> {
    return this.manager.listPages();
  }

  public async newPage(params: NewPageParams): Promise<ToolResult> {
    return this.manager.newPage(params);
  }

  public async closePage(params: ClosePageParams): Promise<ToolResult> {
    return this.manager.closePage(params);
  }

  public async selectPage(params: SelectPageParams): Promise<ToolResult> {
    return this.manager.selectPage(params);
  }

  public async navigatePage(params: NavigatePageParams): Promise<ToolResult> {
    return this.manager.navigatePage(params);
  }

  public async resizePage(params: ResizePageParams): Promise<ToolResult> {
    return this.manager.resizePage(params);
  }

  public async waitFor(params: WaitForParams): Promise<ToolResult> {
    return this.manager.waitFor(params);
  }
}
