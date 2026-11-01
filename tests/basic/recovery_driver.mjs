// CALENDAR-002 vue-track UI driver for tests/basic/verify_recovery_identity.py.
// One phase per invocation; results as JSON on stdout (last line).
//   node recovery_driver.mjs --phase seed      (app on injected 2028-02-29)
//   node recovery_driver.mjs --phase unproven  (identity+manifest damaged)
//   node recovery_driver.mjs --phase consent   (AUTO_CALENDAR_RECOVERY_CONSENT relaunch)
//   node recovery_driver.mjs --phase restart   (after strong-kill reopen, same data dir)
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

async function openForm() {
  await page.getByText('＋ 新建', { exact: true }).click();
  await page.waitForTimeout(400);
}

async function fillAndSave(title, start, end, notes = '') {
  await openForm();
  await page.getByPlaceholder('事件标题').fill(title);
  await page.getByPlaceholder('2026-01-01 09:00').fill(start);
  await page.getByPlaceholder('2026-01-01 10:00').fill(end);
  if (notes) {
    await page.getByPlaceholder('备注（可选）').fill(notes);
  }
  await page.getByRole('button', { name: '保存', exact: true }).click();
  await page.waitForTimeout(1500);
}

async function attemptSave(title, start, end) {
  await openForm();
  await page.getByPlaceholder('事件标题').fill(title);
  await page.getByPlaceholder('2026-01-01 09:00').fill(start);
  await page.getByPlaceholder('2026-01-01 10:00').fill(end);
  await page.getByRole('button', { name: '保存', exact: true }).click();
  await page.waitForTimeout(1500);
  const b = await page.locator('body').innerText();
  const kept = {
    title: await page.getByPlaceholder('事件标题').inputValue(),
    start: await page.getByPlaceholder('2026-01-01 09:00').inputValue(),
    end: await page.getByPlaceholder('2026-01-01 10:00').inputValue(),
  };
  await page.getByRole('button', { name: '取消', exact: true }).click();
  await page.waitForTimeout(400);
  return { b, kept };
}

if (phase === 'seed') {
  // C-04: 中文跨月事件 UI CRUD (create → edit → list), wall-clock fields
  // untouched (v2 storage must not alter 001 semantics)
  let body = await page.locator('body').innerText();
  check('r01-seed-today', body.includes('Selected: 2028-02-29'), 'injected clock');
  await fillAndSave('恢复跨月甲', '2028-02-28 22:00', '2028-03-02 08:00', '跨越二月');
  await fillAndSave('恢复当日乙', '2028-02-29 09:00', '2028-02-29 10:00');
  body = await page.locator('body').innerText();
  check('r01-seed-same-day-visible', body.includes('恢复当日乙'));
  // edit 当日乙 (ev-2): both seeded events cover 02-29 and render in
  // creation order, so the day list shows 跨月甲's row first — target nth(1)
  await page.getByRole('button', { name: '编辑', exact: true }).nth(1).click();
  await page.waitForTimeout(500);
  await page.getByPlaceholder('事件标题').fill('恢复当日乙改');
  await page.getByRole('button', { name: '保存修改', exact: true }).click();
  await page.waitForTimeout(1500);
  body = await page.locator('body').innerText();
  check('r01-seed-edit-saved', body.includes('恢复当日乙改') && !body.includes('保存失败'));
  // cross-month nav both directions
  await page.getByRole('button', { name: '<', exact: true }).click();
  await page.waitForTimeout(1200);
  body = await page.locator('body').innerText();
  check('r01-seed-prev-month', body.includes('January') && body.includes('2028'));
  await page.getByRole('button', { name: '>', exact: true }).click();
  await page.waitForTimeout(1200);
  await page.getByRole('button', { name: '>', exact: true }).click();
  await page.waitForTimeout(1200);
  body = await page.locator('body').innerText();
  check('r01-seed-next-month', body.includes('March') && body.includes('2028'));
  await page.getByRole('button', { name: 'Today', exact: true }).click();
  await page.waitForTimeout(1200);
} else if (phase === 'restart') {
  // C-04: strong-kill reopen — same ids/contents, next write succeeds
  let body = await page.locator('body').innerText();
  check('r04-reopen-events-visible', body.includes('恢复当日乙改') || body.includes('恢复跨月甲'), body.slice(0, 120));
  await fillAndSave('重开后首写', '2028-02-29 15:00', '2028-02-29 16:00');
  body = await page.locator('body').innerText();
  check('r04-reopen-next-write-ok', body.includes('重开后首写') && !body.includes('保存失败'));
} else if (phase === 'unproven') {
  // C-03 UI face: banner + preserved data + refused save with kept input
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(3000);
  let body = await page.locator('body').innerText();
  check('r03-unproven-banner', body.includes('存储身份未能证明') && body.includes('AUTO_CALENDAR_RECOVERY_CONSENT'),
    body.slice(0, 200));
  check('r03-unproven-data-preserved', body.includes('恢复当日乙改'), 'events still listed');
  const r = await attemptSave('拒绝写入', '2028-02-29 11:00', '2028-02-29 12:00');
  check('r03-unproven-save-refused', r.b.includes('recovery_unproven') || r.b.includes('写入已拒绝'),
    r.b.slice(0, 200));
  check('r03-unproven-input-retained',
    r.kept.title === '拒绝写入' && r.kept.start === '2028-02-29 11:00' && r.kept.end === '2028-02-29 12:00',
    JSON.stringify(r.kept));
} else if (phase === 'consent') {
  // AC-02 tail: after controlled recovery the next real UI write succeeds
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(3000);
  let body = await page.locator('body').innerText();
  check('r02-consent-banner-gone', !body.includes('存储身份未能证明'), body.slice(0, 160));
  check('r02-consent-data-preserved', body.includes('恢复当日乙改'), 'folded events still there');
  await fillAndSave('受控恢复后首写', '2028-02-29 17:00', '2028-02-29 18:00');
  body = await page.locator('body').innerText();
  check('r02-consent-next-write-ok', body.includes('受控恢复后首写') && !body.includes('保存失败'));
} else {
  console.error('unknown phase ' + phase);
  process.exit(2);
}

await browser.close();
console.log('RESULTS ' + JSON.stringify(results));
process.exit(results.some(r => !r.ok) ? 1 : 0);
