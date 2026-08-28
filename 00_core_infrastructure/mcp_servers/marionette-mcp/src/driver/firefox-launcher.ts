/**
 * Firefox & GeckoDriver process supervisor and lifecycle manager.
 */

import { spawn, ChildProcess, execSync } from 'node:child_process';
import * as net from 'node:net';
import * as fs from 'node:fs';
import * as path from 'node:path';

export interface FirefoxLauncherOptions {
  geckodriverPath?: string;
  firefoxPath?: string;
  headless?: boolean;
  port?: number;
  marionettePort?: number;
}

export class FirefoxLauncher {
  private process: ChildProcess | null = null;
  private geckodriverPath: string | null = null;
  private firefoxPath: string | null = null;
  private port: number = 4444;
  private marionettePort: number = 2828;
  private headless: boolean = true;
  private isRunning: boolean = false;

  constructor(options: FirefoxLauncherOptions = {}) {
    this.headless = options.headless ?? true;
    this.port = options.port ?? (process.env.GECKODRIVER_PORT ? parseInt(process.env.GECKODRIVER_PORT, 10) : 4444);
    this.marionettePort = options.marionettePort ?? (process.env.MARIONETTE_PORT ? parseInt(process.env.MARIONETTE_PORT, 10) : 2828);

    this.geckodriverPath = options.geckodriverPath || process.env.GECKODRIVER_PATH || this.findGeckoDriver();
    this.firefoxPath = options.firefoxPath || process.env.FIREFOX_BINARY_PATH || this.findFirefox();
  }

  public findGeckoDriver(): string | null {
    const candidates = [
      '/usr/local/bin/geckodriver',
      '/opt/homebrew/bin/geckodriver',
      '/usr/bin/geckodriver',
      path.join(process.env.HOME || '', '.local/bin/geckodriver'),
      path.join(process.env.HOME || '', 'bin/geckodriver'),
    ];

    for (const candidate of candidates) {
      if (fs.existsSync(candidate)) {
        return candidate;
      }
    }

    try {
      const output = execSync('which geckodriver 2>/dev/null', { encoding: 'utf8' }).trim();
      if (output && fs.existsSync(output)) {
        return output;
      }
    } catch {
      // not found in PATH
    }

    return null;
  }

  public findFirefox(): string | null {
    const candidates = [
      '/Applications/Firefox.app/Contents/MacOS/firefox',
      path.join(process.env.HOME || '', 'Applications/Firefox.app/Contents/MacOS/firefox'),
      '/usr/bin/firefox',
      '/usr/lib/firefox/firefox',
      '/opt/firefox/firefox',
      '/Applications/Firefox Developer Edition.app/Contents/MacOS/firefox',
      '/Applications/Firefox Nightly.app/Contents/MacOS/firefox',
    ];

    for (const candidate of candidates) {
      if (fs.existsSync(candidate)) {
        return candidate;
      }
    }

    try {
      const output = execSync('which firefox 2>/dev/null', { encoding: 'utf8' }).trim();
      if (output && fs.existsSync(output)) {
        return output;
      }
    } catch {
      // not found in PATH
    }

    return null;
  }

  public hasGeckoDriver(): boolean {
    return this.geckodriverPath !== null && fs.existsSync(this.geckodriverPath);
  }

  public hasFirefox(): boolean {
    return this.firefoxPath !== null && fs.existsSync(this.firefoxPath);
  }

  public getPort(): number {
    return this.port;
  }

  public getWebDriverUrl(): string {
    return `http://127.0.0.1:${this.port}`;
  }

  public async start(): Promise<boolean> {
    if (this.isRunning) {
      return true;
    }

    // Check if an existing geckodriver is already listening on this port
    const alreadyRunning = await this.isPortOpen(this.port);
    if (alreadyRunning) {
      this.isRunning = true;
      return true;
    }

    if (!this.hasGeckoDriver()) {
      return false;
    }

    const args = [
      '--port',
      this.port.toString(),
      '--marionette-port',
      this.marionettePort.toString(),
      '--log',
      'warn',
    ];

    try {
      this.process = spawn(this.geckodriverPath!, args, {
        stdio: ['ignore', 'pipe', 'pipe'],
        detached: false,
      });

      this.process.on('error', (err) => {
        this.isRunning = false;
        this.process = null;
      });

      this.process.on('exit', () => {
        this.isRunning = false;
        this.process = null;
      });

      // Wait for geckodriver HTTP port to accept connections
      const ready = await this.waitForPort(this.port, 5000);
      this.isRunning = ready;
      return ready;
    } catch (err) {
      this.isRunning = false;
      return false;
    }
  }

  public async stop(): Promise<void> {
    if (this.process) {
      try {
        this.process.kill('SIGTERM');
      } catch {
        // ignore
      }
      this.process = null;
    }
    this.isRunning = false;
  }

  private isPortOpen(port: number): Promise<boolean> {
    return new Promise((resolve) => {
      const socket = new net.Socket();
      socket.setTimeout(500);

      socket.on('connect', () => {
        socket.destroy();
        resolve(true);
      });

      socket.on('timeout', () => {
        socket.destroy();
        resolve(false);
      });

      socket.on('error', () => {
        socket.destroy();
        resolve(false);
      });

      socket.connect(port, '127.0.0.1');
    });
  }

  private async waitForPort(port: number, timeoutMs: number): Promise<boolean> {
    const startTime = Date.now();
    while (Date.now() - startTime < timeoutMs) {
      if (await this.isPortOpen(port)) {
        return true;
      }
      await new Promise((r) => setTimeout(r, 100));
    }
    return false;
  }
}
