// 개발 서버의 실제 화면을 "정적 HTML + 캡처"로 떠 온다. 목업은 이 HTML 위에 새 기능을 얹어 만든다.
//
// 사용:
//   PRD_BASE=https://dev.example.com node snapshot.mjs <경로|URL> <출력 폴더> [--mobile] [--name asis] [--click <css>] [--fill "<css>=<값>"] [--wait ms]
//   예) node snapshot.mjs /orders ../prd/order-badge/assets --mobile
//   예) node snapshot.mjs / ./assets --name asis-typing --fill 'input[type="search"]=검색어'  (입력 후 드롭다운이 열린 상태)
// 산출: <출력 폴더>/<name>.html (스크립트 제거) + <name>.css (페이지 CSS 전부, url 절대경로화) + <name>.png (전체 페이지)
//
// 환경변수: PRD_BASE(개발 서버 주소) · PRD_STORAGE(로그인 storageState 파일) · PRD_LOGIN_PATH(세션 만료 판정, 기본 /login)
//           PRD_FONT_CSS(file:// 에서 폰트가 CORS로 막힐 때 대신 걸 웹폰트 CSS URL)
import fs from 'node:fs';
import path from 'node:path';
import { chromium, executablePath, PC_WIDTH, MOBILE_WIDTH } from './_playwright.mjs';

const args = process.argv.slice(2);
const flag = (k) => args.includes(k);
const opt = (k, d) => (args.includes(k) ? args[args.indexOf(k) + 1] : d);
const VALUE_OPTS = ['--name', '--fill', '--wait', '--click'];
const [target, outDir] = args.filter((a, i) => !a.startsWith('--') && !VALUE_OPTS.includes(args[i - 1]));
if (!target || !outDir) {
  console.error('usage: node snapshot.mjs <경로|URL> <출력 폴더> [--mobile] [--name asis]');
  process.exit(1);
}

const BASE = process.env.PRD_BASE;
if (!/^https?:/.test(target) && !BASE) {
  console.error('경로만 줄 때는 PRD_BASE=<개발 서버 주소> 가 필요하다');
  process.exit(1);
}
const url = /^https?:/.test(target) ? target : BASE.replace(/\/$/, '') + target;
const name = opt('--name', 'asis');
const mobile = flag('--mobile');
const viewport = { width: mobile ? MOBILE_WIDTH : PC_WIDTH, height: 900 };
const LOGIN_PATH = process.env.PRD_LOGIN_PATH || '/login';

const browser = await chromium.launch({ executablePath: executablePath() });
// 로그인이 필요한 화면은 Playwright storageState 파일 경로를 PRD_STORAGE로 넘긴다 (파일은 커밋하지 않는다)
const ctx = await browser.newContext({
  viewport, locale: 'ko-KR', deviceScaleFactor: 2, isMobile: mobile, hasTouch: mobile,
  storageState: process.env.PRD_STORAGE || undefined,
});
const page = await ctx.newPage();

await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
// 세션이 끊겼으면 로그인 화면으로 튕긴다 → 그 화면을 목업 바탕으로 뜨지 않게 멈춘다
if (process.env.PRD_STORAGE && new URL(page.url()).pathname.startsWith(LOGIN_PATH) && !new URL(url).pathname.startsWith(LOGIN_PATH)) {
  console.error(`세션 만료: ${url} → ${page.url()} (login.mjs 로 세션 파일을 다시 만들어야 한다)`);
  process.exit(2);
}
// 지연 로딩 이미지·카드를 깨우려고 끝까지 한 번 내렸다가 올린다
await page.evaluate(async () => {
  for (let y = 0; y < document.body.scrollHeight; y += 600) { window.scrollTo(0, y); await new Promise((r) => setTimeout(r, 120)); }
  window.scrollTo(0, 0);
});
await page.waitForTimeout(800);

// 먼저 눌러야 열리는 화면(드로어·모달)은 --click 으로 연다. 보이는 요소만 대상
const click = opt('--click', null);
if (click) {
  await page.locator(`${click} >> visible=true`).first().click();
  await page.waitForTimeout(Number(opt('--wait', 600)));
}

// 입력창에 값을 넣은 상태(자동완성·필터 결과)를 뜰 때. 보이는 요소만 대상 (PC/모바일 DOM이 둘 다 있는 화면 대비)
const fill = opt('--fill', null);
if (fill) {
  const i = fill.lastIndexOf('=');
  const input = page.locator(`${fill.slice(0, i)} >> visible=true`).first();
  await input.click();
  await input.pressSequentially(fill.slice(i + 1), { delay: 60 });
  await page.waitForTimeout(Number(opt('--wait', 1500)));
}

fs.mkdirSync(outDir, { recursive: true });
await page.screenshot({ path: path.join(outDir, `${name}.png`), fullPage: true });

const { html, css } = await page.evaluate(async (fontCss) => {
  const abs = (u, base) => { try { return new URL(u, base).href; } catch { return u; } };
  const css = [];
  for (const sheet of document.styleSheets) {
    let text = '';
    try { text = [...sheet.cssRules].map((r) => r.cssText).join('\n'); }
    catch { if (sheet.href) text = await (await fetch(sheet.href)).text(); }
    const base = sheet.href || location.href;
    css.push(text.replace(/url\((['"]?)([^'")]+)\1\)/g, (m, q, u) => (u.startsWith('data:') ? m : `url("${abs(u, base)}")`)));
  }
  document.querySelectorAll('input, textarea').forEach((n) => { if (n.value) n.setAttribute('value', n.value); });
  const doc = document.documentElement.cloneNode(true);
  doc.querySelectorAll('script, link[rel="stylesheet"], link[rel="preload"], link[rel="modulepreload"], style, next-route-announcer, nextjs-portal').forEach((n) => n.remove());
  doc.querySelectorAll('[src]').forEach((n) => n.setAttribute('src', abs(n.getAttribute('src'), location.href)));
  doc.querySelectorAll('[srcset]').forEach((n) => n.setAttribute('srcset', n.getAttribute('srcset').split(',').map((s) => { const [u, w] = s.trim().split(/\s+/); return `${abs(u, location.href)} ${w || ''}`.trim(); }).join(', ')));
  doc.querySelectorAll('a[href]').forEach((n) => n.setAttribute('href', '#'));
  // file:// 로 열면 서버 폰트가 CORS로 막힐 수 있다 → CORS 허용되는 웹폰트 CSS를 함께 건다
  if (fontCss) {
    const font = document.createElement('link');
    font.rel = 'stylesheet';
    font.href = fontCss;
    doc.querySelector('head').appendChild(font);
  }
  const link = document.createElement('link');
  link.rel = 'stylesheet';
  link.href = '__CSS__';
  doc.querySelector('head').appendChild(link);
  return { html: '<!doctype html>\n' + doc.outerHTML, css: css.join('\n') };
}, process.env.PRD_FONT_CSS || '');

const stamp = `<!-- snapshot: ${url} · ${mobile ? `mobile ${MOBILE_WIDTH}` : `pc ${PC_WIDTH}`} · ${new Date().toISOString().slice(0, 10)} -->\n`;
// CSS는 따로 뺀다 — 목업은 이 .css를 링크하고 필요한 마크업만 손으로 옮겨 쓴다 (HTML이 작아야 대화하며 고치기 쉽다)
fs.writeFileSync(path.join(outDir, `${name}.css`), css);
fs.writeFileSync(path.join(outDir, `${name}.html`), stamp + html.replace('__CSS__', `${name}.css`));
console.log(`✔ ${path.join(outDir, name)}.html / .css / .png  (${url})`);
await browser.close();
