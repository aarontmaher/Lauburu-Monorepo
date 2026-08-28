/**
 * Resolves UID identifiers to WebDriver element locators and cached element metadata.
 */

import { PageRegistry } from '../driver/page-registry.js';
import { WebDriverClient } from '../driver/webdriver-client.js';
import { ElementReference } from '../types.js';

export class ElementResolver {
  constructor(
    private registry: PageRegistry,
    private driver?: WebDriverClient
  ) {}

  public getElement(pageId: number, uid: string): ElementReference | undefined {
    return this.registry.getElement(pageId, uid);
  }

  public async resolveWebElementId(
    sessionId: string,
    pageId: number,
    uid: string
  ): Promise<string> {
    if (!this.driver) {
      throw new Error('WebDriverClient not initialized');
    }

    const cached = this.registry.getElement(pageId, uid);
    if (cached && cached.webElementId) {
      return cached.webElementId;
    }

    // Try finding by data-marionette-uid attribute
    try {
      const elementId = await this.driver.findElement(
        sessionId,
        'css selector',
        `[data-marionette-uid="${uid}"]`
      );
      if (cached) {
        cached.webElementId = elementId;
      }
      return elementId;
    } catch {
      // Fallback: try selector if available
      if (cached && cached.selector) {
        const elementId = await this.driver.findElement(
          sessionId,
          'css selector',
          cached.selector
        );
        cached.webElementId = elementId;
        return elementId;
      }
      throw new Error(`Element with UID '${uid}' not found on page ${pageId}`);
    }
  }
}
