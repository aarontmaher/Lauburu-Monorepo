/**
 * Interaction tools: click, hover, fill, fill_form, drag, press_key, type_text, upload_file, handle_dialog.
 */

import { SessionManager } from '../driver/session-manager.js';
import {
  ClickParams,
  HoverParams,
  FillParams,
  FillFormParams,
  DragParams,
  PressKeyParams,
  TypeTextParams,
  UploadFileParams,
  HandleDialogParams,
  ToolResult,
} from '../types.js';

export class InteractionTools {
  constructor(private manager: SessionManager) {}

  public async click(params: ClickParams): Promise<ToolResult> {
    return this.manager.click(params);
  }

  public async hover(params: HoverParams): Promise<ToolResult> {
    return this.manager.hover(params);
  }

  public async fill(params: FillParams): Promise<ToolResult> {
    return this.manager.fill(params);
  }

  public async fillForm(params: FillFormParams): Promise<ToolResult> {
    return this.manager.fillForm(params);
  }

  public async drag(params: DragParams): Promise<ToolResult> {
    return this.manager.drag(params);
  }

  public async pressKey(params: PressKeyParams): Promise<ToolResult> {
    return this.manager.pressKey(params);
  }

  public async typeText(params: TypeTextParams): Promise<ToolResult> {
    return this.manager.typeText(params);
  }

  public async uploadFile(params: UploadFileParams): Promise<ToolResult> {
    return this.manager.uploadFile(params);
  }

  public async handleDialog(params: HandleDialogParams): Promise<ToolResult> {
    return this.manager.handleDialog(params);
  }
}
