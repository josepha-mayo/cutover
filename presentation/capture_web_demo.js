/* Record only the Cutover browser page, never the user's desktop. */
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.CUTOVER_PLAYWRIGHT_MODULE || 'playwright');

const url = process.argv[2] || 'https://cutover-rehearsal.onrender.com/';
const output = path.resolve(process.argv[3] || 'work/cutover-browser-draft.webm');
const scene = process.argv[4] || 'late';
const minSeconds = Number(process.argv[5] || (scene === 'direct' ? 23 : 52));
if (!['direct', 'late'].includes(scene)) throw new Error('Scene must be direct or late');
if (!Number.isFinite(minSeconds) || minSeconds < 8 || minSeconds > 120) {
  throw new Error('Capture duration must be 8–120 seconds');
}

async function main() {
  if (fs.existsSync(output)) throw new Error(`Refusing to overwrite ${output}`);
  fs.mkdirSync(path.dirname(output), { recursive: true });
  const browser = await chromium.launch({ headless: true });
  try {
    const context = await browser.newContext({
      viewport: { width: 1280, height: 720 },
      recordVideo: { dir: path.dirname(output), size: { width: 1280, height: 720 } },
    });
    const page = await context.newPage();
    const started = Date.now();
    const video = page.video();
    try {
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 120000 });
      await page.locator('#run').waitFor({ state: 'visible', timeout: 120000 });
      await page.waitForFunction(() => !document.querySelector('#run').disabled, null, { timeout: 120000 });
      await page.locator('.plan-option.selected strong').waitFor({ state: 'visible' });
      if (scene === 'direct') await page.locator('[data-plan="rename"]').click();
      const selected = await page.locator('.plan-option.selected strong').innerText();
      const expected = scene === 'direct' ? 'Direct rename' : 'Late bridge';
      if (selected !== expected) throw new Error(`Unexpected plan: ${selected}`);
      await page.waitForTimeout(900);
      await page.locator('#run').scrollIntoViewIfNeeded();
      await page.waitForTimeout(800);
      await page.locator('#run').click();
      await page.locator('#verdict-title').filter({ hasText: 'The handover breaks.' })
        .waitFor({ timeout: 120000 });
      const count = (await page.locator('#probe-count').innerText()).replace(/\s+/g, ' ').trim();
      const expectedCount = scene === 'direct' ? '24 / 92' : '108 / 124';
      if (count !== expectedCount) throw new Error(`Unexpected live rehearsal: ${count}`);
      await page.locator('#verdict-title').scrollIntoViewIfNeeded();
      await page.waitForTimeout(scene === 'direct' ? 7000 : 3500);
      await page.locator('#trace-title').scrollIntoViewIfNeeded();
      await page.waitForTimeout(scene === 'late' ? 12000 : 3500);
      if (scene === 'late') {
        await page.locator('.comparison').first().scrollIntoViewIfNeeded();
        await page.waitForTimeout(2200);
      }
      await page.waitForTimeout(Math.max(0, minSeconds * 1000 - (Date.now() - started)));
      await context.close();
      await video.saveAs(output);
      console.log(JSON.stringify({ output, selected, count }));
    } finally {
      if (!page.isClosed()) await context.close();
    }
  } finally {
    await browser.close();
  }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
