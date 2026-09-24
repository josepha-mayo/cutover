/* Record only the Cutover browser page, never the user's desktop. */
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.CUTOVER_PLAYWRIGHT_MODULE || 'playwright');

const url = process.argv[2] || 'https://cutover-rehearsal.onrender.com/';
const output = path.resolve(process.argv[3] || 'work/cutover-browser-draft.webm');
const scene = process.argv[4] || 'late';
const minSeconds = Number(process.argv[5] || ({ direct: 23, late: 52, trap: 30, warehouse: 28 }[scene]));
if (!['direct', 'late', 'trap', 'warehouse'].includes(scene)) throw new Error('Scene must be direct, late, trap, or warehouse');
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
      if (scene === 'warehouse') {
        await page.locator('#try-warehouse').click();
        await page.locator('#contract-status').filter({ hasText: 'Prewritten example · Validated' })
          .waitFor({ timeout: 120000 });
        await page.waitForFunction(() => !document.querySelector('#run').disabled);
      }
      const selected = scene === 'trap' ? 'Cross-record trap'
        : scene === 'warehouse' ? await page.locator('#case option:checked').innerText()
        : await page.locator('.plan-option.selected strong').innerText();
      const expected = { direct: 'Direct rename', late: 'Late bridge', trap: 'Cross-record trap',
        warehouse: 'Warehouse / bin relocation · example' }[scene];
      if (selected !== expected) throw new Error(`Unexpected plan: ${selected}`);
      await page.waitForTimeout(3600);
      const trigger = page.locator(scene === 'trap' ? '#try-cross-record' : '#run');
      await trigger.scrollIntoViewIfNeeded();
      await page.waitForTimeout(800);
      await trigger.click();
      await page.locator('#verdict-title').filter({ hasText: 'The handover breaks.' })
        .waitFor({ timeout: 120000 });
      const count = (await page.locator('#probe-count').innerText()).replace(/\s+/g, ' ').trim();
      const expectedCount = { direct: '24 / 92', late: '108 / 124', trap: '100 / 132',
        warehouse: '108 / 124' }[scene];
      if (count !== expectedCount) throw new Error(`Unexpected live rehearsal: ${count}`);
      if (scene === 'trap' && !(await page.locator('#source-label').innerText()).includes('negative control')) {
        throw new Error('Cross-record result lacks its prewritten negative-control label');
      }
      if (scene === 'warehouse' && !(await page.locator('#source-label').innerText()).includes('prewritten warehouse example')) {
        throw new Error('Warehouse result lacks its prewritten-example label');
      }
      await page.locator('#verdict-title').scrollIntoViewIfNeeded();
      await page.waitForTimeout(scene === 'direct' ? 7000 : scene === 'trap' ? 4000 : 3500);
      await page.locator('#trace-title').scrollIntoViewIfNeeded();
      if (scene === 'trap') {
        await page.waitForTimeout(5500);
        await page.locator('.trace-step.fail .comparison').evaluate(node => node.scrollIntoView({block: 'center'}));
        await page.waitForTimeout(8000);
      } else {
        await page.waitForTimeout(scene === 'late' ? 12000 : 3500);
      }
      if (scene === 'late') {
        await page.locator('.comparison').first().scrollIntoViewIfNeeded();
        await page.waitForTimeout(2200);
      }
      if (scene === 'warehouse') {
        await page.locator('#export-review').scrollIntoViewIfNeeded();
        if (await page.locator('#export-review').isDisabled()) throw new Error('Warehouse review export unavailable');
        await page.waitForTimeout(2800);
        const [review] = await Promise.all([
          page.waitForEvent('download'), page.locator('#export-review').click(),
        ]);
        if (!review.suggestedFilename().endsWith('.md') ||
            !fs.readFileSync(await review.path(), 'utf8').includes('108/124 rollout and window probes passed')) {
          throw new Error('Downloaded Warehouse review lacks the executed 108/124 result');
        }
        await page.locator('.comparison').first().scrollIntoViewIfNeeded();
        await page.waitForTimeout(5000);
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
