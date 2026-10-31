---
name: make-prd
description: |
  이슈·아이디어 하나를 놓고 사용자와 대화로 기획하는 스킬. 개발 서버의 실제 화면을 스냅샷으로 떠서
  그 위에 새 기능을 얹은 목업 HTML을 만들고, 상태별 캡처를 박은 prd.md를 기획 폴더 `prd/<slug>/`에 남긴다.
  합의되면 같은 폴더 규칙으로 `plan/<slug>-plan.md`(make-plan 형식)까지 이어간다.
  "이거 기획하자", "이 이슈 기획해줘", "PRD 만들자", "목업으로 보여줘(기획)" 같은 요청이나 /make-prd 로 호출.
user_invocable: true
---

# make-prd — 화면으로 하는 기획

> 한 문장: **실제 서비스 화면 위에 새 기능을 얹은 목업(HTML)을 만들고, 그 캡처를 박은 md로 정리한다.**

> **이 스킬은 "고쳐 쓰는 참고 구현"이다.** 절차(스냅샷 → 목업 → 상태별 캡처 → md)와 도구는 스택과 무관하다. **개발 서버 주소·기획 폴더 위치·로그인 방식·PC/모바일 기준 폭·결정권자**는 프로젝트마다 다르다 — 맨 아래 `프로젝트 커스터마이징` 주석을 채운다.

`$SKILL` = 이 SKILL.md가 있는 디렉토리. `$PRD` = 프로젝트의 기획 폴더(커스터마이징 값, 기본 `./develop`).

## PRD와 plan은 무엇이 다른가

| | `prd/` | `plan/` |
|---|---|---|
| 질문 | **무엇을·왜** 만드나, 유저는 뭘 보게 되나 | **어떻게** 만드나 — 레포·API·DB·STEP |
| 주인공 | 화면(목업)과 유저 시나리오 | 설계 결정·파일·배포·테스트 |
| 형식 | `_kit/prd-template.md` | [`make-plan`](../make-plan/SKILL.md) 형식 |
| 끝나면 | 남긴다 (`status: done` + ✅ 배너) | 남긴다 — STEP 표에 ✅ 표시 |

plan은 PRD가 `agreed`가 된 뒤에만 쓴다. PRD 목업 캡처는 plan에서 **복사하지 않고 링크로** 쓴다 (`../prd/<slug>/assets/…`).

## 순서

0. **기획 폴더 준비(처음 한 번)** — `$PRD/_kit/`이 없으면 만든다:
   ```bash
   mkdir -p $PRD/prd $PRD/plan
   cp -r $SKILL/assets/_kit $PRD/_kit
   [ -f $PRD/README.md ] || cp $SKILL/assets/README.md $PRD/README.md
   grep -qx '*.storage.json' $PRD/.gitignore 2>/dev/null || echo '*.storage.json' >> $PRD/.gitignore
   ```
   `_kit/viewer.html` 맨 위 `TITLE`·`SLACK`을 프로젝트 값으로 바꾼다. playwright가 깔린 레포(보통 프론트)를 `PRD_PLAYWRIGHT_FROM`으로 정한다.
