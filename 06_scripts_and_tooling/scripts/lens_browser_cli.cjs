#!/usr/bin/env node
/**
 * lens_browser_cli.js - Simple CLI for lens-browser automation.
 *
 * Connects to Chrome on port 9224 and provides browser automation commands.
 *
 * Usage:
 *   node lens_browser_cli.js navigate <url>
 *   node lens_browser_cli.js screenshot [filename]
 *   node lens_browser_cli.js title
 *   node lens_browser_cli.js eval <javascript>
 *   node lens_browser_cli.js pages
 *   node lens_browser_cli.js console
 *   node lens_browser_cli.js network
 *   node lens_browser_cli.js lighthouse
 */

const puppeteer = require('puppeteer-core');

const COMMANDS = {
  navigate: async (browser, args) => {
    const url = args[0];
    if (!url) {
      console.error('Usage: node lens_browser_cli.js navigate <url>');
      process.exit(1);
    }
    const pages = await browser.pages();
    let page = pages[0];
    if (!page) {
      page = await browser.newPage();
    }
    await page.goto(url, { waitUntil: 'networkidle2' });
    const title = await page.title();
    console.log(`Navigated to: ${url}`);
    console.log(`Page title: ${title}`);
  },

  screenshot: async (browser, args) => {
    const filename = args[0] || `screenshot_${Date.now()}.png`;
    const pages = await browser.pages();
    let page = pages[0];
    if (!page) {
      page = await browser.newPage();
    }
    await page.screenshot({ path: filename, fullPage: true });
    console.log(`Screenshot saved to: ${filename}`);
  },

  title: async (browser) => {
    const pages = await browser.pages();
    const page = pages[0];
    if (!page) {
      console.log('No open pages');
      return;
    }
    const title = await page.title();
    const url = page.url();
    console.log(`URL: ${url}`);
    console.log(`Title: ${title}`);
  },

  eval: async (browser, args) => {
    const js = args.join(' ');
    if (!js) {
      console.error('Usage: node lens_browser_cli.js eval <javascript>');
      process.exit(1);
    }
    const pages = await browser.pages();
    let page = pages[0];
    if (!page) {
      page = await browser.newPage();
    }
    const result = await page.evaluate((expr) => {
      try {
        return eval(expr);
      } catch (e) {
        return `Error: ${e.message}`;
      }
    }, js);
    console.log(JSON.stringify(result, null, 2));
  },

  pages: async (browser) => {
    const pages = await browser.pages();
    console.log(`Open pages: ${pages.length}`);
    for (let i = 0; i < pages.length; i++) {
      const url = pages[i].url();
      console.log(`  [${i}] ${url}`);
    }
  },

  console: async (browser) => {
    const pages = await browser.pages();
    const page = pages[0];
    if (!page) {
      console.log('No open pages');
      return;
    }
    const messages = [];
    page.on('console', (msg) => {
      messages.push(`[${msg.type()}] ${msg.text()}`);
    });
    console.log('Listening for console messages (Ctrl+C to stop)...');
    await new Promise((resolve) => setTimeout(resolve, 5000));
    if (messages.length === 0) {
      console.log('No console messages captured');
    } else {
      messages.forEach((msg) => console.log(msg));
    }
  },

  network: async (browser) => {
    const pages = await browser.pages();
    const page = pages[0];
    if (!page) {
      console.log('No open pages');
      return;
    }
    const requests = [];
    page.on('request', (req) => {
      requests.push({ url: req.url(), method: req.method(), resourceType: req.resourceType() });
    });
    console.log('Listening for network requests (5 seconds)...');
    await new Promise((resolve) => setTimeout(resolve, 5000));
    if (requests.length === 0) {
      console.log('No network requests captured');
    } else {
      requests.forEach((req, i) => {
        console.log(`  [${i}] ${req.method} ${req.resourceType}: ${req.url}`);
      });
    }
  },

  lighthouse: async (browser, args) => {
    const url = args[0];
    if (!url) {
      console.error('Usage: node lens_browser_cli.js lighthouse <url>');
      process.exit(1);
    }
    console.log('Lighthouse audit requires the lighthouse package. Install with: npm install lighthouse');
    console.log(`Would audit: ${url}`);
  }
};

async function main() {
  const [command, ...args] = process.argv.slice(2);

  if (!command) {
    console.log('Lens Browser CLI - Chrome automation tool');
    console.log('');
    console.log('Commands:');
    console.log('  navigate <url>        Navigate to a URL');
    console.log('  screenshot [file]     Take a screenshot');
    console.log('  title                 Show current page title');
    console.log('  eval <js>             Evaluate JavaScript');
    console.log('  pages                 List open pages');
    console.log('  console               Listen for console messages');
    console.log('  network               Listen for network requests');
    console.log('  lighthouse <url>      Run Lighthouse audit');
    process.exit(0);
  }

  if (!COMMANDS[command]) {
    console.error(`Unknown command: ${command}`);
    console.error(`Available commands: ${Object.keys(COMMANDS).join(', ')}`);
    process.exit(1);
  }

  let browser;
  const aiBrowserEndpoints = [
    process.env.LENS_AI_CDP_URL,
    'http://192.168.8.114:9222', // L1b Apple M2 Pro Dedicated AI Browser
    'http://100.121.247.8:9222', // L8 Podman Sovereign Chromium
  ].filter(Boolean);

  for (const ep of aiBrowserEndpoints) {
    try {
      browser = await puppeteer.connect({ browserURL: ep });
      break;
    } catch (_) {}
  }

  if (!browser) {
    console.error('Could not connect to Dedicated AI Browser Fleet (L1b M2 Pro :9222 or L8 Podman :9222).');
    console.error('NOTE: Personal Google Chrome.app on Human Sanctuary Macs (L5/L1) is strictly protected and NEVER used for CDP automation.');
    process.exit(1);
  }

  try {
    await COMMANDS[command](browser, args);
  } finally {
    // Don't disconnect - Chrome was launched externally
  }
}

main().catch((err) => {
  console.error('Error:', err.message);
  process.exit(1);
});
