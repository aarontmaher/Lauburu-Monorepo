/**
 * ============================================================================
 * Cloudflare Workers Durable Object: AST Undo & State Cache Proxy
 * ============================================================================
 * Subsystem: 00_core_infrastructure/cloudflare_worker/src/ast-undo-cache.ts
 * Purpose: Caches voice coding AST snapshots at the edge for sub-80ms rewind
 *          over mobile cellular WAN without burdening the host Mac Mini.
 * ============================================================================
 */

export interface AstSnapshot {
  timestamp: number;
  directive: string;
  scopeName: string;
  codeDelta: string;
  astHash: string;
}

export class AstUndoCacheDurableObject {
  private state: any;
  private historyStack: AstSnapshot[] = [];
  private redoStack: AstSnapshot[] = [];

  constructor(state: any) {
    this.state = state;
    this.state.blockConcurrencyWhile(async () => {
      const storedHistory = await this.state.storage.get("historyStack");
      if (storedHistory) {
        this.historyStack = storedHistory;
      }
    });
  }

  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);
    const method = request.method;

    // 1. Push Snapshot
    if (method === "POST" && url.pathname.endsWith("/push")) {
      const snapshot: AstSnapshot = await request.json();
      this.historyStack.push(snapshot);
      this.redoStack = [];
      await this.state.storage.put("historyStack", this.historyStack);
      return Response.json({ status: "SUCCESS", depth: this.historyStack.length, latest: snapshot });
    }

    // 2. Undo Snapshot
    if (method === "POST" && url.pathname.endsWith("/undo")) {
      if (this.historyStack.length > 1) {
        const popped = this.historyStack.pop()!;
        this.redoStack.push(popped);
        await this.state.storage.put("historyStack", this.historyStack);
        const current = this.historyStack[this.historyStack.length - 1];
        return Response.json({ status: "SUCCESS", action: "UNDONE", current, remainingDepth: this.historyStack.length });
      }
      return Response.json({ status: "NOOP", message: "History stack at root snapshot", remainingDepth: this.historyStack.length });
    }

    // 3. Query Active Stack
    if (method === "GET") {
      return Response.json({
        status: "ACTIVE",
        historyDepth: this.historyStack.length,
        redoDepth: this.redoStack.length,
        latest: this.historyStack[this.historyStack.length - 1] || null
      });
    }

    return new Response("Not Found", { status: 404 });
  }
}