1. **입력 파악** — 이슈 URL이면 `gh issue view`로 본문·코멘트를 읽는다. 관련 화면 경로(프론트 라우트)를 찾는다. slug(kebab-case 영문)를 정해 사용자에게 한 줄로 알린다.
2. **지식 먼저** — 프로젝트의 맥락 문서(`context/`·지식 베이스 등)에서 관련 정의·정책을 찾아 읽는다. 없으면 "지식 베이스에 없음".
3. **AS-IS 스냅샷** — `cd $PRD/_kit && PRD_BASE=<개발 서버> node snapshot.mjs <경로> ../prd/<slug>/assets --name asis` (모바일이 중요하면 `--mobile --name asis-m`도). 캡처를 Read로 열어 보고 "지금 이렇게 생겼다"를 사용자에게 보여준다.
4. **문제 정리 대화** — 누가·언제 불편한지, In/Out 범위를 짧게 묻는다. 한 번에 다 묻지 말고 목업을 먼저 그릴 수 있을 만큼만.
5. **TO-BE 목업 1안** — `assets/asis.html`을 `prd/<slug>/mockup.html`로 복사 → `<body data-states="asis,tobe,…">` → 새 요소를 `class="mk-new" data-note="…"` + `data-show`로 넣고, 빠지는 요소는 `mk-gone`/`data-hide` → 맨 끝에 `<script src="../../_kit/mockup-kit.js"></script>`. CSS 링크는 `assets/asis.css`로 맞춘다.
   - 새 요소는 같은 화면 기존 요소의 클래스를 복사해 조립한다. PC/모바일 DOM이 둘 다 있는 화면이면 **보이는 쪽**에 넣는다.
   - 갈림길이 있으면 `tobe-a`, `tobe-b` 상태로 나란히.
6. **캡처** — `node capture.mjs ../prd/<slug>/mockup.html [--selector …] [--mobile]` → 생긴 png를 **Read로 직접 열어 확인**.
7. **prd.md** — `_kit/prd-template.md`를 복사해 채운다. 이미지는 마크다운 문법, 결정 표에 고른 것·버린 것·이유, 못 정한 건 ⏳.
8. **보여주기** — 기획 폴더에서 `python3 -m http.server <포트> --bind 0.0.0.0`이 없으면 띄우고 뷰어 링크를 준다: `<공개 주소>/_kit/viewer.html?prd=<slug>`
9. **반복** — 피드백마다 목업 수정 → 재캡처 → prd.md 갱신(대화 기록에 한 줄). md와 목업이 어긋난 채로 턴을 끝내지 않는다.
10. **합의되면** — `status: agreed`. 사용자가 원하면 [`make-plan`](../make-plan/SKILL.md)을 `문서: plan`, `저장 경로: $PRD/plan/<slug>-plan.md`, `화면 재료: ../prd/<slug>/assets/` 로 호출하고 PRD `status: planned`, `plan:` 칸을 채운다.
11. **구현·적용 추적** — STEP이 커밋·배포될 때마다 git·`gh`로 확인한 사실만으로 갱신한다: plan STEP 표 `상태` 칸(⬜ 대기 / 🚧 진행 / ✅ dev `<sha>` / ✅✅ live), PRD `status`(`building`→`done`)·`note`·`dev_applied`·`live_applied`(`server#172 2026-10-25` 형식). `done`은 운영 반영까지 끝났을 때만이고, PRD 맨 위에 `> ✅ **완료 — live 반영 YYYY-MM-DD**` 배너를 붙인다. 접으면 `dropped` + `> 🗑 **접음 — <이유>**`. 완료돼도 지우지 않는다.

## 기획 가이드라인

### 1. 화면이 먼저다

- **모든 기획에는 목업이 있다.** "버튼 하나 추가"여도 실제 화면 위에 그린다. 화면이 없는 기능(배치·API만)이면 그 결과가 **드러나는 화면**(어드민 표, 프론트 숫자)을 목업으로 그린다.
- 목업은 **실제 화면에서 출발한다** — 상상으로 새로 그리지 않는다.
- 스냅샷은 **PC와 모바일을 따로** 뜬다(기본 1440 / 430, `PRD_PC_WIDTH`·`PRD_MOBILE_WIDTH`). 반응형 앱 중에는 PC·모바일 마크업이 DOM에 둘 다 있고 CSS로 하나를 숨기는 경우가 많다 → 새 요소는 그 뷰포트에서 **보이는 쪽** 트리에 넣는다.
- 목업은 **PC·모바일을 한 파일에** 담는다. 모바일이 따로 그려지는 화면은 모바일 스냅샷에서 마크업을 가져오고, 프로젝트 브레이크포인트로 `@media` 블록을 나눈다.
- 처음 보는 영역(새 페이지·새 모달)은 같은 화면 기존 요소(카드·버튼·탭)의 클래스를 복사해 조립한다. 색·폰트는 프로젝트 디자인 토큰(예: tailwind 설정)을 쓴다.
- 목업 숫자는 **그럴듯한 예시값**이다. 근거 있는 값(운영 DB·지식 베이스)을 쓰면 캡션에 출처를, 아니면 "예시값"이라고 적는다.

