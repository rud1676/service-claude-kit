// 목업 HTML을 상태(state)별로 캡처한다. 상태 목록은 목업의 <body data-states="..."> 에서 읽는다.
//
// 사용:
//   node capture.mjs <mockup.html> [--mobile] [--states asis,tobe] [--selector main] [--prefix m]
// 산출: mockup.html 옆 assets/ 에 NN-<state>.png (번호는 data-states 순서. --prefix는 파일명 앞에 붙는 글자)
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { chromium, executablePath, PC_WIDTH, MOBILE_WIDTH } from './_playwright.mjs';

const args = process.argv.slice(2);
const opt = (k, d) => (args.includes(k) ? args[args.indexOf(k) + 1] : d);
const file = args.find((a, i) => !a.startsWith('--') && !['--states', '--selector', '--prefix'].includes(args[i - 1]));
if (!file) {
  console.error('usage: node capture.mjs <mockup.html> [--mobile] [--states a,b] [--selector css] [--prefix 0]');
  process.exit(1);
}

const mobile = args.includes('--mobile');
const viewport = { width: mobile ? MOBILE_WIDTH : PC_WIDTH, height: 900 };
const outDir = path.join(path.dirname(path.resolve(file)), 'assets');
fs.mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch({ executablePath: executablePath() });
const page = await (await browser.newContext({ viewport, locale: 'ko-KR', deviceScaleFactor: 2, isMobile: mobile })).newPage();
const base = pathToFileURL(path.resolve(file)).href;

await page.goto(base, { waitUntil: 'networkidle' });
const allStates = await page.evaluate(() => (document.body.dataset.states || 'default').split(',').map((s) => s.trim()));
// --states 로 일부만 다시 떠도 파일 번호는 data-states 순서를 따른다 (같은 파일을 덮어쓴다)
const states = opt('--states', null)?.split(',') ?? allStates;
const prefix = opt('--prefix', '');
const selector = opt('--selector', null);

for (const state of states) {
  const i = Math.max(allStates.indexOf(state), 0);
  await page.goto(`${base}?state=${encodeURIComponent(state)}&capture=1`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(400);
  const out = path.join(outDir, `${prefix}${String(i + 1).padStart(2, '0')}-${state}${mobile ? '-m' : ''}.png`);
  if (selector) await page.locator(selector).first().screenshot({ path: out });
  else await page.screenshot({ path: out, fullPage: true });
  console.log('✔', path.relative(process.cwd(), out));
}
await browser.close();
