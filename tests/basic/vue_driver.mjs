// CALENDAR-001 vue-track UI driver for tests/basic/verify_basic.py.
// One phase per invocation; results as JSON on stdout (last line).
//   node vue_driver.mjs --phase main      (app on injected 2028-02-29)
//   node vue_driver.mjs --phase midnight  (app on injected 2026-12-31 23:59)
import { chromium } from '../node_modules/playwright/index.mjs';

const FRONT = 'http://localhost:17820';
const args = process.argv.slice(2);
const phase = args[args.indexOf('--phase') + 1];

const results = [];
const check = (name, ok, detail = '') => {
  results.push({ name, ok: !!ok, detail: String(detail).slice(0, 300) });
  console.error((ok ? 'PASS ' : 'FAIL ') + name + (detail ? ' :: ' + detail : ''));
};

const browser = await chromium.launch();
const page = await browser.newPage();
await page.goto(FRONT, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(3000);

async function create(title, start, end, notes = '') {
  await page.getByText('＋ 新建', { exact: true }).click();
  await page.waitForTimeout(400);
  await page.getByPlaceholder('事件标题').fill(title);
  await page.getByPlaceholder('2026-01-01 09:00').fill(start);
  await page.getByPlaceholder('2026-01-01 10:00').fill(end);
  await page.getByPlaceholder('备注（可选）').fill(notes);
  await page.getByRole('button', { name: '保存', exact: true }).click();
  await page.waitForTimeout(1500);
}

async function attemptSave(title, start, end) {
  await page.getByText('＋ 新建', { exact: true }).click();
  await page.waitForTimeout(400);
  await page.getByPlaceholder('事件标题').fill(title);
  await page.getByPlaceholder('2026-01-01 09:00').fill(start);
  await page.getByPlaceholder('2026-01-01 10:00').fill(end);
  await page.getByRole('button', { name: '保存', exact: true }).click();
  await page.waitForTimeout(1500);
  const b = await page.locator('body').innerText();
  const vals = (
    await page.getByPlaceholder('事件标题').inputValue(),
    await page.getByPlaceholder('2026-01-01 09:00').inputValue(),
    await page.getByPlaceholder('2026-01-01 10:00').inputValue()
  );
  const kept = {
    title: await page.getByPlaceholder('事件标题').inputValue(),
    start: await page.getByPlaceholder('2026-01-01 09:00').inputValue(),
    end: await page.getByPlaceholder('2026-01-01 10:00').inputValue(),
  };
  await page.getByRole('button', { name: '取消', exact: true }).click();
  await page.waitForTimeout(400);
  return { b, kept };
}

if (phase === 'main') {
  const body = await page.locator('body').innerText();
  check('v01-clock-banner-absent', !body.includes('无法获取当前日期'));
  check('v01-leap-today', body.includes('Selected: 2028-02-29'), 'today from injected clock');
  check('v01-leap-month', body.includes('February') && body.includes('2028'));

  await create('V02上午', '2028-02-29 09:00', '2028-02-29 10:00');
  await create('V02下午', '2028-02-29 13:00', '2028-02-29 14:00');
  await create('V02跨月', '2028-03-30 09:00', '2028-04-01 10:00');
  let body2 = await page.locator('body').innerText();
  check('v02-same-day-list', body2.includes('V02上午') && body2.includes('V02下午'));
  check('v02-crossmonth-absent-today', !body2.includes('V02跨月'));

  const r1 = await attemptSave('V03无效', '2029-02-29 10:00', '2029-02-29 11:00');
  check('v03-invalid-date-rejected', r1.b.includes('保存失败') && r1.b.includes('invalid_start'));
  check('v03-invalid-input-retained',
    r1.kept.title === 'V03无效' && r1.kept.start === '2029-02-29 10:00' && r1.kept.end === '2029-02-29 11:00',
    JSON.stringify(r1.kept));
  const r2 = await attemptSave('V03倒置', '2028-02-28 16:00', '2028-02-28 15:00');
  check('v03-inverted-rejected', r2.b.includes('保存失败') && r2.b.includes('inverted_range'));
  check('v03-inverted-input-retained',
    r2.kept.title === 'V03倒置' && r2.kept.start === '2028-02-28 16:00' && r2.kept.end === '2028-02-28 15:00',
    JSON.stringify(r2.kept));
} else if (phase === 'midnight') {
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(3000);
  let body = await page.locator('body').innerText();
  check('v01-crossmidnight-view', body.includes('December') && body.includes('2026'), 'clock at 12-31');
  await page.getByRole('button', { name: 'Today', exact: true }).click();
  await page.waitForTimeout(1500);
  body = await page.locator('body').innerText();
  check('v01-crossmidnight-today', body.includes('Selected: 2026-12-31'));
} else {
  console.error('unknown phase ' + phase);
  process.exit(2);
}

await browser.close();
console.log('RESULTS ' + JSON.stringify(results));
process.exit(results.some(r => !r.ok) ? 1 : 0);