### 2. 바뀌는 곳을 눈에 보이게 (`mockup-kit.js`)

| 하고 싶은 것 | 쓰는 법 |
|---|---|
| 새로 생기는 요소 | `class="mk-new" data-note="주간 배지"` → 주황 점선 + `NEW · 주간 배지` 태그 |
| 태그가 위 요소에 가려질 때 | `data-note-pos="bottom"` |
| 빠지는 요소 (비교용) | `class="mk-gone"` → 빨간 점선·흐리게. TO-BE에선 `data-hide`로 실제로 뺀다 |
| 상태 여러 개 | `<body data-states="asis,tobe,tobe-empty">` + 요소에 `data-show="tobe"` / `data-hide="asis"` |
| 상태 바꿔 보기 | `?state=tobe` 또는 화면 아래 상태 바 |

**상태로 그릴 것**: AS-IS · TO-BE 기본 · 데이터 없음 · 로그인 전/후 · 에러 · 모바일. 기획에서 갈리는 경우의 수마다 하나씩.

### 3. 캡처해서 md에 박는다

- `capture.mjs`가 상태마다 `assets/NN-<state>.png`(모바일은 `-m`)를 만든다. **바뀐 영역만** 보이게 `--selector`로 자르는 걸 기본으로 한다(전체 페이지는 한 장이면 충분).
- 캡처는 **Read로 직접 열어 보고** 의도대로 나왔는지 확인한 뒤 md에 넣는다.
- md 이미지는 **마크다운 문법**(`![설명](assets/01-tobe.png)`)으로 건다. HTML `<img>`·`<details>`는 Obsidian 등에서 깨지므로 쓰지 않는다. 나란히 비교는 표 칸에 이미지를 넣는다.

### 4. 기획서(prd.md)

순서는 **화면 → 왜 → 무엇 → 동작 → 결정**.

- 맨 위 **한 줄 요약**과 §0 화면만 읽어도 무엇을 만드는지 알 수 있어야 한다.
- 범위는 **In / Out**을 같이 적는다. "이번엔 안 하는 것"이 기획의 절반이다.
- 경우의 수(로그인×데이터 유무 등)는 문장 말고 **표**로.
- 갈렸던 판단은 §결정 표에 **고른 것·버린 것·이유**. 못 정한 건 `⏳`, 결정권자에게 물을 것은 "물을 사람: <결정권자>"로 표시만 한다 — 기획서에서 도메인 정의·정책을 새로 확정하지 않는다.
- 문장은 짧게, 셀 하나에 사실 하나.

### 5. 대화 방식

- 이슈를 받으면 **먼저 AS-IS 화면을 떠서** 보여주고 "지금 이렇게 생겼다"에서 출발한다.
- 목업은 한 번에 완성하지 않는다. **TO-BE 1안을 빨리** 보여주고 대화로 고친다. 갈림길은 **A안·B안을 나란히** 캡처한다.

## 도구 (`$PRD/_kit/`)

| 도구 | 하는 일 |
|---|---|
| `snapshot.mjs <경로\|URL> <폴더> [--mobile] [--name] [--click css] [--fill "css=값"] [--wait ms]` | 개발 화면을 정적 HTML + `.css` + 전체 캡처로 저장. `--click`으로 드로어·모달을 열고 `--fill`로 입력한 상태(자동완성)를 뜬다 |
| `capture.mjs <mockup.html> [--mobile] [--states a,b] [--selector css] [--prefix]` | `data-states`의 상태마다 캡처 → `assets/NN-<state>.png` |
| `login.mjs <출력 파일>` | 로그인 API로 세션 쿠키를 받아 storageState 저장 → `PRD_STORAGE`로 넘긴다 |
| `mockup-kit.js` | 상태 전환·NEW 표시 |
| `viewer.html` | 왼쪽 prd.md, 오른쪽 살아있는 목업 + 프론트매터로 만든 기획 목록 |
| `prd-template.md` | PRD 뼈대 |

