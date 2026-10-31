// playwright는 이 폴더에 따로 깔지 않고, 이미 깔린 프론트 레포 등에서 빌려 쓴다.
// PRD_PLAYWRIGHT_FROM=<package.json이 있는 폴더> 로 지정한다. 없으면 이 폴더 기준 일반 resolve를 시도한다.
import { createRequire } from 'node:module';
import path from 'node:path';
import fs from 'node:fs';
import os from 'node:os';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const from = process.env.PRD_PLAYWRIGHT_FROM || here;
let pw;
try {
  pw = createRequire(path.join(from, 'package.json'))('playwright');
} catch {
  console.error(`playwright를 찾지 못했다 (${from}). PRD_PLAYWRIGHT_FROM=<playwright가 깔린 레포 경로> 를 지정한다.`);
  process.exit(1);
}
export const { chromium } = pw;

// playwright 버전과 캐시된 브라우저 버전이 어긋나면 launch가 실패한다 → 캐시에 있는 chromium을 찾아 쓴다.
export function executablePath() {
  if (process.env.CHROMIUM_PATH) return process.env.CHROMIUM_PATH;
  const cache = path.join(os.homedir(), '.cache/ms-playwright');
  if (!fs.existsSync(cache)) return undefined;
  const dirs = fs.readdirSync(cache).filter((d) => /^chromium-\d+$/.test(d)).sort().reverse();
  for (const d of dirs) {
    for (const rel of ['chrome-linux64/chrome', 'chrome-linux/chrome', 'chrome-mac/Chromium.app/Contents/MacOS/Chromium']) {
      const p = path.join(cache, d, rel);
      if (fs.existsSync(p)) return p;
    }
  }
  return undefined;
}

// 뷰포트 폭 — 프로젝트의 PC/모바일 기준에 맞춰 바꾼다
export const PC_WIDTH = Number(process.env.PRD_PC_WIDTH || 1440);
export const MOBILE_WIDTH = Number(process.env.PRD_MOBILE_WIDTH || 430);
