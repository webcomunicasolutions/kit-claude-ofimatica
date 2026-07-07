#!/usr/bin/env node
// render_page.js - Render JavaScript-heavy pages using Playwright headless Chromium.
// Outputs the fully rendered HTML to stdout. All messages/errors go to stderr.

const DEFAULTS = { timeout: 30000, waitUntil: 'networkidle', viewport: { width: 1280, height: 720 } };
const BLOCKED_TYPES = new Set(['image', 'font', 'media', 'stylesheet']);

function parseArgs(argv) {
  const args = { url: null, waitFor: null, timeout: DEFAULTS.timeout, waitUntil: DEFAULTS.waitUntil, scroll: false };
  const raw = argv.slice(2);
  for (let i = 0; i < raw.length; i++) {
    switch (raw[i]) {
      case '--wait-for':   args.waitFor = raw[++i]; break;
      case '--timeout':    args.timeout = parseInt(raw[++i], 10); break;
      case '--wait-until': args.waitUntil = raw[++i]; break;
      case '--scroll':     args.scroll = true; break;
      default:
        if (!raw[i].startsWith('--') && !args.url) args.url = raw[i];
    }
  }
  return args;
}

async function autoScroll(page) {
  await page.evaluate(async () => {
    const delay = (ms) => new Promise((r) => setTimeout(r, ms));
    const distance = 300;
    const maxTime = 10000;
    const start = Date.now();
    while (Date.now() - start < maxTime) {
      const prev = window.scrollY;
      window.scrollBy(0, distance);
      await delay(150);
      if (window.scrollY === prev) break;
    }
    window.scrollTo(0, 0);
  });
}

async function run() {
  const args = parseArgs(process.argv);
  if (!args.url) {
    process.stderr.write('Usage: node render_page.js <url> [--wait-for <sel>] [--timeout <ms>] [--wait-until <event>] [--scroll]\n');
    process.exit(1);
  }

  let chromium;
  try {
    ({ chromium } = require('playwright'));
  } catch {
    process.stderr.write('Error: Playwright is not installed.\nRun: npx playwright install chromium\n');
    process.exit(2);
  }

  let browser;
  try {
    browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({ viewport: DEFAULTS.viewport });
    const page = await context.newPage();

    // Block heavy resources to speed up loading
    await page.route('**/*', (route) => {
      BLOCKED_TYPES.has(route.request().resourceType()) ? route.abort() : route.continue();
    });

    process.stderr.write(`Navigating to ${args.url} (waitUntil: ${args.waitUntil}, timeout: ${args.timeout}ms)\n`);
    await page.goto(args.url, { waitUntil: args.waitUntil, timeout: args.timeout });

    if (args.waitFor) {
      process.stderr.write(`Waiting for selector: ${args.waitFor}\n`);
      await page.waitForSelector(args.waitFor, { timeout: args.timeout });
    }

    if (args.scroll) {
      process.stderr.write('Auto-scrolling to trigger lazy loading...\n');
      await autoScroll(page);
      // Brief pause after scrolling for content to settle
      await page.waitForTimeout(1000);
    }

    const html = await page.content();
    process.stdout.write(html);
  } catch (err) {
    if (err.name === 'TimeoutError' || err.message.includes('Timeout')) {
      process.stderr.write(`Timeout: Page did not finish loading within ${args.timeout}ms.\n`);
    } else if (err.message.includes('net::') || err.message.includes('Navigation')) {
      process.stderr.write(`Navigation error: ${err.message}\n`);
    } else {
      process.stderr.write(`Error: ${err.message}\n`);
    }
    process.exit(1);
  } finally {
    if (browser) await browser.close();
  }
}

run();