| 환경변수 | 뜻 |
|---|---|
| `PRD_BASE` | 개발 서버 주소 (경로만 줄 때 필수) |
| `PRD_PLAYWRIGHT_FROM` | playwright가 깔린 레포 경로 (보통 프론트) |
| `PRD_STORAGE` | 로그인 storageState 파일 — **커밋 금지** |
| `PRD_LOGIN_PATH` | 세션 만료 판정용 로그인 화면 경로 (기본 `/login`) |
| `PRD_PC_WIDTH` · `PRD_MOBILE_WIDTH` | 캡처 뷰포트 폭 (기본 1440 · 430) |
| `PRD_FONT_CSS` | `file://`에서 서버 폰트가 CORS로 막힐 때 대신 걸 웹폰트 CSS URL |
| `CHROMIUM_PATH` | 브라우저 직접 지정 (기본은 `~/.cache/ms-playwright`에서 찾는다) |

- 스냅샷의 이미지는 개발 서버 URL을 그대로 가리킨다. 시간이 지나면 깨질 수 있지만 **기록은 png 캡처가 남긴다.**
- 스냅샷 여러 장이 같은 CSS 번들이면 `.css` 하나만 남기고 HTML 링크를 그쪽으로 돌린다.

## 셀프 체크 (PRD를 보여주기 전)

- [ ] 목업이 개발 서버 스냅샷에서 출발했다
- [ ] 바뀐 곳마다 `mk-new`/`mk-gone` 표시가 있다
- [ ] `data-states`의 상태마다 캡처가 있고, 직접 열어 확인했다
- [ ] prd.md의 이미지 경로가 실제로 있다 (`ls assets/`)
- [ ] 이미지는 마크다운 문법이다 (`<img>`·`<details>` 없음)
- [ ] In / Out이 둘 다 있다
- [ ] 못 정한 것은 `⏳`, 결정권자에게 물을 것은 표시돼 있다
- [ ] 비밀번호·토큰·storageState가 들어가지 않았다

## 지키는 것

- 상상으로 화면을 새로 그리지 않는다 — 항상 스냅샷에서 출발.
- 커밋은 사용자가 요청할 때만.
- storageState·비밀번호를 파일이나 문서에 남기지 않는다.
- PRD는 도메인 사실의 확정 근거가 아니다. 결정권자 확인이 필요한 결정은 표시만 한다.

<!-- 프로젝트 커스터마이징 (이 스킬을 설치한 프로젝트에서 채운다):
절차·도구는 보편이지만 아래 값은 프로젝트마다 다르다. 자기 값으로 바꾼다.

- 기획 폴더($PRD): (예: `./develop` 또는 지식 베이스 repo 안 `develop/`)
- 개발 서버(PRD_BASE): (예: `https://dev.example.com`) — 접근 제한(IP 허용 등)이 있으면 적는다
- playwright 빌려 쓸 레포(PRD_PLAYWRIGHT_FROM): (예: `repository/front`)
- 로그인: (login.mjs 용 PRD_LOGIN_API·PRD_ME_API·필드명, 또는 "로그인 화면 없음")
- PC/모바일 기준 폭·브레이크포인트: (예: 1440 / 430, `@media (max-width: 1289px)`)
- 디자인 토큰: (예: 주색 #506CF5, 폰트 Pretendard → PRD_FONT_CSS)
- 뷰어 공개 주소·포트: (예: `http://<호스트>:3000`)
- 결정권자: (예: 대표)
- 배포 반영 확인 방법: (예: dev = main 머지 + 배포 워크플로우 성공, live = stage 반영)
- 골드 샘플 PRD: (잘 쓴 prd.md 경로가 생기면)
-->
