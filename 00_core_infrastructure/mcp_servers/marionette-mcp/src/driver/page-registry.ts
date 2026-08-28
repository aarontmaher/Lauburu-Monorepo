/**
 * PageRegistry manages multi-tab context, page IDs, console logs, network telemetry,
 * and element UID maps.
 */

import { PageInfo, ConsoleMessage, NetworkRequest, ElementReference } from '../types.js';

export class PageRegistry {
  private pages: Map<number, PageInfo> = new Map();
  private nextPageId: number = 1;
  private selectedPageId: number = 1;
  private consoleLogs: Map<number, ConsoleMessage[]> = new Map();
  private networkLogs: Map<number, NetworkRequest[]> = new Map();
  private elementMaps: Map<number, Map<string, ElementReference>> = new Map();
  private nextMsgId: number = 1;
  private nextReqId: number = 1;
  private tracingActive: Map<number, { startTime: number; filePath?: string; rawEvents: any[] }> = new Map();

  constructor() {
    // Initialize default page
    this.createPage({
      url: 'about:blank',
      title: 'New Tab',
    });
  }

  public createPage(options: {
    url?: string;
    title?: string;
    windowHandle?: string;
    isolatedContext?: string;
  }): PageInfo {
    const pageId = this.nextPageId++;
    const page: PageInfo = {
      pageId,
      url: options.url || 'about:blank',
      title: options.title || 'New Tab',
      windowHandle: options.windowHandle,
      isolatedContext: options.isolatedContext,
      selected: this.pages.size === 0,
      createdAt: Date.now(),
      viewport: { width: 1280, height: 720, devicePixelRatio: 1 },
      colorScheme: 'auto',
    };

    this.pages.set(pageId, page);
    this.consoleLogs.set(pageId, []);
    this.networkLogs.set(pageId, []);
    this.elementMaps.set(pageId, new Map());

    if (this.pages.size === 1) {
      this.selectedPageId = pageId;
      page.selected = true;
    }

    return page;
  }

  public getPage(pageId: number): PageInfo | undefined {
    return this.pages.get(pageId);
  }

  public getSelectedPageId(): number {
    return this.selectedPageId;
  }

  public getSelectedPage(): PageInfo | undefined {
    return this.pages.get(this.selectedPageId);
  }

  public selectPage(pageId: number): boolean {
    if (!this.pages.has(pageId)) {
      return false;
    }

    for (const page of this.pages.values()) {
      page.selected = page.pageId === pageId;
    }

    this.selectedPageId = pageId;
    return true;
  }

  public listPages(): PageInfo[] {
    return Array.from(this.pages.values());
  }

  public updatePage(pageId: number, updates: Partial<PageInfo>): PageInfo | undefined {
    const page = this.pages.get(pageId);
    if (!page) return undefined;

    Object.assign(page, updates);
    return page;
  }

  public closePage(pageId: number): boolean {
    if (this.pages.size <= 1) {
      // The last open page cannot be closed according to specification
      return false;
    }

    if (!this.pages.has(pageId)) {
      return false;
    }

    this.pages.delete(pageId);
    this.consoleLogs.delete(pageId);
    this.networkLogs.delete(pageId);
    this.elementMaps.delete(pageId);
    this.tracingActive.delete(pageId);

    if (this.selectedPageId === pageId) {
      // Select the first available page
      const nextAvailable = this.pages.keys().next().value;
      if (nextAvailable !== undefined) {
        this.selectPage(nextAvailable);
      }
    }

    return true;
  }

  public addConsoleMessage(pageId: number, msg: Omit<ConsoleMessage, 'msgid' | 'pageId' | 'timestamp'>): ConsoleMessage {
    const logs = this.consoleLogs.get(pageId) || [];
    const fullMsg: ConsoleMessage = {
      msgid: this.nextMsgId++,
      pageId,
      timestamp: Date.now(),
      ...msg,
    };
    logs.push(fullMsg);
    this.consoleLogs.set(pageId, logs);
    return fullMsg;
  }

  public getConsoleMessages(pageId: number): ConsoleMessage[] {
    return this.consoleLogs.get(pageId) || [];
  }

  public getConsoleMessage(pageId: number, msgid: number): ConsoleMessage | undefined {
    const logs = this.consoleLogs.get(pageId) || [];
    return logs.find((m) => m.msgid === msgid);
  }

  public addNetworkRequest(pageId: number, req: Omit<NetworkRequest, 'reqid' | 'pageId' | 'timestamp'>): NetworkRequest {
    const requests = this.networkLogs.get(pageId) || [];
    const fullReq: NetworkRequest = {
      reqid: this.nextReqId++,
      pageId,
      timestamp: Date.now(),
      ...req,
    };
    requests.push(fullReq);
    this.networkLogs.set(pageId, requests);
    return fullReq;
  }

  public getNetworkRequests(pageId: number): NetworkRequest[] {
    return this.networkLogs.get(pageId) || [];
  }

  public getNetworkRequest(pageId: number, reqid?: number): NetworkRequest | undefined {
    const requests = this.networkLogs.get(pageId) || [];
    if (reqid !== undefined) {
      return requests.find((r) => r.reqid === reqid);
    }
    return requests[requests.length - 1];
  }

  public setElements(pageId: number, elements: ElementReference[]): void {
    const map = new Map<string, ElementReference>();
    for (const el of elements) {
      map.set(el.uid, el);
    }
    this.elementMaps.set(pageId, map);
  }

  public getElement(pageId: number, uid: string): ElementReference | undefined {
    return this.elementMaps.get(pageId)?.get(uid);
  }

  public startTrace(pageId: number, filePath?: string): void {
    this.tracingActive.set(pageId, {
      startTime: Date.now(),
      filePath,
      rawEvents: [
        { name: 'TracingStartedInBrowser', cat: 'disabled-by-default-devtools.timeline', ph: 'I', ts: Date.now() * 1000 },
        { name: 'NavigationStart', cat: 'navigation', ph: 'R', ts: Date.now() * 1000 },
      ],
    });
  }

  public stopTrace(pageId: number): { durationMs: number; filePath?: string; rawEvents: any[] } | undefined {
    const trace = this.tracingActive.get(pageId);
    if (!trace) return undefined;

    this.tracingActive.delete(pageId);
    trace.rawEvents.push({
      name: 'TracingComplete',
      cat: 'disabled-by-default-devtools.timeline',
      ph: 'I',
      ts: Date.now() * 1000,
    });

    return {
      durationMs: Date.now() - trace.startTime,
      filePath: trace.filePath,
      rawEvents: trace.rawEvents,
    };
  }

  public isTracing(pageId: number): boolean {
    return this.tracingActive.has(pageId);
  }
}
