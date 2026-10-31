// browser-e2e 헬퍼 — 실행 스크립트(/tmp/e2e-<slug>/run.cjs)에서 require 해 쓴다.
//   const kit = require('<이 파일 절대경로>');
// playwright 는 이 파일이 아니라 실행하는 쪽이 경로를 넘긴다(레포마다 node_modules 위치가 달라서).
//   PLAYWRIGHT=<레포>/node_modules/playwright node run.cjs
// 비밀번호·토큰은 스크립트에 쓰지 않고 환경변수로 받는다.

const fs = require('fs');
const path = require('path');

function playwright() {
  const p = process.env.PLAYWRIGHT;
  if (!p) throw new Error('PLAYWRIGHT=<레포>/node_modules/playwright 환경변수가 필요하다');
  return require(p);
}

/** 브라우저 + 페이지. viewport 기본은 데스크톱(어드민). 모바일 화면이면 { width: 430, height: 900 }. */
async function open({ viewport = { width: 1440, height: 1000 }, locale = 'ko-KR', chromePath } = {}) {
  const { chromium } = playwright();
  const browser = await chromium.launch(chromePath ? { executablePath: chromePath } : {});
  const ctx = await browser.newContext({ viewport, locale });
  const page = await ctx.newPage();
  return { browser, ctx, page };
}

/**
 * 폼 로그인. 함정 두 가지를 막는다.
 *  1) 하이드레이션 전에 fill 하면 입력이 날아간다 → 비밀번호 칸이 보이고 잠깐 더 기다린 뒤 입력
 *  2) 로그인 직후 클라이언트 리다이렉트가 도는 중에 goto 하면 엉뚱한 페이지로 끌려간다
 *     → URL 변화가 아니라 "로그인 성공 신호 응답"(successUrlPart)을 기다린다
 */
async function formLogin(page, { url, idSelector, pwSelector = 'input[type="password"]', id, pw, successUrlPart, settleMs = 3000 }) {
  await page.goto(url);
  await page.waitForSelector(pwSelector, { timeout: 60000 });
  await page.waitForTimeout(1500);
  await page.fill(idSelector, id);
  await page.fill(pwSelector, pw);
  const ok = successUrlPart
    ? page.waitForResponse((r) => r.url().includes(successUrlPart) && r.status() < 400, { timeout: 30000 })
    : page.waitForTimeout(5000);
  await page.keyboard.press('Enter');
  await ok;
  await page.waitForTimeout(settleMs);
}

/**
 * 네트워크 시간표. match(url) 가 true 인 요청의 시작·끝을 진입 시각 기준 ms 로 모은다.
 * reset() 으로 기준 시각을 다시 잡는다(페이지 이동 직후 호출).
 */
function trackRequests(page, match, nameOf = (u) => new URL(u).pathname) {
  const log = [];
  const inflight = new Set();
  let t0 = Date.now();
  let maxInflight = 0;
  page.on('request', (q) => {
    if (!match(q.url())) return;
    inflight.add(q);
    maxInflight = Math.max(maxInflight, inflight.size);
    log.push({ t: Date.now() - t0, ev: 'start', name: nameOf(q.url()) });
  });
  const done = (ev) => (q) => {
    if (!match(q.url())) return;
    inflight.delete(q);
    log.push({ t: Date.now() - t0, ev, name: nameOf(q.url()), status: ev === 'end' ? undefined : q.failure()?.errorText });
  };
  page.on('requestfinished', done('end'));
  page.on('requestfailed', done('FAIL'));
  return {
    reset() { t0 = Date.now(); log.length = 0; maxInflight = inflight.size; },
    mark(label) { log.push({ t: Date.now() - t0, ev: '----', name: label }); },
    get maxInflight() { return maxInflight; },
    print() {
      log.sort((a, b) => a.t - b.t).forEach((l) => console.log(String(l.t).padStart(7), l.ev.padEnd(5), l.name, l.status || ''));
      console.log('maxInflight', maxInflight);
    },
    rows: () => [...log].sort((a, b) => a.t - b.t),
  };
}

/**
 * 인위 지연 — 로컬처럼 응답이 즉시 끝나 로딩 상태가 안 보일 때만 쓴다.
 * ⚠️ 이걸 켠 실행의 시간은 "실제 속도"가 아니다. 문서에 반드시 적는다.
 */
async function delayResponses(page, pattern, ms) {
  await page.route(pattern, async (r) => { await new Promise((res) => setTimeout(res, ms)); await r.continue(); });
}

/**
 * 응답 붙잡기(hold gate) — 서버가 빨라 단계 전환을 캡처가 못 따라갈 때 쓴다.
 * 요청을 붙잡아 두고, waitBatch() 로 "새 요청이 quietMs 동안 없음"까지 기다린 뒤 화면을 찍고 release() 한다.
 * 붙잡은 동안 다음 요청이 안 나간다는 것 자체가 "앞 요청이 끝나야 다음"을 확인하는 근거가 된다.
 * ⚠️ 시간 측정 실행과 섞지 않는다 — 캡처 실행은 따로 돌린다.
 */
async function holdGate(page, pattern, nameOf = (u) => new URL(u).pathname) {
  let held = [];
  let lastReq = 0;
  await page.route(pattern, async (r) => {
    lastReq = Date.now();
    await new Promise((res) => held.push({ res, name: nameOf(r.request().url()) }));
    await r.continue();
  });
  return {
    async waitBatch({ quietMs = 1200, timeoutMs = 20000 } = {}) {
      const t = Date.now();
      while (!(held.length && Date.now() - lastReq > quietMs) && Date.now() - t < timeoutMs) await page.waitForTimeout(100);
      return held.map((h) => h.name);
    },
    release() { const b = held; held = []; b.forEach((h) => h.res()); return b.map((h) => h.name); },
    get pending() { return held.length; },
  };
}

/** 전체 페이지 캡처. 파일명은 NN-설명.png. 반환값은 문서에 쓸 상대 경로용 파일명. */
async function snap(page, outDir, file, { fullPage = true } = {}) {
  fs.mkdirSync(outDir, { recursive: true });
  await page.screenshot({ path: path.join(outDir, file), fullPage });
  return file;
}

module.exports = { open, formLogin, trackRequests, delayResponses, holdGate, snap };
