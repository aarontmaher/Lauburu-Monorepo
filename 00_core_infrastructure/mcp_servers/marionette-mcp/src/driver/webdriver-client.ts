/**
 * W3C WebDriver HTTP Client implementation for GeckoDriver / Marionette.
 */

export interface WebDriverResponse<T = any> {
  value: T;
}

export class WebDriverClient {
  private baseUrl: string;

  constructor(baseUrl: string = 'http://127.0.0.1:4444') {
    this.baseUrl = baseUrl.replace(/\/$/, '');
  }

  public setBaseUrl(url: string): void {
    this.baseUrl = url.replace(/\/$/, '');
  }

  private async request<T = any>(
    method: string,
    endpoint: string,
    body?: any,
    timeoutMs: number = 30000
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });

      const data = (await response.json()) as any;

      if (!response.ok) {
        const errorMsg =
          data?.value?.message || data?.value?.error || response.statusText || 'WebDriver Request Failed';
        throw new Error(`WebDriver Error (${response.status}): ${errorMsg}`);
      }

      return data.value !== undefined ? data.value : data;
    } finally {
      clearTimeout(timeout);
    }
  }

  public async getStatus(): Promise<any> {
    return this.request('GET', '/status');
  }

  public async createSession(capabilities: Record<string, any> = {}): Promise<{ sessionId: string; capabilities: any }> {
    const payload = {
      capabilities: {
        alwaysMatch: {
          'moz:firefoxOptions': {
            args: ['-headless'],
            ...capabilities['moz:firefoxOptions'],
          },
          ...capabilities,
        },
      },
    };

    const res = await this.request<any>('POST', '/session', payload);
    return {
      sessionId: res.sessionId,
      capabilities: res.capabilities,
    };
  }

  public async deleteSession(sessionId: string): Promise<void> {
    await this.request('DELETE', `/session/${sessionId}`);
  }

  public async navigateTo(sessionId: string, url: string): Promise<void> {
    await this.request('POST', `/session/${sessionId}/url`, { url });
  }

  public async getCurrentUrl(sessionId: string): Promise<string> {
    return this.request<string>('GET', `/session/${sessionId}/url`);
  }

  public async getTitle(sessionId: string): Promise<string> {
    return this.request<string>('GET', `/session/${sessionId}/title`);
  }

  public async back(sessionId: string): Promise<void> {
    await this.request('POST', `/session/${sessionId}/back`);
  }

  public async forward(sessionId: string): Promise<void> {
    await this.request('POST', `/session/${sessionId}/forward`);
  }

  public async refresh(sessionId: string): Promise<void> {
    await this.request('POST', `/session/${sessionId}/refresh`);
  }

  public async takeScreenshot(sessionId: string): Promise<string> {
    // Returns base64 PNG string
    return this.request<string>('GET', `/session/${sessionId}/screenshot`);
  }

  public async takeElementScreenshot(sessionId: string, elementId: string): Promise<string> {
    return this.request<string>('GET', `/session/${sessionId}/element/${elementId}/screenshot`);
  }

  public async findElement(sessionId: string, using: string, value: string): Promise<string> {
    const res = await this.request<{ 'element-6066-11e4-a52e-4f735466cecf': string }>('POST', `/session/${sessionId}/element`, {
      using,
      value,
    });
    return res['element-6066-11e4-a52e-4f735466cecf'] || (res as any).ELEMENT;
  }

  public async findElements(sessionId: string, using: string, value: string): Promise<string[]> {
    const res = await this.request<Array<{ 'element-6066-11e4-a52e-4f735466cecf': string }>>(
      'POST',
      `/session/${sessionId}/elements`,
      { using, value }
    );
    return res.map((r) => r['element-6066-11e4-a52e-4f735466cecf'] || (r as any).ELEMENT);
  }

  public async elementClick(sessionId: string, elementId: string): Promise<void> {
    await this.request('POST', `/session/${sessionId}/element/${elementId}/click`);
  }

  public async elementSendKeys(sessionId: string, elementId: string, text: string): Promise<void> {
    await this.request('POST', `/session/${sessionId}/element/${elementId}/value`, {
      text,
      value: Array.from(text),
    });
  }

  public async elementClear(sessionId: string, elementId: string): Promise<void> {
    await this.request('POST', `/session/${sessionId}/element/${elementId}/clear`);
  }

  public async executeScript<T = any>(sessionId: string, script: string, args: any[] = []): Promise<T> {
    return this.request<T>('POST', `/session/${sessionId}/execute/sync`, {
      script,
      args,
    });
  }

  public async executeAsyncScript<T = any>(sessionId: string, script: string, args: any[] = []): Promise<T> {
    return this.request<T>('POST', `/session/${sessionId}/execute/async`, {
      script,
      args,
    });
  }

  public async getWindowHandle(sessionId: string): Promise<string> {
    return this.request<string>('GET', `/session/${sessionId}/window`);
  }

  public async getWindowHandles(sessionId: string): Promise<string[]> {
    return this.request<string[]>('GET', `/session/${sessionId}/window/handles`);
  }

  public async switchToWindow(sessionId: string, handle: string): Promise<void> {
    await this.request('POST', `/session/${sessionId}/window`, { handle });
  }

  public async newWindow(sessionId: string, type: 'tab' | 'window' = 'tab'): Promise<{ handle: string; type: string }> {
    return this.request<{ handle: string; type: string }>('POST', `/session/${sessionId}/window/new`, { type });
  }

  public async closeWindow(sessionId: string): Promise<string[]> {
    return this.request<string[]>('DELETE', `/session/${sessionId}/window`);
  }

  public async setWindowRect(sessionId: string, width: number, height: number): Promise<any> {
    return this.request('POST', `/session/${sessionId}/window/rect`, { width, height });
  }

  public async getWindowRect(sessionId: string): Promise<{ x: number; y: number; width: number; height: number }> {
    return this.request('GET', `/session/${sessionId}/window/rect`);
  }

  public async performActions(sessionId: string, actions: any[]): Promise<void> {
    await this.request('POST', `/session/${sessionId}/actions`, { actions });
  }

  public async acceptAlert(sessionId: string): Promise<void> {
    await this.request('POST', `/session/${sessionId}/alert/accept`);
  }

  public async dismissAlert(sessionId: string): Promise<void> {
    await this.request('POST', `/session/${sessionId}/alert/dismiss`);
  }

  public async getAlertText(sessionId: string): Promise<string> {
    return this.request<string>('GET', `/session/${sessionId}/alert/text`);
  }

  public async sendAlertText(sessionId: string, text: string): Promise<void> {
    await this.request('POST', `/session/${sessionId}/alert/text`, { text });
  }
}
