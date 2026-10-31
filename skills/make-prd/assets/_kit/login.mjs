// 로그인이 필요한 화면을 뜰 수 있게, 로그인 API로 세션(쿠키)을 받아 Playwright storageState 파일로 저장한다.
// 비밀번호는 환경변수로만 받고 어디에도 쓰지 않는다. 산출 파일은 쿠키라 커밋하지 않는다(.gitignore에 *.storage.json).
//
// 사용:
//   PRD_BASE=https://dev.example.com PRD_LOGIN_API=/api/auth/login PRD_ME_API=/api/me \
//   PRD_ID=<아이디> PRD_PW=<비밀번호> node login.mjs <출력 파일.storage.json>
//
// 로그인 요청 본문 필드명이 다르면 PRD_ID_FIELD(기본 email)·PRD_PW_FIELD(기본 password)로 바꾼다.
// 쿠키가 아니라 토큰을 localStorage에 넣는 앱이면 이 스크립트 대신 화면 폼으로 로그인한 뒤 ctx.storageState()를 저장한다.
import fs from 'node:fs';
import { chromium, executablePath } from './_playwright.mjs';

const {
  PRD_BASE: base, PRD_LOGIN_API: loginApi, PRD_ME_API: meApi,
  PRD_ID: id, PRD_PW: pw, PRD_ID_FIELD: idField = 'email', PRD_PW_FIELD: pwField = 'password',
} = process.env;
const [out] = process.argv.slice(2);
if (!base || !loginApi || !out || !id || !pw) {
  console.error('usage: PRD_BASE=… PRD_LOGIN_API=… [PRD_ME_API=…] PRD_ID=… PRD_PW=… node login.mjs <출력 파일>');
  process.exit(1);
}

const browser = await chromium.launch({ executablePath: executablePath() });
const ctx = await browser.newContext();
// 로그인 API 응답의 Set-Cookie 가 컨텍스트에 그대로 쌓인다(httpOnly 쿠키라 화면 폼을 거칠 필요가 없다)
const res = await ctx.request.post(base + loginApi, { data: { [idField]: id, [pwField]: pw } });
if (!res.ok()) {
  console.error(`로그인 실패 ${res.status()}: ${(await res.text()).slice(0, 200)}`);
  process.exit(1);
}
if (meApi) {
  const me = await ctx.request.get(base + meApi);
  if (!me.ok()) {
    console.error(`세션 확인 실패 ${me.status()} (${meApi})`);
    process.exit(1);
  }
}
await ctx.storageState({ path: out });
fs.chmodSync(out, 0o600);
await browser.close();
console.log(`저장: ${out} (쿠키 ${JSON.parse(fs.readFileSync(out, 'utf8')).cookies.length}개)`);
